"""
Lyrics Service
==============
Orchestrator utama untuk loading dan sinkronisasi lirik.
Mendengarkan event dari SpotifyService, fetch lirik dari provider,
build timeline, dan emit event ke OverlayController.

Perbaikan utama:
- Posisi timeline diambil FRESH dari WindowsMediaProvider setelah fetch selesai
- Bukan dari playback.progress_ms saat TRACK_CHANGED yang sudah stale
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from backend.lyrics.lrclib_provider import LRCLibProvider
from backend.lyrics.parser import parse_lrc
from backend.lyrics.validator import validate_lyrics, ValidationResult
from backend.lyrics.timeline_engine import TimelineEngine
from backend.database.repositories.track_repo import TrackRepository
from backend.database.repositories.lyrics_repo import LyricsRepository
from backend.models.models import PlaybackInfo, SubtitleLine, TrackInfo, TrackTimeline
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.logger.app_logger import app_logger


class LyricsService:
    def __init__(
        self,
        event_bus: EventBus,
        track_repo: TrackRepository,
        lyrics_repo: LyricsRepository,
        timeline_engine: TimelineEngine,
        windows_media_provider=None,   # Optional: untuk fresh position
    ) -> None:
        self._bus = event_bus
        self._track_repo = track_repo
        self._lyrics_repo = lyrics_repo
        self._timeline = timeline_engine
        self._provider = LRCLibProvider()
        self._win_media = windows_media_provider  # reference untuk ambil posisi fresh
        self._current_track: Optional[TrackInfo] = None
        self._lock = threading.Lock()

        # Subscribe events
        self._bus.subscribe(EventType.TRACK_CHANGED, self._on_track_changed)
        self._bus.subscribe(EventType.TRACK_PAUSED, self._on_paused)
        self._bus.subscribe(EventType.TRACK_RESUMED, self._on_resumed)
        self._bus.subscribe(EventType.TRACK_SEEKED, self._on_seeked)
        self._bus.subscribe(EventType.PLAYBACK_UPDATED, self._on_playback_sync)
        self._bus.subscribe(EventType.SPOTIFY_DISCONNECTED, self._on_disconnected)

    # ──────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────

    def _on_playback_sync(self, playback: Optional[PlaybackInfo]) -> None:
        if not playback or not playback.track:
            return

        # Sinkronisasi status play/pause
        if playback.state.name == "PLAYING":
            if not self._timeline.is_running:
                self._timeline.seek(playback.progress_ms)
                self._timeline.resume()
            else:
                # Cek drift — hanya seek jika drift > 800ms (toleransi wajar)
                drift_ms = abs(self._timeline.position_ms - playback.progress_ms)
                if drift_ms > 800:
                    self._timeline.seek(playback.progress_ms)
        elif playback.state.name == "PAUSED":
            if self._timeline.is_running:
                self._timeline.pause()

    def _on_track_changed(self, playback: Optional[PlaybackInfo]) -> None:
        if not playback or not playback.track:
            return
        # Reset timeline langsung agar tidak ada lirik lama terlihat
        self._timeline.reset()
        thread = threading.Thread(
            target=self._load_lyrics,
            args=(playback,),
            daemon=True
        )
        thread.start()

    def _on_paused(self, _) -> None:
        self._timeline.pause()

    def _on_resumed(self, playback: Optional[PlaybackInfo]) -> None:
        if playback:
            self._timeline.seek(playback.progress_ms)
        self._timeline.resume()

    def _on_seeked(self, playback: Optional[PlaybackInfo]) -> None:
        if playback:
            self._timeline.seek(playback.progress_ms)

    def _on_disconnected(self, _) -> None:
        self._timeline.reset()
        self._current_track = None

    # ──────────────────────────────────────────────────────────
    # Load Lyrics
    # ──────────────────────────────────────────────────────────

    def _load_lyrics(self, playback: PlaybackInfo) -> None:
        track = playback.track
        if not track:
            return

        # Catat waktu mulai fetch untuk hitung kompensasi
        fetch_start = time.perf_counter()

        with self._lock:
            self._current_track = track

        app_logger.info(f"[LyricsService] Loading: {track.artist} - {track.title}")

        # 1. Upsert track ke database
        track_id = self._track_repo.upsert(track)

        # 2. Cek cache SQLite
        if self._lyrics_repo.has_lyrics(track_id):
            app_logger.info("[LyricsService] Cache hit — loading from DB.")
            self._bus.publish(EventType.CACHE_HIT, track)
            rows = self._lyrics_repo.load_lines(track_id)
            lines = self._rows_to_lines(rows)
        else:
            # 3. Fetch dari LRCLIB
            self._bus.publish(EventType.CACHE_MISS, track)
            lrc_text = self._provider.fetch(
                artist=track.artist,
                title=track.title,
                duration_ms=track.duration_ms,
                album=track.album,
            )

            if not lrc_text:
                app_logger.warning(f"[LyricsService] Not found: {track.artist} - {track.title}")
                self._bus.publish(EventType.LYRICS_NOT_FOUND, track)
                return

            lines = parse_lrc(lrc_text)
            result = validate_lyrics(lines, track.duration_ms)

            if result == ValidationResult.INVALID:
                app_logger.error("[LyricsService] Lyrics INVALID, discarding.")
                self._bus.publish(EventType.LYRICS_NOT_FOUND, track)
                return

            # 4. Simpan ke cache
            self._lyrics_repo.save_lines(track_id, lines)

        # 5. Build timeline
        timeline = self._timeline.build(track, lines)

        # 6. Ambil posisi FRESH (bukan posisi saat TRACK_CHANGED yang sudah stale)
        #    Fetch lirik butuh ~1-2 detik, lagu sudah maju. Pakai data terkini.
        fresh_pos = self._get_fresh_position(playback, fetch_start)
        self._timeline.start(fresh_pos)
        app_logger.info(f"[LyricsService] Timeline start at {fresh_pos:.0f}ms")

        # 7. Emit LYRICS_FOUND
        self._bus.publish(EventType.LYRICS_FOUND, {
            "track": track,
            "timeline": timeline,
            "track_id": track_id,
        })
        self._bus.publish(EventType.TIMELINE_READY, timeline)

        app_logger.info(f"[LyricsService] Timeline ready: {len(timeline)} lines")

    def _get_fresh_position(self, fallback_playback: PlaybackInfo, fetch_start: float) -> float:
        """
        Ambil posisi playback TERKINI.
        Prioritas: WindowsMediaProvider (real-time) → kompensasi waktu → fallback
        """
        # Opsi 1: Ambil dari WindowsMedia (instant, sudah cached di memory)
        if self._win_media:
            try:
                pb = self._win_media.fetch_playback()
                if pb and pb.progress_ms > 0 and pb.state.name == "PLAYING":
                    app_logger.debug(f"[LyricsService] Fresh pos from WinMedia: {pb.progress_ms}ms")
                    return float(pb.progress_ms)
            except Exception:
                pass

        # Opsi 2: Kompensasi dari posisi lama + waktu yang berlalu saat fetch
        elapsed_ms = (time.perf_counter() - fetch_start) * 1000.0
        compensated = fallback_playback.progress_ms + elapsed_ms
        app_logger.debug(f"[LyricsService] Fresh pos via compensation: {compensated:.0f}ms "
                         f"(base={fallback_playback.progress_ms}, elapsed={elapsed_ms:.0f}ms)")
        return float(compensated)

    def _rows_to_lines(self, rows: list) -> list[SubtitleLine]:
        lines = []
        for r in rows:
            line = SubtitleLine(
                index=r["line_number"],
                timestamp_ms=r["timestamp_ms"],
                end_timestamp_ms=0,
                original_text=r["text_original"],
                translated_text=r.get("text_translation", ""),
            )
            lines.append(line)
        return lines

    # ──────────────────────────────────────────────────────────
    # Tick (dipanggil oleh Scheduler)
    # ──────────────────────────────────────────────────────────

    def tick(self) -> None:
        """Dipanggil setiap 50ms oleh scheduler untuk update subtitle queue."""
        if not self._timeline.is_running:
            return
        queue = self._timeline.get_current_queue()
        # Selalu emit agar overlay bisa clear saat tidak ada lirik aktif
        if queue is not None:
            self._bus.publish(EventType.QUEUE_UPDATED, queue)
