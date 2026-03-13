"""Tests for the download history module."""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.utils.history import DownloadHistory


class TestDownloadHistoryInit:
    """Tests for DownloadHistory initialization."""

    def test_creates_empty_history_when_no_file(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        assert h.history == []
        assert h.get_all() == []

    def test_loads_existing_history(
        self, history_path: Path, sample_history_entries: List[Dict[str, Any]]
    ) -> None:
        history_path.write_text(
            json.dumps(sample_history_entries), encoding="utf-8"
        )
        h = DownloadHistory(history_path=history_path)
        assert len(h.history) == 2
        assert h.history[0]["title"] == "Test Video 1"

    def test_handles_corrupted_json(self, history_path: Path) -> None:
        history_path.write_text("NOT VALID JSON {{{", encoding="utf-8")
        h = DownloadHistory(history_path=history_path)
        assert h.history == []

    def test_handles_non_list_json(self, history_path: Path) -> None:
        history_path.write_text('{"key": "value"}', encoding="utf-8")
        h = DownloadHistory(history_path=history_path)
        assert h.history == []

    def test_respects_max_entries_on_load(self, history_path: Path) -> None:
        entries = [
            {"title": f"Video {i}", "url": f"https://youtu.be/{i}"}
            for i in range(200)
        ]
        history_path.write_text(json.dumps(entries), encoding="utf-8")
        h = DownloadHistory(history_path=history_path, max_entries=50)
        assert len(h.history) == 50


class TestDownloadHistoryAdd:
    """Tests for adding entries."""

    def test_add_single_entry(
        self, history_path: Path, sample_download_info: Dict[str, Any]
    ) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add(sample_download_info)
        assert len(h.get_all()) == 1
        assert h.get_all()[0]["title"] == "Sample Download"

    def test_new_entry_is_first(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"title": "First", "url": "https://youtu.be/aaa"})
        h.add({"title": "Second", "url": "https://youtu.be/bbb"})
        assert h.get_all()[0]["title"] == "Second"

    def test_deduplication_by_url(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        url = "https://youtu.be/same_video"
        h.add({"title": "V1", "url": url})
        h.add({"title": "V1 Updated", "url": url})
        assert len(h.get_all()) == 1
        assert h.get_all()[0]["title"] == "V1 Updated"

    def test_max_entries_enforced(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path, max_entries=5)
        for i in range(10):
            h.add({"title": f"Video {i}", "url": f"https://youtu.be/{i}"})
        assert len(h.get_all()) == 5

    def test_defaults_applied(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"url": "https://youtu.be/xyz"})
        entry = h.get_all()[0]
        assert entry["title"] == "Desconocido"
        assert entry["format"] == "mp4"
        assert entry["status"] == "completed"

    def test_persistence_across_instances(
        self, history_path: Path, sample_download_info: Dict[str, Any]
    ) -> None:
        h1 = DownloadHistory(history_path=history_path)
        h1.add(sample_download_info)

        h2 = DownloadHistory(history_path=history_path)
        assert len(h2.get_all()) == 1
        assert h2.get_all()[0]["url"] == sample_download_info["url"]


class TestDownloadHistoryRemove:
    """Tests for removing entries."""

    def test_remove_existing(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        url = "https://youtu.be/rem"
        h.add({"title": "To Remove", "url": url})
        assert h.remove(url) is True
        assert len(h.get_all()) == 0

    def test_remove_nonexistent_returns_false(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        assert h.remove("https://youtu.be/nope") is False


class TestDownloadHistoryClear:
    """Tests for clearing history."""

    def test_clear_empties_list(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"title": "A", "url": "https://youtu.be/a"})
        h.add({"title": "B", "url": "https://youtu.be/b"})
        h.clear()
        assert h.get_all() == []


class TestDownloadHistorySearch:
    """Tests for search functionality."""

    def test_search_by_title(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"title": "Python Tutorial", "url": "https://youtu.be/py"})
        h.add({"title": "JavaScript Tutorial", "url": "https://youtu.be/js"})
        h.add({"title": "Cooking Show", "url": "https://youtu.be/cook"})

        results = h.search("tutorial")
        assert len(results) == 2

    def test_search_case_insensitive(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"title": "UPPERCASE TITLE", "url": "https://youtu.be/up"})
        results = h.search("uppercase")
        assert len(results) == 1

    def test_search_no_results(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        h.add({"title": "Video", "url": "https://youtu.be/v"})
        assert h.search("nonexistent") == []


class TestDownloadHistoryBackup:
    """Tests for backup and recovery."""

    def test_backup_created_on_save(self, history_path: Path) -> None:
        h = DownloadHistory(history_path=history_path)
        # First save creates the file but no backup (nothing to back up)
        h.add({"title": "First", "url": "https://youtu.be/1"})

        # Second save should create a backup
        h.add({"title": "Second", "url": "https://youtu.be/2"})

        backup = history_path.with_suffix(".json.bak")
        assert backup.exists()

    def test_recovery_from_backup(self, history_path: Path) -> None:
        backup = history_path.with_suffix(".json.bak")
        backup_data = [{"title": "Backup Entry", "url": "https://youtu.be/bak"}]
        backup.write_text(json.dumps(backup_data), encoding="utf-8")

        # Main file is corrupt
        history_path.write_text("CORRUPT!", encoding="utf-8")

        h = DownloadHistory(history_path=history_path)
        assert len(h.get_all()) == 1
        assert h.get_all()[0]["title"] == "Backup Entry"
