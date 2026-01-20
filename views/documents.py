# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# Handles the "Documents" tab.
# - Lists files uploaded for the patient.
# - Handles "Collision Detection" (if you upload a file with the same name).
# - Provides a Search Bar to filter the list.
# - Confirms deletion and reliably closes the dialog on Delete or Cancel.
# -----------------------------------------------------------------------------

import flet as ft
import os
import shutil
import asyncio
from datetime import datetime

from database import (
    get_patient_documents,
    add_document,
    delete_document,
    get_document_path,
)
from utils import s, show_snack


def get_documents_view(page: ft.Page):
    # 1. SETUP
    patient = getattr(page, "current_profile", None)
    if not patient:
        return ft.Text("No patient loaded.")
    patient_id = patient[0]

    all_docs = []

    # 2. CONTROLS
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Type")),
            ft.DataColumn(ft.Text("File Name")),
            ft.DataColumn(ft.Text("Date Added")),
            ft.DataColumn(ft.Text("Open")),
            ft.DataColumn(ft.Text("Delete")),
        ],
        rows=[],
        border=ft.border.all(1, ft.Colors.GREY_400),
        vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
    )

    search_field = ft.TextField(
        label="Search Records",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        dense=True,
    )

    # --- helper: treat "report.pdf" and "report (1).pdf" as the same base name
    def base_key(filename: str) -> str:
        root, ext = os.path.splitext(filename or "")
        root = root.strip()

        # Strip trailing "(number)" or " (number)"
        if root.endswith(")") and "(" in root:
            left = root.rsplit("(", 1)[0].rstrip()
            inside = root.rsplit("(", 1)[1][:-1].strip()  # drop ")"
            if inside.isdigit() and left:
                root = left

        return (root + ext).lower()

    # 3. HELPER FUNCTIONS
    async def open_doc_async(path: str | None):
        if path and os.path.exists(path):
            file_url = "file:///" + path.replace("\\", "/")
            await ft.UrlLauncher().launch_url(file_url)
        else:
            show_snack(page, "File not found.", "red")

    def open_doc_click(e: ft.ControlEvent):
        path = e.control.data
        asyncio.create_task(open_doc_async(path))

    def refresh_table(filter_text: str = "", update_ui: bool = False):
        nonlocal all_docs
        rows: list[ft.DataRow] = []
        ft_filter = (filter_text or "").lower()

        try:
            all_docs = get_patient_documents(page.db_connection, patient_id)
        except Exception:
            all_docs = []

        for doc in all_docs:
            try:
                doc_id, file_name, upload_date, file_path = doc
            except Exception:
                continue

            if ft_filter and ft_filter not in str(file_name).lower():
                continue

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="blue")),
                        ft.DataCell(ft.Text(str(file_name))),
                        ft.DataCell(ft.Text(str(upload_date))),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.OPEN_IN_NEW,
                                data=file_path,
                                on_click=open_doc_click,
                            )
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.DELETE,
                                data=(doc_id, file_name),
                                on_click=delete_handler,
                            )
                        ),
                    ]
                )
            )

        data_table.rows = rows
        if update_ui and data_table.page:
            data_table.update()

    def on_search_change(e: ft.ControlEvent):
        refresh_table(e.control.value, update_ui=True)

    search_field.on_change = on_search_change

    # 4. HANDLERS
    def delete_handler(e: ft.ControlEvent):
        data = getattr(e.control, "data", None)
        if not data:
            return
        doc_id, name = data

        # Prevent stacking dialogs if user double-clicks
        if getattr(page, "_delete_dialog_open", False):
            return
        page._delete_dialog_open = True

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(
                f"Permanently delete '{name}'?\n\n"
                "This removes it from the app and deletes the file from disk."
            ),
            actions=[],
        )

        def close_dlg(_=None, d=dlg):
            # Close
            d.open = False
            page.update()

            # Remove from overlay (important)
            if d in page.overlay:
                page.overlay.remove(d)

            page._delete_dialog_open = False
            page.update()

        def confirm(_=None, d=dlg):
            # ✅ CLOSE FIRST so the dialog always disappears
            close_dlg(d=d)

            try:
                # True delete: DB + disk
                file_path = get_document_path(page.db_connection, int(doc_id))
                delete_document(page.db_connection, int(doc_id))

                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as ex:
                        print(f"Could not delete file {file_path}: {ex}")
                        show_snack(page, "Deleted record, but file could not be removed.", "orange")

                refresh_table(search_field.value, update_ui=True)
                show_snack(page, "Record and file deleted.", "blue")

            except Exception as ex:
                print("DELETE ERROR:", ex)
                show_snack(page, f"Delete failed: {ex}", "red")

        dlg.actions = [
            ft.TextButton("Cancel", on_click=close_dlg),
            ft.Button("Delete", icon=ft.Icons.DELETE, on_click=confirm),
        ]

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # 5. UPLOAD LOGIC
    async def upload_document_click(e: ft.ControlEvent):
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            dialog_title="Select Medical Record",
        )

        if not files:
            return

        picked = files[0]
        src_path = getattr(picked, "path", None) or getattr(picked, "file_path", None)

        if not src_path:
            show_snack(page, "Picker returned no local path.", "red")
            return

        # Path Calculation
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        dest_dir = os.path.join(project_root, "data", str(patient_id))
        os.makedirs(dest_dir, exist_ok=True)

        # --- RENAME LOGIC ---
        original_name = picked.name
        file_name = original_name
        dest_path = os.path.join(dest_dir, file_name)

        # ✅ DB-based duplicate detection (base-name aware)
        try:
            existing_docs = get_patient_documents(page.db_connection, patient_id)
            existing_keys = {base_key(str(d[1])) for d in existing_docs if len(d) > 1 and d[1]}
        except Exception:
            existing_keys = set()

        collision_detected = base_key(original_name) in existing_keys

        name_root, name_ext = os.path.splitext(file_name)
        counter = 1

        while os.path.exists(dest_path):
            file_name = f"{name_root} ({counter}){name_ext}"
            dest_path = os.path.join(dest_dir, file_name)
            counter += 1

        # ✅ If we had to rename, it is also a duplicate/collision
        if counter > 1:
            collision_detected = True
        # --------------------

        try:
            shutil.copy(src_path, dest_path)
            add_document(
                page.db_connection,
                patient_id,
                file_name,
                dest_path,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            refresh_table(search_field.value, update_ui=True)

            # Duplicate-aware message
            if collision_detected:
                show_snack(page, f"Duplicate file detected. Creating {file_name}.", "orange")
            else:
                show_snack(page, "Uploaded successfully.", "green")

        except Exception as ex:
            print(f"Upload Error: {ex}")
            show_snack(page, f"Error: {str(ex)}", "red")

    # 6. INITIAL LAYOUT BUILD
    refresh_table(update_ui=False)

    return ft.Container(
        padding=s(page, 20),
        expand=True,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Medical Records", size=s(page, 24), weight="bold"),
                        ft.Container(expand=True),
                        ft.Button(
                            "Upload Document",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=upload_document_click,
                        ),
                    ]
                ),
                ft.Divider(),
                search_field,
                ft.Divider(),
                ft.Column([data_table], scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            expand=True,
        ),
    )