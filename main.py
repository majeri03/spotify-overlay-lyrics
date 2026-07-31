"""
EchoLyrics (JLyrics)
====================
Entry point aplikasi.

Alur:
1. Inisialisasi logging
2. Inisialisasi database
3. Inisialisasi event bus
4. Inisialisasi backend services
5. Inisialisasi frontend (PySide6)
6. Jalankan app loop
"""

import sys
import os

# Pastikan path root ada di sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Enable High DPI support
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

from app.app import EchoLyricsApp


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("EchoLyrics")
    qt_app.setApplicationDisplayName("EchoLyrics")
    qt_app.setApplicationVersion("1.0.0")
    qt_app.setOrganizationName("EchoLyrics")
    # Agar app tidak keluar saat window di-close (tray mode)
    qt_app.setQuitOnLastWindowClosed(False)

    echo = EchoLyricsApp(qt_app)
    echo.start()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
