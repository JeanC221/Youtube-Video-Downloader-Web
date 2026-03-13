"""YouTube video downloader module using yt-dlp.

Provides a robust downloader with retry logic, format selection,
progress callbacks, filename sanitization, and disk space checks.
"""

import logging
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import imageio_ffmpeg
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

# Characters forbidden in Windows filenames
_WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_FILENAME_LEN = 200


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in Windows filenames.

    Args:
        name: Raw filename string.

    Returns:
        A safe filename string for Windows.
    """
    sanitized = _WINDOWS_FORBIDDEN.sub("_", name)
    sanitized = sanitized.strip(". ")
    if len(sanitized) > _MAX_FILENAME_LEN:
        sanitized = sanitized[:_MAX_FILENAME_LEN]
    return sanitized or "download"


def check_disk_space(path: str, required_bytes: int = 100 * 1024 * 1024) -> bool:
    """Check if there is enough disk space at the given path.

    Args:
        path: Directory path to check.
        required_bytes: Minimum required bytes (default 100 MB).

    Returns:
        True if enough space is available.
    """
    try:
        usage = shutil.disk_usage(path)
        return usage.free >= required_bytes
    except OSError:
        logger.warning("Could not check disk space for %s", path)
        return True


def unique_filepath(filepath: Path) -> Path:
    """Return a unique file path by appending (1), (2), etc. if file exists.

    Args:
        filepath: Desired file path.

    Returns:
        A Path that does not exist on disk.
    """
    if not filepath.exists():
        return filepath
    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


# ---------------------------------------------------------------------------
# Format presets
# ---------------------------------------------------------------------------

FORMAT_PRESETS: Dict[str, Dict[str, Any]] = {
    "mp4": {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "merge_output_format": "mp4",
        "postprocessors": [],
    },
    "mp3": {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    },
    "m4a": {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ],
    },
    "wav": {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
    },
    "webm": {
        "format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best",
        "merge_output_format": "webm",
        "postprocessors": [],
    },
    "mkv": {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mkv",
        "postprocessors": [],
    },
    "original": {
        "format": "bestvideo+bestaudio/best",
        "postprocessors": [],
    },
}

# URL validation pattern supporting youtube.com, youtu.be, and shorts
_URL_PATTERN = re.compile(
    r"(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be)/(watch\?v=|shorts/|embed/|v/|.+\?v=)?[\w\-]{11}"
)


class YouTubeDownloader:
    """Downloads YouTube videos using yt-dlp with progress callbacks.

    Attributes:
        callback_progress: Called with (percent, status_text) during download.
        callback_complete: Called with download info dict on success.
        callback_error: Called with error message string on failure.
        downloading: Whether a download is currently in progress.
        max_retries: Number of retry attempts on transient failures.
    """

    def __init__(
        self,
        callback_progress: Optional[Callable[[float, str], None]] = None,
        callback_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        callback_error: Optional[Callable[[str], None]] = None,
        max_retries: int = 3,
    ) -> None:
        self.callback_progress = callback_progress
        self.callback_complete = callback_complete
        self.callback_error = callback_error
        self.downloading = False
        self.max_retries = max_retries
        self._lock = threading.Lock()
        self._info_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def validate_url(url: str) -> bool:
        """Check if *url* looks like a valid YouTube URL.

        Args:
            url: URL string to validate.

        Returns:
            True if the URL matches the YouTube pattern.
        """
        return bool(_URL_PATTERN.match(url.strip()))

    def get_video_info(
        self,
        url: str,
        callback: Callable[[Optional[Dict[str, Any]]], None],
    ) -> None:
        """Fetch video metadata asynchronously, calling *callback* with the info dict.

        Results are cached so repeated calls for the same URL are instant.

        Args:
            url: YouTube video URL.
            callback: Function receiving the info dict or None on error.
        """
        url = url.strip()
        if not self.validate_url(url):
            callback(None)
            return

        # Check cache
        if url in self._info_cache:
            callback(self._info_cache[url])
            return

        def _fetch() -> None:
            try:
                ydl_opts: Dict[str, Any] = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "noplaylist": True,
                    "socket_timeout": 15,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        self._info_cache[url] = info
                    callback(info)
            except Exception as exc:
                logger.error("Failed to fetch video info for %s: %s", url, exc)
                callback(None)

        threading.Thread(target=_fetch, daemon=True).start()

    def download(
        self,
        url: str,
        output_path: str,
        format_selection: str = "mp4",
    ) -> None:
        """Start an asynchronous download in a background thread.

        Args:
            url: YouTube video URL.
            output_path: Directory to save the downloaded file.
            format_selection: One of the keys in FORMAT_PRESETS.
        """
        url = url.strip()
        if not self.validate_url(url):
            if self.callback_error:
                self.callback_error("URL no válida")
            return

        output_dir = Path(output_path)
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                if self.callback_error:
                    self.callback_error(f"No se pudo crear la carpeta: {exc}")
                return

        if not check_disk_space(str(output_dir)):
            if self.callback_error:
                self.callback_error(
                    "Espacio en disco insuficiente (se requieren al menos 100 MB)"
                )
            return

        with self._lock:
            if self.downloading:
                if self.callback_error:
                    self.callback_error("Ya hay una descarga en curso")
                return
            self.downloading = True

        threading.Thread(
            target=self._download_thread,
            args=(url, output_dir, format_selection),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _download_thread(
        self,
        url: str,
        output_dir: Path,
        format_selection: str,
    ) -> None:
        """Execute the download with retry logic."""
        preset = FORMAT_PRESETS.get(format_selection, FORMAT_PRESETS["mp4"])
        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Download attempt %d/%d for %s (%s)",
                    attempt,
                    self.max_retries,
                    url,
                    format_selection,
                )

                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

                ydl_opts: Dict[str, Any] = {
                    "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
                    "progress_hooks": [self._progress_hook],
                    "noplaylist": True,
                    "ffmpeg_location": ffmpeg_path,
                    "socket_timeout": 30,
                    "retries": 10,
                    "fragment_retries": 10,
                    "file_access_retries": 5,
                    "extractor_retries": 5,
                    "quiet": True,
                    "no_warnings": True,
                    "restrictfilenames": False,
                    "windowsfilenames": True,
                    "format": preset["format"],
                }

                if preset.get("merge_output_format"):
                    ydl_opts["merge_output_format"] = preset["merge_output_format"]

                if preset.get("postprocessors"):
                    ydl_opts["postprocessors"] = preset["postprocessors"]

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                    if info and self.callback_complete:
                        filepath = ydl.prepare_filename(info)
                        # For audio conversions the extension changes
                        if format_selection in ("mp3", "m4a", "wav"):
                            filepath = str(
                                Path(filepath).with_suffix(f".{format_selection}")
                            )

                        download_info: Dict[str, Any] = {
                            "title": info.get("title", "Desconocido"),
                            "url": url,
                            "format": format_selection,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "path": filepath,
                            "thumbnail": info.get("thumbnail", ""),
                            "duration": info.get("duration", 0),
                            "uploader": info.get("uploader", ""),
                            "filesize": info.get("filesize")
                            or info.get("filesize_approx", 0),
                        }
                        self.callback_complete(download_info)
                    return  # Success

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Download attempt %d failed: %s", attempt, last_error
                )
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    if self.callback_progress:
                        self.callback_progress(
                            0,
                            f"Reintentando en {wait}s (intento {attempt}/{self.max_retries})…",
                        )
                    time.sleep(wait)

            finally:
                with self._lock:
                    self.downloading = False

        # All retries exhausted
        if self.callback_error and last_error:
            self.callback_error(
                f"Error tras {self.max_retries} intentos: {last_error}"
            )

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """yt-dlp progress hook, forwarding data to callback_progress."""
        if not self.callback_progress:
            return

        status = d.get("status", "")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)

            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get("speed", 0)
                eta = d.get("eta", 0)

                speed_str = (
                    f"{speed / 1024 / 1024:.2f} MB/s" if speed else "-- MB/s"
                )
                eta_str = f"{eta}s restantes" if eta else "calculando…"

                self.callback_progress(
                    percent,
                    f"Descargando: {percent:.1f}% ({speed_str}, {eta_str})",
                )
            else:
                self.callback_progress(0, "Descargando… (tamaño desconocido)")

        elif status == "finished":
            self.callback_progress(100, "Descarga completa, procesando archivo…")

        elif status == "error":
            logger.error("yt-dlp reported an error during download")
