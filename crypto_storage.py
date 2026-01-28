# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# Centralized helpers for encrypting and decrypting files at rest.
#
# This module implements a simple, explicit encryption model suitable for
# offline-first desktop use with sensitive medical records.
#
# Includes:
# - Generation and management of a File Master Key (FMK)
# - Wrapping/unwrapping the FMK using a password-derived key
# - Fernet-based encryption and decryption helpers for raw file bytes
#
# Design Notes:
# - Encrypted files are stored on disk as *.enc
# - The File Master Key is stored encrypted ("wrapped") inside SQLCipher
# - The database password is used only to unwrap the FMK at runtime
# - No plaintext keys or files are persisted to disk
#
# Non-Goals (by design):
# - Key recovery or password reset (handled at a higher layer)
# - Cloud key storage or synchronization
# - Transparent file system access (decryption is always explicit)
# -----------------------------------------------------------------------------

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DEFAULT_KDF_ITERS = 390_000


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def _derive_wrapping_fernet_key(password: str, salt: bytes, iters: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iters,
    )
    raw = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def get_or_create_file_master_key(conn, db_password: str) -> bytes:
    """
    Returns the decrypted File Master Key (a Fernet key, base64 bytes).
    Stores a wrapped version in SQLCipher app_settings.
    """
    if not db_password:
        raise ValueError("db_password is required to unwrap the file master key.")

    cur = conn.cursor()

    cur.execute("SELECT value FROM app_settings WHERE key=?", ("crypto.fmk_wrapped_b64",))
    wrapped_row = cur.fetchone()

    cur.execute("SELECT value FROM app_settings WHERE key=?", ("crypto.fmk_salt_b64",))
    salt_row = cur.fetchone()

    cur.execute("SELECT value FROM app_settings WHERE key=?", ("crypto.kdf_iters",))
    iters_row = cur.fetchone()

    iters = int(iters_row[0]) if iters_row and iters_row[0] else DEFAULT_KDF_ITERS
    if iters < 100_000:
        iters = DEFAULT_KDF_ITERS

    # Guardrail: refuse to regenerate keys if settings are partially present.
    # This avoids making existing encrypted files unreadable.
    if (wrapped_row is None) != (salt_row is None):
        raise RuntimeError(
            "Encryption key settings are incomplete (salt/wrapped key mismatch). "
            "Refusing to generate a new key to avoid making existing encrypted files unreadable."
        )

    # First run: generate + store
    if wrapped_row is None and salt_row is None:
        salt = os.urandom(16)
        fmk = Fernet.generate_key()
        wrap_key = _derive_wrapping_fernet_key(db_password, salt, iters)
        wrapper = Fernet(wrap_key)
        wrapped = wrapper.encrypt(fmk)

        cur.execute(
            """INSERT INTO app_settings(key, value) VALUES(?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            ("crypto.fmk_salt_b64", _b64e(salt)),
        )
        cur.execute(
            """INSERT INTO app_settings(key, value) VALUES(?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            ("crypto.fmk_wrapped_b64", _b64e(wrapped)),
        )
        cur.execute(
            """INSERT INTO app_settings(key, value) VALUES(?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            ("crypto.kdf_iters", str(iters)),
        )
        conn.commit()
        return fmk

    # Existing: unwrap
    salt = _b64d(salt_row[0])
    wrapped = _b64d(wrapped_row[0])
    wrap_key = _derive_wrapping_fernet_key(db_password, salt, iters)
    wrapper = Fernet(wrap_key)

    try:
        return wrapper.decrypt(wrapped)
    except InvalidToken as ex:
        raise RuntimeError(
            "Unable to unlock file encryption key. "
            "This usually means the database password is incorrect or the stored key is corrupted."
        ) from ex


def encrypt_bytes(fmk: bytes, plaintext: bytes) -> bytes:
    return Fernet(fmk).encrypt(plaintext)


def decrypt_bytes(fmk: bytes, ciphertext: bytes) -> bytes:
    return Fernet(fmk).decrypt(ciphertext)