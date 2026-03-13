"""Tests for the Application class."""

from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from src.app import Application


class TestApplication:
    """Tests for the top-level Application class."""

    def test_init(self) -> None:
        app = Application()
        assert app.page is None

    @patch("src.app.MainWindow")
    def test_main_configures_page(self, mock_main_window: MagicMock) -> None:
        mock_main_window.return_value = ft.Container()

        app = Application()
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        page.window = MagicMock()
        page.add = MagicMock()
        page.update = MagicMock()

        app.main(page)

        assert page.title == "YouTube Video Downloader"
        assert page.padding == 0
        page.add.assert_called_once()
        page.update.assert_called_once()

    @patch("src.app.MainWindow")
    def test_main_handles_exception(self, mock_main_window: MagicMock) -> None:
        mock_main_window.side_effect = RuntimeError("UI crash")

        app = Application()
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        page.window = MagicMock()
        page.add = MagicMock()
        page.update = MagicMock()

        # Should not raise
        app.main(page)
        # add is called with the error container
        page.add.assert_called_once()
        page.update.assert_called_once()

    @patch("src.app.ft.app")
    def test_run_launches_flet(self, mock_flet_app: MagicMock) -> None:
        app = Application()
        app.run()
        mock_flet_app.assert_called_once()
        call_kwargs = mock_flet_app.call_args
        assert call_kwargs.kwargs.get("assets_dir") == "assets" or "assets_dir" in str(call_kwargs)

    @patch("src.app.ft.app")
    def test_run_retries_without_assets(self, mock_flet_app: MagicMock) -> None:
        # First call raises, second succeeds
        mock_flet_app.side_effect = [Exception("No assets dir"), None]
        app = Application()
        app.run()
        assert mock_flet_app.call_count == 2
