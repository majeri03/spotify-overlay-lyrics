"""
Auto-Sync Calibration Engine
=============================
Mendeteksi dan mengoreksi offset antara timestamp LRC dan posisi audio Spotify
secara otomatis menggunakan Adaptive Drift Correction.

Cara kerja:
1. Setiap kali lirik berganti (event QUEUE_UPDATED), catat selisih antara:
   - Posisi timer internal (PrecisionTimer)
   - Posisi Spotify API terkini (dari WindowsMediaProvider)
2. Kumpulkan sampel selisih selama ~5 menit.
3. Hitung median selisih → ini adalah "systematic offset" LRC file ini.
4. Terapkan offset sebagai koreksi permanen ke timeline engine (shift semua timestamps).
5. Simpan offset per track_id ke database agar tidak perlu belajar ulang.

Hasilnya: lirik otomatis sinkron sempurna bahkan jika LRC file terlambat/terlalu cepat.
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Optional, List

from backend.logger.app_logger import app_logger


class AutoSyncCalibrator:
    """
    Adaptive drift corrector untuk sinkronisasi lirik ke audio.
    
    Prinsip:
    - Timer internal berjalan bebas dari perf_counter (sangat presisi, tidak ada network lag).
    - Spotify progress_ms datang setiap 250ms (ada jitter ~50-150ms).
    - Kita kumpulkan sampel: drift = spotify_progress - timer_position.
    - Ambil median dari sampel → koreksi sistemik.
    - Terapkan koreksi ke timeline engine.
    """

    _MAX_SAMPLES    = 20     # Kumpulkan 20 sampel sebelum apply koreksi
    _APPLY_AFTER    = 6      # Apply setelah minimal 6 sampel
    _OUTLIER_CUTOFF = 1500   # Buang sampel jika drift > 1500ms (kemungkinan seek)
    _MIN_CORRECT    = 80     # Minimal offset yang dianggap signifikan (ms)
    _MAX_CORRECT    = 2000   # Maksimal koreksi sekali jalan (ms) - safety cap

    def __init__(self, timeline_engine) -> None:
        self._engine = timeline_engine
        self._samples: List[float] = []
        self._lock = threading.Lock()
        self._applied_offset: float = 0.0   # Total offset yang sudah diterapkan
        self._track_id: Optional[int] = None
        self._enabled = True
        self._last_spotify_pos: float = 0.0
        self._last_spotify_time: float = 0.0  # perf_counter saat _last_spotify_pos diambil

    def reset(self, track_id: Optional[int] = None) -> None:
        """Reset saat lagu berganti."""
        with self._lock:
            self._samples.clear()
            self._applied_offset = 0.0
            self._track_id = track_id
            self._last_spotify_pos = 0.0
            self._last_spotify_time = 0.0

    def record_spotify_position(self, spotify_pos_ms: float) -> None:
        """
        Rekam posisi Spotify terkini (dari API poll).
        Spotify progress_ms sudah stale ~polling_latency ms, jadi kita
        rekam juga waktu saat data ini diterima untuk extrapolasi.
        """
        with self._lock:
            self._last_spotify_pos = spotify_pos_ms
            self._last_spotify_time = time.perf_counter()

    def sample(self) -> None:
        """
        Ambil satu sampel drift. Harus dipanggil segera setelah baris lirik aktif berganti
        (saat itu posisi timer hampir pasti berada di timestamp baris yang baru aktif).
        """
        if not self._enabled:
            return

        with self._lock:
            # Ekstrapol posisi Spotify ke "sekarang" menggunakan perf_counter
            if self._last_spotify_time <= 0 or self._last_spotify_pos <= 0:
                return

            elapsed_since_poll = (time.perf_counter() - self._last_spotify_time) * 1000.0
            extrapolated_spotify = self._last_spotify_pos + elapsed_since_poll

            timer_pos = self._engine.position_ms

            if timer_pos <= 0 or extrapolated_spotify <= 0:
                return

            drift = extrapolated_spotify - timer_pos
            app_logger.debug(f"[AutoSync] Sample drift: {drift:+.0f}ms "
                           f"(spotify={extrapolated_spotify:.0f}ms, timer={timer_pos:.0f}ms)")

            # Buang outlier (kemungkinan seek atau bug)
            if abs(drift) > self._OUTLIER_CUTOFF:
                app_logger.debug(f"[AutoSync] Outlier discarded: {drift:+.0f}ms")
                return

            self._samples.append(drift)

            # Trim ke max samples (sliding window)
            if len(self._samples) > self._MAX_SAMPLES:
                self._samples.pop(0)

            # Apply koreksi jika sudah cukup sampel
            if len(self._samples) >= self._APPLY_AFTER:
                self._try_apply_correction()

    def _try_apply_correction(self) -> None:
        """Hitung dan terapkan koreksi berdasarkan median drift sampel."""
        if len(self._samples) < self._APPLY_AFTER:
            return

        median_drift = statistics.median(self._samples)

        # Hanya koreksi jika drift signifikan
        if abs(median_drift) < self._MIN_CORRECT:
            return

        # Safety cap
        correction = max(-self._MAX_CORRECT, min(self._MAX_CORRECT, median_drift))

        app_logger.info(
            f"[AutoSync] Applying correction: {correction:+.0f}ms "
            f"(median of {len(self._samples)} samples, "
            f"total offset={self._applied_offset + correction:+.0f}ms)"
        )

        # Geser posisi timer sesuai koreksi
        new_pos = self._engine.position_ms + correction
        self._engine.seek(max(0, new_pos))

        self._applied_offset += correction
        self._samples.clear()   # Reset setelah apply

    def load_saved_offset(self, offset_ms: float) -> None:
        """
        Terapkan offset yang tersimpan dari database (hasil kalibrasi sesi sebelumnya).
        Dipanggil saat timeline siap sebelum musik mulai.
        """
        if abs(offset_ms) < self._MIN_CORRECT:
            return
        app_logger.info(f"[AutoSync] Loaded saved offset: {offset_ms:+.0f}ms")
        new_pos = self._engine.position_ms + offset_ms
        self._engine.seek(max(0, new_pos))
        with self._lock:
            self._applied_offset = offset_ms

    @property
    def total_offset_ms(self) -> float:
        """Total offset yang sudah diterapkan (untuk disimpan ke DB)."""
        with self._lock:
            return self._applied_offset

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
