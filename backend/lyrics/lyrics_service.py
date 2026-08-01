"""
Lyrics Service
==============
Orchestrator utama untuk loading dan sinkronisasi lirik.

v3 — Smart Auto-Sync:
- AutoSyncCalibrator digantikan oleh SmartSyncEngine (sinkronisasi kontinu).
- SmartSyncEngine: lerp correction halus (tidak kasar) + hard-seek untuk drift besar.
- Sinkronisasi berjalan otomatis 100% tanpa input manual apapun.
- Offset per-lagu disimpan ke DB dan langsung diterapkan saat lagu diputar kembali.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from backend.lyrics.lrclib_provider import LRCLibProvider
from backend.lyrics.parser import parse_lrc
from backend.lyrics.validator import validate_lyrics, ValidationResult
from backend.lyrics.timeline_engine import TimelineEngine
from backend.lyrics.smart_sync import SmartSyncEngine
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
        windows_media_provider=None,
    ) -> None:
        self._bus = event_bus
        self._track_repo = track_repo
        self._lyrics_repo = lyrics_repo
        self._timeline = timeline_engine
        self._provider = LRCLibProvider()
        self._win_media = windows_media_provider
        self._current_track: Optional[TrackInfo] = None
        self._current_track_id: Optional[int] = None
        self._lock = threading.Lock()

        # SmartSyncEngine — sinkronisasi otomatis kontinu
        self._sync = SmartSyncEngine(timeline_engine, windows_media_provider)

        # Subscribe events
        self._bus.subscribe(EventType.TRACK_CHANGED,        self._on_track_changed)
        self._bus.subscribe(EventType.TRACK_PAUSED,         self._on_paused)
        self._bus.subscribe(EventType.TRACK_RESUMED,        self._on_resumed)
        self._bus.subscribe(EventType.TRACK_SEEKED,         self._on_seeked)
        self._bus.subscribe(EventType.PLAYBACK_UPDATED,     self._on_playback_sync)
        self._bus.subscribe(EventType.SPOTIFY_DISCONNECTED, self._on_disconnected)

    # ──────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────

    def _on_playback_sync(self, playback: Optional[PlaybackInfo]) -> None:
        """
        Dipanggil setiap ~1000ms dari Spotify poll.
        Kirim posisi ke SmartSyncEngine untuk extrapolasi drift.
        Juga handle pause/resume state.
        """
        if not playback or not playback.track:
            return

        # Rekam posisi Spotify ke SmartSyncEngine
        self._sync.record_spotify_position(float(playback.progress_ms))

        state = playback.state.name
        if state == "PLAYING":
            if not self._timeline.is_running:
                self._timeline.seek(playback.progress_ms)
                self._timeline.resume()
        elif state == "PAUSED":
            if self._timeline.is_running:
                self._timeline.pause()

    def _on_track_changed(self, playback: Optional[PlaybackInfo]) -> None:
        if not playback or not playback.track:
            return
        self._timeline.reset()
        self._sync.reset()
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
        # Reset lerp setelah resume — posisi baru sudah akurat dari Spotify
        self._sync.reset(self._current_track_id)
        if self._current_track_id:
            offset = self._track_repo.get_sync_offset(self._current_track_id)
            if abs(offset) > 30:
                self._sync.load_saved_offset(offset)

    def _on_seeked(self, playback: Optional[PlaybackInfo]) -> None:
        if playback:
            self._timeline.seek(playback.progress_ms)
        # Reset SmartSync setelah seek — sampel lama tidak relevan
        self._sync.reset(self._current_track_id)
        if self._current_track_id:
            offset = self._track_repo.get_sync_offset(self._current_track_id)
            if abs(offset) > 30:
                self._sync.load_saved_offset(offset)

    def _on_disconnected(self, _) -> None:
        self._timeline.reset()
        self._sync.reset()
        self._current_track = None
        self._current_track_id = None

    # ──────────────────────────────────────────────────────────
    # Load Lyrics
    # ──────────────────────────────────────────────────────────

    def _load_lyrics(self, playback: PlaybackInfo) -> None:
        track = playback.track
        if not track:
            return

        fetch_start = time.perf_counter()

        with self._lock:
            self._current_track = track

        app_logger.info(f"[LyricsService] Loading: {track.artist} - {track.title}")

        # 1. Upsert track
        track_id = self._track_repo.upsert(track)
        with self._lock:
            self._current_track_id = track_id

        # 2. Cek cache
        if self._lyrics_repo.has_lyrics(track_id):
            app_logger.info("[LyricsService] Cache hit — loading from DB.")
            self._bus.publish(EventType.CACHE_HIT, track)
            rows = self._lyrics_repo.load_lines(track_id)
            lines = self._rows_to_lines(rows)
        else:
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

            self._lyrics_repo.save_lines(track_id, lines)

        # 3. Build timeline
        timeline = self._timeline.build(track, lines)

        # 4. Dapatkan posisi paling akurat — prioritas: WindowsMedia real-time
        fresh_pos = self._get_fresh_position(playback, fetch_start)
        self._timeline.start(fresh_pos)
        app_logger.info(f"[LyricsService] Timeline start at {fresh_pos:.0f}ms")

        # 5. Reset SmartSync dan terapkan offset yang tersimpan dari DB
        self._sync.reset(track_id)
        saved_offset = self._track_repo.get_sync_offset(track_id)
        if abs(saved_offset) > 30:
            app_logger.info(f"[LyricsService] Applying saved sync offset: {saved_offset:+.0f}ms")
            self._sync.load_saved_offset(saved_offset)
            # Apply langsung ke posisi timer
            new_pos = max(0.0, fresh_pos + saved_offset)
            self._timeline.seek(new_pos)

        # 6. Emit events
        self._bus.publish(EventType.LYRICS_FOUND, {
            "track": track,
            "timeline": timeline,
            "track_id": track_id,
        })
        self._bus.publish(EventType.TIMELINE_READY, timeline)
        app_logger.info(f"[LyricsService] Timeline ready: {len(timeline)} lines")

    def _get_fresh_position(self, fallback_playback: PlaybackInfo, fetch_start: float) -> float:
        """
        Ambil posisi playback TERKINI dengan kompensasi latency.
        Prioritas: WindowsMedia real-time → kompensasi elapsed
        """
        if self._win_media:
            try:
                pb = self._win_media.fetch_playback()
                if pb and pb.progress_ms > 0 and pb.state.name == "PLAYING":
                    return float(pb.progress_ms)
            except Exception:
                pass

        elapsed_ms = (time.perf_counter() - fetch_start) * 1000.0
        return float(fallback_playback.progress_ms + elapsed_ms)

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
    # Tick (50ms dari scheduler)
    # ──────────────────────────────────────────────────────────

    def tick(self) -> None:
        """Dipanggil setiap 50ms oleh scheduler untuk update subtitle queue."""
        if not self._timeline.is_running:
            return

        # SmartSyncEngine tick — lerp correction + periodic drift check
        self._sync.tick()

        # Ambil queue lirik setelah koreksi
        queue = self._timeline.get_current_queue()
        if queue is not None:
            self._bus.publish(EventType.QUEUE_UPDATED, queue)

        # Simpan offset ke DB secara periodik jika sudah stabil
        self._maybe_save_offset()

    def _maybe_save_offset(self) -> None:
        """Simpan offset akumulasi ke DB jika sudah cukup signifikan dan stabil."""
        if not self._current_track_id:
            return
        if not self._sync.is_stable:
            return
        total = self._sync.total_corrected_ms
        if abs(total) < 50:
            return

        def _save():
            try:
                self._track_repo.save_sync_offset(
                    self._current_track_id,
                    total
                )
            except Exception:
                pass
        threading.Thread(target=_save, daemon=True).start()

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def reset_current_sync_offset(self) -> bool:
        """Reset offset kalibrasi untuk lagu yang sedang diputar."""
        if not self._current_track_id:
            return False
        self._sync.reset(self._current_track_id)
        self._track_repo.save_sync_offset(self._current_track_id, 0.0)
        app_logger.info(f"[LyricsService] Reset sync offset for track_id={self._current_track_id}")
        return True

    def set_manual_sync_offset(self, offset_ms: float) -> None:
        """Set offset manual dari Settings slider (real-time, langsung aktif)."""
        self._sync.set_manual_offset(offset_ms)

    def force_resync(self) -> None:
        """
        Paksa re-anchor ke posisi Spotify terkini sekarang juga.
        Bisa dipanggil dari Settings atau tombol UI.
        """
        fresh = self._sync.fetch_fresh_anchor()
        if fresh is not None:
            self._timeline.seek(fresh)
            self._sync.reset(self._current_track_id)
            if self._current_track_id:
                offset = self._track_repo.get_sync_offset(self._current_track_id)
                if abs(offset) > 30:
                    self._sync.load_saved_offset(offset)
            app_logger.info(f"[LyricsService] Force re-sync to {fresh:.0f}ms")

    def set_autosync_enabled(self, enabled: bool) -> None:
        """Enable/disable SmartSyncEngine dari Settings."""
        self._sync.set_enabled(enabled)

    def clear_current_track_cache(self) -> bool:
        """Hapus cache lirik, terjemahan, dan offset khusus lagu yang sedang diputar, lalu re-fetch lirik baru."""
        if not self._current_track_id:
            return False
        track_id = self._current_track_id
        track = self._current_track
        try:
            self._lyrics_repo.delete_by_track_id(track_id)
            self._track_repo.delete_by_track_id(track_id)
        except Exception as e:
            app_logger.error(f"[LyricsService] Failed to delete cache for track_id={track_id}: {e}")

        app_logger.info(f"[LyricsService] Cleared cache for current track_id={track_id}")

        # Trigger re-fetch lirik untuk lagu saat ini
        if track:
            self._timeline.reset()
            self._sync.reset()
            from backend.models.models import PlaybackInfo, PlaybackState
            pb = PlaybackInfo(
                track=track,
                progress_ms=0,
                state=PlaybackState.PLAYING,
            )
            threading.Thread(target=self._load_lyrics, args=(pb,), daemon=True).start()
        return True

    @property
    def sync_engine(self) -> SmartSyncEngine:
        return self._sync

