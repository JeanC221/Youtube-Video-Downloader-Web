"""Tests for the YouTube downloader module."""

import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.utils.downloader import (
    FORMAT_PRESETS,
    YouTubeDownloader,
    check_disk_space,
    sanitize_filename,
    unique_filepath,
)


# -----------------------------------------------------------------------
# sanitize_filename
# -----------------------------------------------------------------------

class TestSanitizeFilename:
    """Tests for the sanitize_filename utility."""

    def test_removes_forbidden_characters(self) -> None:
        assert sanitize_filename('video <test>: "file"') == "video _test__ _file_"

    def test_strips_dots_and_spaces(self) -> None:
        assert sanitize_filename("  ...name...  ") == "name"

    def test_truncates_long_names(self) -> None:
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 200

    def test_returns_default_for_empty(self) -> None:
        assert sanitize_filename("") == "download"
        assert sanitize_filename("...") == "download"

    def test_preserves_valid_characters(self) -> None:
        assert sanitize_filename("My Video (2025) - HD") == "My Video (2025) - HD"

    def test_handles_control_characters(self) -> None:
        name = "video\x00\x01\x1ftest"
        result = sanitize_filename(name)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_handles_unicode(self) -> None:
        result = sanitize_filename("日本語テスト動画")
        assert result == "日本語テスト動画"


# -----------------------------------------------------------------------
# check_disk_space
# -----------------------------------------------------------------------

class TestCheckDiskSpace:
    """Tests for the check_disk_space utility."""

    def test_returns_true_when_enough_space(self, tmp_path: Path) -> None:
        assert check_disk_space(str(tmp_path)) is True

    def test_returns_false_when_not_enough(self, tmp_path: Path) -> None:
        # Request absurdly large amount
        assert check_disk_space(str(tmp_path), required_bytes=10**18) is False

    def test_returns_true_on_oserror(self) -> None:
        assert check_disk_space("/nonexistent/path/xyz") is True


# -----------------------------------------------------------------------
# unique_filepath
# -----------------------------------------------------------------------

class TestUniqueFilepath:
    """Tests for the unique_filepath utility."""

    def test_returns_same_if_not_exists(self, tmp_path: Path) -> None:
        fp = tmp_path / "new_file.mp4"
        assert unique_filepath(fp) == fp

    def test_appends_counter_if_exists(self, tmp_path: Path) -> None:
        fp = tmp_path / "video.mp4"
        fp.touch()
        result = unique_filepath(fp)
        assert result == tmp_path / "video (1).mp4"

    def test_increments_counter(self, tmp_path: Path) -> None:
        fp = tmp_path / "video.mp4"
        fp.touch()
        (tmp_path / "video (1).mp4").touch()
        result = unique_filepath(fp)
        assert result == tmp_path / "video (2).mp4"


# -----------------------------------------------------------------------
# FORMAT_PRESETS
# -----------------------------------------------------------------------

class TestFormatPresets:
    """Tests for format preset definitions."""

    def test_all_presets_have_format_key(self) -> None:
        for name, preset in FORMAT_PRESETS.items():
            assert "format" in preset, f"Preset '{name}' missing 'format'"

    def test_audio_presets_have_postprocessors(self) -> None:
        for fmt in ("mp3", "m4a", "wav"):
            assert len(FORMAT_PRESETS[fmt]["postprocessors"]) > 0

    def test_video_presets_have_merge_format(self) -> None:
        for fmt in ("mp4", "webm", "mkv"):
            assert "merge_output_format" in FORMAT_PRESETS[fmt]

    def test_expected_presets_exist(self) -> None:
        expected = {"mp4", "mp3", "m4a", "wav", "webm", "mkv", "original"}
        assert expected == set(FORMAT_PRESETS.keys())


# -----------------------------------------------------------------------
# YouTubeDownloader.validate_url
# -----------------------------------------------------------------------

class TestValidateUrl:
    """Tests for URL validation."""

    VALID_URLS = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "  https://youtube.com/watch?v=dQw4w9WgXcQ  ",  # whitespace
    ]

    INVALID_URLS = [
        "",
        "not a url",
        "https://google.com",
        "https://vimeo.com/12345",
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/",  # no video ID
    ]

    @pytest.mark.parametrize("url", VALID_URLS)
    def test_valid_urls(self, url: str) -> None:
        assert YouTubeDownloader.validate_url(url) is True

    @pytest.mark.parametrize("url", INVALID_URLS)
    def test_invalid_urls(self, url: str) -> None:
        assert YouTubeDownloader.validate_url(url) is False


# -----------------------------------------------------------------------
# YouTubeDownloader.get_video_info
# -----------------------------------------------------------------------

