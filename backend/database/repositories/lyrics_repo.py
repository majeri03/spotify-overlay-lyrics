"""
Lyrics Repository
=================
CRUD untuk tabel lyrics.
"""

import time
from typing import List, Optional

from backend.database.db_manager import DatabaseManager
from backend.models.models import SubtitleLine
from backend.logger.app_logger import app_logger


class LyricsRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def has_lyrics(self, track_id: int) -> bool:
        """Cek apakah lyrics sudah tersimpan."""
        row = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM lyrics WHERE track_id = ?",
            (track_id,)
        )
        return (row["cnt"] > 0) if row else False

    def load_lines(self, track_id: int) -> List[dict]:
        """Load semua baris lyrics beserta translation (jika ada)."""
        rows = self._db.execute_read(
            """
            SELECT l.lyrics_id, l.line_number, l.timestamp_ms, l.text_original,
                   COALESCE(t.text_translation, '') as text_translation,
                   COALESCE(t.provider, '') as trans_provider,
                   COALESCE(t.confidence, 0.0) as confidence
            FROM lyrics l
            LEFT JOIN translations t ON t.lyrics_id = l.lyrics_id AND t.language = 'id'
            WHERE l.track_id = ?
            ORDER BY l.line_number ASC
            """,
            (track_id,)
        )
        return [dict(r) for r in rows]

    def save_lines(self, track_id: int, lines: List[SubtitleLine]) -> bool:
        """Simpan semua baris lyrics. Hapus yang lama terlebih dahulu."""
        now = time.time()
        # Hapus lama
        self._db.execute_write("DELETE FROM lyrics WHERE track_id = ?", (track_id,))

        params = [
            (track_id, line.index, line.timestamp_ms, line.original_text, now)
            for line in lines
        ]
        success = self._db.execute_many(
            "INSERT INTO lyrics (track_id, line_number, timestamp_ms, text_original, created_at) VALUES (?,?,?,?,?)",
            params
        )
        app_logger.debug(f"[LyricsRepo] Saved {len(lines)} lines for track_id={track_id}")
        return success

    def get_lyrics_ids(self, track_id: int) -> List[int]:
        """Ambil semua lyrics_id untuk track tertentu, berurutan."""
        rows = self._db.execute_read(
            "SELECT lyrics_id FROM lyrics WHERE track_id = ? ORDER BY line_number ASC",
            (track_id,)
        )
        return [r["lyrics_id"] for r in rows]
