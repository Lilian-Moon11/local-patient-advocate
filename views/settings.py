# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# Handles App-wide preferences.
# When a user changes a setting here, it updates the DB *and* triggers
# a callback to 'main.py' to re-apply the theme immediately.
# -----------------------------------------------------------------------------

import flet as ft
from database import get_setting, set_setting
from utils import s, show_snack

def get_settings_view(page: ft.Page, apply_settings_callback):
    """
    Args:
        page: The Flet page object.
        apply_settings_callback: A function passed from main.py that re-runs 
                                 'apply_settings()' to refresh the theme instantly.
    """

    # 1. Load current values from DB (or defaults)
    current_theme = get_setting(page.db_connection, "ui.theme", "system")
    is_high_contrast = get_setting(page.db_connection, "ui.high_contrast", "0") == "1"
    is_large_text = get_setting(page.db_connection, "ui.large_text", "0") == "1"

    # 2. Define Controls
    theme_dd = ft.Dropdown(
        label="Theme",
        width=300,
        options=[
            ft.dropdown.Option("system", "System default"),
            ft.dropdown.Option("light", "Light"),
            ft.dropdown.Option("dark", "Dark"),
        ],
        value=current_theme,
    )

    hc_switch = ft.Switch(label="High contrast", value=is_high_contrast)
    lt_switch = ft.Switch(label="Large text", value=is_large_text)

    # 3. Logic: Save and Apply
    def save_settings(e):
        # Save to DB
        set_setting(page.db_connection, "ui.theme", theme_dd.value)
        set_setting(page.db_connection, "ui.high_contrast", "1" if hc_switch.value else "0")
        set_setting(page.db_connection, "ui.large_text", "1" if lt_switch.value else "0")
        
        # Trigger the visual update in main.py
        apply_settings_callback()
        
        show_snack(page, "Settings saved.", "green")

    def reset_settings(e):
        # Reset DB
        set_setting(page.db_connection, "ui.theme", "system")
        set_setting(page.db_connection, "ui.high_contrast", "0")
        set_setting(page.db_connection, "ui.large_text", "0")

        # Reset Controls
        theme_dd.value = "system"
        hc_switch.value = False
        lt_switch.value = False
        page.update()

        # Trigger visual update
        apply_settings_callback()
        show_snack(page, "Defaults restored.", "blue")

    # 4. Return Layout
    return ft.Container(
        padding=s(page, 20),
        content=ft.Column(
            [
                ft.Text("Settings", size=s(page, 24), weight="bold"),
                ft.Divider(),
                theme_dd,
                hc_switch,
                lt_switch,
                ft.Row([
                    ft.Button("Save Settings", icon=ft.Icons.SAVE, on_click=save_settings),
                    ft.Button("Reset Defaults", icon=ft.Icons.RESTART_ALT, on_click=reset_settings),
                ]),
                ft.Divider(),
                ft.Text(
                    "Note: High Contrast mode overrides the Theme selection.", 
                    color=ft.Colors.GREY, 
                    size=s(page, 14)
                )
            ]
        )
    )