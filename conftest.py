"""Shared pytest fixtures and configuration."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock

import pytest

# Ensure project root is on path
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for each test."""
    return tmp_path


@pytest.fixture
def history_path(tmp_path: Path) -> Path:
    """Return a path for a temporary history JSON file."""
    return tmp_path / "test_history.json"


@pytest.fixture
def sample_history_entries() -> List[Dict[str, Any]]:
    """Return a list of realistic history entries for testing."""
    return [
        {
            "title": "Test Video 1",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "mp4",
            "date": "2025-01-15 10:30",
            "path": "C:/Users/test/Downloads/Test Video 1.mp4",
            "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/0.jpg",
            "duration": 212,
            "uploader": "Rick Astley",
            "filesize": 15000000,
            "status": "completed",
        },
        {
            "title": "Test Video 2",
            "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "format": "mp3",
            "date": "2025-01-14 09:00",
            "path": "C:/Users/test/Downloads/Test Video 2.mp3",
            "thumbnail": "",
            "duration": 19,
            "uploader": "jawed",
            "filesize": 500000,
            "status": "completed",
        },
    ]


@pytest.fixture
def sample_download_info() -> Dict[str, Any]:
    """Return a single download info dict."""
    return {
        "title": "Sample Download",
        "url": "https://www.youtube.com/watch?v=abc123def45",
        "format": "mp4",
        "date": "2025-06-01 14:00:00",
        "path": "C:/Users/test/Downloads/Sample Download.mp4",
        "thumbnail": "https://img.youtube.com/vi/abc123def45/0.jpg",
        "duration": 120,
        "uploader": "TestChannel",
        "filesize": 8000000,
    }


@pytest.fixture
def mock_page() -> MagicMock:
    """Return a mock Flet Page object."""
    page = MagicMock()
    page.update = MagicMock()
    page.overlay = []
    return page
