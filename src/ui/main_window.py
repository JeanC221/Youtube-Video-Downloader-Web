import os
import threading
import urllib.request
import time
import flet as ft
from src.ui.theme import AppTheme
from src.utils.downloader import YouTubeDownloader
from src.ui.components import ModernButton, StatusChip, TooltipIconButton

# History Logic (kept simple in this file for portability)
import json
from datetime import datetime
import subprocess # Added for explorer selection

class SimpleHistory:
    def __init__(self):
        self.history_file = os.path.join(os.path.expanduser("~"), ".youtube_downloader_history.json")
        self.history = self._load_history()
    
    def _load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            return []
    
    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def add(self, info):
        # Remove duplicates
        self.history = [h for h in self.history if h.get('url') != info.get('url')]
        entry = {
            'title': info.get('title', 'Desconocido'),
            'url': info.get('url', ''),
            'format': info.get('format', 'mp4'),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'path': info.get('path', ''),
            'thumbnail': info.get('thumbnail', '')
        }
        self.history.insert(0, entry)
        self.history = self.history[:50]
        self._save_history()

def MainWindow(page: ft.Page):
    theme = AppTheme()
    downloader = YouTubeDownloader()
    history_manager = SimpleHistory()
    
    # State
    download_path = os.path.join(os.path.expanduser("~"), "Downloads")
    selected_format = "mp4"
    
    # --- Status & Feedback State ---
    
    # --- Status & Feedback State ---
    
    status_chip = StatusChip(theme)
    main_container = None # Placeholder for closure access
    
    # --- UI Components ---

    # Header
    title_text = ft.Text(
        "YouTube Downloader", 
        size=24, 
        weight=ft.FontWeight.BOLD, 
        color=theme.text_primary
    )
    
    theme_btn = ft.IconButton(
        icon=ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE,
        icon_color=theme.text_primary,
        tooltip="Cambiar tema",
        on_click=lambda e: toggle_theme(e)
    )

    # Input Area
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
        tooltip="Pega aquí el enlace del video de YouTube"
    )

    def paste_from_clipboard(e):
        # Flet doesn't have direct clipboard read efficiently in all versions/platforms roughly
        # but we can try basic python functionality or just rely on user CTRL+V
        pass # Placeholder for button placement

    # Format Chips
    format_chips = []
    
    def create_format_chip(label, value, icon):
        is_selected = (value == selected_format)
        bg_color = ft.Colors.with_opacity(0.15, theme.primary_color) if is_selected else theme.input_bgcolor
        border_color = theme.primary_color if is_selected else ft.Colors.TRANSPARENT
        icon_color = theme.primary_color if is_selected else theme.text_secondary
        text_color = theme.text_primary if is_selected else theme.text_secondary
        font_weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL
        
        chip = ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=18, color=icon_color),
                ft.Text(label, color=text_color, weight=font_weight)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=10,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            on_click=lambda e: select_format(value),
            animate=ft.Animation(200, "easeOut"),
            data=value,
            tooltip=f"Descargar en formato {label}"
        )
        format_chips.append(chip)
        return chip
    
    format_row = ft.Row([
        create_format_chip("MP4", "mp4", ft.Icons.VIDEO_FILE),
        create_format_chip("MP3", "mp3", ft.Icons.MUSIC_NOTE),
        create_format_chip("Original", "original", ft.Icons.FILE_DOWNLOAD),
    ], spacing=10)

    # Folder Selection
    folder_field = ft.TextField(
        label="Carpeta",
        value=download_path,
        prefix_icon=ft.Icons.FOLDER_OPEN,
        border_radius=12,
        bgcolor=theme.input_bgcolor,
        border_color=ft.Colors.TRANSPARENT,
        text_size=14,
        color=theme.text_secondary,
        filled=True,
        read_only=True,
        expand=True,
        tooltip="Carpeta donde se guardarán los archivos"
    )

    folder_btn = TooltipIconButton(
        icon=ft.Icons.DRIVE_FILE_MOVE,
        tooltip="Cambiar carpeta",
        on_click=lambda e: select_folder(e),
        theme=theme
    )

    # Progress
    progress_bar = ft.ProgressBar(
        value=0, 
        color=theme.primary_color, 
        bgcolor=theme.input_bgcolor, 
        height=6,
        border_radius=3
    )
    progress_info_text = ft.Text("Esperando...", size=12, color=theme.text_secondary)
    progress_percent = ft.Text("0%", size=12, weight=ft.FontWeight.BOLD, color=theme.primary_color)
    
    progress_container = ft.Column([
        ft.Row([progress_info_text, ft.Container(expand=True), progress_percent]),
        progress_bar
    ], spacing=5, visible=False)

    # Download Button
    download_btn = ModernButton(
        text="DESCARGAR AHORA",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        gradient_colors=theme.primary_gradient,
        on_click=lambda e: start_download(),
        width=None, # Expand to container
        height=54,
        tooltip="Iniciar la descarga del video"
    )

    # Video Info Skeleton/Card
    video_img = ft.Image(src_base64=None, width=320, height=180, fit=ft.ImageFit.COVER, border_radius=12, visible=False)
    video_placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.VIDEO_LIBRARY_OUTLINED, size=40, color=theme.text_disabled),
            ft.Text("Vista previa", color=theme.text_disabled)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=320, height=180, bgcolor=theme.input_bgcolor, border_radius=12, alignment=ft.alignment.center
    )
    video_title = ft.Text("...", size=16, weight=ft.FontWeight.BOLD, color=theme.text_primary, no_wrap=True)
    video_author = ft.Text("...", size=14, color=theme.text_secondary)
    
    video_info_card = ft.Container(
        content=ft.Column([
            ft.Stack([video_placeholder, video_img]),
            ft.Container(height=5),
            video_title,
            ft.Row([ft.Icon(ft.Icons.PERSON, size=14, color=theme.text_secondary), video_author], spacing=5)
        ]),
        visible=False,
        animate_opacity=300,
        padding=10,
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, theme.border_color)),
        border_radius=12
    )

    # History List
    # Height calculation: ~60px per item * 3.5 items = ~210px
    history_list = ft.ListView(
        height=220, 
        spacing=10, 
        padding=10,
        expand=False # Don't expand to fill, use fixed height
    )

    # --- Logic ---

    def toggle_theme(e):
        theme.toggle()
        theme.apply_to_page(page)
        theme_btn.icon = ft.Icons.DARK_MODE if not theme.is_dark else ft.Icons.LIGHT_MODE
        update_ui_colors()
        page.update()

    def update_ui_colors():
        # Update colors manually for inputs/text where not auto-bound
        url_field.bgcolor = theme.input_bgcolor
        url_field.color = theme.text_primary
        url_field.focused_border_color = theme.primary_color
        
        folder_field.bgcolor = theme.input_bgcolor
        folder_field.color = theme.text_secondary
        
        title_text.color = theme.text_primary
        theme_btn.icon_color = theme.text_primary
        
        select_format(selected_format) # Refresh chips
        
        status_chip.set_status(status_chip._status) # Refresh chip colors
        
        # Refresh history
        update_history_list()
        
        # Update panels and container if they exist
        if download_panel:
            download_panel.bgcolor = theme.surface_color
            download_panel.shadow.color = theme.shadow_color
            download_panel.update()
            
        if history_panel:
            history_panel.bgcolor = theme.bg_color
            history_panel.update()
            
        if video_info_card:
            video_info_card.border = ft.border.all(1, ft.Colors.with_opacity(0.1, theme.border_color))
            video_info_card.update()
            
        if main_container:
            main_container.gradient.colors = [theme.bg_color, theme.bg_color]
            main_container.update()
            
        # Update text labels
        header_download.color = theme.text_primary
        header_download.update()
        
        header_history.color = theme.text_primary
        header_history.update()
        
        label_format.color = theme.text_secondary
        label_format.update()
        
        label_save.color = theme.text_secondary
        label_save.update()
        
        # Update Video Info Card Text
        video_title.color = theme.text_primary
        video_author.color = theme.text_secondary
        video_info_card.update()

    def select_format(value):
        nonlocal selected_format
        selected_format = value
        for chip in format_chips:
            is_me = chip.data == value
            # Styling
            chip.bgcolor = ft.Colors.with_opacity(0.15, theme.primary_color) if is_me else theme.input_bgcolor
            chip.border = ft.border.all(1, theme.primary_color if is_me else ft.Colors.TRANSPARENT)
            
            row = chip.content
            row.controls[0].color = theme.primary_color if is_me else theme.text_secondary
            row.controls[1].color = theme.text_primary if is_me else theme.text_secondary
            row.controls[1].weight = ft.FontWeight.W_600 if is_me else ft.FontWeight.NORMAL
        page.update()

    def on_url_change(e):
        url = e.control.value.strip()
        if downloader.validate_url(url):
            status_chip.set_status("working", "Analizando...")
            video_info_card.visible = True
            video_info_card.opacity = 0.5 # Dim while loading
            page.update()
            
            def load():
                downloader.get_video_info(url, show_video_info)
            threading.Timer(0.5, load).start()
        else:
            status_chip.set_status("ready")
            video_info_card.visible = False
            page.update()

    def show_video_info(info):
        if not info:
             status_chip.set_status("error", "URL inválida")
             return
             
        video_title.value = info.get('title', 'Desconocido')
        video_author.value = info.get('uploader', 'Desconocido')
        
        status_chip.set_status("ready")
        video_info_card.opacity = 1.0
        
        thumb_url = info.get('thumbnail')
        if thumb_url:
            def load_img():
                try:
                    with urllib.request.urlopen(thumb_url) as res:
                        import base64
                        b64 = base64.b64encode(res.read()).decode()
                        video_img.src_base64 = b64
                        video_img.visible = True
                        video_placeholder.visible = False
                        page.update()
                except: pass
            threading.Thread(target=load_img, daemon=True).start()
        
        page.update()

    def start_download():
        url = url_field.value.strip()
        if not url: return
        
        download_btn.set_disabled(True)
        status_chip.set_status("working", "Iniciando...")
        progress_container.visible = True
        progress_bar.color = theme.primary_color
        page.update()
        
        def on_progress(percent, text):
            progress_bar.value = percent / 100
            progress_percent.value = f"{int(percent)}%"
            progress_info_text.value = text
            status_chip.set_status("working", "Descargando...")
            page.update()
            
        def on_complete(info):
            download_btn.set_disabled(False)
            status_chip.set_status("done", "¡Listo!")
            progress_bar.color = theme.success_color
            history_manager.add(info)
            update_history_list()
            
            time.sleep(3)
            progress_container.visible = False
            status_chip.set_status("ready")
            progress_bar.color = theme.primary_color
            page.update()
            
        def on_error(err):
            download_btn.set_disabled(False)
            status_chip.set_status("error", "Error")
            progress_bar.color = theme.error_color
            progress_info_text.value = str(err)
            page.update()
            
        downloader.callback_progress = on_progress
        downloader.callback_complete = on_complete
        downloader.callback_error = on_error
        
        downloader.download(url, download_path, selected_format)

    def update_history_list():
        history_list.controls.clear()
        for item in history_manager.history:
            history_list.controls.append(create_history_item(item))
        page.update()

    def create_history_item(item):
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.success_color, size=16),
                ft.Column([
                    ft.Text(item['title'], color=theme.text_primary, weight=ft.FontWeight.W_600, size=13, no_wrap=True),
                    ft.Text(f"{item['format'].upper()} • {item['date']}", color=theme.text_secondary, size=11)
                ], expand=True, spacing=2),
                ft.IconButton(ft.Icons.FOLDER_OPEN, icon_color=theme.text_secondary, icon_size=18, 
                    tooltip="Mostrar en carpeta", 
                    on_click=lambda e: open_file_in_explorer(item['path'])
                )
            ], spacing=10),
            padding=10,
            bgcolor=theme.surface_color,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, theme.border_color))
        )

    def select_folder(e):
        fp = ft.FilePicker(on_result=lambda res: on_folder_result(res))
        page.overlay.append(fp)
        page.update()
        fp.get_directory_path("Seleccionar carpeta")
        
    def on_folder_result(e):
        if e.path:
            nonlocal download_path
            download_path = e.path
            folder_field.value = e.path
            page.update()
            
    def open_file_in_explorer(path):
        if os.path.exists(path):
            try:
                # normalize path to windows format
                path = os.path.normpath(path)
                subprocess.Popen(['explorer', '/select,', path])
            except: pass

    # --- Layout (Responsive) ---
    
    # Left Panel (Download)
    header_download = ft.Text("Descargar Video", size=18, weight=ft.FontWeight.BOLD, color=theme.text_primary)
    label_format = ft.Text("Formato", color=theme.text_secondary, size=13, weight=ft.FontWeight.BOLD)
    label_save = ft.Text("Guardar en", color=theme.text_secondary, size=13, weight=ft.FontWeight.BOLD)

    download_panel = ft.Container(
        content=ft.Column([
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
            ft.Column([download_btn], horizontal_alignment=ft.CrossAxisAlignment.STRETCH), # Full width button
            ft.Container(height=20)
        ], scroll=ft.ScrollMode.HIDDEN),
        padding=30,
        bgcolor=theme.surface_color,
        border_radius=20,
        shadow=ft.BoxShadow(blur_radius=10, color=theme.shadow_color)
    )
    
    # Right Panel (History)
    header_history = ft.Text("Historial", size=18, weight=ft.FontWeight.BOLD, color=theme.text_primary)
    
    history_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color=theme.text_primary),
                header_history
            ], spacing=10),
            ft.Divider(color=theme.border_color),
            history_list
        ]),
        padding=20,
        bgcolor=theme.bg_color, # Clean background
        border_radius=20
    )

    # Main Grid Layout
    layout = ft.ResponsiveRow([
        # Header (Full width)
        ft.Column(col=12, controls=[
            ft.Container(
                content=ft.Row([
                    ft.Row([ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED, color=theme.primary_color, size=30), title_text], spacing=10),
                    ft.Row([status_chip, theme_btn], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(horizontal=20, vertical=15),
            )
        ]),
        
        # Content
        ft.Column(col={"sm": 12, "md": 7, "lg": 8}, controls=[download_panel]),
        ft.Column(col={"sm": 12, "md": 5, "lg": 4}, controls=[
            video_info_card,
            history_panel
        ]),
    ])

    # Initial Init
    # update_ui_colors() # Removed to prevent crash on startup (controls not yet on page)
    
    # Assign to closure variable
    main_container = ft.Container(
        content=layout,
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[theme.bg_color, theme.bg_color]
        ),
        padding=10
    )
    
    return main_container