"""
System Tray
===========
EchoLyrics berjalan melalui System Tray.
Menyediakan menu konteks dan ikon tray.
"""

from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PySide6.QtCore import QObject, Signal, Qt

from backend.logger.app_logger import app_logger


def _create_tray_icon() -> QIcon:
    """Buat ikon tray sederhana (musik note) jika tidak ada file ikon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background lingkaran hijau (warna Spotify-like)
    painter.setBrush(QColor(30, 215, 96))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, 32, 32)

    # Teks "♪"
    painter.setPen(QColor(0, 0, 0))
    font = QFont("Arial", 16)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
    painter.end()
    return QIcon(pixmap)


class SystemTraySignals(QObject):
    show_overlay  = Signal()
    toggle_drag   = Signal()
    hide_overlay  = Signal()
    show_settings = Signal()
    show_lyrics   = Signal()
    refresh       = Signal()
    clear_cache   = Signal()
    restart       = Signal()
    quit_app      = Signal()


class SystemTray:
    def __init__(self) -> None:
        self.signals = SystemTraySignals()
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_create_tray_icon())
        self._tray.setToolTip("EchoLyrics")
        self._setup_menu()
        self._tray.activated.connect(self._on_activated)

    def _setup_menu(self) -> None:
        menu = QMenu()

        action_drag = menu.addAction("🖐  Mode Geser Subtitle (Drag)")
        action_drag.triggered.connect(self.signals.toggle_drag)

        action_show = menu.addAction("▶  Show Overlay")
        action_show.triggered.connect(self.signals.show_overlay)

        action_hide = menu.addAction("■  Hide Overlay")
        action_hide.triggered.connect(self.signals.hide_overlay)

        menu.addSeparator()

        action_settings = menu.addAction("⚙  Settings")
        action_settings.triggered.connect(self.signals.show_settings)

        action_lyrics = menu.addAction("♪  Full Lyrics")
        action_lyrics.triggered.connect(self.signals.show_lyrics)

        menu.addSeparator()

        action_refresh = menu.addAction("↻  Refresh Spotify")
        action_refresh.triggered.connect(self.signals.refresh)

        action_cache = menu.addAction("🗑  Clear Cache")
        action_cache.triggered.connect(self.signals.clear_cache)

        menu.addSeparator()

        action_restart = menu.addAction("⟳  Restart")
        action_restart.triggered.connect(self.signals.restart)

        action_exit = menu.addAction("✕  Exit")
        action_exit.triggered.connect(self.signals.quit_app)

        self._tray.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.signals.show_lyrics.emit()

    def show(self) -> None:
        self._tray.show()
        app_logger.info("[SystemTray] Tray icon shown.")

    def update_tooltip(self, text: str) -> None:
        self._tray.setToolTip(f"EchoLyrics — {text}")

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
