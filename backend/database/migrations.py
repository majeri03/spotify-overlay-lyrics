"""
Database Migrations
===================
Sistem migrasi versi database EchoLyrics.
Setiap versi memiliki SQL yang dieksekusi satu kali saja.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.database.db_manager import DatabaseManager
from backend.logger.app_logger import app_logger


# (versi, deskripsi, list_sql)
MIGRATIONS: List[Tuple[str, str, List[str]]] = [
    (
        "1.0.0",
        "Initial Schema",
        [
            # ── migration_history ────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS migration_history (
                version      TEXT PRIMARY KEY,
                description  TEXT NOT NULL,
                executed_at  REAL NOT NULL
            );
            """,

            # ── tracks ───────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS tracks (
                track_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                spotify_track_id TEXT UNIQUE NOT NULL,
                title            TEXT NOT NULL,
                artist           TEXT NOT NULL,
                album            TEXT NOT NULL DEFAULT '',
                duration_ms      INTEGER NOT NULL DEFAULT 0,
                isrc             TEXT NOT NULL DEFAULT '',
                language         TEXT NOT NULL DEFAULT '',
                cover_url        TEXT NOT NULL DEFAULT '',
                provider         TEXT NOT NULL DEFAULT 'lrclib',
                cache_key        TEXT NOT NULL DEFAULT '',
                created_at       REAL NOT NULL,
                updated_at       REAL NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_tracks_spotify_id ON tracks(spotify_track_id);",
            "CREATE INDEX IF NOT EXISTS idx_tracks_cache_key ON tracks(cache_key);",

            # ── lyrics ───────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS lyrics (
                lyrics_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id         INTEGER NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
                line_number      INTEGER NOT NULL,
                timestamp_ms     INTEGER NOT NULL,
                text_original    TEXT NOT NULL,
                created_at       REAL NOT NULL,
                UNIQUE(track_id, line_number)
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_lyrics_track_id ON lyrics(track_id);",
            "CREATE INDEX IF NOT EXISTS idx_lyrics_timestamp ON lyrics(timestamp_ms);",

            # ── translations ─────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS translations (
                translation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                lyrics_id        INTEGER NOT NULL REFERENCES lyrics(lyrics_id) ON DELETE CASCADE,
                language         TEXT NOT NULL DEFAULT 'id',
                text_translation TEXT NOT NULL,
                provider         TEXT NOT NULL DEFAULT '',
                confidence       REAL NOT NULL DEFAULT 1.0,
                created_at       REAL NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_trans_lyrics_id ON translations(lyrics_id);",

            # ── settings ─────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS settings (
                setting_key   TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                value_type    TEXT NOT NULL DEFAULT 'string',
                updated_at    REAL NOT NULL
            );
            """,

            # ── cache ─────────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS cache (
                cache_key    TEXT PRIMARY KEY,
                track_id     INTEGER REFERENCES tracks(track_id) ON DELETE CASCADE,
                status       TEXT NOT NULL DEFAULT 'READY',
                last_access  REAL NOT NULL,
                hit_count    INTEGER NOT NULL DEFAULT 0,
                hash         TEXT NOT NULL DEFAULT ''
            );
            """,

            # ── providers ─────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS providers (
                provider_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT UNIQUE NOT NULL,
                priority      INTEGER NOT NULL DEFAULT 1,
                enabled       INTEGER NOT NULL DEFAULT 1
            );
            """,
            """
            INSERT OR IGNORE INTO providers (provider_name, priority, enabled)
            VALUES ('lrclib', 1, 1);
            """,
        ]
    ),
    (
        "1.1.0",
        "Add sync_offset_ms to tracks for auto-sync calibration",
        [
            """
            ALTER TABLE tracks ADD COLUMN sync_offset_ms REAL NOT NULL DEFAULT 0.0;
            """,
        ]
    ),
]


def run_migrations(db: DatabaseManager) -> None:
    """Jalankan semua migrasi yang belum dieksekusi."""
    import time

    # Pastikan tabel migration_history ada terlebih dahulu
    db.execute_write("""
        CREATE TABLE IF NOT EXISTS migration_history (
            version      TEXT PRIMARY KEY,
            description  TEXT NOT NULL,
            executed_at  REAL NOT NULL
        );
    """)

    for version, description, sql_list in MIGRATIONS:
        row = db.fetchone(
            "SELECT version FROM migration_history WHERE version = ?",
            (version,)
        )
        if row:
            app_logger.debug(f"[Migration] Skip {version} (already applied)")
            continue

        app_logger.info(f"[Migration] Applying {version}: {description}")
        for sql in sql_list:
            db.execute_write(sql.strip())

        db.execute_write(
            "INSERT INTO migration_history (version, description, executed_at) VALUES (?, ?, ?)",
            (version, description, time.time())
        )
        app_logger.info(f"[Migration] Applied {version} ✓")
