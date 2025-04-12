import os
import threading
import urllib.request
from io import BytesIO
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.ui.theme import AppTheme
from src.utils.downloader import YouTubeDownloader
from src.utils.history import DownloadHistory

class ScrollableFrame(ctk.CTkScrollableFrame):
    """Frame con desplazamiento para el historial"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

class HistoryItem(ctk.CTkFrame):
    """Elemento individual del historial"""
    def __init__(self, master, entry, theme, redownload_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configurar apariencia
        self.configure(corner_radius=10, fg_color=theme.card_color)
        
        # Icono según el tipo de descarga
        format_icon = "🎵" if entry.get('format') == "mp3" else "🎬"
        
        # Título limitado
        title = entry.get('title', 'Desconocido')
        if len(title) > 30:
            title = title[:27] + "..."
        
        # Widgets
        title_label = ctk.CTkLabel(
            self, 
            text=f"{format_icon} {title}", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # Detalles
        details = f"{entry.get('format', 'unknown')} • {entry.get('date', '')}"
        details_label = ctk.CTkLabel(
            self, 
            text=details,
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray70")
        )
        details_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))
        
        # Botón de descargar de nuevo
        download_again = ctk.CTkButton(
            self,
            text="Descargar de nuevo",
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            text_color=theme.link_color,
            hover_color=("gray90", "gray20"),
            height=20,
            command=lambda: redownload_callback(entry.get('url', ''))
        )
        download_again.grid(row=2, column=0, sticky="w", padx=5, pady=(0, 10))

class MainWindow:
    """Ventana principal de la aplicación"""
    def __init__(self, root):
        self.root = root
        
        # Variables de la aplicación
        self.theme = AppTheme()
        self.downloader = YouTubeDownloader(
            callback_progress=self.update_progress,
            callback_complete=self.download_complete,
            callback_error=self.download_error
        )
        self.history_manager = DownloadHistory()
        
        # Variables de interfaz
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.video_url = ""
        self.download_format = "mp4"
        self.current_thumbnail = None
        self.video_info = None
        
        # Crear la interfaz de usuario
        self.create_ui()
        
    def create_ui(self):
        """Crear la interfaz de usuario principal"""
        # Configurar grid de la ventana principal
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Frame principal con padding
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Configurar grid del frame principal
        self.main_frame.grid_columnconfigure(0, weight=3)  # Panel izquierdo
        self.main_frame.grid_columnconfigure(1, weight=1)  # Panel derecho
        self.main_frame.grid_rowconfigure(0, weight=0)     # Header
        self.main_frame.grid_rowconfigure(1, weight=1)     # Contenido
        self.main_frame.grid_rowconfigure(2, weight=0)     # Footer
        
        # Crear componentes
        self.create_header()
        self.create_content()
        self.create_footer()
        
        # Enlazar eventos
        self.url_entry.bind("<KeyRelease>", self._on_url_change)
        
    def _on_url_change(self, event):
        """Manejar cambios en la URL"""
        # Debouncing para no hacer demasiadas peticiones
        if hasattr(self, '_url_check_after_id'):
            self.root.after_cancel(self._url_check_after_id)
        
        self._url_check_after_id = self.root.after(1000, self.fetch_video_info)
        
    def create_header(self):
        """Crear la cabecera con título y botón de tema"""
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Configurar grid del header
        header.grid_columnconfigure(0, weight=1)
        
        # Título de la aplicación
        title = ctk.CTkLabel(
            header, 
            text="YouTube Video Downloader",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme.accent_color
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Botón para cambiar tema
        self.theme_btn = ctk.CTkButton(
            header,
            text="🌙" if not self.theme.is_dark else "☀️",
            width=40,
            height=40,
            corner_radius=20,
            fg_color=self.theme.accent_color,
            hover_color=self.theme.button_hover_color,
            command=self.toggle_theme
        )
        self.theme_btn.grid(row=0, column=1, sticky="e")
        
    def create_content(self):
        """Crear el área de contenido principal (paneles izquierdo y derecho)"""
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        # Configurar grid del content
        content.grid_columnconfigure(0, weight=3)  # Panel izquierdo
        content.grid_columnconfigure(1, weight=1)  # Panel derecho
        content.grid_rowconfigure(0, weight=1)
        
        # Crear paneles
        self.create_left_panel(content)
        self.create_right_panel(content)
        
    def create_left_panel(self, parent):
        """Crear panel izquierdo con controles de descarga"""
        left_panel = ctk.CTkFrame(parent, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Configuración del grid
        left_panel.grid_columnconfigure(0, weight=1)
        for i in range(5):  # 5 filas
            left_panel.grid_rowconfigure(i, weight=0)
        
        # URL del video
        url_label = ctk.CTkLabel(
            left_panel, 
            text="Video URL",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        url_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        # Entrada de URL con botón de limpiar
        url_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        url_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        url_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(
            url_frame, 
            placeholder_text="Pega aquí la URL del video de YouTube",
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew")
        
        clear_btn = ctk.CTkButton(
            url_frame,
            text="✕",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            text_color=self.theme.accent_color,
            hover_color=("gray90", "gray20"),
            command=self.clear_url
        )
        clear_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Formato de descarga
        format_label = ctk.CTkLabel(
            left_panel,
            text="Download Format",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        format_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))
        
        format_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        format_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.format_var = ctk.StringVar(value="mp4")
        
        mp4_radio = ctk.CTkRadioButton(
            format_frame,
            text="MP4 Video",
            variable=self.format_var,
            value="mp4",
            font=ctk.CTkFont(size=12)
        )
        mp4_radio.grid(row=0, column=0, padx=(0, 20))
        
        mp3_radio = ctk.CTkRadioButton(
            format_frame,
            text="MP3 Audio",
            variable=self.format_var,
            value="mp3",
            font=ctk.CTkFont(size=12)
        )
        mp3_radio.grid(row=0, column=1, padx=(0, 20))
        
        original_radio = ctk.CTkRadioButton(
            format_frame,
            text="Original Format",
            variable=self.format_var,
            value="original",
            font=ctk.CTkFont(size=12)
        )
        original_radio.grid(row=0, column=2)
        
        # Ubicación de descarga
        location_label = ctk.CTkLabel(
            left_panel,
            text="Download Location",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        location_label.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 5))
        
        location_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        location_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        location_frame.grid_columnconfigure(0, weight=1)
        
        self.location_entry = ctk.CTkEntry(
            location_frame,
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.location_entry.insert(0, self.download_path)
        self.location_entry.grid(row=0, column=0, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            location_frame,
            text="📂 Browse",
            height=40,
            corner_radius=8,
            fg_color=self.theme.accent_color,
            hover_color=self.theme.button_hover_color,
            command=self.select_directory
        )
        browse_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Progreso de descarga
        progress_label = ctk.CTkLabel(
            left_panel,
            text="Download Progress",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        progress_label.grid(row=6, column=0, sticky="w", padx=20, pady=(0, 5))
        
        progress_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        progress_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 20))
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=15)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(10, 0))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=1, column=0, sticky="e", pady=(5, 0))
        
        # Botón de descarga
        self.download_btn = ctk.CTkButton(
            left_panel,
            text="▼ Descargar Video",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            corner_radius=25,
            fg_color=self.theme.accent_color,
            hover_color=self.theme.button_hover_color,
            command=self.start_download
        )
        self.download_btn.grid(row=8, column=0, sticky="ew", padx=20, pady=(10, 20))
    
    def create_right_panel(self, parent):
        """Crear panel derecho con información del video e historial"""
        right_panel = ctk.CTkFrame(parent, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # Configuración del grid
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=0)  # Info del video
        right_panel.grid_rowconfigure(1, weight=1)  # Historial (expandible)
        
        # Panel de información del video
        self.info_frame = ctk.CTkFrame(right_panel, corner_radius=15)
        self.info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Título del panel
        info_title = ctk.CTkLabel(
            self.info_frame,
            text="Video Information",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        info_title.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # Contenedor para la miniatura
        self.thumbnail_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.thumbnail_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        # Placeholder para la miniatura
        self.thumbnail_label = ctk.CTkLabel(self.thumbnail_frame, text="")
        self.thumbnail_label.grid(row=0, column=0)
        
        # Labels para información del video
        self.title_label = ctk.CTkLabel(
            self.info_frame, 
            text="",
            wraplength=280,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.duration_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.duration_label.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 5))
        
        self.channel_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.channel_label.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 15))
        
        # Panel de historial
        history_frame = ctk.CTkFrame(right_panel, corner_radius=15)
        history_frame.grid(row=1, column=0, sticky="nsew")
        
        # Configuración del grid
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(1, weight=1)  # El scrollable frame crece
        
        # Cabecera del historial
        history_header = ctk.CTkFrame(history_frame, fg_color="transparent")
        history_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        history_header.grid_columnconfigure(0, weight=1)
        
        history_title = ctk.CTkLabel(
            history_header,
            text="Download History",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent_color
        )
        history_title.grid(row=0, column=0, sticky="w")
        
        clear_btn = ctk.CTkButton(
            history_header,
            text="Clear",
            font=ctk.CTkFont(size=12),
            width=60,
            height=25,
            corner_radius=8,
            fg_color="transparent",
            text_color=self.theme.error_color,
            hover_color=("gray90", "gray20"),
            command=self.clear_history
        )
        clear_btn.grid(row=0, column=1, sticky="e")
        
        # Contenedor con scroll para el historial
        self.history_scroll = ScrollableFrame(
            history_frame,
            fg_color="transparent",
            corner_radius=0
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Actualizar historial
        self.update_history_display()
    
    def create_footer(self):
        """Crear pie de página con estado y versión"""
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=30)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            footer,
            text="Listo",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        version_label = ctk.CTkLabel(
            footer,
            text="v1.0.0",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray70")
        )
        version_label.grid(row=0, column=1, sticky="e")
    
    def toggle_theme(self):
        """Cambiar entre tema claro y oscuro"""
        self.theme.toggle()
        self.theme_btn.configure(
            text="☀️" if self.theme.is_dark else "🌙"
        )
        
        # Actualizar historial
        self.update_history_display()
    
    def select_directory(self):
        """Seleccionar directorio de descarga"""
        directory = filedialog.askdirectory()
        if directory:
            self.download_path = directory
            self.location_entry.delete(0, "end")
            self.location_entry.insert(0, directory)
    
    def clear_url(self):
        """Limpiar la URL del video"""
        self.url_entry.delete(0, "end")
        self.clear_video_info()
    
    def clear_video_info(self):
        """Limpiar la información del video"""
        self.title_label.configure(text="")
        self.duration_label.configure(text="")
        self.channel_label.configure(text="")
        self.thumbnail_label.configure(text="", image=None)
        self.video_info = None
        self.current_thumbnail = None
    
    def update_progress(self, percent, text):
        """Actualizar barra de progreso y texto de estado"""
        self.progress_bar.set(percent / 100)  # CustomTkinter usa valores de 0 a 1
        self.progress_label.configure(text=text)
        self.status_label.configure(text=text)
        
        # Actualizar colores según el progreso
        if percent < 30:
            self.progress_bar.configure(progress_color=self.theme.warning_color)
        elif percent < 70:
            self.progress_bar.configure(progress_color=self.theme.accent_color)
        else:
            self.progress_bar.configure(progress_color=self.theme.success_color)
    
    def start_download(self):
        """Iniciar la descarga del video"""
        if self.downloader.downloading:
            return
            
        url = self.url_entry.get().strip()
        download_dir = self.location_entry.get()
        format_selection = self.format_var.get()
        
        if not url or not download_dir:
            messagebox.showerror("Error", "Por favor complete todos los campos")
            return
            
        # Actualizar estado
        self.download_btn.configure(state="disabled")
        
        # Iniciar descarga
        self.downloader.download(url, download_dir, format_selection)
    
    def fetch_video_info(self):
        """Obtener información del video cuando cambia la URL"""
        url = self.url_entry.get().strip()
        if not url:
            return
        
        self.status_label.configure(text="Obteniendo información del video...")
        
        # Obtener información del video
        self.downloader.get_video_info(url, self.update_video_info)
    
    def update_video_info(self, info):
        """Actualizar interfaz con información del video"""
        if not info:
            return
            
        self.video_info = info
        
        # Actualizar título
        title = info.get('title', 'Título desconocido')
        self.title_label.configure(text=f"Título: {title}")
        
        # Actualizar duración
        duration = info.get('duration')
        if duration:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
                
            self.duration_label.configure(text=f"⏱️ Duración: {duration_str}")
        
        # Actualizar información del canal
        if 'uploader' in info:
            self.channel_label.configure(text=f"👤 Canal: {info['uploader']}")
        
        # Obtener miniatura
        self._fetch_thumbnail(info.get('thumbnail'))
        
        self.status_label.configure(text="Información del video cargada")
    
    def _fetch_thumbnail(self, thumbnail_url):
        """Descargar y mostrar la miniatura del video"""
        if not thumbnail_url:
            return
            
        def download_thumbnail():
            try:
                with urllib.request.urlopen(thumbnail_url) as response:
                    image_data = response.read()
                
                image = Image.open(BytesIO(image_data))
                image = image.resize((280, 158), Image.LANCZOS)
                photo_image = ImageTk.PhotoImage(image)
                
                self.root.after(0, lambda: self._set_thumbnail(photo_image))
            except Exception as e:
                print(f"Error al obtener la miniatura: {e}")
        
        threading.Thread(target=download_thumbnail, daemon=True).start()
    
    def _set_thumbnail(self, photo_image):
        """Establecer la miniatura en la interfaz"""
        self.current_thumbnail = photo_image
        self.thumbnail_label.configure(image=photo_image)
    
    def download_complete(self, download_info):
        """Manejar finalización de descarga"""
        # Añadir al historial
        self.history_manager.add(download_info)
        
        # Actualizar interfaz
        self.update_history_display()
        self.download_btn.configure(state="normal")
        
        # Notificar éxito
        messagebox.showinfo("Éxito", "Descarga completada con éxito")
        
        # Reiniciar estado
        self.reset_download_state()
    
    def download_error(self, error_msg):
        """Manejar error de descarga"""
        self.download_btn.configure(state="normal")
        messagebox.showerror("Error", f"Ocurrió un error: {error_msg}")
        self.reset_download_state()
    
    def reset_download_state(self):
        """Reiniciar estado después de descarga"""
        self.progress_bar.set(0)
        self.progress_label.configure(text="Listo para descargar")
        self.status_label.configure(text="Listo")
        self.download_btn.configure(state="normal")
    
    def clear_history(self):
        """Limpiar historial de descargas"""
        result = messagebox.askyesno("Confirmar", "¿Borrar historial de descargas?")
        if result:
            self.history_manager.clear()
            self.update_history_display()
    
    def update_history_display(self):
        """Actualizar la visualización del historial"""
        # Limpiar elementos existentes
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
        
        # Mostrar mensaje si no hay historial
        if not self.history_manager.history:
            empty_label = ctk.CTkLabel(
                self.history_scroll,
                text="No hay historial de descargas",
                font=ctk.CTkFont(size=12)
            )
            empty_label.pack(pady=20)
            return
        
        # Añadir elementos del historial
        for entry in self.history_manager.history:
            history_item = HistoryItem(
                self.history_scroll,
                entry,
                self.theme,
                self.redownload,
                height=100,
                fg_color=self.theme.card_color,
                corner_radius=10
            )
            history_item.pack(fill="x", padx=10, pady=5)
    
    def redownload(self, url):
        """Volver a descargar un video desde el historial"""
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self.fetch_video_info()