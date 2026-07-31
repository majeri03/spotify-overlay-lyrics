"""
Translation Repository
======================
CRUD untuk tabel translations.
"""

import time
from typing import Dict, List, Optional

from backend.database.db_manager import DatabaseManager
from backend.models.models import TranslationResult
from backend.logger.app_logger import app_logger


class TranslationRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def has_translations(self, track_id: int, language: str = "id") -> bool:
        """Cek apakah translation sudah ada untuk track ini."""
        row = self._db.fetchone(
            """
            SELECT COUNT(*) as cnt FROM translations t
            JOIN lyrics l ON l.lyrics_id = t.lyrics_id
            WHERE l.track_id = ? AND t.language = ?
            """,
            (track_id, language)
        )
        return (row["cnt"] > 0) if row else False

    def save_translations(
        self,
        lyrics_ids: List[int],
        translations: List[TranslationResult],
        language: str = "id"
    ) -> bool:
        """Simpan batch translations. lyrics_ids dan translations harus sama panjang."""
        if len(lyrics_ids) != len(translations):
            app_logger.error("[TransRepo] Mismatch: lyrics_ids vs translations length")
            return False

        now = time.time()
        # Hapus yang lama dulu
        for lid in lyrics_ids:
            self._db.execute_write(
                "DELETE FROM translations WHERE lyrics_id = ? AND language = ?",
                (lid, language)
            )

        params = [
            (lid, language, tr.translated, tr.provider, tr.confidence, now)
            for lid, tr in zip(lyrics_ids, translations)
        ]
        return self._db.execute_many(
            """
            INSERT INTO translations (lyrics_id, language, text_translation, provider, confidence, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            params
        )

    def load_by_lyrics_id(self, lyrics_id: int, language: str = "id") -> Optional[str]:
        """Load translation text untuk satu baris."""
        row = self._db.fetchone(
            "SELECT text_translation FROM translations WHERE lyrics_id = ? AND language = ?",
            (lyrics_id, language)
        )
        return row["text_translation"] if row else None
