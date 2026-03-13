"""Main window layout and logic for the YouTube Video Downloader.

This module builds the entire UI as a single Flet container and wires
up all event handlers for downloading, history, theme switching, etc.
"""

from __future__ import annotations

import base64
import logging
import subprocess
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

import flet as ft

from src.ui.components import ModernButton, StatusChip, TooltipIconButton
from src.ui.theme import AppTheme
from src.utils.downloader import YouTubeDownloader
from src.utils.history import DownloadHistory

logger = logging.getLogger(__name__)


def MainWindow(page: ft.Page) -> ft.Container:
    """Build and return the main application container.

    This function-based component creates all UI elements, wires callbacks,
    and returns a single :class:`ft.Container` to be added to the page.
    """
    theme = AppTheme()
    downloader = YouTubeDownloader()
    history_manager = DownloadHistory()

    # Mutable state via list (avoids ``nonlocal`` for simple scalars)
    download_path = [str(Path.home() / "Downloads")]
    selected_format = ["mp4"]

    # ------------------------------------------------------------------ #
    # Status chip                                                         #
    # ------------------------------------------------------------------ #
    status_chip = StatusChip(theme)
    main_container: Optional[ft.Container] = None  # set at end

    # ------------------------------------------------------------------ #
    # Header                                                              #
    # ------------------------------------------------------------------ #
    title_text = ft.Text(
        "YouTube Downloader",
        size=24,
        weight=ft.FontWeight.BOLD,
        color=theme.text_primary,
    )

    theme_btn = ft.IconButton(
        icon=ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE,
        icon_color=theme.text_primary,
        tooltip="Cambiar tema",
        on_click=lambda e: toggle_theme(e),
    )

    # ------------------------------------------------------------------ #
    # URL input                                                           #
    # ------------------------------------------------------------------ #
    url_field = ft.TextField(
        label="URL del Video",
        hint_text="https://youtube.com/watch?v=...",
        prefix_icon=ft.Icons.LINK,
        border_radius=12,
        bgcolor=theme.input_bgcolor,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=theme.primary_color,
        text_size=15,
        color=theme.text_primary,
        filled=True,
        expand=True,
        on_change=lambda e: on_url_change(e),
        tooltip="Pega aquí el enlace del video de YouTube",
    )

    # ------------------------------------------------------------------ #
    # Format chips                                                        #
    # ------------------------------------------------------------------ #
    format_chips: list[ft.Container] = []

    def _create_format_chip(
        label: str, value: str, icon: str
    ) -> ft.Container:
        is_selected = value == selected_format[0]
        bg = (
            ft.Colors.with_opacity(0.15, theme.primary_color)
            if is_selected
            else theme.input_bgcolor
        )
        border_clr = theme.primary_color if is_selected else ft.Colors.TRANSPARENT
        icon_clr = theme.primary_color if is_selected else theme.text_secondary
        text_clr = theme.text_primary if is_selected else theme.text_secondary
        weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL

        chip = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=18, color=icon_clr),
                    ft.Text(label, color=text_clr, weight=weight),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=10,
            bgcolor=bg,
            border=ft.border.all(1, border_clr),
            on_click=lambda _e, v=value: select_format(v),
            animate=ft.Animation(200, "easeOut"),
            data=value,
            tooltip=f"Descargar en formato {label}",
        )
        format_chips.append(chip)
        return chip

    format_row = ft.Row(
        [
            _create_format_chip("MP4", "mp4", ft.Icons.VIDEO_FILE),
            _create_format_chip("MP3", "mp3", ft.Icons.MUSIC_NOTE),
            _create_format_chip("Original", "original", ft.Icons.FILE_DOWNLOAD),
        ],
        spacing=10,
    )

    # ------------------------------------------------------------------ #
    # Folder selection                                                    #
    # ------------------------------------------------------------------ #
    folder_field = ft.TextField(
        label="Carpeta",
        value=download_path[0],
        prefix_icon=ft.Icons.FOLDER_OPEN,
        border_radius=12,
        bgcolor=theme.input_bgcolor,
        border_color=ft.Colors.TRANSPARENT,
        text_size=14,
        color=theme.text_secondary,
        filled=True,
        read_only=True,
        expand=True,
        tooltip="Carpeta donde se guardarán los archivos",
    )

    folder_btn = TooltipIconButton(
        icon=ft.Icons.DRIVE_FILE_MOVE,
        tooltip="Cambiar carpeta",
        on_click=lambda e: select_folder(e),
        theme=theme,
    )

    # ------------------------------------------------------------------ #
    # Progress                                                            #
    # ------------------------------------------------------------------ #
    progress_bar = ft.ProgressBar(
        value=0,
        color=theme.primary_color,
        bgcolor=theme.input_bgcolor,
        height=6,
        border_radius=3,
    )
    progress_info_text = ft.Text(
        "Esperando…", size=12, color=theme.text_secondary
    )
    progress_percent = ft.Text(
        "0%", size=12, weight=ft.FontWeight.BOLD, color=theme.primary_color
    )

    progress_container = ft.Column(
        [
            ft.Row(
                [
                    progress_info_text,
                    ft.Container(expand=True),
                    progress_percent,
                ]
            ),
            progress_bar,
        ],
        spacing=5,
        visible=False,
    )

    # ------------------------------------------------------------------ #
    # Download button                                                     #
    # ------------------------------------------------------------------ #
    download_btn = ModernButton(
        text="DESCARGAR AHORA",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        gradient_colors=theme.primary_gradient,
        on_click=lambda _e: start_download(),
        width=None,
        height=54,
        tooltip="Iniciar la descarga del video",
    )

    # ------------------------------------------------------------------ #
    # Video info card                                                     #
    # ------------------------------------------------------------------ #
    video_img = ft.Image(
        src_base64=None,
        width=320,
        height=180,
        fit=ft.ImageFit.COVER,
        border_radius=12,
        visible=False,
    )
    video_placeholder = ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.VIDEO_LIBRARY_OUTLINED,
                    size=40,
                    color=theme.text_disabled,
                ),
                ft.Text("Vista previa", color=theme.text_disabled),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=320,
        height=180,
        bgcolor=theme.input_bgcolor,
        border_radius=12,
        alignment=ft.alignment.center,
    )
    video_title = ft.Text(
        "…",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=theme.text_primary,
        no_wrap=True,
    )
    video_author = ft.Text("…", size=14, color=theme.text_secondary)

    video_info_card = ft.Container(
        content=ft.Column(
            [
                ft.Stack([video_placeholder, video_img]),
                ft.Container(height=5),
                video_title,
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PERSON, size=14, color=theme.text_secondary
                        ),
                        video_author,
                    ],
                    spacing=5,
                ),
            ]
        ),
        visible=False,
        animate_opacity=300,
        padding=10,
        border=ft.border.all(
            1, ft.Colors.with_opacity(0.1, theme.border_color)
        ),
        border_radius=12,
    )

    # ------------------------------------------------------------------ #
    # History list                                                        #
    # ------------------------------------------------------------------ #
    history_list = ft.ListView(
        height=220, spacing=10, padding=10, expand=False
    )

    # ================================================================== #
    # Event handlers                                                      #
    # ================================================================== #

    def toggle_theme(_e: ft.ControlEvent) -> None:
        theme.toggle()
        theme.apply_to_page(page)
        theme_btn.icon = (
            ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE
        )
        _refresh_ui_colors()
        page.update()

    def _refresh_ui_colors() -> None:
        """Re-apply theme colours to all controls."""
        url_field.bgcolor = theme.input_bgcolor
        url_field.color = theme.text_primary
        url_field.focused_border_color = theme.primary_color

        folder_field.bgcolor = theme.input_bgcolor
        folder_field.color = theme.text_secondary

        title_text.color = theme.text_primary
        theme_btn.icon_color = theme.text_primary

        select_format(selected_format[0])
        status_chip.set_status(status_chip._status)
        update_history_list()

        if download_panel:
            download_panel.bgcolor = theme.surface_color
            download_panel.shadow = ft.BoxShadow(
                blur_radius=10, color=theme.shadow_color
            )

        if history_panel:
            history_panel.bgcolor = theme.bg_color

        video_info_card.border = ft.border.all(
            1, ft.Colors.with_opacity(0.1, theme.border_color)
        )
        video_title.color = theme.text_primary
        video_author.color = theme.text_secondary

        header_download.color = theme.text_primary
        header_history.color = theme.text_primary
        label_format.color = theme.text_secondary
        label_save.color = theme.text_secondary

    def select_format(value: str) -> None:
        selected_format[0] = value
        for chip in format_chips:
            is_me = chip.data == value
            chip.bgcolor = (
                ft.Colors.with_opacity(0.15, theme.primary_color)
                if is_me
                else theme.input_bgcolor
            )
            chip.border = ft.border.all(
                1,
                theme.primary_color if is_me else ft.Colors.TRANSPARENT,
            )
            row = chip.content
            row.controls[0].color = (
                theme.primary_color if is_me else theme.text_secondary
            )
            row.controls[1].color = (
                theme.text_primary if is_me else theme.text_secondary
            )
            row.controls[1].weight = (
                ft.FontWeight.W_600 if is_me else ft.FontWeight.NORMAL
            )
        page.update()

    # Debounce timer for URL changes
    _url_timer: list[Optional[threading.Timer]] = [None]

    def on_url_change(e: ft.ControlEvent) -> None:
        url = e.control.value.strip()

        # Cancel any pending timer
        if _url_timer[0] is not None:
            _url_timer[0].cancel()

        if downloader.validate_url(url):
            status_chip.set_status("working", "Analizando…")
            video_info_card.visible = True
            video_info_card.opacity = 0.5
            page.update()

            def _delayed_load() -> None:
                downloader.get_video_info(url, _show_video_info)

            _url_timer[0] = threading.Timer(0.6, _delayed_load)
            _url_timer[0].start()
        else:
            status_chip.set_status("ready")
            video_info_card.visible = False
            page.update()

    def _show_video_info(info: Optional[Dict[str, Any]]) -> None:
        if not info:
            status_chip.set_status("error", "URL inválida")
            return

        video_title.value = info.get("title", "Desconocido")
        video_author.value = info.get("uploader", "Desconocido")

        status_chip.set_status("ready")
        video_info_card.opacity = 1.0

        thumb_url = info.get("thumbnail")
        if thumb_url:
            def _load_thumb() -> None:
                try:
                    req = urllib.request.Request(
                        thumb_url,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with urllib.request.urlopen(req, timeout=10) as res:
                        b64 = base64.b64encode(res.read()).decode()
                        video_img.src_base64 = b64
                        video_img.visible = True
                        video_placeholder.visible = False
                        page.update()
                except Exception as exc:
                    logger.debug("Failed to load thumbnail: %s", exc)

            threading.Thread(target=_load_thumb, daemon=True).start()

        page.update()

    def start_download() -> None:
        url = url_field.value.strip()
        if not url:
            return

        download_btn.set_disabled(True)
        status_chip.set_status("working", "Iniciando…")
        progress_container.visible = True
        progress_bar.value = 0
        progress_bar.color = theme.primary_color
        progress_percent.value = "0%"
        page.update()

        def _on_progress(percent: float, text: str) -> None:
            progress_bar.value = percent / 100
            progress_percent.value = f"{int(percent)}%"
            progress_info_text.value = text
            status_chip.set_status("working", "Descargando…")
            page.update()

        def _on_complete(info: Dict[str, Any]) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("done", "¡Listo!")
            progress_bar.color = theme.success_color
            progress_bar.value = 1.0
            progress_percent.value = "100%"
            history_manager.add(info)
            update_history_list()
            page.update()

            # Reset progress after a delay (non-blocking)
            def _reset() -> None:
                import time
                time.sleep(3)
                progress_container.visible = False
                status_chip.set_status("ready")
                progress_bar.color = theme.primary_color
                progress_bar.value = 0
                page.update()

            threading.Thread(target=_reset, daemon=True).start()

        def _on_error(err: str) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("error", "Error")
            progress_bar.color = theme.error_color
            progress_info_text.value = str(err)
            page.update()

        downloader.callback_progress = _on_progress
        downloader.callback_complete = _on_complete
        downloader.callback_error = _on_error

        downloader.download(url, download_path[0], selected_format[0])

    def update_history_list() -> None:
        history_list.controls.clear()
        for item in history_manager.get_all():
            history_list.controls.append(_create_history_item(item))
        page.update()

    def _create_history_item(item: Dict[str, Any]) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE,
                        color=theme.success_color,
                        size=16,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                item.get("title", ""),
                                color=theme.text_primary,
                                weight=ft.FontWeight.W_600,
                                size=13,
                                no_wrap=True,
                            ),
                            ft.Text(
                                f"{item.get('format', '').upper()} • {item.get('date', '')}",
                                color=theme.text_secondary,
                                size=11,
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN,
                        icon_color=theme.text_secondary,
                        icon_size=18,
                        tooltip="Mostrar en carpeta",
                        on_click=lambda _e, p=item.get("path", ""): _open_in_explorer(p),
                    ),
                ],
                spacing=10,
            ),
            padding=10,
            bgcolor=theme.surface_color,
            border_radius=8,
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.1, theme.border_color)
            ),
        )

    def select_folder(_e: ft.ControlEvent) -> None:
        fp = ft.FilePicker(on_result=_on_folder_result)
        page.overlay.append(fp)
        page.update()
        fp.get_directory_path("Seleccionar carpeta")

    def _on_folder_result(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            download_path[0] = e.path
            folder_field.value = e.path
            page.update()

    def _open_in_explorer(path: str) -> None:
        p = Path(path)
        target = p if p.exists() else p.parent
        if target.exists():
            try:
                subprocess.Popen(
                    ["explorer", "/select,", str(target.resolve())]
                )
            except OSError as exc:
                logger.warning("Could not open explorer: %s", exc)

    # ================================================================== #
    # Layout                                                              #
    # ================================================================== #

    header_download = ft.Text(
        "Descargar Video",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=theme.text_primary,
    )
    label_format = ft.Text(
        "Formato",
        color=theme.text_secondary,
        size=13,
        weight=ft.FontWeight.BOLD,
    )
    label_save = ft.Text(
        "Guardar en",
        color=theme.text_secondary,
        size=13,
        weight=ft.FontWeight.BOLD,
    )

    download_panel = ft.Container(
        content=ft.Column(
            [
                header_download,
                ft.Container(height=10),
                url_field,
                ft.Container(height=10),
                label_format,
                format_row,
                ft.Container(height=10),
                label_save,
                ft.Row([folder_field, folder_btn]),
                ft.Container(height=20),
                progress_container,
                ft.Container(height=10),
                ft.Column(
                    [download_btn],
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                ft.Container(height=20),
            ],
            scroll=ft.ScrollMode.HIDDEN,
        ),
        padding=30,
        bgcolor=theme.surface_color,
        border_radius=20,
        shadow=ft.BoxShadow(blur_radius=10, color=theme.shadow_color),
    )

    header_history = ft.Text(
        "Historial",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=theme.text_primary,
    )

    history_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.HISTORY, color=theme.text_primary),
                        header_history,
                    ],
                    spacing=10,
                ),
                ft.Divider(color=theme.border_color),
                history_list,
            ]
        ),
        padding=20,
        bgcolor=theme.bg_color,
        border_radius=20,
    )

    layout = ft.ResponsiveRow(
        [
            ft.Column(
                col=12,
                controls=[
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.PLAY_CIRCLE_FILLED,
                                            color=theme.primary_color,
                                            size=30,
                                        ),
                                        title_text,
                                    ],
                                    spacing=10,
                                ),
                                ft.Row(
                                    [status_chip, theme_btn], spacing=10
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=20, vertical=15
                        ),
                    )
                ],
            ),
            ft.Column(
                col={"sm": 12, "md": 7, "lg": 8},
                controls=[download_panel],
            ),
            ft.Column(
                col={"sm": 12, "md": 5, "lg": 4},
                controls=[video_info_card, history_panel],
            ),
        ]
    )

    # Load existing history on startup
    update_history_list()

    main_container = ft.Container(
        content=layout,
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[theme.bg_color, theme.bg_color],
        ),
        padding=10,
    )

    return main_container
