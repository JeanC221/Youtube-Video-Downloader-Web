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


def _check_flet_compatibility() -> None:
    """Fail fast with a clear message if Flet is on an unsupported version.

    The UI layer is currently validated against the 0.84.x family only.
    Keep the range tight until a newer release is explicitly revalidated.
    """
    import importlib.metadata

    try:
        version = importlib.metadata.version("flet")
    except importlib.metadata.PackageNotFoundError:
        sys.stderr.write("ERROR: Flet is not installed. Run: pip install -r requirements.txt\n")
        sys.exit(2)

    major, minor, *_ = (int(p) for p in (version.split(".") + ["0", "0"])[:3])
    if (major, minor) >= (0, 85):
        sys.stderr.write(
            f"ERROR: Flet {version} is not supported.\n"
            "       This project targets Flet 0.84.x (see requirements.txt).\n"
            "       Run: pip install 'flet>=0.84,<0.85' 'flet-desktop>=0.84,<0.85'\n"
        )
        sys.exit(2)
    if (major, minor) < (0, 84):
        sys.stderr.write(
            f"ERROR: Flet {version} is too old. Minimum supported: 0.84.\n"
        )
        sys.exit(2)


if __name__ == "__main__":
    _configure_logging()
    _check_flet_compatibility()
    app = Application()
    app.run()
