"""
EchoLyrics App
==============
Bootstrap & DI Container utama.
Menginisialisasi semua komponen dan menghubungkannya.
"""

from __future__ import annotations

import sys
import os
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut

from backend.logger.app_logger import setup_logger, app_logger
from backend.database.db_manager import DatabaseManager
from backend.database.migrations import run_migrations
from backend.database.repositories.track_repo import TrackRepository
from backend.database.repositories.lyrics_repo import LyricsRepository
from backend.database.repositories.translation_repo import TranslationRepository
from backend.database.repositories.settings_repo import SettingsRepository
from backend.config.config_manager import ConfigManager
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.spotify.spotify_service import SpotifyService
from backend.lyrics.lyrics_service import LyricsService
from backend.lyrics.timeline_engine import TimelineEngine
from backend.translate.translation_service import TranslationService
from backend.scheduler.scheduler import Scheduler

from frontend.overlay.overlay_window import OverlayWindow
from frontend.overlay.overlay_controller import OverlayController
from frontend.tray.system_tray import SystemTray
from frontend.windows.settings_window import SettingsWindow
from frontend.windows.full_lyrics_window import FullLyricsWindow
from backend.spotify.windows_media_provider import WindowsMediaProvider


class EchoLyricsApp:
    """
    Root application class.
    Semua lifecycle dan DI dikelola di sini.
    """

    def __init__(self, qt_app: QApplication) -> None:
        self._qt_app = qt_app
        self._spotify: Optional[SpotifyService] = None
        self._scheduler: Optional[Scheduler] = None
        self._settings_win: Optional[SettingsWindow] = None
        self._lyrics_win: Optional[FullLyricsWindow] = None

    def start(self) -> None:
        """Urutan inisialisasi sesuai panduan SDD."""
        # 1. Logger
        setup_logger(debug=False)
        app_logger.info("=" * 50)
        app_logger.info("EchoLyrics starting...")

        # 2. Database
        self._db = DatabaseManager.instance()
        run_migrations(self._db)

        # 3. Repositories
        self._track_repo        = TrackRepository(self._db)
        self._lyrics_repo       = LyricsRepository(self._db)
        self._translation_repo  = TranslationRepository(self._db)
        self._settings_repo     = SettingsRepository(self._db)

        # 4. Config
        self._config = ConfigManager.instance(self._settings_repo)

        # 5. Event Bus
        self._bus = EventBus.instance()

        # 6. Spotify Service
        client_id     = self._config.get("spotify_client_id", "")
        client_secret = self._config.get("spotify_client_secret", "")

        # 6b. Windows Media Provider (shared, persistent PowerShell process — SATU proses untuk semua)
        self._win_media = WindowsMediaProvider()

        self._spotify = SpotifyService(
            client_id, client_secret, self._bus,
            windows_media_provider=self._win_media,
        )

        # 7. Timeline + Lyrics Engine
        self._timeline = TimelineEngine()
        self._lyrics_service = LyricsService(
            self._bus,
            self._track_repo,
            self._lyrics_repo,
            self._timeline,
            windows_media_provider=self._win_media,   # inject untuk fresh position
        )
        # Apply initial settings ke SmartSyncEngine
        auto_sync = bool(self._config.get("auto_sync_enabled", 1))
        manual_offset = float(self._config.get("manual_sync_offset_ms", 0))
        self._lyrics_service.set_autosync_enabled(auto_sync)
        if abs(manual_offset) > 5:
            self._lyrics_service.set_manual_sync_offset(manual_offset)


        # 8. Translation
        self._translation_service = TranslationService(
            self._bus,
            self._lyrics_repo,
            self._translation_repo,
        )

        # 9. Frontend — Overlay
        self._overlay = OverlayWindow()
        self._overlay_ctrl = OverlayController(self._bus, self._overlay)
        self._overlay_ctrl.apply_settings(self._config.get_all())
        self._overlay.show_overlay()

        # 10. System Tray
        self._tray = SystemTray()
        self._tray.show()
        self._connect_tray()

        # 11. Global shortcuts
        self._setup_shortcuts()

        # 12. Scheduler
        self._scheduler = Scheduler(
            spotify_poll_fn=self._poll_spotify,
            lyrics_tick_fn=self._lyrics_service.tick,
        )
        self._scheduler.start()

        # 13. Cek apakah perlu login Spotify
        if not client_id or not client_secret:
            app_logger.warning("[App] Spotify credentials not set. Opening settings...")
            QTimer.singleShot(500, self._show_settings)
        else:
            # Authenticate di background
            QTimer.singleShot(100, self._auth_spotify)

        app_logger.info("EchoLyrics started successfully.")

    # ──────────────────────────────────────────────────────────
    # Spotify
    # ──────────────────────────────────────────────────────────

    def _auth_spotify(self, force: bool = False) -> None:
        import threading
        def _do_auth():
            ok = self._spotify.ensure_authenticated(force=force)
            if not ok:
                app_logger.error("[App] Spotify authentication failed.")
        threading.Thread(target=_do_auth, daemon=True).start()

    def _poll_spotify(self) -> None:
        if self._spotify:
            self._spotify.poll()

    # ──────────────────────────────────────────────────────────
    # Tray
    # ──────────────────────────────────────────────────────────

    def _connect_tray(self) -> None:
        t = self._tray.signals
        t.toggle_drag.connect(self._toggle_drag_mode)
        t.show_overlay.connect(self._overlay.show_overlay)
        t.hide_overlay.connect(self._overlay.hide_overlay)
        t.show_settings.connect(self._show_settings)
        t.show_lyrics.connect(self._show_lyrics)
        t.refresh.connect(self._refresh_session)
        t.clear_cache.connect(self._clear_cache)
        t.restart.connect(self._restart)
        t.quit_app.connect(self._quit)

    def _toggle_drag_mode(self) -> None:
        is_edit = self._overlay.toggle_edit_mode()
        if is_edit:
            self._tray.notify(
                "Mode Geser Aktif 🖐",
                "Tahan & geser mouse ke posisi mana saja di layar. Klik kanan di subtitle untuk mengunci kembali."
            )
        else:
            self._tray.notify(
                "Posisi Terkunci 🔒",
                "Subtitle dikunci dan kembali tembus pandang (click-through)."
            )

    def _refresh_session(self) -> None:
        if self._spotify:
            self._auth_spotify(force=True)
            self._spotify.poll()
        self._tray.notify("Refreshed ↻", "Sesi media & Spotify telah diperbarui.")

    # ──────────────────────────────────────────────────────────
    # Windows
    # ──────────────────────────────────────────────────────────

    def _show_settings(self) -> None:
        if self._settings_win and self._settings_win.isVisible():
            self._settings_win.raise_()
            return
        self._settings_win = SettingsWindow(self._config)
        self._settings_win.settings_applied.connect(self._on_settings_applied)
        self._settings_win.show()

    def _show_lyrics(self) -> None:
        if self._lyrics_win and self._lyrics_win.isVisible():
            self._lyrics_win.raise_()
            return
        self._lyrics_win = FullLyricsWindow(self._bus, timeline_engine=self._timeline)
        self._lyrics_win.show()

    def _on_settings_applied(self, data: dict) -> None:
        action = data.get("action")
        if action == "clear_cache":
            self._clear_cache()
            return
        if action == "clear_current_cache":
            if self._lyrics_service:
                ok = self._lyrics_service.clear_current_track_cache()
                if ok:
                    self._tray.notify("Cache Lagu Dihapus 🗑", "Cache lirik & terjemahan lagu ini telah dihapus. Lirik baru sedang dimuat...")
                else:
                    self._tray.notify("Informasi ℹ", "Tidak ada lagu yang sedang diputar.")
            return

        if action == "reset_sync":
            if self._lyrics_service:
                self._lyrics_service.reset_current_sync_offset()
            self._tray.notify("Reset Kalibrasi ↺", "Offset kalibrasi lagu ini telah di-reset.")
            return
        if action == "force_resync":
            if self._lyrics_service:
                self._lyrics_service.force_resync()
            self._tray.notify("Re-Sync ↻", "Lirik di-sinkronkan ulang ke posisi audio sekarang.")
            return
        if action == "manual_offset":
            offset_ms = float(data.get("offset_ms", 0))
            if self._lyrics_service:
                self._lyrics_service.set_manual_sync_offset(offset_ms)
            return
        if action == "autosync_toggle":
            enabled = bool(data.get("enabled", True))
            if self._lyrics_service:
                self._lyrics_service.set_autosync_enabled(enabled)
            return
        if action == "spotify_login":
            # Update credentials dan re-auth (menggunakan shared win_media provider agar tidak ganda)
            self._spotify = SpotifyService(
                self._config.get("spotify_client_id", ""),
                self._config.get("spotify_client_secret", ""),
                self._bus,
                windows_media_provider=self._win_media,
            )
            self._auth_spotify(force=True)
            return
        # Apply settings ke overlay
        self._overlay_ctrl.apply_settings(self._config.get_all())
        self._bus.publish(EventType.SETTINGS_CHANGED, data)

    # ──────────────────────────────────────────────────────────
    # Shortcuts (Ctrl+Shift+...)
    # ──────────────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        self._shortcut_drag = QShortcut(QKeySequence("Ctrl+Shift+D"), self._overlay)
        self._shortcut_drag.activated.connect(self._toggle_drag_mode)

    # ──────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────

    def _clear_cache(self) -> None:
        try:
            self._db.execute_write("DELETE FROM translations")
            self._db.execute_write("DELETE FROM lyrics")
            self._db.execute_write("DELETE FROM tracks")
            self._db.execute_write("DELETE FROM cache")
            self._tray.notify("Cache Cleared", "Semua cache telah dihapus.")
            app_logger.info("[App] Cache cleared.")
        except Exception as e:
            app_logger.error(f"[App] Clear cache error: {e}")

    def _restart(self) -> None:
        self._quit()
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)

    def _quit(self) -> None:
        app_logger.info("[App] Quitting...")
        if self._scheduler:
            self._scheduler.stop()
        if self._translation_service:
            self._translation_service.shutdown()
        if hasattr(self, '_win_media') and self._win_media:
            self._win_media.stop()
        if self._db:
            self._db.close()
        self._qt_app.quit()
