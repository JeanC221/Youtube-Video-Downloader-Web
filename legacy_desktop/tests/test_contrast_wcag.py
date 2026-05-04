"""WCAG AA contrast checks for the app theme.

Verifies that the main foreground/background text pairings in both dark and
light modes meet the WCAG 2.1 AA contrast thresholds:

* 4.5:1 for normal text
* 3.0:1 for large text (>= 18 px, or 14 px bold)

These tests only read colour tokens from :class:`AppTheme`; no Flet page is
required.
"""

from __future__ import annotations

import pytest

from src.ui.theme import AppTheme


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB hex colour, got: {value!r}")
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return r, g, b


def _channel_luminance(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_channel_luminance(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """Return the WCAG contrast ratio between two hex colours."""
    l1 = _relative_luminance(_hex_to_rgb(fg))
    l2 = _relative_luminance(_hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# (foreground_attr, background_attr, min_ratio, label)
_NORMAL_TEXT_PAIRS = [
    ("text_primary", "bg_color", 4.5, "body text on page background"),
    ("text_primary", "surface_elevated", 4.5, "body text on elevated surface"),
    ("text_primary", "card_color", 4.5, "body text on card"),
    ("text_secondary", "bg_color", 4.5, "secondary text on page background"),
    ("text_secondary", "surface_elevated", 4.5, "secondary text on elevated surface"),
]

_LARGE_TEXT_PAIRS = [
    ("text_muted", "bg_color", 3.0, "muted text on page background"),
    ("text_muted", "surface_elevated", 3.0, "muted text on elevated surface"),
]


@pytest.mark.parametrize("is_dark", [True, False])
@pytest.mark.parametrize(
    "fg_attr,bg_attr,min_ratio,label",
    _NORMAL_TEXT_PAIRS + _LARGE_TEXT_PAIRS,
)
def test_theme_contrast_meets_wcag_aa(
    is_dark: bool, fg_attr: str, bg_attr: str, min_ratio: float, label: str
) -> None:
    theme = AppTheme(is_dark=is_dark)
    fg = getattr(theme, fg_attr)
    bg = getattr(theme, bg_attr)
    ratio = contrast_ratio(fg, bg)
    mode = "dark" if is_dark else "light"
    assert ratio >= min_ratio, (
        f"WCAG AA fail in {mode} mode: {label} "
        f"({fg_attr}={fg} on {bg_attr}={bg}) ratio={ratio:.2f} < {min_ratio}"
    )
