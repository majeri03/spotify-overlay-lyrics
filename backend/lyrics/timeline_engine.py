"""
Timeline Engine
===============
Mengubah list SubtitleLine menjadi TrackTimeline yang immutable.
Menghitung end_timestamp dan smart duration untuk setiap baris.
Menggunakan Binary Search untuk pencarian subtitle O(log n).
"""

from __future__ import annotations

import bisect
import time
from typing import List, Optional, Tuple

from backend.models.models import SubtitleLine, SubtitleQueue, TrackInfo, TrackTimeline
from backend.utils.timer_helper import PrecisionTimer
from backend.logger.app_logger import app_logger

_MAX_DISPLAY_MS = 8000  # Maksimum tampil 8 detik per baris


class TimelineEngine:
    """
    Mengelola timeline subtitle untuk satu lagu.
    Thread-safe via immutable timeline.
    """

    def __init__(self) -> None:
        self._timeline: Optional[TrackTimeline] = None
        self._timer = PrecisionTimer()
        self._timestamps: List[int] = []  # Sorted timestamps untuk binary search
        self._current_index: int = -1

    # ──────────────────────────────────────────────────────────
    # Build Timeline
    # ──────────────────────────────────────────────────────────

    def build(self, track: TrackInfo, lines: List[SubtitleLine]) -> TrackTimeline:
        """
        Build immutable timeline dari list subtitle.
        Hitung end_timestamp dan duration setiap baris.
        """
        if not lines:
            return TrackTimeline(track=track, lines=[])

        # Normalisasi — sort ulang
        sorted_lines = sorted(lines, key=lambda l: l.timestamp_ms)

        # Hitung end_timestamp dan duration
        for i, line in enumerate(sorted_lines):
            if i < len(sorted_lines) - 1:
                next_ts = sorted_lines[i + 1].timestamp_ms
                natural_duration = next_ts - line.timestamp_ms
                line.end_timestamp_ms = line.timestamp_ms + min(natural_duration, _MAX_DISPLAY_MS)
            else:
                # Baris terakhir
                line.end_timestamp_ms = line.timestamp_ms + _MAX_DISPLAY_MS

            line.duration_ms = line.end_timestamp_ms - line.timestamp_ms
            line.index = i
            line.previous_index = i - 1 if i > 0 else -1
            line.next_index = i + 1 if i < len(sorted_lines) - 1 else -1

        timeline = TrackTimeline(track=track, lines=sorted_lines)
        self._timeline = timeline
        self._timestamps = [l.timestamp_ms for l in sorted_lines]
        self._current_index = -1

        app_logger.info(
            f"[Timeline] Built {len(sorted_lines)} lines for: {track.artist} - {track.title}"
        )
        return timeline

    # ──────────────────────────────────────────────────────────
    # Timer Control
    # ──────────────────────────────────────────────────────────

    def start(self, position_ms: float) -> None:
        self._timer.start(position_ms)

    def pause(self) -> None:
        self._timer.pause()

    def resume(self) -> None:
        self._timer.resume()

    def seek(self, position_ms: float) -> None:
        self._timer.seek(position_ms)
        # Reset current index sehingga next lookup fresh
        self._current_index = -1

    def reset(self) -> None:
        self._timer.reset()
        self._current_index = -1
        self._timeline = None
        self._timestamps = []

    # ──────────────────────────────────────────────────────────
    # Lookup
    # ──────────────────────────────────────────────────────────

    def get_current_queue(self) -> Optional[SubtitleQueue]:
        """
        Return SubtitleQueue (previous, current, next) berdasarkan posisi timer.
        Menggunakan Binary Search O(log n).
        """
        if not self._timeline or not self._timestamps:
            return None

        pos_ms = self._timer.position_ms

        # Binary search: cari index baris yang aktif
        idx = bisect.bisect_right(self._timestamps, pos_ms) - 1

        if idx < 0:
            return SubtitleQueue()

        lines = self._timeline.lines

        # Pastikan masih dalam durasi tampil
        current_line = lines[idx]
        if pos_ms > current_line.end_timestamp_ms:
            # Sudah melewati window display → teks hilang sementara
            return SubtitleQueue()

        previous = lines[idx - 1] if idx > 0 else None
        nxt = lines[idx + 1] if idx < len(lines) - 1 else None

        changed = idx != self._current_index
        self._current_index = idx

        return SubtitleQueue(
            previous=previous,
            current=current_line,
            next=nxt,
            current_index=idx,
        )

    @property
    def position_ms(self) -> float:
        return self._timer.position_ms

    @property
    def is_running(self) -> bool:
        return self._timer.is_running

    @property
    def timeline(self) -> Optional[TrackTimeline]:
        return self._timeline
