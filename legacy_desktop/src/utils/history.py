"""Download history persistence with atomic writes and data integrity.

Stores the download history as a JSON file in the user's home directory,
with automatic backups and safe concurrent access via file locking.
"""

import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_HISTORY_PATH = Path.home() / ".youtube_downloader_history.json"
_MAX_ENTRIES = 100


class DownloadHistory:
    """Manages a persistent list of download records stored as JSON.

    Features:
        - Thread-safe read/write via a lock.
        - Atomic file writes (write to temp, then rename).
        - Automatic backup before each write.
        - Deduplication by URL.
        - Configurable maximum history size.

    Args:
        history_path: Path for the JSON file (default: ~/.youtube_downloader_history.json).
        max_entries: Maximum number of entries to keep.
    """

    def __init__(
        self,
        history_path: Optional[Path] = None,
        max_entries: int = _MAX_ENTRIES,
    ) -> None:
        self.history_path = history_path or _DEFAULT_HISTORY_PATH
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self.history: List[Dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, info: Dict[str, Any]) -> None:
        """Add a download entry, removing any prior entry with the same URL.

        Args:
            info: Dictionary with at least 'url'. Recognised keys:
                title, url, format, date, path, thumbnail, duration,
                uploader, filesize, status.
        """
        with self._lock:
            url = info.get("url", "")
            # Remove previous entry with same URL
            self.history = [h for h in self.history if h.get("url") != url]

            entry: Dict[str, Any] = {
                "title": info.get("title", "Desconocido"),
                "url": url,
                "format": info.get("format", "mp4"),
                "date": info.get("date", datetime.now().strftime("%Y-%m-%d %H:%M")),
                "path": info.get("path", ""),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "filesize": info.get("filesize", 0),
                "status": info.get("status", "completed"),
            }

            self.history.insert(0, entry)
            self.history = self.history[: self.max_entries]
            self._save()

    def remove(self, url: str) -> bool:
        """Remove the entry matching *url*.

        Returns:
            True if an entry was removed.
        """
        with self._lock:
            before = len(self.history)
            self.history = [h for h in self.history if h.get("url") != url]
            if len(self.history) < before:
                self._save()
                return True
            return False

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self.history.clear()
            self._save()

    def get_all(self) -> List[Dict[str, Any]]:
        """Return a shallow copy of all history entries."""
        with self._lock:
            return list(self.history)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Return entries whose title contains *query* (case-insensitive)."""
        q = query.lower()
        with self._lock:
            return [h for h in self.history if q in h.get("title", "").lower()]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load history from disk, falling back to backup on corruption."""
        path = Path(self.history_path)
        backup = path.with_suffix(".json.bak")

        for candidate in (path, backup):
            if candidate.exists():
                try:
                    raw = candidate.read_text(encoding="utf-8")
                    data = json.loads(raw)
                    if isinstance(data, list):
                        self.history = data[: self.max_entries]
                        logger.info(
                            "Loaded %d history entries from %s",
                            len(self.history),
                            candidate,
                        )
                        return
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(
                        "Failed to load history from %s: %s", candidate, exc
                    )

        self.history = []

    def _save(self) -> None:
        """Atomically write history to disk with a backup of the previous file."""
        path = Path(self.history_path)
        backup = path.with_suffix(".json.bak")

        # Backup existing file
        if path.exists():
            try:
                shutil.copy2(str(path), str(backup))
            except OSError as exc:
                logger.warning("Could not create history backup: %s", exc)

        # Atomic write: write to temp file then rename
        try:
            dir_path = path.parent
            dir_path.mkdir(parents=True, exist_ok=True)

            fd, tmp_path = tempfile.mkstemp(
                dir=str(dir_path), suffix=".tmp", prefix="hist_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)

                # On Windows, we must remove the target first
                if path.exists():
                    path.unlink()
                os.rename(tmp_path, str(path))
            except BaseException:
                # Cleanup temp file on error
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        except OSError as exc:
            logger.error("Failed to save history: %s", exc)
