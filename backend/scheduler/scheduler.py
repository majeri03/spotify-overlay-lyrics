"""
Scheduler
=========
Menjalankan dua tugas periodik:
1. Spotify polling setiap 1000ms
2. Subtitle sync (lyrics tick) setiap 250ms
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from backend.logger.app_logger import app_logger

_SPOTIFY_INTERVAL = 0.25   # seconds (250ms) — lebih responsif
_LYRICS_INTERVAL  = 0.05   # seconds (50ms) — subtitle sangat smooth


class Scheduler:
    def __init__(
        self,
        spotify_poll_fn: Callable,
        lyrics_tick_fn: Callable,
    ) -> None:
        self._spotify_poll = spotify_poll_fn
        self._lyrics_tick = lyrics_tick_fn
        self._running = False
        self._spotify_thread: Optional[threading.Thread] = None
        self._lyrics_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._spotify_thread = threading.Thread(
            target=self._spotify_loop,
            daemon=True,
            name="SpotifyPoller"
        )
        self._lyrics_thread = threading.Thread(
            target=self._lyrics_loop,
            daemon=True,
            name="LyricsTick"
        )
        self._spotify_thread.start()
        self._lyrics_thread.start()
        app_logger.info("[Scheduler] Started.")

    def stop(self) -> None:
        self._running = False
        app_logger.info("[Scheduler] Stopped.")

    def _spotify_loop(self) -> None:
        while self._running:
            try:
                self._spotify_poll()
            except Exception as e:
                app_logger.error(f"[Scheduler] Spotify poll error: {e}")
            time.sleep(_SPOTIFY_INTERVAL)

    def _lyrics_loop(self) -> None:
        while self._running:
            try:
                self._lyrics_tick()
            except Exception as e:
                app_logger.error(f"[Scheduler] Lyrics tick error: {e}")
            time.sleep(_LYRICS_INTERVAL)
