# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

import flet as ft
import os
import shutil
import asyncio
from datetime import datetime

# Ensure database.py exists in the same folder
from database import (
    init_db,
    create_profile,
    get_profile,
    update_profile,
    add_document,
    get_patient_documents,
    list_field_definitions,
    ensure_field_definition,
    get_patient_field_map,
    upsert_patient_field_value,
    get_setting,          
    set_setting, 
)


def main(page: ft.Page):
    page.title = "Local Patient Advocate"
    page.window.width = 1000
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.SYSTEM

    # --- STATE ---
    page.current_profile = None
    page.db_connection = None

    # --- UI COMPONENTS ---
    error_text = ft.Text(color=ft.Colors.RED, visible=False)

    # --- HELPERS (Defined early so controls can use them) ---
    def show_snack(message: str, color: str = "green"):
        try:
            page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print("SNACK ERROR:", ex, "| message:", message)

    def s(px: int) -> int:
        return int(px * getattr(page, "ui_scale", 1.0))
    
    def is_dark_mode() -> bool:
        if page.theme_mode == ft.ThemeMode.DARK:
            return True
        if page.theme_mode == ft.ThemeMode.LIGHT:
            return False
        # SYSTEM: best-effort; if not available, default False
        return getattr(page, "platform_brightness", None) == ft.Brightness.DARK

    def themed_panel(content, padding=s(15), radius=6):
        """A theme-safe container that looks good in light/dark, and enforces high-contrast when enabled."""
        hc = (get_setting(page.db_connection, "ui.high_contrast", "0") == "1") if page.db_connection else False

        if hc:
            return ft.Container(
                content=content,
                padding=padding,
                bgcolor=ft.Colors.BLACK,
                border=ft.Border.all(2, ft.Colors.YELLOW),
                border_radius=radius,
            )

        # default (theme-friendly): don't hardcode light colors
        return ft.Container(
            content=content,
            padding=padding,
            bgcolor=None,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT) if hasattr(ft.Colors, "OUTLINE_VARIANT") else None,
            border_radius=radius,
        )

    def apply_settings():
        """Apply theme/accessibility settings from DB to the page."""
        if not page.db_connection:
            return

        theme_pref = get_setting(page.db_connection, "ui.theme", "system")  # system|light|dark
        high_contrast = get_setting(page.db_connection, "ui.high_contrast", "0") == "1"
        large_text = get_setting(page.db_connection, "ui.large_text", "0") == "1"

        # Theme mode
        if theme_pref == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        elif theme_pref == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM  # inherit OS

        # High contrast
        if high_contrast:
            page.theme = ft.Theme(color_scheme_seed=ft.Colors.YELLOW)
        else:
            page.theme = None

        # ✅ Large text: use explicit UI scale (reliable with your hard-coded sizes)
        page.ui_scale = 1.25 if large_text else 1.0

        # ✅ Refresh current view WITHOUT resetting NavigationRail index
        if hasattr(page, "nav_rail") and hasattr(page, "content_area") and page.current_profile is not None:
            idx = page.nav_rail.selected_index
            page.content_area.content = get_view_for_index(idx)
            page.content_area.update()

        page.update()    
        
    def attempt_login(e):
        try:
            if not password_field.value:
                raise ValueError("Please enter a password.")

            page.db_connection = init_db(password_field.value)
            apply_settings()
            load_dashboard_logic()

        except Exception as ex:
            print(f"LOGIN ERROR: {ex}")
            error_text.value = f"Error: {str(ex)}"
            error_text.visible = True
            page.update()

    # --- CONTROLS ---
    password_field = ft.TextField(
        label="Database Password",
        password=True,
        can_reveal_password=True,
        on_submit=lambda e: attempt_login(e),
    )

    name_input = ft.TextField(label="Full Name", width=400)
    dob_input = ft.TextField(label="Date of Birth (YYYY-MM-DD)", width=400)
    notes_input = ft.TextField(
        label="Medical Notes / Conditions", multiline=True, width=400, height=150
    )

    # --- FILE PICKER LOGIC ---
    async def pick_and_save_document(e):
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            dialog_title="Select Medical Record",
    )
        if not files:
            show_snack("No file selected (cancelled).", "orange")
            return

        picked = files[0]
        file_path = getattr(picked, "path", None)

        show_snack(f"Picked: {picked.name}", "blue")

        if not file_path:
            show_snack("Picker returned no local path.", "red")
            return

        save_file_to_system(file_path)

    # --- FILE OPENING ---
    async def open_document(path: str):
        if not path:
            show_snack("No file path found for this document.", "red")
            return
        if not os.path.exists(path):
            show_snack("File not found on disk.", "red")
            return

        # Use forward slashes for file URL compatibility on Windows
        file_url = "file:///" + path.replace("\\", "/")
        await ft.UrlLauncher().launch_url(file_url)

    def open_document_click(e):
        path = e.control.data
        asyncio.create_task(open_document(path))


    # --- BUSINESS LOGIC ---
    def load_dashboard_logic():
        page.clean()
        page.current_profile = get_profile(page.db_connection)

        if page.current_profile is None:
            show_create_profile_view()
        else:
            show_main_dashboard()
        page.update()

    def save_profile_click(e):
        try:
            if not name_input.value:
                raise ValueError("Name is required")

            create_profile(
                page.db_connection,
                name_input.value,
                dob_input.value,
                notes_input.value,
            )
            load_dashboard_logic()

        except Exception as ex:
            show_snack(f"Error: {str(ex)}", "red")

    def save_file_to_system(file_path: str):
        try:
            if not page.current_profile:
                raise ValueError("No patient profile loaded.")

            if not file_path:
                print("Empty file_path, returning")
                return

            patient_id = page.current_profile[0]

            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "data", str(patient_id))
            os.makedirs(storage_path, exist_ok=True)

            file_name = os.path.basename(file_path)
            destination = os.path.join(storage_path, file_name)

            shutil.copy(file_path, destination)

            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            add_document(page.db_connection, patient_id, file_name, destination, upload_date)

            load_dashboard_logic()
            show_snack(f"Successfully uploaded {file_name}", "green")

        except Exception as ex:
            print(f"UPLOAD ERROR: {ex}")
            show_snack(f"Upload Failed: {str(ex)}", "red")

    def edit_mode_toggle(e):
        name_input.value = page.current_profile[1]
        dob_input.value = page.current_profile[2]
        notes_input.value = page.current_profile[3]

        def update_click(ev):
            update_profile(
                page.db_connection,
                page.current_profile[0],
                name_input.value,
                dob_input.value,
                notes_input.value,
            )
            load_dashboard_logic()

        page.clean()
        page.add(
            ft.Column(
                [
                    ft.Text("Edit Profile", size=s(30), weight="bold"),
                    name_input,
                    dob_input,
                    notes_input,
                    ft.Button("Save Changes", on_click=update_click),
                    ft.Button("Cancel", on_click=lambda _: load_dashboard_logic(), color="red"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    # --- VIEWS ---
    def show_create_profile_view():
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.PERSON_ADD, size=s(64), color=ft.Colors.BLUE),
                        ft.Text("Welcome!", size=s(30), weight="bold"),
                        ft.Text("Let's set up the primary patient profile.", size=s(16)),
                        ft.Divider(),
                        name_input,
                        dob_input,
                        notes_input,
                        ft.Button("Create Profile", on_click=save_profile_click),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        )

    def show_patient_info_view():
        patient = page.current_profile
        patient_id = patient[0]

        defs = list_field_definitions(page.db_connection)
        value_map = get_patient_field_map(page.db_connection, patient_id)

        def save_value(field_key: str, tf: ft.TextField, src_text: ft.Text, upd_text: ft.Text):
            upsert_patient_field_value(
                page.db_connection,
                patient_id,
                field_key,
                tf.value or "",
                source="user",
            )

            # Update only this row (no full refresh)
            src_text.value = "user"
            upd_text.value = datetime.now().strftime("%Y-%m-%d %H:%M")
            src_text.update()
            upd_text.update()

            show_snack("Saved.", "green")

        def add_field_dialog(e):
            key_tf = ft.TextField(label="Field key (e.g., patient.employer)", width=400)
            label_tf = ft.TextField(label="Label (e.g., Employer)", width=400)
            cat_tf = ft.TextField(label="Category", value="General", width=400)

            def do_add(ev):
                if not key_tf.value or not label_tf.value:
                    show_snack("Field key and label are required.", "red")
                    return

                ensure_field_definition(
                    page.db_connection,
                    key_tf.value.strip(),
                    label_tf.value.strip(),
                    category=cat_tf.value.strip() or "General",
                )

                page.dialog.open = False
                page.update()
                show_snack("Field added.", "green")

                # Here we DO need a refresh so the new field shows up
                load_dashboard_logic()

            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add Patient Info Field"),
                content=ft.Column([key_tf, label_tf, cat_tf], tight=True),
                actions=[
                    ft.TextButton(
                        "Cancel",
                        on_click=lambda _: (setattr(page.dialog, "open", False), page.update()),
                    ),
                    ft.Button("Add", on_click=do_add),
                ],
            )
            page.dialog.open = True
            page.update()

        rows = []
        for field_key, label, data_type, category, is_sensitive in defs:
            existing = value_map.get(field_key, {})
            val = existing.get("value") or ""
            src = existing.get("source") or ""
            upd = existing.get("updated_at") or ""

            value_tf = ft.TextField(value=val, dense=True, width=320)

            # These are the per-row controls we update after save
            src_text = ft.Text(src)
            upd_text = ft.Text(upd)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(category)),
                        ft.DataCell(ft.Text(label)),
                        ft.DataCell(value_tf),
                        ft.DataCell(src_text),
                        ft.DataCell(upd_text),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.SAVE,
                                tooltip="Save",
                                on_click=lambda e, k=field_key, tf=value_tf, st=src_text, ut=upd_text: save_value(k, tf, st, ut),
                            )
                        ),
                    ]
                )
            )

        return ft.Container(
            padding=s(20),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Patient Info", size=s(24), weight="bold"),
                            ft.Container(expand=True),
                            ft.Button("Add Field", icon=ft.Icons.ADD, on_click=add_field_dialog),
                        ]
                    ),

                    themed_panel(
                        ft.Text(
                            "Tip: You can fill multiple fields. Click the 💾 icon to save a field. "
                            "Unsaved fields will stay until you navigate away.",
                            size=s(14),
                        ),
                        padding=s(10),
                        radius=8,
                    ),

                    ft.Divider(),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Category")),
                            ft.DataColumn(ft.Text("Field")),
                            ft.DataColumn(ft.Text("Value")),
                            ft.DataColumn(ft.Text("Source")),
                            ft.DataColumn(ft.Text("Updated")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=rows,
                    ),
                ]
            ),
        )
   

    def show_settings_view():
        theme_dd = ft.Dropdown(
            label="Theme",
            width=300,
            options=[
                ft.dropdown.Option("system", "System default"),
                ft.dropdown.Option("light", "Light"),
                ft.dropdown.Option("dark", "Dark"),
            ],
            value=get_setting(page.db_connection, "ui.theme", "system"),
        )

        hc_switch = ft.Switch(
            label="High contrast",
            value=get_setting(page.db_connection, "ui.high_contrast", "0") == "1",
        )

        lt_switch = ft.Switch(
            label="Large text",
            value=get_setting(page.db_connection, "ui.large_text", "0") == "1",
        )

        def save_settings(e):
            set_setting(page.db_connection, "ui.theme", theme_dd.value or "system")
            set_setting(page.db_connection, "ui.high_contrast", "1" if hc_switch.value else "0")
            set_setting(page.db_connection, "ui.large_text", "1" if lt_switch.value else "0")
            apply_settings()
            show_snack("Settings saved.", "green")

        def reset_settings(e):
            set_setting(page.db_connection, "ui.theme", "system")
            set_setting(page.db_connection, "ui.high_contrast", "0")
            set_setting(page.db_connection, "ui.large_text", "0")

            theme_dd.value = "system"
            hc_switch.value = False
            lt_switch.value = False
            theme_dd.update()
            hc_switch.update()
            lt_switch.update()

            apply_settings()
            show_snack("Settings reset.", "blue")

        return ft.Container(
            padding=s(20),
            content=ft.Column(
                [
                    ft.Text("Settings", size=s(24), weight="bold"),
                    ft.Divider(),
                    theme_dd,
                    hc_switch,
                    lt_switch,
                    ft.Row(
                        [
                            ft.Button("Save", icon=ft.Icons.SAVE, on_click=save_settings),
                            ft.Button("Reset", icon=ft.Icons.RESTART_ALT, on_click=reset_settings),
                        ]
                    ),
                    ft.Divider(),
                    ft.Text(
                        "Tip: “System default” follows your Windows/macOS theme automatically.",
                        color=ft.Colors.BLUE_GREY,
                        size=s(14)
                    ),
                ],
                tight=True,
            ),
        )

    def show_main_dashboard():
        content_area = ft.Container(expand=True, padding=s(20))

        def nav_change(e):
            index = e.control.selected_index
            content_area.content = get_view_for_index(index)
            content_area.update()

        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD,
                    label="Overview",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.BADGE,
                    label="Patient Info",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.FOLDER,
                    label="Documents",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=nav_change,
        )

        page.nav_rail = rail
        page.content_area = content_area

        content_area.content = get_view_for_index(0)

        page.add(
            ft.Row(
                [
                    rail,
                    ft.VerticalDivider(width=1),
                    content_area,
                ],
                expand=True,
            )
        )

    def get_view_for_index(index):
        patient = page.current_profile

        # 0: OVERVIEW
        if index == 0:
            return ft.Container(
                padding=s(20),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=s(80), color=ft.Colors.BLUE_GREY),
                                ft.Column(
                                    [
                                        ft.Text(patient[1], size=s(30), weight="bold"),
                                        ft.Text(f"DOB: {patient[2]}", size=s(16)),
                                    ]
                                ),
                                ft.Container(expand=True),
                                ft.Button("Edit", icon=ft.Icons.EDIT, on_click=edit_mode_toggle),
                            ]
                        ),
                        ft.Divider(),
                        ft.Text("Medical Summary / Notes", weight="bold", size=s(18)),
                        themed_panel(ft.Text(patient[3] or "", size=s(16)), padding=s(15), radius=6),
                    ]
                ),
            )

        elif index == 1:
            return show_patient_info_view()
    
        # 1: DOCUMENTS
        elif index == 2:
            docs = get_patient_documents(page.db_connection, patient[0])

            rows = []
            for doc in docs:
                file_name = doc[0]
                upload_date = doc[1]
                file_path = doc[2]

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="blue")),
                            ft.DataCell(ft.Text(file_name)),
                            ft.DataCell(ft.Text(upload_date)),
                            ft.DataCell(
                                ft.IconButton(
                                    ft.Icons.OPEN_IN_NEW,
                                    tooltip="Open File",
                                    data=file_path,
                                    on_click=open_document_click,
                                )
                            ),
                        ]
                    )
                )

            return ft.Container(
                padding=s(20),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Medical Records", size=s(24), weight="bold"),
                                ft.Container(expand=True),
                                ft.Button(
                                    "Upload Document",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    on_click=pick_and_save_document,
                                ),
                            ]
                        ),
                        ft.Divider(),
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("Type")),
                                ft.DataColumn(ft.Text("File Name")),
                                ft.DataColumn(ft.Text("Date Added")),
                                ft.DataColumn(ft.Text("Actions")),
                            ],
                            rows=rows,
                        ),
                    ]
                ),
            )

        elif index == 3:
            return show_settings_view()
        else:
            return ft.Text("Unknown view", size=s(20))

    # --- STARTUP SCREEN ---
    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.SECURITY, size=s(64), color=ft.Colors.BLUE),
                ft.Text("Secure Login", size=s(30)),
                password_field,
                ft.Button("Unlock Database", on_click=attempt_login),
                error_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

if __name__ == "__main__":
    # UPDATED FOR FLET 0.80+: Use ft.app instead of ft.run
    ft.run(main)