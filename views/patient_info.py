# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# This view handles "Structured Data" (Phone, Address, Insurance ID).
# It fetches the list of fields from the DB and renders them as a Grid.
# It supports "Inline Editing" (saving per row).
# -----------------------------------------------------------------------------

import flet as ft
from datetime import datetime
from database import (
    list_field_definitions, 
    get_patient_field_map, 
    upsert_patient_field_value, 
    ensure_field_definition
)
from utils import s, themed_panel, show_snack

def get_patient_info_view(page: ft.Page):
    patient = page.current_profile
    if not patient: return ft.Text("No patient loaded.")
    patient_id = patient[0]

    # 1. Fetch Data
    # 'defs' = What fields exist? (Label, Key, Category)
    defs = list_field_definitions(page.db_connection)
    # 'value_map' = What has the patient actually entered?
    value_map = get_patient_field_map(page.db_connection, patient_id)

    # 2. Logic: Saving a single row
    def save_value(field_key, tf, src_text, upd_text):
        """
        Saves just ONE field to the DB without reloading the whole page.
        """
        upsert_patient_field_value(
            page.db_connection,
            patient_id,
            field_key,
            tf.value or "",
            source="user",
        )
        # Visual Feedback: Update the "Source" and "Updated" columns instantly
        src_text.value = "user"
        upd_text.value = datetime.now().strftime("%Y-%m-%d %H:%M")
        src_text.update()
        upd_text.update()
        show_snack(page, "Saved.", "green")

    # 3. Logic: Adding a NEW field definition (e.g. "Dentist Phone")
    def add_field_dialog(e):
        key_tf = ft.TextField(label="Field key (e.g. patient.dentist)")
        label_tf = ft.TextField(label="Label (e.g. Dentist Phone)")
        cat_tf = ft.TextField(label="Category", value="General")

        def do_add(ev):
            if not key_tf.value: return
            ensure_field_definition(
                page.db_connection, 
                key_tf.value, 
                label_tf.value, 
                category=cat_tf.value
            )
            page.dialog.open = False
            page.update()
            # We MUST refresh the whole view to see the new row
            page.content_area.content = get_patient_info_view(page)
            page.content_area.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Add New Field"),
            content=ft.Column([key_tf, label_tf, cat_tf], tight=True),
            actions=[ft.Button("Add", on_click=do_add)]
        )
        page.dialog.open = True
        page.update()

    # 4. Build the Table Rows
    rows = []
    for field_key, label, data_type, category, is_sensitive in defs:
        # Get existing data or empty string
        existing = value_map.get(field_key, {})
        val = existing.get("value") or ""
        
        # Controls
        value_tf = ft.TextField(value=val, dense=True)
        src_text = ft.Text(existing.get("source") or "")
        upd_text = ft.Text(existing.get("updated_at") or "")

        # Create row
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
                            tooltip="Save this field",
                            # Use lambda to capture the specific controls for THIS row
                            on_click=lambda e, k=field_key, t=value_tf, s=src_text, u=upd_text: save_value(k, t, s, u),
                        )
                    ),
                ]
            )
        )

    # 5. Return Layout
    return ft.Container(
        padding=s(page, 20),
        content=ft.Column(
            [
                ft.Row([
                    ft.Text("Patient Info", size=s(page, 24), weight="bold"),
                    ft.Container(expand=True),
                    ft.Button("Add Field", icon=ft.Icons.ADD, on_click=add_field_dialog),
                ]),
                themed_panel(
                    page,
                    ft.Text("Tip: Click the save icon 💾 next to a field to save it."), 
                    padding=s(page, 10)
                ),
                ft.Divider(),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Category")),
                        ft.DataColumn(ft.Text("Field")),
                        ft.DataColumn(ft.Text("Value")),
                        ft.DataColumn(ft.Text("Source")),
                        ft.DataColumn(ft.Text("Updated")),
                        ft.DataColumn(ft.Text("Save")),
                    ],
                    rows=rows,
                ),
            ]
        )
    )