"""Flet application entry point.

Configures the page (window size, theme, etc.) and adds the main UI.
"""

from __future__ import annotations

import logging

import flet as ft

from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class Application:
    """Top-level application that configures the Flet page and runs the event loop."""

    def __init__(self) -> None:
        self.page: ft.Page | None = None

    def main(self, page: ft.Page) -> None:
        """Configure and populate *page* with the main window."""
        self.page = page

        page.title = "YouTube Video Downloader"
        page.window.width = 1100
        page.window.height = 750
        page.window.min_width = 800
        page.window.min_height = 600

        try:
            page.window.center()
        except AttributeError:
            pass

        page.padding = 0
        page.spacing = 0

        try:
            main_window = MainWindow(page)
            page.add(main_window)
        except Exception as exc:
            logger.exception("Failed to load main window")
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.ERROR, size=48, color="red"),
                            ft.Text("Error al cargar la aplicacion:", size=20),
                            ft.Text(str(exc), size=14),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )

        page.update()

    def run(self) -> None:
        """Launch the Flet desktop application."""
        try:
            ft.app(target=self.main, assets_dir="assets")
        except Exception:
            logger.warning("Retrying without assets_dir")
            ft.app(target=self.main)
