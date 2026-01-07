import sqlite3
import os
import sys
import hashlib

def resource_path(relative_path):
    """ Get absolute path to resource for development and for PyInstaller (the .exe file). """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def init_db(input_password):
    """
    Connects to the database.
    - If it's the first run, it sets the password.
    - If it's a subsequent run, it checks the password.
    """
    
    # Use resource_path to ensure we find the DB even if packaged later
    db_path = resource_path("patients.db")
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    # Create a hidden table to store the password hash (simulated security)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security (
            id INTEGER PRIMARY KEY,
            password_hash TEXT
        )
    """)
    
    # Check if a password has been set previously
    cursor.execute("SELECT password_hash FROM security WHERE id = 1")
    stored_data = cursor.fetchone()

    # Hash the input password for comparison
    input_hash = hashlib.sha256(input_password.encode()).hexdigest()

    if stored_data is None:
        # CASE 1: First time run (Setup)
        cursor.execute("INSERT INTO security (id, password_hash) VALUES (1, ?)", (input_hash,))
        conn.commit()
    else:
        # CASE 2: Login attempt
        stored_hash = stored_data[0]
        if input_hash != stored_hash:
            conn.close()
            raise ValueError("Invalid Password.")
    
    # If we get here, login was successful
    # Ensure patient table exists for the dashboard
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dob TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    
    return conn

def add_patient(conn, name, dob, notes):
    """ Save a new patient to the database """
    cursor = conn.cursor()
    cursor.execute("INSERT INTO patients (name, dob, notes) VALUES (?, ?, ?)", (name, dob, notes))
    conn.commit()

def get_patients(conn):
    """ Get all patients to display in a list """
    cursor = conn.cursor()
    cursor.execute("SELECT name, dob FROM patients")
    return cursor.fetchall()