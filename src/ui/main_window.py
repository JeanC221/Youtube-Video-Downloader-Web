"""Main window layout and logic for the YouTube Video Downloader.

This module builds the entire UI as a single Flet container and wires
up all event handlers for downloading, history, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import shutil as _shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from src.ui.components import ModernButton, StatusChip, TooltipIconButton
from src.ui.theme import AppTheme
from src.utils.downloader import FORMAT_PRESETS, YouTubeDownloader
from src.utils.history import DownloadHistory

logger = logging.getLogger(__name__)

# Design tokens are re-imported locally to avoid touching unrelated imports.
from src.ui.theme import DesignTokens as DT  # noqa: E402

_CONFIG_PATH = Path.home() / ".youtube_downloader_config.json"

# Format metadata for UI display (one entry per FORMAT_PRESETS key).
_FORMAT_UI: List[Dict[str, Any]] = [
    {"value": "mp4", "label": "MP4", "desc": "Vídeo (H.264 + AAC)", "icon": ft.Icons.MOVIE_OUTLINED},
    {"value": "mkv", "label": "MKV", "desc": "Vídeo de máxima calidad (multi-pista)", "icon": ft.Icons.HD_OUTLINED},
    {"value": "webm", "label": "WebM", "desc": "Vídeo VP9/Opus, navegador-friendly", "icon": ft.Icons.PUBLIC_OUTLINED},
    {"value": "mp3", "label": "MP3", "desc": "Audio (compatible)", "icon": ft.Icons.MUSIC_NOTE_OUTLINED},
    {"value": "m4a", "label": "M4A", "desc": "Audio AAC (alta calidad)", "icon": ft.Icons.HEADPHONES_OUTLINED},
    {"value": "wav", "label": "WAV", "desc": "Audio sin pérdida (archivos grandes)", "icon": ft.Icons.GRAPHIC_EQ_OUTLINED},
    {"value": "original", "label": "Original", "desc": "Mejor calidad disponible (sin reconvertir)", "icon": ft.Icons.AUTO_AWESOME_OUTLINED},
]

# Sanity check: every UI option must map to a known preset.
assert {f["value"] for f in _FORMAT_UI} == set(FORMAT_PRESETS.keys()), (
    "_FORMAT_UI and FORMAT_PRESETS are out of sync"
)


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


def _read_clipboard() -> str:
    """Read the system clipboard cross-platform.

    Returns an empty string if the clipboard is empty or unsupported.
    Never raises.
    """
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=2
            )
            return result.stdout
        if system == "Windows":
            # PowerShell prints a trailing newline; strip when caller wants
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return result.stdout
        # Linux / *nix
        for cmd in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
            if _shutil.which(cmd[0]):
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                return result.stdout
        return ""
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Clipboard read failed: %s", exc)
        return ""


def _download_thumbnail_bytes(url: str) -> Optional[bytes]:
    """Fetch thumbnail bytes without touching UI state."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.read()
    except Exception as exc:
        logger.debug("Failed to load thumbnail: %s", exc)
        return None


async def _run_ui_callback(callback: Callable[..., None], *args: Any) -> None:
    """Execute a plain callback inside Flet's task loop."""
    callback(*args)


def _schedule_on_ui(page: ft.Page, callback: Callable[..., None], *args: Any) -> None:
    """Marshal a UI mutation back onto the page task loop when available."""
    run_task = getattr(page, "run_task", None)
    if callable(run_task):
        run_task(_run_ui_callback, callback, *args)
        return
    callback(*args)


