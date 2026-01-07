# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

import flet as ft
from database import init_db, create_profile, get_profile, update_profile

def main(page: ft.Page):
    page.title = "Local Patient Advocate"
    page.window_width = 1000
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # --- STATE ---
    # Store the current profile data here once loaded
    # Format: (id, name, dob, notes)
    page.current_profile = None 

    # --- UI COMPONENTS ---
    
    # LOGIN SCREEN
    error_text = ft.Text(color=ft.Colors.RED, visible=False)
    password_field = ft.TextField(
        label="Database Password", 
        password=True, 
        can_reveal_password=True,
        on_submit=lambda e: attempt_login(e)
    )

    # PROFILE FORM (Used for both creating and editing)
    name_input = ft.TextField(label="Full Name", width=400)
    dob_input = ft.TextField(label="Date of Birth (YYYY-MM-DD)", width=400)
    notes_input = ft.TextField(label="Medical Notes / Conditions", multiline=True, width=400, height=150)

    # --- ACTIONS ---

    def attempt_login(e):
        try:
            if not password_field.value:
                raise ValueError("Please enter a password.")
            
            page.db_connection = init_db(password_field.value)
            
            # Login Success! Now check if we have a profile.
            load_dashboard_logic()
            
        except Exception as ex:
            print(f"CRITICAL ERROR: {ex}") 
            error_text.value = f"Error: {str(ex)}"
            error_text.visible = True
            page.update()

    def load_dashboard_logic():
        """ Decides whether to show the 'Create Profile' form or the 'Dashboard' """
        page.clean()
        
        # Check database for a profile
        page.current_profile = get_profile(page.db_connection)
        
        if page.current_profile is None:
            show_create_profile_view()
        else:
            show_main_dashboard()

        page.update()

    def save_profile_click(e):
        try:
            print("Attempting to create profile...") # Debug print
            if not name_input.value:
                raise ValueError("Name is required")
            
            # Create the profile in SQL
            create_profile(page.db_connection, name_input.value, dob_input.value, notes_input.value)
            print("Profile created in DB. Loading dashboard...") # Debug print
            
            # Try to load the UI
            load_dashboard_logic() 
            print("Dashboard loaded.") # Debug print
            
        except Exception as ex:
            # THIS IS THE KEY PART: Print the error to the terminal
            print(f"CRITICAL DASHBOARD ERROR: {ex}")
            import traceback
            traceback.print_exc()
            
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    def edit_mode_toggle(e):
        """ Switch back to the form to edit details """
        # Pre-fill the form with current data
        name_input.value = page.current_profile[1]
        dob_input.value = page.current_profile[2]
        notes_input.value = page.current_profile[3]
        
        # Override the save button to UPDATE instead of CREATE
        def update_click(ev):
            update_profile(page.db_connection, page.current_profile[0], name_input.value, dob_input.value, notes_input.value)
            load_dashboard_logic()

        page.clean()
        page.add(
            ft.Column([
                ft.Text("Edit Profile", size=30, weight="bold"),
                name_input,
                dob_input,
                notes_input,
                ft.Button("Save Changes", on_click=update_click),
                ft.Button("Cancel", on_click=lambda _: load_dashboard_logic(), color="red")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # --- VIEWS ---

    def show_create_profile_view():
        """ The Onboarding Screen """
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.PERSON_ADD, size=64, color=ft.Colors.BLUE),
                    ft.Text("Welcome!", size=30, weight="bold"),
                    ft.Text("Let's set up the primary patient profile.", size=16),
                    ft.Divider(),
                    name_input,
                    dob_input,
                    notes_input,
                    ft.Button("Create Profile", on_click=save_profile_click)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        )

    def show_main_dashboard():
        """ The Single-User Unified Interface """
        # Unpack data for readability
        p_name = page.current_profile[1]
        p_dob = page.current_profile[2]
        p_notes = page.current_profile[3]

        page.add(
            ft.Row([
                # SIDEBAR (Navigation)
                ft.NavigationRail(
                    selected_index=0,
                    destinations=[
                        ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Overview"),
                        ft.NavigationRailDestination(icon=ft.Icons.FOLDER, label="Documents"),
                        ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
                    ]
                ),
                ft.VerticalDivider(width=1),
                
                # MAIN CONTENT AREA
                ft.Container(
                    padding=20,  # Apply padding here instead
                    expand=True,
                    content=ft.Column([
                        # Header: The Patient Card
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_GREY),
                                ft.Column([
                                    ft.Text(p_name, size=30, weight="bold"),
                                    ft.Text(f"DOB: {p_dob}", size=16, color="grey"),
                                ]),
                                ft.Container(expand=True), # Spacer
                                ft.IconButton(ft.Icons.EDIT, tooltip="Edit Profile", on_click=edit_mode_toggle)
                            ]),
                            padding=20,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=10
                        ),
                        
                        ft.Divider(),
                        
                        # Body: The Medical Notes (Read Only)
                        ft.Text("Medical Summary / Notes", weight="bold", size=18),
                        ft.Container(
                            content=ft.Text(p_notes, size=16),
                            padding=15,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5,
                            expand=True 
                        )
                    ], expand=True)
                )
            ], expand=True)
        )

    # --- STARTUP ---
    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.SECURITY, size=64, color=ft.Colors.BLUE),
                ft.Text("Secure Login", size=30),
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