# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import flet as ft
from database import init_db

def main(page: ft.Page):
    # 1. Setup the window
    page.title = "Local Patient Advocate"
    page.window_width = 800
    page.window_height = 600
    
    # --- UI COMPONENTS ---
    
    # Create the error text (hidden at first)
    error_text = ft.Text(color=ft.Colors.RED, visible=False)
    
    # Create the password box
    password_field = ft.TextField(
        label="Database Password", 
        password=True, 
        can_reveal_password=True
    )

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
        page.add(
            ft.Row([
                ft.NavigationRail(
                    selected_index=0,
                    destinations=[
                        ft.NavigationRailDestination(icon=ft.Icons.PEOPLE, label="Patients"),
                        ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
                    ]
                ),
                ft.VerticalDivider(width=1),
                ft.Column([
                    ft.Text("Welcome to the Dashboard", size=30),
                    ft.Text("Database is connected.", color="green")
                ])
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