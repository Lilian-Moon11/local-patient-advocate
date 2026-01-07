import os
import sqlite3
from hashlib import pbkdf2_hmac
import binascii

# Try to import sqlcipher3, but fall back to standard sqlite3 for testing if needed
# Note: Standard sqlite3 will NOT be encrypted, this is just to prevent crash on install errors.
try:
    from sqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    print("WARNING: sqlcipher3 not found. Using standard sqlite3 (NOT ENCRYPTED).")
    import sqlite3 as sqlcipher

DB_FILENAME = "medical_records.db"

def get_derived_key(password: str, salt: bytes) -> str:
    """
    Derives a 64-character hex key from the password using PBKDF2.
    This creates a secure key from the user's password[cite: 83].
    """
    kdf = pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000 # 100,000 iterations for security
    )
    return binascii.hexlify(kdf).decode('utf-8')

def init_db(password: str):
    """
    Initializes the encrypted database connection.
    """
    # In production, salt should be random and stored, but for this local app 
    # we use a fixed application salt to allow the user to recover data with just their password.
    salt = b'local_medical_app_salt' 
    key = get_derived_key(password, salt)

    conn = sqlcipher.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # EXECUTE ENCRYPTION PRAGMA [cite: 84]
    cursor.execute(f"PRAGMA key = '{key}';")
    
    # Try to access the database to verify the key works
    try:
        cursor.execute("SELECT count(*) FROM sqlite_master;")
    except Exception as e:
        conn.close()
        raise ValueError("Invalid password or corrupt database.") from e

    # Create the Patients table (Phase 1 Requirement)
    create_patients_table = """
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        dob TEXT,
        encrypted_notes TEXT
    );
    """
    cursor.execute(create_patients_table)
    conn.commit()
    return conn