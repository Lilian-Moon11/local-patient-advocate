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
)


def main(page: ft.Page):
    page.title = "Local Patient Advocate"
    page.window.width = 1000
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.LIGHT

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

    def attempt_login(e):
        try:
            if not password_field.value:
                raise ValueError("Please enter a password.")

            page.db_connection = init_db(password_field.value)
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
                    ft.Text("Edit Profile", size=30, weight="bold"),
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
                        ft.Icon(ft.Icons.PERSON_ADD, size=64, color=ft.Colors.BLUE),
                        ft.Text("Welcome!", size=30, weight="bold"),
                        ft.Text("Let's set up the primary patient profile.", size=16),
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

    def show_main_dashboard():
        content_area = ft.Container(expand=True, padding=20)

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
                ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Overview"),
                ft.NavigationRailDestination(icon=ft.Icons.FOLDER, label="Documents"),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
            ],
            on_change=nav_change,
        )

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
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_GREY),
                                ft.Column(
                                    [
                                        ft.Text(patient[1], size=30, weight="bold"),
                                        ft.Text(f"DOB: {patient[2]}", size=16, color="grey"),
                                    ]
                                ),
                                ft.Container(expand=True),
                                ft.Button("Edit", icon=ft.Icons.EDIT, on_click=edit_mode_toggle),
                            ]
                        ),
                        ft.Divider(),
                        ft.Text("Medical Summary / Notes", weight="bold", size=18),
                        ft.Container(
                            content=ft.Text(patient[3] or "", size=16),
                            padding=15,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5,
                        ),
                    ]
                ),
            )

        # 1: DOCUMENTS
        elif index == 1:
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
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Medical Records", size=24, weight="bold"),
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

        else:
            return ft.Text("Settings (Coming Soon)", size=20)

    # --- STARTUP SCREEN ---
    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.SECURITY, size=64, color=ft.Colors.BLUE),
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
    # UPDATED FOR FLET 0.80+: Use ft.app instead of ft.run
    ft.run(main)