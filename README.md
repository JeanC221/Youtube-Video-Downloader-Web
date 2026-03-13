  # YouTube Video Downloader

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-86%20passed-brightgreen)]()

Modern desktop application to download YouTube videos in multiple formats with a premium UI, persistent history, and robust error handling.

## Features

- **Multiple Formats** — MP4, MP3, M4A, WAV, WebM, MKV, or original quality
- **Best Quality Selection** — Automatically merges best video + best audio via ffmpeg
- **Smart Preview** — Thumbnails and video details before downloading
- **Dark / Light Themes** — Premium gradient UI with one-click toggle
- **Download History** — Persistent history with search, deduplication, and atomic saves
- **Retry Logic** — Automatic retries with exponential backoff on network failures
- **Disk Space Check** — Validates available space before downloading
- **Windows-Safe Filenames** — Sanitizes forbidden characters automatically
- **Progress Tracking** — Real-time speed, ETA, and percentage display
- **Metadata Caching** — Avoids re-fetching info for the same URL

## Quick Start

### Requirements

- Python 3.10+
- ffmpeg (bundled via `imageio-ffmpeg`)

### Installation

```bash
git clone https://github.com/JeanC221/Youtube-Video-Downloader.git
cd Youtube-Video-Downloader
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
python main.py
```

### Run Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Project Structure

```
Youtube-Video-Downloader/
├── main.py                  # Entry point with logging configuration
├── requirements.txt         # Python dependencies
├── conftest.py              # Shared pytest fixtures
├── src/
│   ├── app.py               # Flet Application class
│   ├── ui/
│   │   ├── components.py    # StatusChip, ModernButton, TooltipIconButton
│   │   ├── main_window.py   # Main window layout and event handlers
│   │   └── theme.py         # Dark/Light theme colour definitions
│   └── utils/
│       ├── downloader.py    # YouTubeDownloader with retry, formats, progress
│       └── history.py       # DownloadHistory with atomic writes and backups
├── tests/
│   ├── test_app.py          # Application class tests
│   ├── test_components.py   # UI component tests
│   ├── test_downloader.py   # Downloader, sanitization, disk space tests
│   ├── test_history.py      # History persistence, backup, search tests
│   └── test_theme.py        # Theme toggle and colour attribute tests
└── installer.iss            # Inno Setup installer script
```

## Build Executable

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico \
  --add-data "assets/*;assets" --name "YouTube Downloader" main.py
```

## License

Copyright © 2025 [Jean Herran](https://github.com/JeanC221).
This project is [MIT](LICENSE) licensed.

## Support

[![GitHub Issues](https://img.shields.io/badge/Report-Issue-red?style=flat&logo=github)](https://github.com/JeanC221/Youtube-Video-Downloader/issues)
