"""Reusable Flet UI components for the YouTube Video Downloader."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import flet as ft


class StatusChip(ft.Container):
    """A small pill-shaped widget that shows the current application status.

    Supported statuses: ``ready``, ``working``, ``done``, ``error``.
    """

    _ICON_MAP = {
        "ready": ft.Icons.CHECK_CIRCLE_OUTLINE,
        "working": ft.Icons.DOWNLOADING,
        "done": ft.Icons.CHECK_CIRCLE,
        "error": ft.Icons.ERROR_OUTLINE,
    }

    _TEXT_MAP = {
        "ready": "Listo",
        "working": "Procesando...",
        "done": "Completado",
        "error": "Error",
    }

    def __init__(self, theme: object) -> None:
        super().__init__()
        self.theme = theme
        self._status = "ready"

        self._color_map = self._build_color_map()

        color = self._color_map["ready"]
        self.status_icon = ft.Icon(self._ICON_MAP["ready"], size=16, color=color)
        self.status_text = ft.Text(
            self._TEXT_MAP["ready"],
            size=12,
            color=color,
            weight=ft.FontWeight.W_500,
        )

        self.content = ft.Row(
            [self.status_icon, self.status_text],
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        self.padding = ft.padding.symmetric(horizontal=12, vertical=6)
        self.border_radius = 20
        self.bgcolor = ft.Colors.with_opacity(0.1, color)
        self.border = ft.border.all(1, ft.Colors.with_opacity(0.2, color))
        self.animate = ft.Animation(300, "easeOut")

    def _build_color_map(self) -> dict[str, str]:
        return {
            "ready": self.theme.text_secondary,
            "working": self.theme.primary_color,
            "done": self.theme.success_color,
            "error": self.theme.error_color,
        }

    def set_status(self, status: str, custom_text: Optional[str] = None) -> None:
        """Update the displayed status.

        Args:
            status: One of ``ready``, ``working``, ``done``, ``error``.
            custom_text: Override the default label text.
        """
        if status not in self._ICON_MAP:
            return

        self._status = status
        self._color_map = self._build_color_map()
        color = self._color_map[status]

        self.bgcolor = ft.Colors.with_opacity(0.1, color)
        self.border = ft.border.all(1, ft.Colors.with_opacity(0.2, color))

        self.status_icon.name = self._ICON_MAP[status]
        self.status_icon.color = color
        self.status_text.value = custom_text or self._TEXT_MAP[status]
        self.status_text.color = color

        self.update()


class ModernButton(ft.Container):
    """A gradient-filled button with hover and press animations."""

    def __init__(
        self,
        text: str,
        on_click: Optional[Callable[..., None]] = None,
        icon: Optional[str] = None,
        width: Optional[int] = None,
        height: int = 50,
        gradient_colors: Optional[list[str]] = None,
        disabled: bool = False,
        tooltip: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._label = text
        self.base_on_click = on_click
        self.icon_name = icon
        self.width = width
        self.height = height
        self.gradient_colors = gradient_colors or ["#6366F1", "#8B5CF6"]
        self.is_disabled = disabled
        self.tooltip = tooltip

        content_items: list[ft.Control] = []
        if self.icon_name:
            content_items.append(ft.Icon(self.icon_name, color="white", size=20))
            if text:
                content_items.append(ft.Container(width=8))
        if text:
            content_items.append(
                ft.Text(text, size=15, weight=ft.FontWeight.W_600, color="white")
            )

        self.content = ft.Row(
            content_items, alignment=ft.MainAxisAlignment.CENTER, spacing=0
        )

        self.gradient = ft.LinearGradient(
            colors=self.gradient_colors,
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
        )
        self.border_radius = 12
        self.on_click = self._handle_click if not disabled else None
        self.on_hover = self._on_hover
        self.animate_scale = ft.Animation(100, "easeOut")
        self.scale = 1.0
        self.opacity = 0.5 if disabled else 1.0
        self.shadow = ft.BoxShadow(
            blur_radius=12,
            color=ft.Colors.with_opacity(0.25, self.gradient_colors[0]),
            offset=ft.Offset(0, 4),
        )
        self.ink = True

    def _handle_click(self, e: ft.ControlEvent) -> None:
        if self.base_on_click:
            self.scale = 0.97
            self.update()

            def _reset() -> None:
                time.sleep(0.1)
                self.scale = 1.0
                self.update()

            threading.Thread(target=_reset, daemon=True).start()
            self.base_on_click(e)

    def _on_hover(self, e: ft.HoverEvent) -> None:
        if not self.is_disabled:
            self.scale = 1.02 if e.data == "true" else 1.0
            self.update()

    def set_disabled(self, disabled: bool) -> None:
        """Enable or disable the button."""
        self.is_disabled = disabled
        self.opacity = 0.5 if disabled else 1.0
        self.on_click = None if disabled else self._handle_click
        self.update()


class TooltipIconButton(ft.IconButton):
    """A thin wrapper around :class:`ft.IconButton` with consistent theming."""

    def __init__(
        self,
        icon: str,
        on_click: Callable[..., None],
        tooltip: str,
        theme: object,
        icon_color: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.icon = icon
        self.on_click = on_click
        self.tooltip = tooltip
        self.icon_color = icon_color or theme.text_secondary
        self.selected_icon_color = theme.primary_color
