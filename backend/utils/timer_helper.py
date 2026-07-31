"""
Timer Helper
============
High-precision timer menggunakan time.perf_counter()
untuk internal timeline engine.
"""

import time
from typing import Optional


class PrecisionTimer:
    """
    High-precision elapsed timer.
    Digunakan oleh Timeline Engine untuk sinkronisasi subtitle
    tanpa bergantung pada polling Spotify setiap frame.
    """

    def __init__(self) -> None:
        self._start: Optional[float] = None
        self._offset_ms: float = 0.0
        self._running: bool = False

    def start(self, offset_ms: float = 0.0) -> None:
        """Mulai timer dengan offset posisi playback."""
        self._offset_ms = offset_ms
        self._start = time.perf_counter()
        self._running = True

    def pause(self) -> None:
        """Hentikan timer (saat lagu di-pause)."""
        if self._running and self._start is not None:
            elapsed = (time.perf_counter() - self._start) * 1000.0
            self._offset_ms += elapsed
            self._start = None
            self._running = False

    def resume(self) -> None:
        """Lanjutkan timer (setelah resume)."""
        if not self._running:
            self._start = time.perf_counter()
            self._running = True

    def seek(self, position_ms: float) -> None:
        """Set posisi timer ke timestamp baru (setelah seek)."""
        self._offset_ms = position_ms
        self._start = time.perf_counter() if self._running else None

    def reset(self) -> None:
        """Reset timer ke 0."""
        self._start = None
        self._offset_ms = 0.0
        self._running = False

    @property
    def position_ms(self) -> float:
        """Posisi saat ini dalam milidetik."""
        if self._running and self._start is not None:
            elapsed = (time.perf_counter() - self._start) * 1000.0
            return self._offset_ms + elapsed
        return self._offset_ms

    @property
    def is_running(self) -> bool:
        return self._running
