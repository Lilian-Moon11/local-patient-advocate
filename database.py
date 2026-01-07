# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

from sqlcipher3 import dbapi2 as sqlite3 
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource for dev and .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def init_db(input_password):
    """ Initialize DB and check password """
    db_path = resource_path("medical_records_v1.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    # --- FIX: Set the Key FIRST, before doing anything else ---
    cursor.execute(f"PRAGMA key = '{input_password}';")
    
    # Try to read the database to verify password is correct
    try:
        cursor.execute("SELECT count(*) FROM sqlite_master;")
    except Exception:
        conn.close()
        raise ValueError("Invalid Password or Corrupted Database.")

    # --- NOW it is safe to create tables ---
    
    # Security Table (Optional now, but keeping for legacy compatibility)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security (
            id INTEGER PRIMARY KEY,
            password_hash TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dob TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            file_name TEXT,
            file_path TEXT,
            parsed_text TEXT,
            upload_date TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)
    
    conn.commit()
    return conn

def create_profile(conn, name, dob, notes):
    """ Create the primary user profile """
    cursor = conn.cursor()
    cursor.execute("INSERT INTO patients (name, dob, notes) VALUES (?, ?, ?)", (name, dob, notes))
    conn.commit()

def get_profile(conn):
    """ 
    Get the SINGLE primary profile. 
    Returns None if no profile exists yet.
    """
    cursor = conn.cursor()
    # We limit to 1 because we are focusing on a single user interface right now
    cursor.execute("SELECT id, name, dob, notes FROM patients LIMIT 1")
    return cursor.fetchone()

def update_profile(conn, profile_id, name, dob, notes):
    """ Update the existing profile """
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET name=?, dob=?, notes=? WHERE id=?", (name, dob, notes, profile_id))
    conn.commit()

def add_document(conn, patient_id, file_name, file_path, upload_date):
    """ Save a document reference to the database """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (patient_id, file_name, file_path, upload_date)
        VALUES (?, ?, ?, ?)
    """, (patient_id, file_name, file_path, upload_date))
    conn.commit()

def get_patient_documents(conn, patient_id):
    """ Retrieve all documents for a specific patient """
    cursor = conn.cursor()
    cursor.execute("SELECT file_name, upload_date, file_path FROM documents WHERE patient_id = ?", (patient_id,))
    return cursor.fetchall()