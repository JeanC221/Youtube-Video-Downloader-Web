"""Tests for the UI components module."""

from unittest.mock import MagicMock

import pytest

from src.ui.components import ModernButton, StatusChip
from src.ui.theme import AppTheme


class TestStatusChip:
    """Tests for the StatusChip component."""

    def test_initial_status_is_ready(self) -> None:
        theme = AppTheme()
        chip = StatusChip(theme)
        assert chip._status == "ready"

    def test_set_valid_status(self) -> None:
        theme = AppTheme()
        chip = StatusChip(theme)
        # Patch update to avoid Flet runtime checks
        chip.update = MagicMock()

        for status in ("ready", "working", "done", "error"):
            chip.set_status(status)
            assert chip._status == status

    def test_set_custom_text(self) -> None:
        theme = AppTheme()
        chip = StatusChip(theme)
        chip.update = MagicMock()

        chip.set_status("working", "Downloading 50%...")
        assert chip.status_text.value == "Downloading 50%..."

    def test_invalid_status_ignored(self) -> None:
        theme = AppTheme()
        chip = StatusChip(theme)
        chip.update = MagicMock()

        chip.set_status("nonexistent_status")
        assert chip._status == "ready"  # Unchanged


class TestModernButton:
    """Tests for the ModernButton component."""

    def test_creation_with_defaults(self) -> None:
        btn = ModernButton(text="Click")
        assert btn._label == "Click"
        assert btn.is_disabled is False
        assert btn.opacity == 1.0

    def test_disabled_state(self) -> None:
        btn = ModernButton(text="Click", disabled=True)
        assert btn.is_disabled is True
        assert btn.opacity == 0.5
        assert btn.on_click is None

    def test_set_disabled(self) -> None:
        btn = ModernButton(text="Click")
        btn.update = MagicMock()

        btn.set_disabled(True)
        assert btn.is_disabled is True
        assert btn.opacity == 0.5

        btn.set_disabled(False)
        assert btn.is_disabled is False
        assert btn.opacity == 1.0

    def test_click_handler_called(self) -> None:
        handler = MagicMock()
        btn = ModernButton(text="Click", on_click=handler)
        btn.update = MagicMock()

        event = MagicMock()
        btn._handle_click(event)

        handler.assert_called_once_with(event)

    def test_with_icon(self) -> None:
        btn = ModernButton(text="Download", icon="download")
        # Should have icon + spacer + text = 3 controls
        assert len(btn.content.controls) == 3

    def test_with_custom_gradient(self) -> None:
        colors = ["#ff0000", "#00ff00"]
        btn = ModernButton(text="Custom", gradient_colors=colors)
        assert btn.gradient_colors == colors
