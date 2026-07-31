"""
Spotify Service
===============
Facade untuk seluruh Spotify Engine.
Menggabungkan Auth + TokenManager + Client + PlaybackController.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from backend.spotify.auth import SpotifyAuth
from backend.spotify.token_manager import TokenManager
from backend.spotify.client import SpotifyClient, TokenExpiredException
from backend.spotify.playback import PlaybackController
from backend.models.models import PlaybackInfo
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.logger.app_logger import app_logger


class SpotifyService:
    """
    Entry point untuk semua interaksi Spotify.
    Aplikasi lain hanya memanggil SpotifyService.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        event_bus: EventBus,
        windows_media_provider=None,   # shared instance, tidak buat proses baru
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._bus = event_bus
        self._token_mgr = TokenManager()
        self._auth = SpotifyAuth(client_id, client_secret)
        self._client = SpotifyClient(self._get_access_token)
        self._playback_ctrl = PlaybackController(self._client, windows_media_provider)
        self._current_playback: Optional[PlaybackInfo] = None
        self._is_connected = False
        self._client_403_count = 0

    # ──────────────────────────────────────────────────────────
    # Auth
    # ──────────────────────────────────────────────────────────

    def ensure_authenticated(self, force: bool = False) -> bool:
        """
        Pastikan token valid. Login browser jika diperlukan.
        Return True jika berhasil.
        """
        if force:
            self._token_mgr.clear()

        if not force and self._token_mgr.is_valid():
            app_logger.info("[SpotifyService] Token valid, skip login.")
            return True

        if not force and self._token_mgr.get_refresh_token():
            app_logger.info("[SpotifyService] Token expired, refreshing...")
            if self._refresh_token():
                return True

        if force:
            app_logger.info("[SpotifyService] Force re-auth requested — opening browser...")
            result = self._auth.login_with_browser()
            if result:
                access, refresh, expires = result
                self._token_mgr.save(access, refresh, expires)
                return True

        return False

    def _refresh_token(self) -> bool:
        rt = self._token_mgr.get_refresh_token()
        if not rt:
            return False
        result = self._auth.refresh_access_token(rt)
        if result:
            access, expires = result
            self._token_mgr.save(access, rt, expires)
            return True
        return False

    def _get_access_token(self) -> str:
        """Getter untuk SpotifyClient — otomatis refresh jika perlu."""
        if self._token_mgr.is_expired():
            if not self._refresh_token():
                app_logger.error("[SpotifyService] Cannot refresh token.")
        return self._token_mgr.get_access_token() or ""

    # ──────────────────────────────────────────────────────────
    # Polling
    # ──────────────────────────────────────────────────────────

    def poll(self) -> Optional[PlaybackInfo]:
        """
        Ambil playback terkini dan emit events ke EventBus.
        Dipanggil oleh Scheduler setiap 1000ms.
        """
        try:
            current = self._playback_ctrl.fetch()

            events = self._playback_ctrl.detect_changes(current)

            for evt_name in events:
                try:
                    evt = EventType(evt_name)
                    self._bus.publish(evt, data=current)
                    app_logger.debug(f"[SpotifyService] Emit: {evt_name}")
                except ValueError:
                    pass

            if current:
                self._current_playback = current
                if not self._is_connected:
                    self._is_connected = True
                    self._bus.publish(EventType.SPOTIFY_CONNECTED, current)
                # Kirim update posisi setiap poll untuk sinkronisasi timeline
                self._bus.publish(EventType.PLAYBACK_UPDATED, current)
            else:
                if self._is_connected:
                    self._is_connected = False
                    self._bus.publish(EventType.SPOTIFY_DISCONNECTED, None)

            return current

        except TokenExpiredException:
            return None
        except Exception as e:
            return None

    @property
    def current_playback(self) -> Optional[PlaybackInfo]:
        return self._current_playback

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def logout(self) -> None:
        self._token_mgr.clear()
        app_logger.info("[SpotifyService] Logged out.")
