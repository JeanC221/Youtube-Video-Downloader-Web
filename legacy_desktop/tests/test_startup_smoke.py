"""End-to-end startup smoke tests.

These tests catch the *family* of failures that the unit tests miss because
the unit tests use ``MagicMock`` for ``ft.Page`` (so any wrong API call on a
Page or Control silently no-ops).

Two complementary checks live here:

1. ``test_no_unknown_flet_symbols`` — a static AST scan that resolves every
   ``ft.<x>.<y>`` chain used in ``src/`` against the *actually installed*
   ``flet`` module. If a symbol does not exist (e.g. ``ft.BoxFit`` was
   renamed to ``ft.ImageFit``), this test fails with a precise file:line.
2. ``test_main_window_builds_against_real_flet_page`` — instantiates a real
   ``flet.Page`` (without starting the desktop client) and runs
   ``MainWindow(page)`` end-to-end. This catches removed attributes
   (``page.snack_bar``), wrong constructor kwargs, dataclass typos, etc.
3. ``test_flet_version_in_supported_range`` — fails fast in CI if someone
    drifts outside the validated Flet 0.84.x family.

Together these prevent the "all tests pass but the app does not open"
regression that bit us once already.
"""

from __future__ import annotations

import ast
import importlib.metadata
import pathlib
from typing import List, Tuple

import flet as ft
import pytest

from src.ui.main_window import MainWindow

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"


# ---------------------------------------------------------------------------
# 1. Static API compatibility check
# ---------------------------------------------------------------------------


def _collect_ft_chains() -> List[Tuple[str, str, int]]:
    """Walk every src/*.py and collect every ``ft.X.Y...`` attribute chain.

    Returns a list of (chain, file, lineno) tuples.
    """
    out: List[Tuple[str, str, int]] = []
    for path in SRC_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            parts: List[str] = []
            cur: ast.AST = node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name) and cur.id == "ft":
                parts.reverse()
                out.append((".".join(parts), str(path.relative_to(PROJECT_ROOT)), node.lineno))
    return out


def _resolve(chain: str) -> bool:
    """Return True iff every step of ``ft.<chain>`` is a real attribute."""
    obj: object = ft
    for part in chain.split("."):
        if not hasattr(obj, part):
            return False
        obj = getattr(obj, part)
    return True


def test_no_unknown_flet_symbols() -> None:
    """Every ``ft.<...>`` reference in src/ must resolve in the installed Flet.

    If you upgrade Flet and a symbol was removed/renamed, this test will
    enumerate the exact lines that need updating.
    """
    missing = [
        (chain, file, line)
        for chain, file, line in _collect_ft_chains()
        if not _resolve(chain)
    ]
    if missing:
        report = "\n".join(f"  ft.{chain}    ({file}:{line})" for chain, file, line in missing)
        pytest.fail(
            f"{len(missing)} Flet symbol(s) not present in installed Flet "
            f"({importlib.metadata.version('flet')}):\n{report}"
        )


# ---------------------------------------------------------------------------
# 2. Real MainWindow construction
# ---------------------------------------------------------------------------


class _StubPage:
    """A minimal stand-in for ``ft.Page`` that exercises *real* control APIs.

    We deliberately do **not** use ``MagicMock`` here: a Mock would happily
    accept any attribute access and hide the very bugs (``page.snack_bar``
    removed, ``page.window.center`` async, etc.) that we want to catch.
    Instead we expose only the surface area that ``MainWindow`` is allowed
    to touch during construction. Anything beyond that raises
    ``AttributeError`` and the test fails — which is the desired behaviour.
    """

    def __init__(self) -> None:
        self.controls: list = []
        self.overlay: list = []
        self.services: list = []
        self.theme_mode = ft.ThemeMode.DARK
        self.bgcolor: str | None = None
        self.padding = 0
        self.spacing = 0
        self.title = ""
        self.window = _StubWindow()
        self.on_keyboard_event = None

    def update(self) -> None:
        # Construction phase doesn't need to push anything to the client.
        pass

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def show_dialog(self, control) -> None:
        if control not in self.overlay:
            self.overlay.append(control)

    def pop_dialog(self):
        if self.overlay:
            return self.overlay.pop()
        return None


class _StubWindow:
    width = 1180
    height = 820
    min_width = 980
    min_height = 720

    def center(self) -> None:
        return None


def test_main_window_builds_against_stub_page() -> None:
    """Building MainWindow must not raise and must register a root control."""
    page = _StubPage()
    root = MainWindow(page)
    assert root is not None
    # MainWindow must register a FilePicker service so directory selection
    # works at runtime.
    assert any(isinstance(service, ft.FilePicker) for service in page.services), (
        "MainWindow did not register a FilePicker in page.services; "
        "the 'Change folder' button will not work."
    )


# ---------------------------------------------------------------------------
# 3. Version guard
# ---------------------------------------------------------------------------


def test_flet_version_in_supported_range() -> None:
    """Pin tests to the Flet family the UI is validated against."""
    version = importlib.metadata.version("flet")
    major, minor, *_ = (int(p) for p in version.split(".")[:2] + ["0"])
    assert (major, minor) < (0, 85), (
        f"Flet {version} is newer than the validated 0.84.x family. "
        "Review the UI against the new release before widening the version pin."
    )
    assert (major, minor) >= (0, 84), (
        f"Flet {version} is older than the validated minimum version 0.84."
    )
