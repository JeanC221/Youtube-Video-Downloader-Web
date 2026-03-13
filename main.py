"""YouTube Video Downloader – Entry point.

Configures logging and launches the application.
"""

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path for relative imports
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.app import Application


def _configure_logging() -> None:
    """Set up root logger with console output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    _configure_logging()
    app = Application()
    app.run()
