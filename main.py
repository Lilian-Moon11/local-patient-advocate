# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import flet as ft
from database import init_db, add_patient, get_patients

def main(page: ft.Page):
    # 1. Setup the window
    page.title = "Local Patient Advocate"
    page.window_width = 1000
    page.window_height = 800
    
    # --- UI COMPONENTS ---
    
    # Create the error text (hidden at first)
    error_text = ft.Text(color=ft.Colors.RED, visible=False)
    
    # Create the password box
    password_field = ft.TextField(
        label="Database Password", 
        password=True, 
        can_reveal_password=True
    )

    # DASHBOARD COMPONENTS (The Form)
    name_input = ft.TextField(label="Patient Name", width=300)
    dob_input = ft.TextField(label="Date of Birth (YYYY-MM-DD)", width=300)
    notes_input = ft.TextField(label="Medical Notes", multiline=True, width=300)
    
    # The list where we will show saved patients
    patient_list_view = ft.ListView(expand=True, spacing=10)

    # --- ACTIONS ---

    def refresh_patient_list():
        """ clear the list and re-fetch from database """
        patient_list_view.controls.clear()
        patients = get_patients(page.db_connection)
        for p in patients:
            # p[0] is name, p[1] is dob
            patient_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PERSON),
                    title=ft.Text(p[0]),
                    subtitle=ft.Text(f"DOB: {p[1]}")
                )
            )
        page.update()

    def save_patient_click(e):
        try:
            if not name_input.value:
                raise ValueError("Name is required")
            
            # Save to database
            add_patient(page.db_connection, name_input.value, dob_input.value, notes_input.value)
            
            # Clear inputs
            name_input.value = ""
            dob_input.value = ""
            notes_input.value = ""
            
            # Show success and refresh list
            page.snack_bar = ft.SnackBar(ft.Text("Patient Saved!"))
            page.snack_bar.open = True
            
            refresh_patient_list()
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # Define what happens when you click "Unlock"
    def attempt_login(e):
        try:
            if not password_field.value:
                raise ValueError("Please enter a password.")
            
            # Connect to DB
            page.db_connection = init_db(password_field.value)
            
            # CLEAR the screen and show the Dashboard
            page.clean()
            show_dashboard()
            
        except Exception as ex:
            error_text.value = f"Error: {str(ex)}"
            error_text.visible = True
            page.update()

    # Define the Dashboard (We show this only after login)
    def show_dashboard():
        # Load any existing patients immediately
        refresh_patient_list()
        
        page.add(
            ft.Row([
                # Sidebar (Visual only for now)
                ft.NavigationRail(
                    selected_index=0,
                    destinations=[
                        ft.NavigationRailDestination(icon=ft.Icons.PEOPLE, label="Patients"),
                        ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
                    ]
                ),
                ft.VerticalDivider(width=1),
                
                # Main Content Area
                ft.Row([
                    # LEFT COLUMN: Input Form
                    ft.Column([
                        ft.Text("Add New Patient", size=20, weight="bold"),
                        name_input,
                        dob_input,
                        notes_input,
                        ft.Button("Save Patient", on_click=save_patient_click)
                    ], alignment=ft.MainAxisAlignment.START, spacing=20),
                    
                    ft.VerticalDivider(width=1),
                    
                    # RIGHT COLUMN: Saved List
                    ft.Column([
                        ft.Text("Saved Records", size=20, weight="bold"),
                        patient_list_view
                    ], expand=True)
                    
                ], expand=True, alignment=ft.MainAxisAlignment.START)
            ], expand=True)
        )
        page.update()

    # --- STARTUP ---
    # Directly add the login controls to the page immediately
    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.SECURITY, size=64, color=ft.Colors.BLUE),
                ft.Text("Secure Login", size=30),
                ft.Text("Enter password to unlock records:"),
                password_field,
                ft.Button("Unlock Database", on_click=attempt_login),
                error_text
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

if __name__ == "__main__":
    ft.run(main)