_FRIENDLY_ERROR_PATTERNS = [
    (re.compile(r"Video unavailable|This video is not available", re.I),
     "El vídeo no está disponible (puede haber sido eliminado o ser privado)."),
    (re.compile(r"Sign in to confirm your age|age[- ]?restricted", re.I),
     "El vídeo está restringido por edad y requiere iniciar sesión."),
    (re.compile(r"is private", re.I),
     "El vídeo es privado y no se puede descargar."),
    (re.compile(r"members[- ]only", re.I),
     "El vídeo es solo para miembros del canal."),
    (re.compile(r"This live event will begin", re.I),
     "Es una emisión en directo programada que aún no ha comenzado."),
    (re.compile(r"live", re.I),
     "Las emisiones en directo no se pueden descargar mientras están en curso."),
    (re.compile(r"region|country|geo", re.I),
     "El vídeo no está disponible en tu región."),
    (re.compile(r"HTTP Error 429|Too Many Requests", re.I),
     "YouTube está limitando las peticiones. Espera unos minutos e inténtalo de nuevo."),
    (re.compile(r"timed? out|timeout", re.I),
     "Se agotó el tiempo de espera. Comprueba tu conexión a internet."),
    (re.compile(r"name resolution|getaddrinfo|Network is unreachable|Failed to establish", re.I),
     "No hay conexión a internet o YouTube no responde."),
    (re.compile(r"Permission denied|EACCES|EPERM", re.I),
     "Permisos insuficientes para escribir en la carpeta de destino."),
    (re.compile(r"No space left|ENOSPC", re.I),
     "No queda espacio libre en el disco."),
    (re.compile(r"ffmpeg.*not found|ffprobe.*not found", re.I),
     "No se encontró ffmpeg. Reinstala la aplicación o ejecuta `pip install -U imageio-ffmpeg`."),
    (re.compile(r"playlist", re.I),
     "Las listas de reproducción no están soportadas: descarga vídeos uno a uno."),
    (re.compile(r"unsupported url|is not a valid URL", re.I),
     "El enlace no es un vídeo de YouTube válido."),
]


def friendly_error(message: str) -> str:
    """Translate a raw yt-dlp/ffmpeg error message into a user-friendly text."""
    if not message:
        return "Error desconocido al descargar el vídeo."
    for pattern, friendly in _FRIENDLY_ERROR_PATTERNS:
        if pattern.search(message):
            return friendly
    # Fallback: trim very long messages
    short = message.strip().splitlines()[0]
    if len(short) > 160:
        short = short[:157] + "…"
    return f"Error: {short}"


