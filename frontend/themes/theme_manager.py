"""
Theme Manager
=============
Mengelola tema (dark/light/custom) untuk overlay dan windows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ThemeColors:
    text_primary: str       = "#ffffff"
    text_secondary: str     = "#c0c0d0"
    glow_color: str         = "#ffffff"
    background: str         = "transparent"
    accent: str             = "#e94560"


_DARK_THEME = ThemeColors(
    text_primary="#ffffff",
    text_secondary="#c8c8d8",
    glow_color="#ffffff",
    background="transparent",
    accent="#e94560",
)

_LIGHT_THEME = ThemeColors(
    text_primary="#1a1a2e",
    text_secondary="#444466",
    glow_color="#000000",
    background="transparent",
    accent="#e94560",
)


class ThemeManager:
    """Menyediakan warna berdasarkan tema aktif."""

    def __init__(self) -> None:
        self._theme = "dark"
        self._colors = _DARK_THEME

    def set_theme(self, name: str) -> None:
        self._theme = name
        if name == "light":
            self._colors = _LIGHT_THEME
        else:
            self._colors = _DARK_THEME

    @property
    def colors(self) -> ThemeColors:
        return self._colors

    @property
    def current_theme(self) -> str:
        return self._theme
