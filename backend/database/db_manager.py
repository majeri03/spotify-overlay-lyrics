"""
Database Manager
================
Singleton SQLite connection manager dengan WAL mode.
Seluruh akses database melalui kelas ini.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, List, Optional, Tuple

from backend.logger.app_logger import app_logger

# Database location: %LOCALAPPDATA%\\EchoLyrics\\cache\\echolyrics.db
_APP_NAME = "EchoLyrics"
_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
_DB_DIR = os.path.join(_LOCAL_APPDATA, _APP_NAME, "cache")
_DB_PATH = os.path.join(_DB_DIR, "echolyrics.db")


class DatabaseManager:
    """
    Singleton database manager.
    Menggunakan WAL journal mode dan thread-safe mutex untuk write.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._write_lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_dir()
        self._connect()
        self._setup_pragmas()

    @classmethod
    def instance(cls, db_path: str = _DB_PATH) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    # ──────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            isolation_level=None,   # autocommit off — kita manage sendiri
        )
        self._conn.row_factory = sqlite3.Row
        app_logger.info(f"[DB] Connected: {self._db_path}")

    def _setup_pragmas(self) -> None:
        """Aktifkan WAL mode dan foreign keys."""
        self.execute_write("PRAGMA journal_mode=WAL;")
        self.execute_write("PRAGMA foreign_keys=ON;")
        self.execute_write("PRAGMA synchronous=NORMAL;")
        self.execute_write("PRAGMA cache_size=10000;")
        app_logger.debug("[DB] WAL mode and pragmas set.")

    # ──────────────────────────────────────────────────────────
    # Query Methods
    # ──────────────────────────────────────────────────────────

    def execute_read(
        self,
        sql: str,
        params: Tuple = ()
    ) -> List[sqlite3.Row]:
        """Read query — thread-safe dengan mutex."""
        with self._write_lock:
            try:
                cursor = self._conn.execute(sql, params)
                return cursor.fetchall()
            except sqlite3.Error as e:
                app_logger.error(f"[DB] Read error: {e} | SQL: {sql[:80]}")
                return []

    def execute_write(
        self,
        sql: str,
        params: Tuple = ()
    ) -> Optional[int]:
        """Write query — thread-safe dengan mutex."""
        with self._write_lock:
            try:
                cursor = self._conn.execute(sql, params)
                self._conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                app_logger.error(f"[DB] Write error: {e} | SQL: {sql[:80]}")
                try:
                    self._conn.rollback()
                except Exception:
                    pass
                return None

    def execute_many(
        self,
        sql: str,
        params_list: List[Tuple]
    ) -> bool:
        """Batch write query dalam satu transaction."""
        with self._write_lock:
            try:
                self._conn.execute("BEGIN")
                self._conn.executemany(sql, params_list)
                self._conn.execute("COMMIT")
                return True
            except sqlite3.Error as e:
                app_logger.error(f"[DB] Batch write error: {e} | SQL: {sql[:80]}")
                try:
                    self._conn.execute("ROLLBACK")
                except Exception:
                    pass
                return False

    def fetchone(
        self,
        sql: str,
        params: Tuple = ()
    ) -> Optional[sqlite3.Row]:
        """Ambil satu baris — thread-safe dengan mutex."""
        with self._write_lock:
            try:
                cursor = self._conn.execute(sql, params)
                return cursor.fetchone()
            except sqlite3.Error as e:
                app_logger.error(f"[DB] Fetchone error: {e}")
                return None

    # ──────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                app_logger.info("[DB] Connection closed.")
            except Exception:
                pass

    @property
    def db_path(self) -> str:
        return self._db_path
