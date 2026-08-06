"""
Overlay Controller
==================
Penghubung antara Backend Event Bus dan OverlayWindow.
Menangani semua event yang memengaruhi tampilan overlay.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.models.models import SubtitleQueue, TrackTimeline
from backend.logger.app_logger import app_logger


class OverlayControllerSignals(QObject):
    """Qt signals untuk thread-safe UI update dari backend thread."""
    queue_updated     = Signal(object)     # SubtitleQueue
    show_overlay      = Signal()
    hide_overlay      = Signal()
    track_ended       = Signal()
    translation_ready = Signal(object)     # TrackTimeline (setelah terjemahan lengkap)


class OverlayController:
    """
    Menerima event dari backend dan mengupdate overlay di Qt main thread.
    """

    def __init__(self, event_bus: EventBus, overlay_window) -> None:
        self._bus = event_bus
        self._overlay = overlay_window
        self._signals = OverlayControllerSignals()
        self._connect_signals()
        self._subscribe_events()

    def _connect_signals(self) -> None:
        self._signals.queue_updated.connect(self._on_queue_updated)
        self._signals.show_overlay.connect(self._overlay.show_overlay)
        self._signals.hide_overlay.connect(self._overlay.hide_overlay)
        self._signals.track_ended.connect(self._overlay.clear)
        self._signals.translation_ready.connect(self._on_translation_ready)

    def _subscribe_events(self) -> None:
        self._bus.subscribe(EventType.QUEUE_UPDATED, self._evt_queue_updated)
        self._bus.subscribe(EventType.SPOTIFY_DISCONNECTED, self._evt_disconnected)
        self._bus.subscribe(EventType.SPOTIFY_CONNECTED, self._evt_connected)
        self._bus.subscribe(EventType.TRACK_ENDED, self._evt_track_ended)
        # LYRICS_NOT_FOUND: clear subtitle tapi jangan sembunyikan overlay
        self._bus.subscribe(EventType.LYRICS_NOT_FOUND, self._evt_lyrics_not_found)
        # TRACK_CHANGED: JANGAN clear overlay — biarkan lirik lama tampil sampai lirik baru siap
        # self._bus.subscribe(EventType.TRACK_CHANGED, self._evt_track_changed)
        self._bus.subscribe(EventType.TRANSLATION_READY, self._evt_translation_ready)

    # ──────────────────────────────────────────────────────────
    # Event handlers (backend thread)
    # ──────────────────────────────────────────────────────────

    def _evt_queue_updated(self, queue: Optional[SubtitleQueue]) -> None:
        if queue:
            self._signals.queue_updated.emit(queue)

    def _evt_connected(self, _) -> None:
        self._signals.show_overlay.emit()

    def _evt_disconnected(self, _) -> None:
        self._signals.hide_overlay.emit()

    def _evt_track_ended(self, _) -> None:
        self._signals.track_ended.emit()

    def _evt_lyrics_not_found(self, _) -> None:
        # Tidak ada lirik untuk lagu ini — clear teks subtitle di main thread
        self._signals.track_ended.emit()

    def _evt_track_changed(self, _) -> None:
        # SENGAJA tidak clear overlay saat track ganti.
        # Lirik lama tetap tampil sampai lirik baru siap (QUEUE_UPDATED).
        # Ini mencegah gap kosong antara ganti lagu.
        pass

    def _evt_translation_ready(self, timeline) -> None:
        if timeline:
            self._signals.translation_ready.emit(timeline)

    # ──────────────────────────────────────────────────────────
    # Qt Slots (main thread)
    # ──────────────────────────────────────────────────────────

    @Slot(object)
    def _on_queue_updated(self, queue: SubtitleQueue) -> None:
        self._overlay.update_queue(queue)

    @Slot(object)
    def _on_translation_ready(self, timeline) -> None:
        """Ketika terjemahan sudah siap, paksa overlay re-draw."""
        self._overlay.update()

    # ──────────────────────────────────────────────────────────
    # Settings delegation
    # ──────────────────────────────────────────────────────────

    def apply_settings(self, settings: dict) -> None:
        self._overlay.set_theme(settings.get("theme", "dark"))
        self._overlay.set_font_sizes(
            en=settings.get("font_size_english", 32),
            id_=settings.get("font_size_translation", 24)
        )
        self._overlay.set_glow(bool(settings.get("glow_enabled", 1)))
        self._overlay.set_click_through(bool(settings.get("click_through", 1)))
        opacity = settings.get("overlay_opacity", 100) / 100.0
        self._overlay.set_opacity(opacity)
