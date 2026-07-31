"""
Click-Through Manager
=====================
Mengaktifkan WS_EX_TRANSPARENT dan WS_EX_LAYERED menggunakan Win32 API
sehingga overlay benar-benar click-through.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from backend.logger.app_logger import app_logger

# Win32 style constants
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST     = 0x00000008
WS_EX_NOACTIVATE  = 0x08000000


def _hwnd(window) -> Optional[int]:
    """Ambil HWND dari PySide6 window."""
    try:
        return int(window.winId())
    except Exception:
        return None


def enable_click_through(window) -> None:
    """Aktifkan click-through menggunakan Win32 API."""
    hwnd = _hwnd(window)
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        app_logger.debug("[ClickThrough] Click-through ENABLED")
    except Exception as e:
        app_logger.error(f"[ClickThrough] Enable error: {e}")


def disable_click_through(window) -> None:
    """Nonaktifkan click-through (untuk drag mode)."""
    hwnd = _hwnd(window)
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style &= ~WS_EX_TRANSPARENT
        style |= WS_EX_LAYERED | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        app_logger.debug("[ClickThrough] Click-through DISABLED")
    except Exception as e:
        app_logger.error(f"[ClickThrough] Disable error: {e}")
