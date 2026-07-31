"""
Track Repository
================
CRUD operasi untuk tabel tracks.
"""

import time
from typing import Optional

from backend.database.db_manager import DatabaseManager
from backend.models.models import TrackInfo
from backend.utils.hash_helper import make_cache_key
from backend.logger.app_logger import app_logger


class TrackRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def find_by_spotify_id(self, spotify_id: str) -> Optional[int]:
        """Cari track_id berdasarkan Spotify ID. Return None jika tidak ada."""
        row = self._db.fetchone(
            "SELECT track_id FROM tracks WHERE spotify_track_id = ?",
            (spotify_id,)
        )
        return row["track_id"] if row else None

    def upsert(self, track: TrackInfo) -> int:
        """Insert atau update track. Return track_id."""
        now = time.time()
        cache_key = make_cache_key(track.artist, track.title, track.duration_ms)

        existing = self.find_by_spotify_id(track.spotify_id)
        if existing:
            self._db.execute_write(
                """
                UPDATE tracks SET title=?, artist=?, album=?, duration_ms=?,
                isrc=?, language=?, cover_url=?, cache_key=?, updated_at=?
                WHERE spotify_track_id=?
                """,
                (track.title, track.artist, track.album, track.duration_ms,
                 track.isrc, track.language, track.image_url, cache_key, now,
                 track.spotify_id)
            )
            return existing

        row_id = self._db.execute_write(
            """
            INSERT INTO tracks
            (spotify_track_id, title, artist, album, duration_ms, isrc, language,
             cover_url, cache_key, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (track.spotify_id, track.title, track.artist, track.album,
             track.duration_ms, track.isrc, track.language, track.image_url,
             cache_key, now, now)
        )
        app_logger.debug(f"[TrackRepo] Inserted track_id={row_id}: {track.artist} - {track.title}")
        return row_id or 0
