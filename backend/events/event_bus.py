"""
Event Bus
=========
Pusat komunikasi antar modul EchoLyrics.
Menggunakan pattern Publisher-Subscriber berbasis Qt signals agar thread-safe
ketika berinteraksi dengan frontend PySide6.

Penggunaan:
    from backend.events.event_bus import EventBus
    bus = EventBus.instance()
    bus.subscribe(EventType.TRACK_CHANGED, my_handler)
    bus.publish(EventType.TRACK_CHANGED, data={"track": ...})
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from backend.events.event_types import EventType
from backend.logger.app_logger import app_logger


class EventBus:
    """
    Thread-safe singleton Event Bus.
    Handler dipanggil di thread yang sama dengan publisher kecuali
    qt_invoke=True (invoke via Qt main thread).
    """

    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._sub_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "EventBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ──────────────────────────────────────────────────────────
    # Subscribe
    # ──────────────────────────────────────────────────────────
    def subscribe(self, event: EventType, handler: Callable) -> None:
        """Daftarkan handler untuk event tertentu."""
        with self._sub_lock:
            if handler not in self._subscribers[event.value]:
                self._subscribers[event.value].append(handler)
                app_logger.debug(f"[EventBus] Subscribe: {event.value} → {handler.__qualname__}")

    def unsubscribe(self, event: EventType, handler: Callable) -> None:
        """Hapus handler dari event."""
        with self._sub_lock:
            try:
                self._subscribers[event.value].remove(handler)
                app_logger.debug(f"[EventBus] Unsubscribe: {event.value} → {handler.__qualname__}")
            except ValueError:
                pass

    def unsubscribe_all(self, event: EventType) -> None:
        """Hapus semua handler dari event."""
        with self._sub_lock:
            self._subscribers[event.value].clear()

    # ──────────────────────────────────────────────────────────
    # Publish
    # ──────────────────────────────────────────────────────────
    def publish(self, event: EventType, data: Any = None) -> None:
        """Kirim event ke semua subscriber."""
        with self._sub_lock:
            handlers = list(self._subscribers[event.value])

        app_logger.debug(f"[EventBus] Publish: {event.value} | handlers={len(handlers)}")

        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                app_logger.error(f"[EventBus] Handler error [{event.value}] {handler.__qualname__}: {e}")

    def clear(self) -> None:
        """Reset seluruh subscriber (untuk testing)."""
        with self._sub_lock:
            self._subscribers.clear()
