"""Flet application entry point.

Configures the page (window size, theme, etc.) and adds the main UI.
"""

from __future__ import annotations

import inspect
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

        async def _center_window_async() -> None:
            try:
                await page.window.center()
            except AttributeError:
                logger.debug("page.window.center() not supported by this Flet version")

        page.title = "YouTube Video Downloader"

        # Configure window. The ``page.window`` API has changed across Flet
        # versions; we degrade gracefully if any attribute is missing.
        try:
            page.window.width = 1180
            page.window.height = 820
            page.window.min_width = 980
            page.window.min_height = 720
        except AttributeError:
            logger.debug("page.window attributes not supported by this Flet version")

        center_window = getattr(page.window, "center", None)
        if callable(center_window):
            run_task = getattr(page, "run_task", None)
            if callable(run_task):
                run_task(_center_window_async)
            else:
                result = center_window()
                if inspect.isawaitable(result):
                    logger.debug("Skipping async page.window.center() without page.run_task")

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
                            ft.Text("Error al cargar la aplicación:", size=20),
                            ft.Text(str(exc), size=14, selectable=True),
                            ft.Text(
                                "Vuelve a iniciar la aplicación. Si el problema "
                                "continúa, revisa los logs en la consola.",
                                size=12,
                                color="#94A3B8",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                    padding=ft.Padding.all(24),
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
