"""
Settings Repository
===================
Key-value store untuk konfigurasi persistent.
"""

import time
from typing import Any, Optional

from backend.database.db_manager import DatabaseManager
from backend.logger.app_logger import app_logger


_DEFAULTS = {
    "theme": ("dark", "string"),
    "language": ("id", "string"),
    "overlay_opacity": ("100", "integer"),
    "glow_enabled": ("1", "boolean"),
    "glow_opacity": ("35", "integer"),
    "glow_radius": ("10", "integer"),
    "font_size_english": ("32", "integer"),
    "font_size_translation": ("24", "integer"),
    "animation_speed_ms": ("200", "integer"),
    "subtitle_position": ("bottom_center", "string"),
    "startup_with_windows": ("0", "boolean"),
    "translation_provider": ("libretranslate", "string"),
    "translation_style": ("natural", "string"),
    "translation_enabled": ("1", "boolean"),
    "click_through": ("1", "boolean"),
    "monitor_index": ("0", "integer"),
    "developer_mode": ("0", "boolean"),
    "subtitle_mode": ("standard", "string"),
    "spotify_client_id": ("", "string"),
    "spotify_client_secret": ("", "string"),
}


class SettingsRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Isi nilai default jika belum ada."""
        now = time.time()
        for key, (value, vtype) in _DEFAULTS.items():
            self._db.execute_write(
                """
                INSERT OR IGNORE INTO settings (setting_key, setting_value, value_type, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value, vtype, now)
            )

    def get(self, key: str, default: Any = None) -> Any:
        row = self._db.fetchone(
            "SELECT setting_value, value_type FROM settings WHERE setting_key = ?",
            (key,)
        )
        if not row:
            return default
        raw = row["setting_value"]
        vtype = row["value_type"]
        if vtype == "integer":
            return int(raw) if raw else 0
        if vtype == "boolean":
            return bool(int(raw)) if raw else False
        if vtype == "float":
            return float(raw) if raw else 0.0
        return raw

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        self._db.execute_write(
            """
            INSERT INTO settings (setting_key, setting_value, value_type, updated_at)
            VALUES (?, ?, 'string', ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, updated_at=excluded.updated_at
            """,
            (key, str(value), now)
        )

    def get_all(self) -> dict:
        rows = self._db.execute_read("SELECT setting_key, setting_value, value_type FROM settings")
        result = {}
        for r in rows:
            key = r["setting_key"]
            raw = r["setting_value"]
            vtype = r["value_type"]
            if vtype == "integer":
                result[key] = int(raw) if raw else 0
            elif vtype == "boolean":
                result[key] = bool(int(raw)) if raw else False
            elif vtype == "float":
                result[key] = float(raw) if raw else 0.0
            else:
                result[key] = raw
        return result
