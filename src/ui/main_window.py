import os
import threading
import urllib.request
from io import BytesIO
from PIL import Image
import flet as ft
import json
from datetime import datetime

from src.ui.theme import AppTheme
from src.utils.downloader import YouTubeDownloader

class SimpleHistory:
    def __init__(self):
        self.history_file = os.path.join(os.path.expanduser("~"), ".youtube_downloader_history.json")
        self.history = self._load_history()
    
    def _load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error al cargar historial: {e}")
        return []
    
    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar historial: {e}")
    
    def add(self, info):
        entry = {
            'title': info.get('title', 'Desconocido'),
            'url': info.get('url', ''),
            'format': info.get('format', 'mp4'),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'path': info.get('path', '')
        }
        self.history.insert(0, entry)
        self.history = self.history[:50]  # Mantener solo 50
        self._save_history()
    
    def clear(self):
        """Limpiar todo el historial"""
        print("Limpiando historial...")  # Debug
        self.history = []
        self._save_history()
        print(f"Historial después de limpiar: {len(self.history)} items")  # Debug

def MainWindow(page: ft.Page):
    """Ventana principal como función en lugar de clase"""
    theme = AppTheme()
    
    # Inicializar componentes
    downloader = YouTubeDownloader()
    history_manager = SimpleHistory()  # Usar la clase simple
    
    # Variables de estado
    download_path = os.path.join(os.path.expanduser("~"), "Downloads")
    selected_format = "mp4"
    
    # Crear componentes UI
    url_field = ft.TextField(
        label="URL del Video",
        hint_text="https://youtube.com/watch?v=...",
        prefix_icon=ft.Icons.LINK,
        border_radius=12,
        filled=True,
        expand=True
    )
    
    # Selector de formato con chips personalizados
    format_chips = []
    
    def create_format_chip(label, value, icon, is_selected=False):
        chip = ft.Chip(
            label=ft.Text(label),
            leading=ft.Icon(icon),
            selected=is_selected,
            on_click=lambda e: select_format(value, e.control)
        )
        format_chips.append((value, chip))
        return chip
    
    def select_format(format_value, clicked_chip):
        nonlocal selected_format
        selected_format = format_value
        for value, chip in format_chips:
            chip.selected = (chip == clicked_chip)
        page.update()
    
    format_row = ft.Row([
        create_format_chip("MP4 Video", "mp4", ft.Icons.VIDEO_FILE, True),
        create_format_chip("MP3 Audio", "mp3", ft.Icons.AUDIO_FILE),
        create_format_chip("Original", "original", ft.Icons.FILE_DOWNLOAD)
    ], spacing=10)
    
    # Selector de carpeta
    folder_field = ft.TextField(
        label="Carpeta de descarga",
        value=download_path,
        prefix_icon=ft.Icons.FOLDER,
        border_radius=12,
        filled=True,
        read_only=True,
        expand=True
    )
    
    def select_folder(e):
        def handle_result(e: ft.FilePickerResultEvent):
            if e.path:
                nonlocal download_path
                download_path = e.path
                folder_field.value = e.path
                page.update()
        
        file_picker = ft.FilePicker(on_result=handle_result)
        page.overlay.append(file_picker)
        page.update()
        file_picker.get_directory_path(dialog_title="Seleccionar carpeta de descarga")
    
    browse_button = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        tooltip="Seleccionar carpeta",
        on_click=select_folder
    )
    
    # Progress bar con estilo
    progress_bar = ft.ProgressBar(
        value=0,
        height=8,
        color=theme.primary_color,
        bgcolor=theme.border_color
    )
    progress_text = ft.Text("Listo para descargar", size=14, color=theme.text_primary)
    progress_percent = ft.Text("0%", size=14, weight=ft.FontWeight.BOLD, color=theme.text_primary)
    
    # Botón de descarga con gradiente
    download_button = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.DOWNLOAD, color="white", size=20),
            ft.Text("Descargar Video", size=16, weight=ft.FontWeight.BOLD, color="white")
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        gradient=ft.LinearGradient(
            colors=theme.primary_gradient,
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right
        ),
        width=300,
        height=56,
        border_radius=28,
        on_click=lambda e: start_download(),
        ink=True
    )
    
    # Panel de información del video
    video_info_content = ft.Column([
        ft.Container(
            content=ft.Icon(ft.Icons.VIDEO_LIBRARY, color=theme.text_disabled, size=48),
            alignment=ft.alignment.center,
            padding=40
        ),
        ft.Text(
            "Pega una URL para ver la información del video",
            size=14,
            color=theme.text_secondary,
            text_align=ft.TextAlign.CENTER
        )
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    # Lista de historial
    history_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10)
    
    # Funciones de callback
    def update_progress(percent: float, text: str):
        progress_bar.value = percent / 100
        progress_text.value = text
        progress_text.color = theme.text_primary
        progress_percent.value = f"{int(percent)}%"
        progress_percent.color = theme.text_primary
        page.update()
    
    def download_complete(info: dict):
        download_button.disabled = False
        download_button.opacity = 1.0
        history_manager.add(info)
        update_history()
        progress_bar.value = 0
        progress_text.value = "Listo para descargar"
        progress_percent.value = "0%"
        
        # Mostrar notificación de éxito
        page.snack_bar = ft.SnackBar(
            content=ft.Text("¡Descarga completada exitosamente!", color="white"),
            bgcolor=theme.success_color,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()
    
    def download_error(error: str):
        download_button.disabled = False
        download_button.opacity = 1.0
        progress_bar.value = 0
        progress_text.value = "Error en la descarga"
        progress_percent.value = "0%"
        
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Error: {error}", color="white"),
            bgcolor=theme.error_color,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()
    
    # Configurar callbacks del downloader
    downloader.callback_progress = update_progress
    downloader.callback_complete = download_complete
    downloader.callback_error = download_error
    
    def start_download():
        url = url_field.value.strip()
        if not url:
            show_error("Por favor ingresa una URL")
            return
        
        if not is_valid_youtube_url(url):
            show_error("URL de YouTube no válida")
            return
        
        download_button.disabled = True
        download_button.opacity = 0.6
        page.update()
        
        # Iniciar descarga
        downloader.download(url, download_path, selected_format)
    
    def is_valid_youtube_url(url: str) -> bool:
        import re
        pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.*'
        return bool(re.match(pattern, url))
    
    def show_error(message: str):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor=theme.error_color,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()
    
    def on_url_change(e):
        url = e.control.value.strip()
        if url and is_valid_youtube_url(url):
            # Obtener información del video después de un delay
            threading.Timer(1.0, lambda: fetch_video_info(url)).start()
    
    def fetch_video_info(url: str):
        def update_ui(info):
            if info:
                display_video_info(info)
        
        downloader.get_video_info(url, update_ui)
    
    def display_video_info(info: dict):
        title = info.get('title', 'Título desconocido')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Canal desconocido')
        thumbnail_url = info.get('thumbnail', '')
        
        # Formatear duración
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
        
        # Actualizar contenido con colores del tema actual
        video_info_content.controls = [
            ft.Container(
                content=ft.Icon(ft.Icons.IMAGE, size=80, color=theme.text_disabled),
                bgcolor=theme.surface_color,
                width=320,
                height=180,
                border_radius=12,
                alignment=ft.alignment.center
            ),
            ft.Container(height=15),
            ft.Text(
                title[:60] + "..." if len(title) > 60 else title,
                size=16,
                weight=ft.FontWeight.W_500,
                color=theme.text_primary,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(height=10),
            ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.PERSON, size=16, color=theme.text_secondary),
                    ft.Text(uploader, size=14, color=theme.text_secondary)
                ], spacing=5),
                ft.Container(width=20),
                ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=theme.text_secondary),
                    ft.Text(duration_str, size=14, color=theme.text_secondary)
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.CENTER)
        ]
        
        page.update()
        
        # Cargar thumbnail si existe
        if thumbnail_url:
            threading.Thread(target=lambda: load_thumbnail(thumbnail_url), daemon=True).start()
    
    def load_thumbnail(url: str):
        try:
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
            
            image = Image.open(BytesIO(image_data))
            image = image.resize((320, 180), Image.Resampling.LANCZOS)
            
            temp_path = os.path.join(os.path.expanduser("~"), ".youtube_downloader_thumb.jpg")
            image.save(temp_path, "JPEG")
            
            # Actualizar UI en el thread principal
            def update():
                if video_info_content.controls:
                    video_info_content.controls[0] = ft.Container(
                        content=ft.Image(
                            src=temp_path,
                            width=320,
                            height=180,
                            fit=ft.ImageFit.COVER,
                            border_radius=12
                        )
                    )
                    page.update()
            
            page.run_task(update)
        except Exception as e:
            print(f"Error al cargar miniatura: {e}")
    
    def create_history_item(entry: dict):
        format_icon = ft.Icons.MUSIC_NOTE if entry.get('format') == 'mp3' else ft.Icons.VIDEO_FILE
        format_color = theme.accent_color if entry.get('format') == 'mp3' else theme.primary_color
        
        title = entry.get('title', 'Desconocido')
        if len(title) > 35:
            title = title[:32] + "..."
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(format_icon, color=format_color, size=20),
                    bgcolor=ft.Colors.with_opacity(0.1, format_color),
                    padding=10,
                    border_radius=10
                ),
                ft.Column([
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=theme.text_primary),
                    ft.Text(
                        f"{entry.get('format', '').upper()} • {entry.get('date', '')}",
                        size=12,
                        color=theme.text_secondary
                    )
                ], spacing=2, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DOWNLOAD,
                    icon_color=theme.primary_color,
                    icon_size=18,
                    tooltip="Descargar de nuevo",
                    on_click=lambda e, url=entry.get('url', ''): redownload(url)
                )
            ], spacing=15),
            padding=15,
            border_radius=12,
            bgcolor=theme.surface_color,
            on_hover=lambda e: update_hover(e)
        )
    
    def update_hover(e):
        e.control.bgcolor = theme.hover_color if e.data == "true" else theme.surface_color
        e.control.update()
    
    def update_history():
        history_list.controls.clear()
        
        if not history_manager.history:
            history_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No hay descargas recientes",
                        size=14,
                        color=theme.text_disabled,
                        text_align=ft.TextAlign.CENTER
                    ),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
        else:
            for entry in history_manager.history:
                history_list.controls.append(create_history_item(entry))
        
        page.update()
    
    def redownload(url: str):
        url_field.value = url
        page.update()
        fetch_video_info(url)
    
    def clear_history(e):
        def confirm(e):
            print(f"Botón presionado: {e.control.text}")  # Debug
            if e.control.text == "Sí":
                print("Confirmando limpieza...")  # Debug
                history_manager.clear()
                update_history()
                print("Historial limpiado y UI actualizada")  # Debug
            page.close(dialog)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar"),
            content=ft.Text("¿Estás seguro de que quieres limpiar el historial?"),
            actions=[
                ft.TextButton("Cancelar", on_click=confirm),
                ft.TextButton("Sí", on_click=confirm, style=ft.ButtonStyle(color=theme.error_color))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        print("Abriendo diálogo de confirmación...")  # Debug
        page.open(dialog)
        page.update()
    
    def toggle_theme(e):
        theme.toggle()
        theme.apply_to_page(page)
        
        # Actualizar icono del botón
        e.control.icon = ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE
        
        # Actualizar colores de todos los componentes
        update_theme_colors()
        page.update()
    
    def update_theme_colors():
        """Actualizar todos los colores de la interfaz cuando cambie el tema"""
        # Header
        main_container.content.controls[0].bgcolor = theme.surface_color
        main_container.bgcolor = theme.bg_color
        
        # Progress bar
        progress_bar.color = theme.primary_color
        progress_bar.bgcolor = theme.border_color
        
        # Textos del header
        main_container.content.controls[0].content.controls[0].controls[1].color = theme.text_primary
        
        # Botón de cambio de tema
        main_container.content.controls[0].content.controls[1].icon_color = theme.text_primary
        
        # Divider
        main_container.content.controls[1].color = theme.border_color
        
        # Paneles principales
        main_container.content.controls[2].controls[0].bgcolor = theme.bg_color  # Panel izquierdo
        main_container.content.controls[2].controls[2].bgcolor = theme.bg_color  # Panel derecho
        
        # Divider vertical
        main_container.content.controls[2].controls[1].color = theme.border_color
        
        # Actualizar textos de las secciones del panel izquierdo
        left_panel = main_container.content.controls[2].controls[0].content.controls
        
        # "URL del Video" - índice 0
        if len(left_panel) > 0 and hasattr(left_panel[0], 'controls'):
            if len(left_panel[0].controls) > 0 and hasattr(left_panel[0].controls[0], 'color'):
                left_panel[0].controls[0].color = theme.text_primary
        
        # "Formato de descarga" - índice 2 (después del Container de altura 30)
        if len(left_panel) > 2 and hasattr(left_panel[2], 'controls'):
            if len(left_panel[2].controls) > 0 and hasattr(left_panel[2].controls[0], 'color'):
                left_panel[2].controls[0].color = theme.text_primary
        
        # "Ubicación de descarga" - índice 4
        if len(left_panel) > 4 and hasattr(left_panel[4], 'controls'):
            if len(left_panel[4].controls) > 0 and hasattr(left_panel[4].controls[0], 'color'):
                left_panel[4].controls[0].color = theme.text_primary
        
        # "Progreso de descarga" - índice 6
        if len(left_panel) > 6 and hasattr(left_panel[6], 'controls'):
            if len(left_panel[6].controls) > 0 and hasattr(left_panel[6].controls[0], 'color'):
                left_panel[6].controls[0].color = theme.text_primary
        
        # Actualizar textos de progreso
        progress_text.color = theme.text_primary
        progress_percent.color = theme.text_primary
        
        # Card de información del video
        video_card = main_container.content.controls[2].controls[2].content.controls[0]
        video_card.content.bgcolor = theme.card_color
        video_card.color = theme.card_color
        
        # Texto "Información del Video"
        video_card.content.content.controls[0].controls[1].color = theme.text_primary
        
        # Divider de la card
        video_card.content.content.controls[1].color = theme.border_color
        
        # Texto "Historial de descargas"
        history_header = main_container.content.controls[2].controls[2].content.controls[2]
        history_header.controls[0].controls[1].color = theme.text_primary
        
        # Contenedor del historial
        history_container = main_container.content.controls[2].controls[2].content.controls[4]
        history_container.border = ft.border.all(1, theme.border_color)
        history_container.bgcolor = theme.surface_color
        
        # Actualizar items del historial
        update_history()
        
        # Actualizar información del video si existe
        update_video_info_colors()
    
    def update_video_info_colors():
        """Actualizar colores del panel de información del video"""
        if len(video_info_content.controls) > 1:
            # Si hay información del video cargada
            for i, control in enumerate(video_info_content.controls):
                if hasattr(control, 'color'):
                    if i == 2:  # Título del video
                        control.color = theme.text_primary
                    elif i == 4:  # Row con información adicional
                        for row in control.controls:
                            if hasattr(row, 'controls'):
                                for item in row.controls:
                                    if hasattr(item, 'color'):
                                        item.color = theme.text_secondary
                elif hasattr(control, 'bgcolor'):
                    if i == 0:  # Contenedor de imagen/icono
                        control.bgcolor = theme.surface_color
        else:
            # Si no hay información, mostrar el estado inicial
            video_info_content.controls = [
                ft.Container(
                    content=ft.Icon(ft.Icons.VIDEO_LIBRARY, color=theme.text_disabled, size=48),
                    alignment=ft.alignment.center,
                    padding=40
                ),
                ft.Text(
                    "Pega una URL para ver la información del video",
                    size=14,
                    color=theme.text_secondary,
                    text_align=ft.TextAlign.CENTER
                )
            ]
    
    def clear_url(e):
        url_field.value = ""
        video_info_content.controls = [
            ft.Container(
                content=ft.Icon(ft.Icons.VIDEO_LIBRARY, color=theme.text_disabled, size=48),
                alignment=ft.alignment.center,
                padding=40
            ),
            ft.Text(
                "Pega una URL para ver la información del video",
                size=14,
                color=theme.text_secondary,
                text_align=ft.TextAlign.CENTER
            )
        ]
        page.update()
    
    # Asignar eventos
    url_field.on_change = on_url_change
    
    # Layout principal
    main_container = ft.Container(
        content=ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED, color=theme.primary_color, size=32),
                        ft.Text("YouTube Downloader", size=24, weight=ft.FontWeight.BOLD, color=theme.text_primary)
                    ], spacing=15),
                    ft.IconButton(
                        icon=ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE,
                        icon_color=theme.text_primary,
                        tooltip="Cambiar tema",
                        on_click=toggle_theme
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(horizontal=30, vertical=20),
                bgcolor=theme.surface_color
            ),
            
            ft.Divider(height=1, color=theme.border_color),
            
            # Contenido principal
            ft.Row([
                # Panel izquierdo
                ft.Container(
                    content=ft.Column([
                        # URL Input
                        ft.Column([
                            ft.Text("URL del Video", size=16, weight=ft.FontWeight.W_500, color=theme.text_primary),
                            ft.Row([url_field, ft.IconButton(ft.Icons.CLEAR, on_click=clear_url)], spacing=10)
                        ], spacing=10),
                        
                        ft.Container(height=30),
                        
                        # Formato
                        ft.Column([
                            ft.Text("Formato de descarga", size=16, weight=ft.FontWeight.W_500, color=theme.text_primary),
                            format_row
                        ], spacing=10),
                        
                        ft.Container(height=30),
                        
                        # Ubicación
                        ft.Column([
                            ft.Text("Ubicación de descarga", size=16, weight=ft.FontWeight.W_500, color=theme.text_primary),
                            ft.Row([folder_field, browse_button], spacing=10)
                        ], spacing=10),
                        
                        ft.Container(height=30),
                        
                        # Progreso
                        ft.Column([
                            ft.Text("Progreso de descarga", size=16, weight=ft.FontWeight.W_500, color=theme.text_primary),
                            ft.Container(
                                content=progress_bar,
                                border_radius=4,
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=4,
                                    color=ft.Colors.with_opacity(0.1, theme.primary_color),
                                    offset=ft.Offset(0, 2)
                                )
                            ),
                            ft.Row([progress_text, ft.Container(expand=True), progress_percent])
                        ], spacing=10),
                        
                        ft.Container(height=40),
                        
                        # Botón de descarga
                        ft.Row([download_button], alignment=ft.MainAxisAlignment.CENTER)
                    ], scroll=ft.ScrollMode.AUTO),
                    padding=40,
                    expand=3,
                    bgcolor=theme.bg_color
                ),
                
                ft.VerticalDivider(width=1, color=theme.border_color),
                
                # Panel derecho
                ft.Container(
                    content=ft.Column([
                        # Card de información del video
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.INFO, color=theme.primary_color, size=24),
                                        ft.Text("Información del Video", size=18, weight=ft.FontWeight.BOLD, color=theme.text_primary)
                                    ], spacing=10),
                                    ft.Divider(color=theme.border_color),
                                    video_info_content
                                ], spacing=10),
                                padding=20,
                                bgcolor=theme.card_color
                            ),
                            elevation=2,
                            color=theme.card_color
                        ),
                        
                        ft.Container(height=20),
                        
                        # Encabezado del historial
                        ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.HISTORY, color=theme.primary_color, size=24),
                                ft.Text("Historial de descargas", size=18, weight=ft.FontWeight.BOLD, color=theme.text_primary)
                            ], spacing=10),
                            ft.TextButton(
                                "Limpiar",
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=theme.error_color,
                                style=ft.ButtonStyle(color=theme.error_color),
                                on_click=clear_history
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Container(height=10),
                        
                        # Lista de historial
                        ft.Container(
                            content=history_list,
                            border=ft.border.all(1, theme.border_color),
                            border_radius=12,
                            padding=10,
                            bgcolor=theme.surface_color,
                            height=300,
                            expand=True
                        )
                    ]),
                    padding=40,
                    expand=2,
                    bgcolor=theme.bg_color
                )
            ], expand=True)
        ], spacing=0),
        bgcolor=theme.bg_color,
        expand=True
    )
    
    # Cargar historial inicial
    update_history()
    
    return main_container