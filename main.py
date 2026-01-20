# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# App entry point and UI shell for Local Patient Advocate.
#
# Responsibilities:
# - Initializes the Flet page/window and app-wide state (db connection, profile,
#   accessibility flags, UI scale)
# - Handles secure login and database initialization
# - Loads and applies persisted UI settings (theme mode, high contrast, large text)
#   and refreshes the active view immediately when settings change
# - Provides top-level navigation (NavigationRail) and routes to view modules
#   (Overview / Patient Info / Documents / Settings)
# - Centralizes error handling for view loading and critical startup failures
# -----------------------------------------------------------------------------

import flet as ft
import traceback
from database import init_db, get_profile, get_setting

# Import your views
from views.documents import get_documents_view
from views.overview import get_overview_view
from views.patient_info import get_patient_info_view
from views.settings import get_settings_view

def main(page: ft.Page):
    page.title = "Local Patient Advocate"
    page.window.width = 1000
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.SYSTEM

    # --- STATE ---
    page.current_profile = None
    page.db_connection = None
    page.is_high_contrast = False
    page.ui_scale = 1.0


    # --- MAIN LOGIC ---
    def apply_settings():
        if not page.db_connection: return
        
        try:
            theme_pref = get_setting(page.db_connection, "ui.theme", "system")
            high_contrast = get_setting(page.db_connection, "ui.high_contrast", "0") == "1"
            large_text = get_setting(page.db_connection, "ui.large_text", "0") == "1"

            page.theme_mode = {
                "dark": ft.ThemeMode.DARK,
                "light": ft.ThemeMode.LIGHT,
                "system": ft.ThemeMode.SYSTEM
            }.get(theme_pref, ft.ThemeMode.SYSTEM)

            if high_contrast:
                page.theme = ft.Theme(color_scheme_seed=ft.Colors.YELLOW)
            else:
                page.theme = None
                
            page.is_high_contrast = high_contrast
            page.ui_scale = 1.25 if large_text else 1.0
            
            # Refresh UI if active
            if hasattr(page, "nav_rail") and page.nav_rail:
                idx = page.nav_rail.selected_index
                page.content_area.content = get_view_for_index(idx)
                page.content_area.update()
                
            page.update()
        except Exception as e:
            print(f"Settings Error: {e}")

    def get_view_for_index(index):
        try:
            # 0: Overview
            if index == 0: 
                return get_overview_view(page)
            # 1: Patient Info
            elif index == 1: 
                return get_patient_info_view(page)
            # 2: Documents
            elif index == 2: 
                return get_documents_view(page)
            # 3: Settings
            elif index == 3: 
                return get_settings_view(page, apply_settings_callback=apply_settings)
            
            return ft.Text("Unknown View")
        except Exception as ex:
            return ft.Column([
                ft.Icon(ft.Icons.ERROR, color="red", size=40),
                ft.Text(f"Error loading view #{index}:", color="red", weight="bold"),
                ft.Text(str(ex), color="red"),
                ft.Text(traceback.format_exc(), size=10, font_family="Consolas")
            ], scroll=True)

    def show_main_dashboard():
        try:
            page.clean()
            content_area = ft.Container(expand=True, padding=20)
            page.content_area = content_area

            def nav_change(e):
                content_area.content = get_view_for_index(e.control.selected_index)
                content_area.update()

            rail = ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=200,
                destinations=[
                    ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Overview"),
                    ft.NavigationRailDestination(icon=ft.Icons.BADGE, label="Patient Info"),
                    ft.NavigationRailDestination(icon=ft.Icons.FOLDER, label="Documents"),
                    ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
                ],
                on_change=nav_change,
            )
            page.nav_rail = rail
            
            # Initial load
            content_area.content = get_view_for_index(0)

            page.add(
                ft.Row([rail, ft.VerticalDivider(width=1), content_area], expand=True)
            )
            page.update()
            
        except Exception as ex:
            page.clean()
            page.add(ft.Text(f"CRITICAL ERROR: {ex}", color="red"))
            page.update()

    def attempt_login(e):
        try:
            pwd = password_field.value
            if not pwd: return
            
            page.db_connection = init_db(pwd)
            apply_settings()
            page.current_profile = get_profile(page.db_connection)
            show_main_dashboard()
                
        except Exception as ex:
            error_text.value = f"Login Error: {str(ex)}"
            error_text.visible = True
            page.update()
            print(traceback.format_exc())

    # --- STARTUP UI ---
    password_field = ft.TextField(label="Database Password", password=True, on_submit=attempt_login)
    error_text = ft.Text(color="red", visible=False)

    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.SECURITY, size=64, color="blue"),
                ft.Text("Secure Login", size=30),
                password_field,
                ft.Button("Unlock Database", on_click=attempt_login),
                error_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

if __name__ == "__main__":
    ft.run(main)