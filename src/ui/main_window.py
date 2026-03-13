"""Main window layout and logic for the YouTube Video Downloader.

This module builds the entire UI as a single Flet container and wires
up all event handlers for downloading, history, etc.
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import flet as ft

from src.ui.components import ModernButton, StatusChip, TooltipIconButton
from src.ui.theme import AppTheme
from src.utils.downloader import FORMAT_PRESETS, YouTubeDownloader
from src.utils.history import DownloadHistory

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path.home() / ".youtube_downloader_config.json"

# Format metadata for UI display
_FORMAT_UI: List[Dict[str, str]] = [
    {"value": "mp4", "label": "MP4", "desc": "Video", "icon": ft.Icons.MOVIE_OUTLINED},
    {"value": "mkv", "label": "MKV", "desc": "Video HD", "icon": ft.Icons.HD_OUTLINED},
    {"value": "mp3", "label": "MP3", "desc": "Audio", "icon": ft.Icons.MUSIC_NOTE_OUTLINED},
    {"value": "m4a", "label": "M4A", "desc": "Audio HQ", "icon": ft.Icons.HEADPHONES_OUTLINED},
    {"value": "wav", "label": "WAV", "desc": "Audio Raw", "icon": ft.Icons.GRAPHIC_EQ_OUTLINED},
    {"value": "original", "label": "Original", "desc": "Mejor calidad", "icon": ft.Icons.AUTO_AWESOME_OUTLINED},
]


def _load_config() -> Dict[str, Any]:
    try:
        if _CONFIG_PATH.exists():
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_config(data: Dict[str, Any]) -> None:
    try:
        _CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.debug("Could not save config: %s", exc)


def _fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return ""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def MainWindow(page: ft.Page) -> ft.Container:
    """Build and return the main application container."""

    theme = AppTheme()
    downloader = YouTubeDownloader()
    history_manager = DownloadHistory()
    config = _load_config()

    download_path = [str(Path.home() / "Downloads")]
    selected_format = ["mp4"]

    # Apply dark theme on startup
    theme.apply_to_page(page)

    # ================================================================== #
    #  SNACKBAR HELPER                                                    #
    # ================================================================== #

    def show_snackbar(
        message: str,
        icon: str = ft.Icons.INFO_OUTLINED,
        color: Optional[str] = None,
    ) -> None:
        bg = theme.snackbar_bg
        txt_color = theme.snackbar_text
        icon_color = color or theme.primary_color
        page.snack_bar = ft.SnackBar(
            content=ft.Row(
                [
                    ft.Icon(icon, color=icon_color, size=20),
                    ft.Text(message, color=txt_color, size=14, expand=True),
                ],
                spacing=10,
            ),
            bgcolor=bg,
            duration=3000,
        )
        page.snack_bar.open = True
        page.update()

    # ================================================================== #
    #  STATUS CHIP                                                        #
    # ================================================================== #

    status_chip = StatusChip(theme)

    # ================================================================== #
    #  HEADER                                                             #
    # ================================================================== #

    title_text = ft.Text(
        "YouTube Downloader",
        size=22,
        weight=ft.FontWeight.BOLD,
        color=theme.text_primary,
    )

    help_btn = ft.IconButton(
        icon=ft.Icons.HELP_OUTLINE,
        icon_color=theme.text_secondary,
        tooltip="Ayuda",
        icon_size=22,
        on_click=lambda _e: show_help_dialog(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Row([title_text], spacing=10),
                ft.Row([status_chip, help_btn], spacing=4),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
    )

    # ================================================================== #
    #  URL INPUT SECTION                                                  #
    # ================================================================== #

    url_validation_icon = ft.Icon(
        ft.Icons.CIRCLE_OUTLINED, size=20, color=theme.text_disabled, visible=False
    )

    url_field = ft.TextField(
        label="URL del video",
        hint_text="Pega aqui el enlace de YouTube...",
        prefix_icon=ft.Icons.LINK,
        border_radius=12,
        bgcolor=theme.input_bgcolor,
        border_color=theme.input_border,
        focused_border_color=theme.border_focus,
        text_size=15,
        color=theme.text_primary,
        label_style=ft.TextStyle(color=theme.text_secondary),
        hint_style=ft.TextStyle(color=theme.text_disabled),
        filled=True,
        expand=True,
        on_change=lambda e: on_url_change(e),
    )

    paste_btn = ft.IconButton(
        icon=ft.Icons.CONTENT_PASTE,
        icon_color=theme.text_secondary,
        tooltip="Pegar desde portapapeles",
        icon_size=20,
        on_click=lambda _e: paste_from_clipboard(),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )

    url_section = ft.Container(
        content=ft.Row(
            [url_field, url_validation_icon, paste_btn],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=24, right=24, top=8, bottom=8),
    )

    # ================================================================== #
    #  FORMAT SELECTOR                                                    #
    # ================================================================== #

    format_chips: list[ft.Container] = []

    def _create_format_chip(fmt: Dict[str, str]) -> ft.Container:
        value = fmt["value"]
        is_selected = value == selected_format[0]
        bg = (
            ft.Colors.with_opacity(0.15, theme.primary_color)
            if is_selected
            else theme.input_bgcolor
        )
        border_clr = theme.primary_color if is_selected else theme.border_color
        icon_clr = theme.primary_color if is_selected else theme.text_secondary
        text_clr = theme.text_primary if is_selected else theme.text_secondary
        weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL

        chip = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(fmt["icon"], size=14, color=icon_clr),
                    ft.Text(fmt["label"], color=text_clr, weight=weight, size=12),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=7),
            border_radius=8,
            bgcolor=bg,
            border=ft.border.all(1, border_clr),
            on_click=lambda _e, v=value: select_format(v),
            animate=ft.Animation(200, "easeOut"),
            data=value,
            expand=True,
            tooltip=f"{fmt['label']} \u2013 {fmt['desc']}",
        )
        format_chips.append(chip)
        return chip

    # Build compact grid: 3 per row
    _fmt_grid_rows: list[ft.Row] = []
    for _i in range(0, len(_FORMAT_UI), 3):
        _row_fmts = _FORMAT_UI[_i : _i + 3]
        _row_chips = [_create_format_chip(f) for f in _row_fmts]
        # pad incomplete rows so chips don't stretch full width
        while len(_row_chips) < 3:
            _row_chips.append(ft.Container(expand=True))
        _fmt_grid_rows.append(ft.Row(_row_chips, spacing=8))

    format_grid = ft.Column(_fmt_grid_rows, spacing=6)

    format_section_label = ft.Text(
        "Formato de descarga",
        color=theme.text_secondary,
        size=13,
        weight=ft.FontWeight.W_600,
    )

    # ================================================================== #
    #  FOLDER SELECTION                                                   #
    # ================================================================== #

    folder_field = ft.TextField(
        label="Guardar en",
        value=download_path[0],
        prefix_icon=ft.Icons.FOLDER_OUTLINED,
        border_radius=12,
        bgcolor=theme.input_bgcolor,
        border_color=theme.input_border,
        text_size=13,
        color=theme.text_secondary,
        label_style=ft.TextStyle(color=theme.text_secondary),
        filled=True,
        read_only=True,
        expand=True,
    )

    folder_btn = ft.IconButton(
        icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINED,
        tooltip="Cambiar carpeta de destino",
        icon_color=theme.text_secondary,
        icon_size=22,
        on_click=lambda e: select_folder(e),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )

    folder_section = ft.Row(
        [folder_field, folder_btn],
        spacing=8,
    )

    # ================================================================== #
    #  PROGRESS                                                           #
    # ================================================================== #

    progress_bar = ft.ProgressBar(
        value=0,
        color=theme.primary_color,
        bgcolor=ft.Colors.with_opacity(0.15, theme.primary_color),
        height=8,
        border_radius=4,
    )
    progress_info_text = ft.Text(
        "Esperando...", size=12, color=theme.text_secondary
    )
    progress_percent = ft.Text(
        "0%", size=14, weight=ft.FontWeight.BOLD, color=theme.primary_color
    )

    progress_container = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        progress_info_text,
                        ft.Container(expand=True),
                        progress_percent,
                    ],
                ),
                progress_bar,
            ],
            spacing=6,
        ),
        visible=False,
        animate_opacity=ft.Animation(300, "easeOut"),
        padding=ft.padding.only(top=4, bottom=4),
    )

    # ================================================================== #
    #  DOWNLOAD BUTTON                                                    #
    # ================================================================== #

    download_btn = ModernButton(
        text="Descargar",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        gradient_colors=theme.primary_gradient,
        on_click=lambda _e: start_download(),
        width=None,
        height=50,
        disabled=True,
        tooltip="Iniciar la descarga del video",
    )

    # ================================================================== #
    #  VIDEO INFO CARD                                                    #
    # ================================================================== #

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
                ft.Icon(ft.Icons.VIDEO_LIBRARY_OUTLINED, size=36, color=theme.text_disabled),
                ft.Text("Vista previa del video", color=theme.text_disabled, size=13),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        width=320,
        height=180,
        bgcolor=theme.input_bgcolor,
        border_radius=12,
        alignment=ft.alignment.center,
    )

    video_loading = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=30, height=30, stroke_width=3, color=theme.primary_color),
                ft.Text("Cargando info...", color=theme.text_secondary, size=12),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        width=320,
        height=180,
        bgcolor=theme.input_bgcolor,
        border_radius=12,
        alignment=ft.alignment.center,
        visible=False,
    )

    video_title = ft.Text(
        "", size=15, weight=ft.FontWeight.W_600, color=theme.text_primary,
        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
    )
    video_author = ft.Text("", size=13, color=theme.text_secondary)
    video_duration_text = ft.Text("", size=12, color=theme.text_secondary)
    video_meta_row = ft.Row(
        [
            ft.Row(
                [ft.Icon(ft.Icons.PERSON_OUTLINED, size=14, color=theme.text_secondary), video_author],
                spacing=4,
            ),
            ft.Row(
                [ft.Icon(ft.Icons.TIMER_OUTLINED, size=14, color=theme.text_secondary), video_duration_text],
                spacing=4,
            ),
        ],
        spacing=16,
    )

    video_info_card = ft.Container(
        content=ft.Column(
            [
                ft.Stack([video_placeholder, video_loading, video_img]),
                ft.Container(height=8),
                video_title,
                video_meta_row,
            ],
            spacing=4,
        ),
        visible=False,
        animate_opacity=300,
        padding=16,
        bgcolor=theme.surface_color,
        border=ft.border.all(1, theme.border_color),
        border_radius=16,
        shadow=ft.BoxShadow(blur_radius=8, color=theme.shadow_color),
    )

    # ================================================================== #
    #  HISTORY                                                            #
    # ================================================================== #

    history_list = ft.ListView(height=300, spacing=8, padding=8, auto_scroll=False)

    history_empty_msg = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.HISTORY_OUTLINED, size=32, color=theme.text_disabled),
                ft.Text("Sin descargas recientes", color=theme.text_disabled, size=13),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.alignment.center,
        padding=30,
    )

    header_history = ft.Text(
        "Historial", size=16, weight=ft.FontWeight.W_600, color=theme.text_primary
    )

    clear_history_btn = ft.TextButton(
        text="Limpiar",
        icon=ft.Icons.DELETE_SWEEP_OUTLINED,
        style=ft.ButtonStyle(color=theme.text_secondary),
        on_click=lambda _e: clear_history(),
        tooltip="Eliminar todo el historial",
    )

    history_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [ft.Icon(ft.Icons.HISTORY, color=theme.text_secondary, size=20), header_history],
                            spacing=8,
                        ),
                        clear_history_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=theme.divider_color, height=1),
                history_list,
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor=theme.surface_color,
        border_radius=16,
        border=ft.border.all(1, theme.border_color),
    )

    # ================================================================== #
    #  DOWNLOAD PANEL (left side card)                                    #
    # ================================================================== #

    download_panel = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Descargar video",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=theme.text_primary,
                    ),
                    padding=ft.padding.symmetric(horizontal=24),
                ),
                ft.Container(height=12),
                url_section,
                ft.Container(height=16),
                ft.Container(
                    content=ft.Column(
                        [format_section_label, ft.Container(height=6), format_grid],
                        spacing=0,
                    ),
                    padding=ft.padding.symmetric(horizontal=24),
                ),
                ft.Container(height=16),
                ft.Container(
                    content=folder_section,
                    padding=ft.padding.symmetric(horizontal=24),
                ),
                ft.Container(height=16),
                ft.Container(
                    content=progress_container,
                    padding=ft.padding.symmetric(horizontal=24),
                ),
                ft.Container(
                    content=ft.Column(
                        [download_btn],
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    padding=ft.padding.symmetric(horizontal=24),
                ),
                ft.Container(height=12),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.only(top=20, bottom=20),
        bgcolor=theme.surface_color,
        border_radius=20,
        border=ft.border.all(1, theme.border_color),
        shadow=ft.BoxShadow(blur_radius=12, color=theme.shadow_color, offset=ft.Offset(0, 2)),
    )

    # ================================================================== #
    #  FOOTER                                                             #
    # ================================================================== #

    footer = ft.Container(
        content=ft.Row(
            [
                ft.Text("YouTube Downloader v2.0", size=11, color=theme.text_disabled),
                ft.Text("Powered by yt-dlp", size=11, color=theme.text_disabled),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=8),
    )

    # ================================================================== #
    #  EVENT HANDLERS                                                     #
    # ================================================================== #

    def select_format(value: str) -> None:
        selected_format[0] = value
        for chip in format_chips:
            is_me = chip.data == value
            chip.bgcolor = (
                ft.Colors.with_opacity(0.15, theme.primary_color) if is_me else theme.input_bgcolor
            )
            chip.border = ft.border.all(1, theme.primary_color if is_me else theme.border_color)
            row = chip.content
            row.controls[0].color = theme.primary_color if is_me else theme.text_secondary
            row.controls[1].color = theme.text_primary if is_me else theme.text_secondary
            row.controls[1].weight = ft.FontWeight.W_600 if is_me else ft.FontWeight.NORMAL
        page.update()

    _url_timer: list[Optional[threading.Timer]] = [None]

    def on_url_change(e: ft.ControlEvent) -> None:
        url = e.control.value.strip()

        if _url_timer[0] is not None:
            _url_timer[0].cancel()

        if downloader.validate_url(url):
            url_validation_icon.visible = True
            url_validation_icon.name = ft.Icons.CHECK_CIRCLE
            url_validation_icon.color = theme.success_color
            download_btn.set_disabled(False)
            download_btn.gradient_colors = theme.primary_gradient
            download_btn.gradient = ft.LinearGradient(
                colors=theme.primary_gradient,
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
            )

            status_chip.set_status("working", "Analizando...")
            video_info_card.visible = True
            video_loading.visible = True
            video_img.visible = False
            video_placeholder.visible = False
            page.update()

            def _delayed_load() -> None:
                downloader.get_video_info(url, _show_video_info)

            _url_timer[0] = threading.Timer(0.6, _delayed_load)
            _url_timer[0].start()
        else:
            has_text = len(url) > 0
            url_validation_icon.visible = has_text
            if has_text:
                url_validation_icon.name = ft.Icons.CANCEL
                url_validation_icon.color = theme.error_color
            download_btn.set_disabled(True)
            status_chip.set_status("ready")
            video_info_card.visible = False
            video_loading.visible = False
            page.update()

    def _show_video_info(info: Optional[Dict[str, Any]]) -> None:
        video_loading.visible = False
        if not info:
            status_chip.set_status("error", "No se pudo obtener info")
            video_info_card.visible = False
            page.update()
            return

        video_title.value = info.get("title", "Desconocido")
        video_author.value = info.get("uploader", "Desconocido")
        duration = info.get("duration", 0)
        video_duration_text.value = _fmt_duration(duration) if duration else ""

        status_chip.set_status("ready")
        video_info_card.opacity = 1.0

        thumb_url = info.get("thumbnail")
        if thumb_url:
            def _load_thumb() -> None:
                try:
                    req = urllib.request.Request(
                        thumb_url, headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with urllib.request.urlopen(req, timeout=10) as res:
                        b64 = base64.b64encode(res.read()).decode()
                        video_img.src_base64 = b64
                        video_img.visible = True
                        video_placeholder.visible = False
                        page.update()
                except Exception as exc:
                    logger.debug("Failed to load thumbnail: %s", exc)
                    video_placeholder.visible = True
                    page.update()

            threading.Thread(target=_load_thumb, daemon=True).start()
        else:
            video_placeholder.visible = True

        page.update()

    def paste_from_clipboard() -> None:
        url_field.focus()
        page.update()
        show_snackbar(
            "Usa Ctrl+V para pegar el enlace",
            ft.Icons.CONTENT_PASTE,
            theme.info_color,
        )

    def start_download() -> None:
        url = url_field.value.strip()
        if not url:
            return

        download_btn.set_disabled(True)
        status_chip.set_status("working", "Iniciando...")
        progress_container.visible = True
        progress_bar.value = 0
        progress_bar.color = theme.primary_color
        progress_percent.value = "0%"
        progress_info_text.value = "Preparando descarga..."
        show_snackbar("Descarga iniciada", ft.Icons.DOWNLOAD_ROUNDED, theme.info_color)
        page.update()

        def _on_progress(percent: float, text: str) -> None:
            progress_bar.value = percent / 100
            progress_percent.value = f"{int(percent)}%"
            progress_info_text.value = text
            status_chip.set_status("working", f"Descargando {int(percent)}%")
            page.update()

        def _on_complete(info: Dict[str, Any]) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("done", "Descarga completa")
            progress_bar.color = theme.success_color
            progress_bar.value = 1.0
            progress_percent.value = "100%"
            progress_percent.color = theme.success_color
            progress_info_text.value = "Descarga completada"
            history_manager.add(info)
            update_history_list()
            show_snackbar(
                "Descarga completada correctamente",
                ft.Icons.CHECK_CIRCLE,
                theme.success_color,
            )
            page.update()

            def _reset() -> None:
                import time
                time.sleep(4)
                progress_container.visible = False
                status_chip.set_status("ready")
                progress_bar.color = theme.primary_color
                progress_bar.value = 0
                progress_percent.value = "0%"
                progress_percent.color = theme.primary_color
                progress_info_text.value = "Esperando..."
                page.update()

            threading.Thread(target=_reset, daemon=True).start()

        def _on_error(err: str) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("error", "Error en descarga")
            progress_bar.color = theme.error_color
            progress_info_text.value = str(err)
            progress_percent.color = theme.error_color
            show_snackbar(
                f"Error: {err[:80]}",
                ft.Icons.ERROR_OUTLINE,
                theme.error_color,
            )
            page.update()

        downloader.callback_progress = _on_progress
        downloader.callback_complete = _on_complete
        downloader.callback_error = _on_error

        downloader.download(url, download_path[0], selected_format[0])

    def update_history_list() -> None:
        history_list.controls.clear()
        entries = history_manager.get_all()
        if not entries:
            history_list.controls.append(history_empty_msg)
        else:
            for item in entries:
                history_list.controls.append(_create_history_item(item))
        page.update()

    def _create_history_item(item: Dict[str, Any]) -> ft.Container:
        fmt = item.get("format", "mp4").upper()
        title = item.get("title", "Sin titulo")
        date = item.get("date", "")
        status = item.get("status", "completed")
        icon = ft.Icons.CHECK_CIRCLE if status == "completed" else ft.Icons.ERROR_OUTLINE
        icon_color = theme.success_color if status == "completed" else theme.error_color

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=icon_color, size=18),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                color=theme.text_primary,
                                weight=ft.FontWeight.W_500,
                                size=13,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(fmt, size=10, color=theme.primary_color, weight=ft.FontWeight.W_600),
                                        bgcolor=ft.Colors.with_opacity(0.1, theme.primary_color),
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4,
                                    ),
                                    ft.Text(date, color=theme.text_disabled, size=10),
                                ],
                                spacing=8,
                            ),
                        ],
                        expand=True,
                        spacing=3,
                    ),
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN_OUTLINED,
                        icon_color=theme.text_secondary,
                        icon_size=18,
                        tooltip="Abrir en explorador",
                        on_click=lambda _e, p=item.get("path", ""): _open_in_explorer(p),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=theme.card_color,
            border_radius=12,
            border=ft.border.all(1, theme.border_color),
        )

    def clear_history() -> None:
        history_manager.clear()
        update_history_list()
        show_snackbar("Historial limpiado", ft.Icons.DELETE_SWEEP_OUTLINED, theme.warning_color)

    def select_folder(_e: ft.ControlEvent) -> None:
        fp = ft.FilePicker(on_result=_on_folder_result)
        page.overlay.append(fp)
        page.update()
        fp.get_directory_path("Seleccionar carpeta de destino")

    def _on_folder_result(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            download_path[0] = e.path
            folder_field.value = e.path
            show_snackbar(
                "Carpeta actualizada",
                ft.Icons.FOLDER_OUTLINED,
                theme.success_color,
            )
            page.update()

    def _open_in_explorer(path: str) -> None:
        p = Path(path)
        target = p if p.exists() else p.parent
        if target.exists():
            try:
                subprocess.Popen(["explorer", "/select,", str(target.resolve())])
            except OSError as exc:
                logger.warning("Could not open explorer: %s", exc)

    # ================================================================== #
    #  HELP DIALOG                                                        #
    # ================================================================== #

    def show_help_dialog() -> None:
        steps = [
            (ft.Icons.CONTENT_COPY, "Copia el enlace del video de YouTube"),
            (ft.Icons.LINK, "Pegalo en el campo de URL de arriba"),
            (ft.Icons.TUNE, "Selecciona el formato deseado (MP4, MP3, etc.)"),
            (ft.Icons.DOWNLOAD_ROUNDED, "Presiona el boton Descargar y espera"),
            (ft.Icons.FOLDER_OUTLINED, "El archivo se guardara en tu carpeta de Descargas"),
        ]

        step_controls = []
        for i, (icon, text) in enumerate(steps, 1):
            step_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(str(i), size=14, weight=ft.FontWeight.BOLD, color=theme.text_on_primary),
                                width=28,
                                height=28,
                                border_radius=14,
                                bgcolor=theme.primary_color,
                                alignment=ft.alignment.center,
                            ),
                            ft.Icon(icon, size=22, color=theme.primary_color),
                            ft.Text(text, size=14, color=theme.text_primary, expand=True),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=10),
                )
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HELP_OUTLINE, color=theme.primary_color, size=24),
                    ft.Text("Como usar YouTube Downloader", size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(step_controls, spacing=4, scroll=ft.ScrollMode.AUTO),
                width=450,
                height=300,
            ),
            actions=[
                ft.TextButton(
                    "Entendido",
                    on_click=lambda _e: _close_help(),
                    style=ft.ButtonStyle(color=theme.primary_color),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def _close_help() -> None:
            dialog.open = False
            page.update()

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ================================================================== #
    #  LAYOUT                                                             #
    # ================================================================== #

    layout = ft.Column(
        [
            header,
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=download_panel,
                            expand=2,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    video_info_card,
                                    ft.Container(height=12),
                                    history_panel,
                                ],
                                spacing=0,
                            ),
                            expand=1,
                        ),
                    ],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.padding.symmetric(horizontal=16),
                expand=True,
            ),
            footer,
        ],
        spacing=0,
        expand=True,
    )

    # Load existing history on startup
    update_history_list()

    # Show help on first launch
    if not config.get("help_shown"):
        config["help_shown"] = True
        _save_config(config)

        def _show_initial_help() -> None:
            import time
            time.sleep(0.5)
            show_help_dialog()

        threading.Thread(target=_show_initial_help, daemon=True).start()

    main_container = ft.Container(
        content=layout,
        expand=True,
        bgcolor=theme.bg_color,
    )

    return main_container
