"""Application theme definitions for light and dark modes."""

from __future__ import annotations

import flet as ft


class AppTheme:
    """Encapsulates all colour tokens for the UI.

    Toggle between dark and light modes with :meth:`toggle` and apply
    the mode to a Flet page with :meth:`apply_to_page`.
    """

    def __init__(self, is_dark: bool = True) -> None:
        self.is_dark = is_dark
        self._define_colors()

    # ------------------------------------------------------------------
    # Colour palette
    # ------------------------------------------------------------------

    def _define_colors(self) -> None:
        """Set all colour attributes based on the current mode."""
        if self.is_dark:
            self.bg_color = "#0B1120"
            self.surface_color = "#1E293B"
            self.card_color = "#334155"

            self.primary_color = "#F472B6"
            self.secondary_color = "#22D3EE"
            self.accent_color = "#818CF8"

            self.primary_gradient = ["#EC4899", "#9333EA", "#4F46E5"]

            self.text_primary = "#F8FAFC"
            self.text_secondary = "#94A3B8"
            self.text_disabled = "#475569"

            self.border_color = "#334155"
            self.hover_color = "#334155"
            self.input_bgcolor = "#1E293B"

            self.error_color = "#EF4444"
            self.success_color = "#10B981"
            self.warning_color = "#F59E0B"
            self.info_color = "#3B82F6"

            self.shadow_color = ft.Colors.with_opacity(0.5, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.5, "#000000")
        else:
            self.bg_color = "#F1F5F9"
            self.surface_color = "#FFFFFF"
            self.card_color = "#FFFFFF"

            self.primary_color = "#EC4899"
            self.secondary_color = "#06B6D4"
            self.accent_color = "#6366F1"

            self.primary_gradient = ["#EC4899", "#A855F7", "#6366F1"]

            self.text_primary = "#0F172A"
            self.text_secondary = "#64748B"
            self.text_disabled = "#CBD5E1"

            self.border_color = "#E2E8F0"
            self.hover_color = "#F1F5F9"
            self.input_bgcolor = "#F1F5F9"

            self.error_color = "#EF4444"
            self.success_color = "#10B981"
            self.warning_color = "#F59E0B"
            self.info_color = "#3B82F6"

            self.shadow_color = ft.Colors.with_opacity(0.1, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.3, "#000000")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        """Switch between dark and light modes."""
        self.is_dark = not self.is_dark
        self._define_colors()

    def get_flet_theme_mode(self) -> ft.ThemeMode:
        """Return the matching :class:`ft.ThemeMode`."""
        return ft.ThemeMode.DARK if self.is_dark else ft.ThemeMode.LIGHT

    def apply_to_page(self, page: ft.Page) -> None:
        """Apply the current theme mode and background colour to *page*."""
        page.theme_mode = self.get_flet_theme_mode()
        page.bgcolor = self.bg_color
        page.update()
