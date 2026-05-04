"""Tests for module-level helpers in src.ui.main_window.

These don't require a running Flet app — only the pure functions exposed
at module level (friendly_error, _read_clipboard, the format/UI sync).
"""

import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from src.ui.main_window import MainWindow, _FORMAT_UI, _schedule_on_ui, friendly_error
from src.utils.downloader import FORMAT_PRESETS


class TestFormatUiSync:
    """Every UI format button must map to a real preset and vice-versa."""

    def test_ui_keys_subset_of_presets(self) -> None:
        ui_keys = {entry["value"] for entry in _FORMAT_UI}
        assert ui_keys.issubset(FORMAT_PRESETS.keys()), (
            f"UI references unknown format(s): {ui_keys - FORMAT_PRESETS.keys()}"
        )

    def test_all_presets_have_ui(self) -> None:
        ui_keys = {entry["value"] for entry in _FORMAT_UI}
        # Every preset that the user can pick from a downloaded build must
        # be reachable in the UI. If you intentionally hide one, exclude it
        # in the assertion below.
        missing = set(FORMAT_PRESETS.keys()) - ui_keys
        assert not missing, f"Preset(s) not exposed in UI: {missing}"


class TestFriendlyError:
    """Mapping raw yt-dlp errors to short Spanish messages for the user."""

    @pytest.mark.parametrize(
        ("raw", "needle"),
        [
            ("ERROR: Video unavailable", "no está disponible"),
            ("This video is private", "privado"),
            ("Sign in to confirm your age", "edad"),
            ("HTTP Error 429: Too Many Requests", "limitando"),
            ("Connection timed out", "tiempo de espera"),
            ("getaddrinfo failed", "conexión"),
            ("Permission denied: '/foo'", "Permisos"),
            ("No space left on device", "espacio"),
            ("ffmpeg not found", "ffmpeg"),
            ("Unsupported URL: foo", "enlace"),
        ],
    )
    def test_known_patterns(self, raw: str, needle: str) -> None:
        assert needle.lower() in friendly_error(raw).lower()

    def test_empty_message(self) -> None:
        assert friendly_error("") == "Error desconocido al descargar el vídeo."

    def test_unknown_message_truncated(self) -> None:
        long = "x" * 500
        result = friendly_error(long)
        assert result.startswith("Error: ")
        assert len(result) <= 200

    def test_only_first_line(self) -> None:
        result = friendly_error("first line\nsecond line\nthird line")
        assert "second line" not in result
        assert "third line" not in result


class TestFletApiCompatibility:
    """Guard against using removed top-level Flet API names."""

    def test_all_top_level_flet_symbols_exist(self) -> None:
        root = Path(__file__).resolve().parents[1] / "src"
        pattern = re.compile(r"ft\.([A-Z][A-Za-z0-9_]*)")
        alignment_pattern = re.compile(r"ft\.alignment\.([a-z_]+)")
        missing_by_file = {}

        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            names = sorted(set(pattern.findall(text)))
            missing = [name for name in names if not hasattr(ft, name)]
            alignment_names = sorted(set(alignment_pattern.findall(text)))
            missing_alignment = [
                name for name in alignment_names if not hasattr(ft.alignment, name)
            ]
            if missing or missing_alignment:
                missing_by_file[str(path.relative_to(root.parent))] = {
                    "top_level": missing,
                    "alignment": missing_alignment,
                }

        assert not missing_by_file, (
            "Project references removed or unavailable top-level Flet symbols: "
            f"{missing_by_file}"
        )


class TestUiScheduling:
    """Background work must marshal UI mutations back onto the page loop."""

    def test_schedule_on_ui_uses_page_run_task(self) -> None:
        page = MagicMock()
        callback = MagicMock()

        _schedule_on_ui(page, callback, 42, "ok")

        page.run_task.assert_called_once()
        run_task_args = page.run_task.call_args.args
        asyncio.run(run_task_args[0](*run_task_args[1:]))
        callback.assert_called_once_with(42, "ok")

    def test_schedule_on_ui_falls_back_without_run_task(self) -> None:
        class NoTaskPage:
            pass

        callback = MagicMock()
        _schedule_on_ui(NoTaskPage(), callback, "fallback")
        callback.assert_called_once_with("fallback")


class _FakeHistory:
    def get_all(self) -> list[dict[str, object]]:
        return []

    def clear(self) -> None:
        return None

    def add(self, _info: dict[str, object]) -> None:
        return None


class TestMainWindowSmoke:
    """Basic startup smoke coverage for the real UI tree."""

    def test_builds_main_window_without_runtime_flet_errors(self, mock_page) -> None:
        with patch("src.ui.main_window._load_config", return_value={}), patch(
            "src.ui.main_window.DownloadHistory", return_value=_FakeHistory()
        ):
            view = MainWindow(mock_page)

        assert isinstance(view, ft.Container)
        assert mock_page.services, "MainWindow should register its FilePicker service"