class TestGetVideoInfo:
    """Tests for fetching video info."""

    def test_invalid_url_calls_callback_with_none(self) -> None:
        dl = YouTubeDownloader()
        result = []
        dl.get_video_info("not a url", lambda info: result.append(info))
        time.sleep(0.1)
        assert result == [None]

    def test_cached_result_returned_immediately(self) -> None:
        dl = YouTubeDownloader()
        fake_info = {"title": "Cached Video", "uploader": "Test"}
        dl._info_cache["https://www.youtube.com/watch?v=dQw4w9WgXcQ"] = fake_info

        result = []
        dl.get_video_info(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lambda info: result.append(info),
        )
        assert len(result) == 1
        assert result[0]["title"] == "Cached Video"

    @patch("src.utils.downloader.YoutubeDL")
    def test_fetches_info_on_valid_url(self, mock_ydl_class: MagicMock) -> None:
        fake_info = {"title": "Real Video", "uploader": "RealUser"}
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.extract_info.return_value = fake_info
        mock_ydl_class.return_value = mock_instance

        dl = YouTubeDownloader()
        result = []

        dl.get_video_info(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lambda info: result.append(info),
        )
        time.sleep(1)  # Wait for thread
        assert len(result) == 1
        assert result[0]["title"] == "Real Video"

    @patch("src.utils.downloader.YoutubeDL")
    def test_returns_none_on_exception(self, mock_ydl_class: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.extract_info.side_effect = Exception("Network error")
        mock_ydl_class.return_value = mock_instance

        dl = YouTubeDownloader()
        result = []

        dl.get_video_info(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lambda info: result.append(info),
        )
        time.sleep(1)
        assert result == [None]


# -----------------------------------------------------------------------
# YouTubeDownloader.download
# -----------------------------------------------------------------------

class TestDownload:
    """Tests for the download method (no real network calls)."""

    def test_rejects_invalid_url(self) -> None:
        errors = []
        dl = YouTubeDownloader(callback_error=lambda e: errors.append(e))
        dl.download("bad url", "/tmp", "mp4")
        time.sleep(0.1)
        assert any("no válida" in e.lower() for e in errors)

    def test_rejects_when_already_downloading(self, tmp_path: Path) -> None:
        errors = []
        dl = YouTubeDownloader(callback_error=lambda e: errors.append(e))
        dl.downloading = True  # Simulate active download
        dl.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            str(tmp_path),
            "mp4",
        )
        time.sleep(0.1)
        assert any("en curso" in e for e in errors)

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir" / "downloads"
        dl = YouTubeDownloader(callback_error=lambda e: None)
        with patch("src.utils.downloader.check_disk_space", return_value=True):
            with patch.object(dl, "_download_thread"):
                dl.download(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    str(new_dir),
                    "mp4",
                )
                time.sleep(0.2)
                assert new_dir.exists()

    def test_rejects_when_disk_full(self, tmp_path: Path) -> None:
        errors = []
        dl = YouTubeDownloader(callback_error=lambda e: errors.append(e))
        with patch(
            "src.utils.downloader.check_disk_space", return_value=False
        ):
            dl.download(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                str(tmp_path),
                "mp4",
            )
            time.sleep(0.1)
        assert any("insuficiente" in e.lower() for e in errors)

    @patch("src.utils.downloader.imageio_ffmpeg")
    @patch("src.utils.downloader.YoutubeDL")
    def test_successful_download_calls_complete(
        self,
        mock_ydl_class: MagicMock,
        mock_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_ffmpeg.get_ffmpeg_exe.return_value = "ffmpeg"

        fake_info = {"title": "Downloaded", "uploader": "User", "thumbnail": ""}
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.extract_info.return_value = fake_info
        mock_instance.prepare_filename.return_value = str(
            tmp_path / "Downloaded.mp4"
        )
        mock_ydl_class.return_value = mock_instance

        completed = []
        dl = YouTubeDownloader(
            callback_complete=lambda info: completed.append(info),
            callback_error=lambda e: None,
            max_retries=1,
        )

        dl.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            str(tmp_path),
            "mp4",
        )
        time.sleep(2)

        assert len(completed) == 1
        assert completed[0]["title"] == "Downloaded"
        assert completed[0]["format"] == "mp4"

    @patch("src.utils.downloader.imageio_ffmpeg")
    @patch("src.utils.downloader.YoutubeDL")
    def test_retries_on_failure(
        self,
        mock_ydl_class: MagicMock,
        mock_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_ffmpeg.get_ffmpeg_exe.return_value = "ffmpeg"

        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.extract_info.side_effect = Exception("Network timeout")
        mock_ydl_class.return_value = mock_instance

        errors = []
        dl = YouTubeDownloader(
            callback_error=lambda e: errors.append(e),
            max_retries=2,
        )

        dl.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            str(tmp_path),
            "mp4",
        )
        time.sleep(8)  # Wait for retries (2^1 + 2^2 = 6s + margin)

        assert len(errors) >= 1
        assert "2 intentos" in errors[-1]


# -----------------------------------------------------------------------
# Progress hook
# -----------------------------------------------------------------------

class TestProgressHook:
    """Tests for the _progress_hook method."""

    def test_downloading_status(self) -> None:
        calls = []
        dl = YouTubeDownloader(
            callback_progress=lambda p, t: calls.append((p, t))
        )

        dl._progress_hook(
            {
                "status": "downloading",
                "total_bytes": 1000,
                "downloaded_bytes": 500,
                "speed": 1024 * 1024,
                "eta": 10,
            }
        )

        assert len(calls) == 1
        percent, text = calls[0]
        assert 49 <= percent <= 51
        assert "MB/s" in text

    def test_finished_status(self) -> None:
        calls = []
        dl = YouTubeDownloader(
            callback_progress=lambda p, t: calls.append((p, t))
        )
        dl._progress_hook({"status": "finished"})

        assert len(calls) == 1
        assert calls[0][0] == 100

    def test_no_callback_does_not_raise(self) -> None:
        dl = YouTubeDownloader()
        dl._progress_hook({"status": "downloading", "total_bytes": 100, "downloaded_bytes": 50})

    def test_unknown_total_bytes(self) -> None:
        calls = []
        dl = YouTubeDownloader(
            callback_progress=lambda p, t: calls.append((p, t))
        )
        dl._progress_hook(
            {"status": "downloading", "downloaded_bytes": 500}
        )
        assert len(calls) == 1
        assert "desconocido" in calls[0][1].lower()
