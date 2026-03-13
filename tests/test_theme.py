"""Tests for the theme module."""

import flet as ft
import pytest

from src.ui.theme import AppTheme


class TestAppTheme:
    """Tests for the AppTheme class."""

    def test_default_is_dark(self) -> None:
        theme = AppTheme()
        assert theme.is_dark is True

    def test_light_mode_init(self) -> None:
        theme = AppTheme(is_dark=False)
        assert theme.is_dark is False
        assert theme.bg_color == "#F1F5F9"

    def test_dark_mode_colors(self) -> None:
        theme = AppTheme(is_dark=True)
        assert theme.bg_color == "#0B1120"
        assert theme.surface_color == "#1E293B"

    def test_toggle_switches_mode(self) -> None:
        theme = AppTheme(is_dark=True)
        theme.toggle()
        assert theme.is_dark is False
        assert theme.bg_color == "#F1F5F9"

    def test_toggle_twice_returns_original(self) -> None:
        theme = AppTheme(is_dark=True)
        theme.toggle()
        theme.toggle()
        assert theme.is_dark is True
        assert theme.bg_color == "#0B1120"

    def test_get_flet_theme_mode_dark(self) -> None:
        theme = AppTheme(is_dark=True)
        assert theme.get_flet_theme_mode() == ft.ThemeMode.DARK

    def test_get_flet_theme_mode_light(self) -> None:
        theme = AppTheme(is_dark=False)
        assert theme.get_flet_theme_mode() == ft.ThemeMode.LIGHT

    def test_all_color_attributes_exist(self) -> None:
        required_attrs = [
            "bg_color",
            "surface_color",
            "card_color",
            "primary_color",
            "secondary_color",
            "accent_color",
            "primary_gradient",
            "text_primary",
            "text_secondary",
            "text_disabled",
            "border_color",
            "hover_color",
            "input_bgcolor",
            "error_color",
            "success_color",
            "warning_color",
            "info_color",
            "shadow_color",
            "overlay_color",
        ]
        for mode in (True, False):
            theme = AppTheme(is_dark=mode)
            for attr in required_attrs:
                assert hasattr(theme, attr), f"Missing '{attr}' in {'dark' if mode else 'light'} mode"

    def test_gradient_has_multiple_colors(self) -> None:
        theme = AppTheme()
        assert len(theme.primary_gradient) >= 2