def MainWindow(page: ft.Page) -> ft.Container:
    """Build and return the main application container."""

    config = _load_config()

    theme = AppTheme(is_dark=bool(config.get("is_dark", True)))
    downloader = YouTubeDownloader()
    history_manager = DownloadHistory()

    saved_dir = config.get("download_dir")
    default_dir = str(Path.home() / "Downloads")
    if not saved_dir or not Path(saved_dir).is_dir():
        saved_dir = default_dir if Path(default_dir).is_dir() else str(Path.home())
    download_path = [saved_dir]

    saved_format = config.get("format", "mp4")
    if saved_format not in FORMAT_PRESETS:
        saved_format = "mp4"
    selected_format = [saved_format]

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
        snack = ft.SnackBar(
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
        page.show_dialog(snack)

    # ================================================================== #
    #  STATUS CHIP                                                        #
    # ================================================================== #

    status_chip = StatusChip(theme)

    # ================================================================== #
    #  HEADER                                                             #
    # ================================================================== #

    brand_mark = ft.Container(
        content=ft.Icon(
            ft.Icons.PLAY_CIRCLE_FILLED,
            size=28,
            color=theme.text_on_primary,
        ),
        width=40,
        height=40,
        border_radius=DT.RADIUS_MD,
        gradient=ft.LinearGradient(
            colors=theme.primary_gradient,
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
        ),
        alignment=ft.Alignment(0, 0),
        shadow=ft.BoxShadow(
            blur_radius=14,
            color=ft.Colors.with_opacity(0.35, theme.primary_gradient[0]),
            offset=ft.Offset(0, 4),
        ),
    )

    title_text = ft.Text(
        "YouTube Downloader",
        size=DT.FONT_H2,
        weight=DT.WEIGHT_BOLD,
        color=theme.text_primary,
    )
    subtitle_text = ft.Text(
        "Descarga audio y vídeo de YouTube en segundos",
        size=DT.FONT_BODY_SM,
        color=theme.text_secondary,
    )

    help_btn = ft.IconButton(
        icon=ft.Icons.HELP_OUTLINE,
        icon_color=theme.text_secondary,
        tooltip="Cómo usar la aplicación",
        icon_size=22,
        on_click=lambda _e: show_help_dialog(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=DT.RADIUS_SM),
            bgcolor={ft.ControlState.HOVERED: theme.hover_color},
        ),
    )

    theme_btn = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_OUTLINED if theme.is_dark else ft.Icons.DARK_MODE_OUTLINED,
        icon_color=theme.text_secondary,
        tooltip="Cambiar tema (claro/oscuro)",
        icon_size=22,
        on_click=lambda _e: toggle_theme(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=DT.RADIUS_SM),
            bgcolor={ft.ControlState.HOVERED: theme.hover_color},
        ),
    )

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                brand_mark,
                                ft.Column(
                                    [title_text, subtitle_text],
                                    spacing=2,
                                    tight=True,
                                ),
                            ],
                            spacing=DT.SPACING_MD,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row([status_chip, theme_btn, help_btn], spacing=DT.SPACING_XS),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    height=1,
                    bgcolor=theme.divider_color,
                    margin=ft.margin.only(top=DT.SPACING_MD),
                ),
            ],
            spacing=0,
        ),
        padding=ft.padding.symmetric(horizontal=DT.SPACING_XL, vertical=DT.SPACING_LG),
    )

    # ================================================================== #
    #  URL INPUT SECTION                                                  #
    # ================================================================== #

    url_validation_icon = ft.Icon(
        ft.Icons.CIRCLE_OUTLINED, size=20, color=theme.text_disabled, visible=False
    )

    url_field = ft.TextField(
        label="URL del vídeo",
        hint_text="Pega aquí el enlace de YouTube (https://youtube.com/...)",
        prefix_icon=ft.Icons.LINK,
        border_radius=DT.RADIUS_MD,
        bgcolor=theme.input_bgcolor,
        border_color=theme.input_border,
        focused_border_color=theme.border_focus,
        focused_border_width=2,
        cursor_color=theme.primary_color,
        cursor_width=1.5,
        text_size=DT.FONT_SUBTITLE,
        color=theme.text_primary,
        label_style=ft.TextStyle(color=theme.text_secondary, weight=DT.WEIGHT_MEDIUM),
        hint_style=ft.TextStyle(color=theme.text_muted),
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
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=DT.RADIUS_SM),
            bgcolor={ft.ControlState.HOVERED: theme.hover_color},
        ),
    )

    url_section = ft.Container(
        content=ft.Row(
            [url_field, url_validation_icon, paste_btn],
            spacing=DT.SPACING_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=DT.SPACING_XL, right=DT.SPACING_XL, top=DT.SPACING_SM, bottom=DT.SPACING_SM),
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
                    ft.Icon(fmt["icon"], size=16, color=icon_clr),
                    ft.Text(fmt["label"], color=text_clr, weight=weight, size=DT.FONT_BODY_SM),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=DT.SPACING_XS + 2,
            ),
            padding=ft.padding.symmetric(horizontal=DT.SPACING_MD, vertical=10),
            border_radius=DT.RADIUS_SM,
            bgcolor=bg,
            border=ft.border.all(1.5 if is_selected else 1, border_clr),
            on_click=lambda _e, v=value: select_format(v),
            animate=ft.Animation(180, "easeOut"),
            data=value,
            expand=True,
            tooltip=f"{fmt['label']} \u2013 {fmt['desc']}",
            ink=True,
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
        "FORMATO DE DESCARGA",
        color=theme.text_muted,
        size=DT.FONT_CAPTION,
        weight=DT.WEIGHT_SEMIBOLD,
    )

    # ================================================================== #
    #  FOLDER SELECTION                                                   #
    # ================================================================== #

    folder_field = ft.TextField(
        label="Guardar en",
        value=download_path[0],
        prefix_icon=ft.Icons.FOLDER_OUTLINED,
        border_radius=DT.RADIUS_MD,
        bgcolor=theme.input_bgcolor,
        border_color=theme.input_border,
        text_size=DT.FONT_BODY_SM,
        color=theme.text_secondary,
        label_style=ft.TextStyle(color=theme.text_secondary, weight=DT.WEIGHT_MEDIUM),
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
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=DT.RADIUS_SM),
            bgcolor={ft.ControlState.HOVERED: theme.hover_color},
        ),
    )

    folder_section = ft.Row(
        [folder_field, folder_btn],
        spacing=DT.SPACING_SM,
    )

    # ================================================================== #
    #  PROGRESS                                                           #
    # ================================================================== #

    progress_bar = ft.ProgressBar(
        value=0,
        color=theme.primary_color,
        bgcolor=ft.Colors.with_opacity(0.15, theme.primary_color),
        height=6,
        border_radius=DT.RADIUS_SM,
    )
    progress_info_text = ft.Text(
        "Esperando enlace…",
        size=DT.FONT_BODY_SM,
        color=theme.text_secondary,
    )
    progress_percent = ft.Text(
        "0%",
        size=DT.FONT_SUBTITLE,
        weight=DT.WEIGHT_BOLD,
        color=theme.primary_color,
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
            spacing=DT.SPACING_SM,
        ),
        visible=False,
        animate_opacity=ft.Animation(300, "easeOut"),
        padding=ft.padding.symmetric(horizontal=DT.SPACING_MD, vertical=DT.SPACING_MD),
        bgcolor=theme.surface_subtle,
        border=ft.border.all(1, theme.border_color),
        border_radius=DT.RADIUS_MD,
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
        src=b"",
        width=320,
        height=180,
        fit=ft.BoxFit.COVER,
        border_radius=DT.RADIUS_MD,
        visible=False,
    )
    video_placeholder = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.VIDEO_LIBRARY_OUTLINED, size=40, color=theme.text_disabled),
                ft.Text(
                    "Vista previa del video",
                    color=theme.text_disabled,
                    size=DT.FONT_BODY_SM,
                    weight=DT.WEIGHT_MEDIUM,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=DT.SPACING_SM,
        ),
        width=320,
        height=180,
        bgcolor=theme.surface_subtle,
        border=ft.border.all(1, theme.border_color),
        border_radius=DT.RADIUS_MD,
        alignment=ft.Alignment(0, 0),
    )

    video_loading = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=30, height=30, stroke_width=3, color=theme.primary_color),
                ft.Text("Cargando info...", color=theme.text_secondary, size=DT.FONT_BODY_SM),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=DT.SPACING_SM,
        ),
        width=320,
        height=180,
        bgcolor=theme.surface_subtle,
        border=ft.border.all(1, theme.border_color),
        border_radius=DT.RADIUS_MD,
        alignment=ft.Alignment(0, 0),
        visible=False,
    )

    video_title = ft.Text(
        "",
        size=DT.FONT_SUBTITLE,
        weight=DT.WEIGHT_SEMIBOLD,
        color=theme.text_primary,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    video_author = ft.Text("", size=DT.FONT_BODY_SM, color=theme.text_secondary)
    video_duration_text = ft.Text("", size=DT.FONT_BODY_SM, color=theme.text_secondary)
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
                ft.Container(height=DT.SPACING_MD),
                video_title,
                ft.Container(height=DT.SPACING_XS),
                video_meta_row,
            ],
            spacing=0,
        ),
        visible=False,
        animate_opacity=300,
        padding=DT.SPACING_LG,
        bgcolor=theme.surface_elevated,
        border=ft.border.all(1, theme.border_color),
        border_radius=DT.RADIUS_LG,
        shadow=theme.elevation_1(),
    )

    # ================================================================== #
    #  HISTORY                                                            #
    # ================================================================== #

    history_list = ft.ListView(
        height=300,
        spacing=DT.SPACING_SM,
        padding=ft.padding.symmetric(horizontal=0, vertical=DT.SPACING_SM),
        auto_scroll=False,
    )

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
        alignment=ft.Alignment(0, 0),
        padding=30,
    )

    header_history = ft.Text(
        "Historial",
        size=DT.FONT_TITLE,
        weight=DT.WEIGHT_SEMIBOLD,
        color=theme.text_primary,
    )

    clear_history_btn = ft.TextButton(
        "Limpiar",
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
                            [
                                ft.Icon(ft.Icons.HISTORY, color=theme.text_secondary, size=20),
                                header_history,
                            ],
                            spacing=DT.SPACING_SM,
                        ),
                        clear_history_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=theme.divider_color, height=1),
                history_list,
            ],
            spacing=DT.SPACING_SM,
        ),
        padding=DT.SPACING_LG,
        bgcolor=theme.surface_elevated,
        border_radius=DT.RADIUS_LG,
        border=ft.border.all(1, theme.border_color),
        shadow=theme.elevation_1(),
    )

    # ================================================================== #
    #  DOWNLOAD PANEL (left side card)                                    #
    # ================================================================== #

    download_panel = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Descargar vídeo",
                        size=DT.FONT_TITLE,
                        weight=DT.WEIGHT_BOLD,
                        color=theme.text_primary,
                    ),
                    padding=ft.padding.symmetric(horizontal=DT.SPACING_XL),
                ),
                ft.Container(height=DT.SPACING_MD),
                url_section,
                ft.Container(height=DT.SPACING_LG),
                ft.Container(
                    content=ft.Column(
                        [format_section_label, ft.Container(height=DT.SPACING_SM), format_grid],
                        spacing=0,
                    ),
                    padding=ft.padding.symmetric(horizontal=DT.SPACING_XL),
                ),
                ft.Container(height=DT.SPACING_LG),
                ft.Container(
                    content=folder_section,
                    padding=ft.padding.symmetric(horizontal=DT.SPACING_XL),
                ),
                ft.Container(height=DT.SPACING_LG),
                ft.Container(
                    content=progress_container,
                    padding=ft.padding.symmetric(horizontal=DT.SPACING_XL),
                ),
                ft.Container(height=DT.SPACING_SM),
                ft.Container(
                    content=ft.Column(
                        [download_btn],
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    padding=ft.padding.symmetric(horizontal=DT.SPACING_XL),
                ),
                ft.Container(height=DT.SPACING_MD),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.only(top=DT.SPACING_XL, bottom=DT.SPACING_XL),
        bgcolor=theme.surface_elevated,
        border_radius=DT.RADIUS_XL,
        border=ft.border.all(1, theme.border_color),
        shadow=theme.elevation_2(),
    )

    # ================================================================== #
    #  FOOTER                                                             #
    # ================================================================== #

    footer = ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    "YouTube Downloader v2.0",
                    size=DT.FONT_CAPTION,
                    color=theme.text_muted,
                    weight=DT.WEIGHT_MEDIUM,
                ),
                ft.Text(
                    "Powered by yt-dlp",
                    size=DT.FONT_CAPTION,
                    color=theme.text_muted,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=DT.SPACING_XL, vertical=DT.SPACING_MD),
    )

    # ================================================================== #
    #  EVENT HANDLERS                                                     #
    # ================================================================== #

    def toggle_theme() -> None:
        theme.toggle()
        config["is_dark"] = theme.is_dark
        _save_config(config)
        # Live re-theming would require touching every colour token; rebuilding
        # the page is simpler and instantaneous on desktop.
        try:
            page.controls.clear()
            page.overlay.clear()
            page.add(MainWindow(page))
            page.update()
        except Exception:
            logger.exception("Failed to rebuild UI for theme change")

    def select_format(value: str) -> None:
        selected_format[0] = value
        config["format"] = value
        _save_config(config)
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

    _preview_request_id = [0]

    async def _load_video_info_preview(url: str, request_id: int) -> None:
        await asyncio.sleep(0.6)
        if request_id != _preview_request_id[0] or url_field.value.strip() != url:
            return
        info = await asyncio.to_thread(downloader.fetch_video_info, url)
        if request_id != _preview_request_id[0] or url_field.value.strip() != url:
            return
        _show_video_info(info, request_id)

    async def _load_thumbnail_preview(thumb_url: str, request_id: int) -> None:
        image_bytes = await asyncio.to_thread(_download_thumbnail_bytes, thumb_url)
        if request_id != _preview_request_id[0]:
            return
        if image_bytes:
            video_img.src = image_bytes
            video_img.visible = True
            video_placeholder.visible = False
        else:
            video_img.visible = False
            video_placeholder.visible = True
        page.update()

    def _trigger_url_change(url: str) -> None:
        url = (url or "").strip()
        _preview_request_id[0] += 1
        request_id = _preview_request_id[0]

        if downloader.validate_url(url):
            url_validation_icon.visible = True
            url_validation_icon.name = ft.Icons.CHECK_CIRCLE
            url_validation_icon.color = theme.success_color
            download_btn.set_disabled(False)
            status_chip.set_status("working", "Analizando enlace…")
            video_info_card.visible = True
            video_loading.visible = True
            video_img.visible = False
            video_placeholder.visible = False
            page.update()
            page.run_task(_load_video_info_preview, url, request_id)
        else:
            has_text = len(url) > 0
            url_validation_icon.visible = has_text
            if has_text:
                url_validation_icon.name = ft.Icons.CANCEL
                url_validation_icon.color = theme.error_color
                status_chip.set_status("error", "Enlace no válido")
            else:
                status_chip.set_status("ready")
            download_btn.set_disabled(True)
            video_info_card.visible = False
            video_loading.visible = False
            page.update()

    def on_url_change(e: ft.ControlEvent) -> None:
        _trigger_url_change(e.control.value)

    def _show_video_info(info: Optional[Dict[str, Any]], request_id: int) -> None:
        if request_id != _preview_request_id[0]:
            return
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
            page.run_task(_load_thumbnail_preview, thumb_url, request_id)
        else:
            video_img.visible = False
            video_placeholder.visible = True

        page.update()

    def paste_from_clipboard() -> None:
        text = _read_clipboard()
        if not text:
            show_snackbar(
                "El portapapeles está vacío. Copia un enlace de YouTube primero.",
                ft.Icons.CONTENT_PASTE_OFF,
                theme.warning_color,
            )
            return
        text = text.strip().splitlines()[0].strip() if text else ""
        url_field.value = text
        # Trigger validation/preview manually since assigning .value does not
        # fire on_change in Flet.
        _trigger_url_change(text)
        show_snackbar(
            "Enlace pegado desde el portapapeles",
            ft.Icons.CONTENT_PASTE,
            theme.info_color,
        )

    def start_download() -> None:
        url = url_field.value.strip()
        if not url:
            return

        # Re-validate just before launching: the user may have edited and the
        # debounce timer may not have fired yet.
        if not downloader.validate_url(url):
            show_snackbar(
                "El enlace no es un vídeo de YouTube válido.",
                ft.Icons.ERROR_OUTLINE,
                theme.error_color,
            )
            return

        if not download_path[0] or not Path(download_path[0]).is_dir():
            show_snackbar(
                "La carpeta de destino no existe. Selecciona otra carpeta.",
                ft.Icons.FOLDER_OFF_OUTLINED,
                theme.error_color,
            )
            return

        download_btn.set_disabled(True)
        status_chip.set_status("working", "Iniciando descarga…")
        progress_container.visible = True
        progress_bar.value = 0
        progress_bar.color = theme.primary_color
        progress_percent.value = "0%"
        progress_percent.color = theme.primary_color
        progress_info_text.value = "Preparando descarga…"
        show_snackbar("Descarga iniciada", ft.Icons.DOWNLOAD_ROUNDED, theme.info_color)
        page.update()

        def _apply_progress(percent: float, text: str) -> None:
            progress_bar.value = max(0.0, min(percent / 100, 1.0))
            progress_percent.value = f"{int(percent)}%"
            progress_info_text.value = text
            status_chip.set_status("working", f"Descargando {int(percent)}%")
            page.update()

        def _on_progress(percent: float, text: str) -> None:
            _schedule_on_ui(page, _apply_progress, percent, text)

        async def _reset_progress_after_delay() -> None:
            await asyncio.sleep(5)
            progress_container.visible = False
            status_chip.set_status("ready")
            progress_bar.color = theme.primary_color
            progress_bar.value = 0
            progress_percent.value = "0%"
            progress_percent.color = theme.primary_color
            progress_info_text.value = "Esperando enlace…"
            page.update()

        def _apply_complete(info: Dict[str, Any]) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("done", "Descarga completa")
            progress_bar.color = theme.success_color
            progress_bar.value = 1.0
            progress_percent.value = "100%"
            progress_percent.color = theme.success_color
            progress_info_text.value = f"Guardado en: {info.get('path', download_path[0])}"
            history_manager.add(info)
            update_history_list()
            show_snackbar(
                "Descarga completada correctamente",
                ft.Icons.CHECK_CIRCLE,
                theme.success_color,
            )
            page.update()

            page.run_task(_reset_progress_after_delay)

        def _on_complete(info: Dict[str, Any]) -> None:
            _schedule_on_ui(page, _apply_complete, info)

        def _apply_error(err: str) -> None:
            download_btn.set_disabled(False)
            status_chip.set_status("error", "Descarga fallida")
            progress_bar.color = theme.error_color
            friendly = friendly_error(err)
            progress_info_text.value = friendly
            progress_percent.color = theme.error_color
            show_snackbar(friendly, ft.Icons.ERROR_OUTLINE, theme.error_color)
            page.update()

        def _on_error(err: str) -> None:
            _schedule_on_ui(page, _apply_error, err)

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

        container = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=icon_color, size=18),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                color=theme.text_primary,
                                weight=DT.WEIGHT_MEDIUM,
                                size=DT.FONT_BODY_SM + 1,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            fmt,
                                            size=DT.FONT_CAPTION - 1,
                                            color=theme.primary_color,
                                            weight=DT.WEIGHT_BOLD,
                                        ),
                                        bgcolor=ft.Colors.with_opacity(0.12, theme.primary_color),
                                        padding=ft.padding.symmetric(
                                            horizontal=DT.SPACING_SM,
                                            vertical=2,
                                        ),
                                        border_radius=DT.RADIUS_SM - 2,
                                    ),
                                    ft.Text(date, color=theme.text_muted, size=DT.FONT_CAPTION - 1),
                                ],
                                spacing=DT.SPACING_SM,
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
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=DT.RADIUS_SM),
                            bgcolor={ft.ControlState.HOVERED: theme.hover_color},
                        ),
                    ),
                ],
                spacing=DT.SPACING_MD,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=DT.SPACING_MD, vertical=DT.SPACING_MD - 2),
            bgcolor=theme.card_color,
            border_radius=DT.RADIUS_MD,
            border=ft.border.all(1, theme.border_color),
            animate=ft.Animation(150, "easeOut"),
        )

        def _on_hover(e: ft.HoverEvent, c: ft.Container = container) -> None:
            hovering = e.data == "true"
            c.border = ft.border.all(1, theme.border_strong if hovering else theme.border_color)
            c.bgcolor = theme.hover_color if hovering else theme.card_color
            try:
                c.update()
            except (AssertionError, AttributeError):
                pass

        container.on_hover = _on_hover
        return container

    def clear_history() -> None:
        history_manager.clear()
        update_history_list()
        show_snackbar("Historial limpiado", ft.Icons.DELETE_SWEEP_OUTLINED, theme.warning_color)

    # FilePicker is a Service in Flet 0.84+, not an overlay control.
    folder_picker = ft.FilePicker()
    page.services.append(folder_picker)

    def select_folder(_e: ft.ControlEvent) -> None:
        page.run_task(_pick_folder)

    async def _pick_folder() -> None:
        selected_path = await folder_picker.get_directory_path(
            dialog_title="Seleccionar carpeta de destino",
            initial_directory=download_path[0],
        )
        _apply_folder_path(selected_path)

    def _apply_folder_path(selected_path: Optional[str]) -> None:
        if not selected_path:
            return
        new_path = Path(selected_path)
        if not new_path.is_dir():
            show_snackbar(
                "La carpeta seleccionada no existe.",
                ft.Icons.ERROR_OUTLINE,
                theme.error_color,
            )
            return
        if not os.access(str(new_path), os.W_OK):
            show_snackbar(
                "No tienes permisos para escribir en esa carpeta.",
                ft.Icons.LOCK_OUTLINE,
                theme.error_color,
            )
            return
        download_path[0] = str(new_path)
        folder_field.value = str(new_path)
        config["download_dir"] = str(new_path)
        _save_config(config)
        show_snackbar(
            "Carpeta de destino actualizada",
            ft.Icons.FOLDER_OUTLINED,
            theme.success_color,
        )
        page.update()

    def _open_in_explorer(path: str) -> None:
        if not path:
            show_snackbar(
                "No hay ruta asociada a este elemento.",
                ft.Icons.INFO_OUTLINED,
                theme.warning_color,
            )
            return
        p = Path(path)
        target = p if p.exists() else p.parent
        if not target.exists():
            show_snackbar(
                "El archivo o la carpeta ya no existen.",
                ft.Icons.WARNING_AMBER,
                theme.warning_color,
            )
            return

        target_str = str(target.resolve())
        system = platform.system()
        try:
            if system == "Windows":
                # /select highlights the file inside the folder
                if p.exists() and p.is_file():
                    subprocess.Popen(["explorer", "/select,", target_str])
                else:
                    subprocess.Popen(["explorer", target_str])
            elif system == "Darwin":
                if p.exists() and p.is_file():
                    subprocess.Popen(["open", "-R", target_str])
                else:
                    subprocess.Popen(["open", target_str])
            else:  # Linux / *nix
                opener = _shutil.which("xdg-open") or _shutil.which("gio")
                if opener:
                    subprocess.Popen([opener, str(target if target.is_dir() else target.parent)])
                else:
                    show_snackbar(
                        "No se encontró un explorador de archivos compatible.",
                        ft.Icons.INFO_OUTLINED,
                        theme.warning_color,
                    )
        except OSError as exc:
            logger.warning("Could not open file manager: %s", exc)
            show_snackbar(
                "No se pudo abrir el explorador de archivos.",
                ft.Icons.ERROR_OUTLINE,
                theme.error_color,
            )

    # ================================================================== #
    #  HELP DIALOG                                                        #
    # ================================================================== #

    def show_help_dialog() -> None:
        steps = [
            (ft.Icons.CONTENT_COPY, "Copia el enlace del vídeo desde YouTube."),
            (ft.Icons.LINK, "Pégalo en el campo de URL (o pulsa el icono de pegar)."),
            (ft.Icons.TUNE, "Elige el formato: MP4 para vídeo, MP3 para audio, etc."),
            (ft.Icons.FOLDER_OUTLINED, "Si quieres, cambia la carpeta de destino."),
            (ft.Icons.DOWNLOAD_ROUNDED, "Pulsa Descargar y espera a que termine."),
            (ft.Icons.HISTORY, "Tu historial queda guardado por si quieres reabrir el archivo."),
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
                                alignment=ft.Alignment(0, 0),
                            ),
                            ft.Icon(icon, size=22, color=theme.primary_color),
                            ft.Text(text, size=14, color=theme.text_primary, expand=True),
                        ],
                        spacing=12,
                    ),
                    padding=ft.padding.symmetric(horizontal=6, vertical=8),
                    border_radius=10,
                    bgcolor=theme.card_color,
                ),
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HELP_OUTLINE, color=theme.primary_color, size=24),
                    ft.Text("Cómo usar YouTube Downloader", size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(step_controls, spacing=4, scroll=ft.ScrollMode.AUTO),
                width=480,
                height=340,
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
            page.pop_dialog()

        page.show_dialog(dialog)

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
                                    ft.Container(height=DT.SPACING_LG),
                                    history_panel,
                                ],
                                spacing=0,
                            ),
                            expand=1,
                        ),
                    ],
                    spacing=DT.SPACING_XL,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.padding.symmetric(horizontal=DT.SPACING_XL, vertical=DT.SPACING_SM),
                expand=True,
            ),
            footer,
        ],
        spacing=0,
        expand=True,
    )

    # Load existing history on startup
    update_history_list()

    # Show help on first launch (one-shot, deferred so the UI is mounted).
    if not config.get("help_shown"):
        config["help_shown"] = True
        _save_config(config)

        async def _show_help_later() -> None:
            await asyncio.sleep(0.6)
            show_help_dialog()

        page.run_task(_show_help_later)

    main_container = ft.Container(
        content=layout,
        expand=True,
        gradient=ft.LinearGradient(
            colors=theme.bg_gradient,
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
        ),
    )

    return main_container
