# Copyright (C) 2026 Lilian-Moon11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# -----------------------------------------------------------------------------
# PURPOSE:
# Shared UI utilities for consistent, accessible rendering across the app.
#
# Includes:
# - Scale-safe sizing helpers (respecting user UI scale preferences)
# - Centralized snackbar messaging with safe error handling
# - Theme-aware container helpers that adapt to light/dark mode and
#   enforce high-contrast accessibility when enabled
# -----------------------------------------------------------------------------

import flet as ft

def s(page: ft.Page, px: int) -> int:
    """Scale-safe sizing helper."""
    # Defaults to 1.0 if ui_scale is not set yet
    scale = getattr(page, "ui_scale", 1.0)
    if scale is None: scale = 1.0
    return int(px * scale)

def show_snack(page: ft.Page, message: str, color: str = "green"):
    """Displays a snackbar message."""
    try:
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()
    except Exception as ex:
        print("SNACK ERROR:", ex, "| message:", message)

def themed_panel(page: ft.Page, content, padding=None, radius=6):
    """
    A theme-safe container that looks good in light/dark, 
    and enforces high-contrast when enabled.
    """
    hc = getattr(page, "is_high_contrast", False)
    
    if padding is None:
        padding = s(page, 15)

    if hc:
        # FIX: Ensure text is visible against the forced Black background.
        # If the content is text, we turn it Yellow to match the border.
        if isinstance(content, ft.Text) and content.color is None:
            content.color = ft.Colors.YELLOW

        return ft.Container(
            content=content,
            padding=padding,
            bgcolor=ft.Colors.BLACK,
            border=ft.Border.all(2, ft.Colors.YELLOW),
            border_radius=radius,
        )

    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=None,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT) if hasattr(ft.Colors, "OUTLINE_VARIANT") else None,
        border_radius=radius,
    )