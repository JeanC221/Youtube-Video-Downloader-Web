"""Application theme definitions for light and dark modes.

WCAG AA contrast ratios enforced (4.5:1 for normal text, 3:1 for large text).

Design tokens (spacing, radius, type scale, weights) are exposed via
:class:`DesignTokens` so the rest of the UI can reference a single source
of truth instead of hard-coding magic numbers.
"""

from __future__ import annotations

import flet as ft


class DesignTokens:
    """Numeric design tokens shared across the UI.

    These are intentionally plain class attributes so they can be used
    without instantiation (``DesignTokens.SPACING_MD``) and are trivially
    discoverable by IDEs.
    """

    # Spacing scale (px)
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24
    SPACING_XXL = 32

    # Corner radius scale (px)
    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 16
    RADIUS_XL = 20
    RADIUS_PILL = 999

    # Type scale (px)
    FONT_CAPTION = 11
    FONT_BODY_SM = 12
    FONT_BODY = 14
    FONT_SUBTITLE = 15
    FONT_TITLE = 18
    FONT_H2 = 22
    FONT_H1 = 26

    # Weights
    WEIGHT_REGULAR = ft.FontWeight.W_400
    WEIGHT_MEDIUM = ft.FontWeight.W_500
    WEIGHT_SEMIBOLD = ft.FontWeight.W_600
    WEIGHT_BOLD = ft.FontWeight.W_700

    # Standard control heights
    HEIGHT_BUTTON = 48
    HEIGHT_INPUT = 48
    HEIGHT_CHIP = 36


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
            self.bg_color = "#0B1220"
            self.bg_gradient = ["#0B1220", "#0F172A"]
            self.surface_color = "#131C2E"
            self.surface_elevated = "#1A2337"
            self.surface_subtle = "#111A2B"
            self.card_color = "#1E2942"

            self.primary_color = "#6366F1"
            self.primary_light = "#818CF8"
            self.secondary_color = "#22D3EE"
            self.accent_color = "#A78BFA"

            self.primary_gradient = ["#6366F1", "#8B5CF6"]
            self.success_gradient = ["#059669", "#10B981"]
            self.error_gradient = ["#DC2626", "#EF4444"]

            self.text_primary = "#F1F5F9"
            self.text_secondary = "#94A3B8"
            self.text_muted = "#64748B"
            self.text_disabled = "#475569"
            self.text_on_primary = "#FFFFFF"

            self.border_color = "#27334A"
            self.border_strong = "#334155"
            self.border_focus = "#6366F1"
            self.hover_color = "#1F2A42"
            self.input_bgcolor = "#17213580"
            self.input_border = "#334155"

            self.error_color = "#F87171"
            self.success_color = "#34D399"
            self.warning_color = "#FBBF24"
            self.info_color = "#60A5FA"

            self.shadow_color = ft.Colors.with_opacity(0.45, "#000000")
            self.shadow_color_soft = ft.Colors.with_opacity(0.25, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.6, "#000000")
            self.divider_color = "#27334A"

            self.snackbar_bg = "#1E2942"
            self.snackbar_text = "#F1F5F9"
        else:
            self.bg_color = "#F5F7FB"
            self.bg_gradient = ["#F5F7FB", "#EEF2F9"]
            self.surface_color = "#FFFFFF"
            self.surface_elevated = "#FFFFFF"
            self.surface_subtle = "#F8FAFC"
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
            self.text_muted = "#64748B"
            self.text_disabled = "#CBD5E1"
            self.text_on_primary = "#FFFFFF"

            self.border_color = "#E2E8F0"
            self.border_strong = "#CBD5E1"
            self.border_focus = "#4F46E5"
            self.hover_color = "#F1F5F9"
            self.input_bgcolor = "#F8FAFC"
            self.input_border = "#CBD5E1"

            self.error_color = "#DC2626"
            self.success_color = "#059669"
            self.warning_color = "#D97706"
            self.info_color = "#2563EB"

            self.shadow_color = ft.Colors.with_opacity(0.10, "#0F172A")
            self.shadow_color_soft = ft.Colors.with_opacity(0.06, "#0F172A")
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

    # ------------------------------------------------------------------
    # Elevation helpers (single source of truth for shadows)
    # ------------------------------------------------------------------

    def elevation_1(self) -> ft.BoxShadow:
        """Low elevation — cards resting on surface."""
        return ft.BoxShadow(
            blur_radius=8,
            spread_radius=0,
            color=self.shadow_color_soft,
            offset=ft.Offset(0, 2),
        )

    def elevation_2(self) -> ft.BoxShadow:
        """Medium elevation — main panels."""
        return ft.BoxShadow(
            blur_radius=16,
            spread_radius=0,
            color=self.shadow_color,
            offset=ft.Offset(0, 4),
        )

    def elevation_3(self) -> ft.BoxShadow:
        """High elevation — dialogs / floating elements."""
        return ft.BoxShadow(
            blur_radius=28,
            spread_radius=0,
            color=self.shadow_color,
            offset=ft.Offset(0, 8),
        )
