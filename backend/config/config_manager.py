"""
Config Manager
==============
Mengelola konfigurasi runtime dan persistent.
Priority: RAM → SQLite → Default
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from backend.database.repositories.settings_repo import SettingsRepository
from backend.logger.app_logger import app_logger


class ConfigManager:
    """
    Thread-safe konfigurasi manager.
    Membaca dari RAM cache terlebih dahulu, fallback ke SQLite.
    """

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._repo = settings_repo
        self._ram: dict = {}
        self._ram_lock = threading.Lock()
        self._load_all()

    @classmethod
    def instance(cls, settings_repo: Optional[SettingsRepository] = None) -> "ConfigManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if settings_repo is None:
                        raise RuntimeError("ConfigManager belum diinisialisasi.")
                    cls._instance = cls(settings_repo)
        return cls._instance

    def _load_all(self) -> None:
        """Load semua settings dari SQLite ke RAM."""
        with self._ram_lock:
            self._ram = self._repo.get_all()
        app_logger.debug(f"[Config] Loaded {len(self._ram)} settings from DB.")

    def get(self, key: str, default: Any = None) -> Any:
        with self._ram_lock:
            value = self._ram.get(key)
        if value is None:
            value = self._repo.get(key, default)
        return value

    def set(self, key: str, value: Any) -> None:
        with self._ram_lock:
            self._ram[key] = value
        self._repo.set(key, value)
        app_logger.debug(f"[Config] Set {key} = {value}")

    def reload(self) -> None:
        """Reload dari SQLite (misal setelah settings window ditutup)."""
        self._load_all()

    def get_all(self) -> dict:
        with self._ram_lock:
            return dict(self._ram)
