"""
Logger Module
=============
Centralized logging menggunakan loguru.
Format: logs/YYYY-MM-DD.log
"""

import os
import sys
from datetime import datetime
from loguru import logger

# Root project dir
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOGS_DIR = os.path.join(_ROOT, "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)


def setup_logger(debug: bool = False) -> None:
    """Inisialisasi logger. Panggil satu kali saat startup."""
    logger.remove()  # Hapus handler default

    level = "DEBUG" if debug else "INFO"

    # Console handler
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level=level,
            format="{time:HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
            colorize=False,
        )

    # File handler – rotasi harian
    log_file = os.path.join(_LOGS_DIR, "{time:YYYY-MM-DD}.log")
    logger.add(
        log_file,
        level="DEBUG",
        rotation="00:00",       # Rotasi tengah malam
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        encoding="utf-8",
    )

    logger.info("EchoLyrics logger initialized.")


def get_logger(name: str = "echolyrics"):
    """Mengembalikan logger yang dapat digunakan oleh modul lain."""
    return logger.bind(name=name)


# Singleton logger instance
app_logger = logger
