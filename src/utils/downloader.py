import threading
import re
from datetime import datetime
from yt_dlp import YoutubeDL
import imageio_ffmpeg

class YouTubeDownloader:
    def __init__(self, callback_progress=None, callback_complete=None, callback_error=None):
        self.callback_progress = callback_progress
        self.callback_complete = callback_complete
        self.callback_error = callback_error
        self.downloading = False
    
    def validate_url(self, url):
        return bool(re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.*', url))
    
    def get_video_info(self, url, callback):
        if not self.validate_url(url):
            if self.callback_error:
                self.callback_error("URL no válida")
            return
            
        def fetch_info_thread():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'noplaylist': True,
                }
                
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    callback(info)
            except Exception as e:
                if self.callback_error:
                    self.callback_error(str(e))
        
        threading.Thread(target=fetch_info_thread, daemon=True).start()
    
    def download(self, url, output_path, format_selection):
        if not self.validate_url(url):
            if self.callback_error:
                self.callback_error("URL no válida")
            return
            
        self.downloading = True
        
        def download_thread():
            try:
                # Configurar opciones
                ydl_opts = {
                    'outtmpl': f'{output_path}/%(title)s.%(ext)s',
                    'progress_hooks': [self._progress_hook],
                    'noplaylist': True,
                    'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe()
                }
                
                # Formato
                if format_selection == "mp4":
                    ydl_opts['format'] = 'best[ext=mp4]'
                elif format_selection == "mp3":
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                else:
                    ydl_opts['format'] = 'best'
                
                # Descargar
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if self.callback_complete:
                        download_info = {
                            'title': info.get('title', 'Unknown'),
                            'url': url,
                            'format': format_selection,
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        self.callback_complete(download_info)
                        
            except Exception as e:
                if self.callback_error:
                    self.callback_error(str(e))
            finally:
                self.downloading = False
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def _progress_hook(self, d):
        if not self.callback_progress:
            return
            
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                if speed:
                    speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
                else:
                    speed_str = "-- MB/s"
                    
                if eta:
                    eta_str = f"{eta} segundos restantes"
                else:
                    eta_str = "calculando..."
                
                self.callback_progress(percent, f"Descargando: {percent:.1f}% ({speed_str}, {eta_str})")
        
        elif d['status'] == 'finished':
            self.callback_progress(100, "Descarga completa, procesando archivo...")