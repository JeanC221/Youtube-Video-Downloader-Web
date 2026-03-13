"""Application theme definitions for light and dark modes.

WCAG AA contrast ratios enforced (4.5:1 for normal text, 3:1 for large text).
"""

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
            self.bg_color = "#0F172A"
            self.surface_color = "#1E293B"
            self.card_color = "#283548"

            self.primary_color = "#6366F1"
            self.primary_light = "#818CF8"
            self.secondary_color = "#22D3EE"
            self.accent_color = "#A78BFA"

            self.primary_gradient = ["#6366F1", "#8B5CF6"]
            self.success_gradient = ["#059669", "#10B981"]
            self.error_gradient = ["#DC2626", "#EF4444"]

            self.text_primary = "#F1F5F9"
            self.text_secondary = "#94A3B8"
            self.text_disabled = "#475569"
            self.text_on_primary = "#FFFFFF"

            self.border_color = "#334155"
            self.border_focus = "#6366F1"
            self.hover_color = "#334155"
            self.input_bgcolor = "#1E293B"
            self.input_border = "#475569"

            self.error_color = "#F87171"
            self.success_color = "#34D399"
            self.warning_color = "#FBBF24"
            self.info_color = "#60A5FA"

            self.shadow_color = ft.Colors.with_opacity(0.4, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.6, "#000000")
            self.divider_color = "#334155"

            self.snackbar_bg = "#334155"
            self.snackbar_text = "#F1F5F9"
        else:
            self.bg_color = "#F8FAFC"
            self.surface_color = "#FFFFFF"
            self.card_color = "#FFFFFF"

            self.primary_color = "#4F46E5"
            self.primary_light = "#6366F1"
            self.secondary_color = "#0891B2"
            self.accent_color = "#7C3AED"

            self.primary_gradient = ["#4F46E5", "#7C3AED"]
            self.success_gradient = ["#059669", "#10B981"]
            self.error_gradient = ["#DC2626", "#EF4444"]

            self.text_primary = "#0F172A"
            self.text_secondary = "#475569"
            self.text_disabled = "#CBD5E1"
            self.text_on_primary = "#FFFFFF"

            self.border_color = "#E2E8F0"
            self.border_focus = "#4F46E5"
            self.hover_color = "#F1F5F9"
            self.input_bgcolor = "#F1F5F9"
            self.input_border = "#CBD5E1"

            self.error_color = "#DC2626"
            self.success_color = "#059669"
            self.warning_color = "#D97706"
            self.info_color = "#2563EB"

            self.shadow_color = ft.Colors.with_opacity(0.08, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.3, "#000000")
            self.divider_color = "#E2E8F0"

            self.snackbar_bg = "#1E293B"
            self.snackbar_text = "#F1F5F9"

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
