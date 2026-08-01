"""
Smart Sync Engine
=================
Sinkronisasi lirik ke audio Spotify secara OTOMATIS dan KONTINU.

Cara kerja:
1. Setiap 500ms — ambil posisi akurat dari WindowsMediaProvider (real-time).
2. Hitung drift = media_pos - timer_pos.
3. Drift kecil  (< LERP_THRESHOLD) → koreksi halus (lerp): timer digeser
   secara gradual, tidak ada "lompatan" lirik.
4. Drift sedang (LERP_THRESHOLD..HARD_SEEK_ABOVE) → percepat lerp.
5. Drift besar  (> HARD_SEEK_ABOVE) → hard-seek langsung (user mungkin seek
   atau ada lag besar).

TIDAK ADA tebakan, TIDAK ADA manual input yang dibutuhkan.
Setiap lagu — cepat, lambat, pop, ballad — ditangani sama oleh engine ini.

Penyimpanan offset per-lagu ke SQLite opsional (untuk startup sesi berikutnya).
"""

from __future__ import annotations

import threading
import time
from typing import Optional, TYPE_CHECKING

from backend.logger.app_logger import app_logger

if TYPE_CHECKING:
    from backend.lyrics.timeline_engine import TimelineEngine
    from backend.spotify.windows_media_provider import WindowsMediaProvider


# ── Konstanta ──────────────────────────────────────────────────────────────────

# Lerp: koreksi halus saat drift kecil
_LERP_THRESHOLD_MS   = 400    # ms — di bawah ini gunakan lerp
_LERP_MAX_SPEED_MS_S = 300    # ms/s — kecepatan koreksi lerp maks
_LERP_MIN_SPEED_MS_S = 50     # ms/s — kecepatan lerp minimum (masih terasa)

# Hard seek: langsung lompat jika drift terlalu besar
_HARD_SEEK_MS        = 800    # ms — di atas ini hard-seek

# Seberapa sering cek & koreksi drift (ms)
_SYNC_INTERVAL_MS    = 500

# Minimal drift yang dianggap signifikan (noise filter)
_DRIFT_NOISE_MS      = 30     # ms — di bawah ini abaikan

# Outlier: kemungkinan seek user atau bug GSMTC
_OUTLIER_MS          = 5000   # ms — di atas ini abaikan sampel

# Stabilisasi: berapa sampel valid sebelum trust offset awal
_STABLE_SAMPLES      = 3


class SmartSyncEngine:
    """
    Sinkronisasi otomatis dan kontinu antara PrecisionTimer dan audio Spotify.

    Thread-safe. Dijalankan dari tick() di scheduler utama (50ms interval).
    """

    def __init__(
        self,
        timeline_engine: "TimelineEngine",
        win_media: Optional["WindowsMediaProvider"] = None,
    ) -> None:
        self._engine     = timeline_engine
        self._win_media  = win_media
        self._lock       = threading.Lock()

        # State sinkronisasi
        self._enabled: bool = True
        self._manual_offset_ms: float = 0.0   # Offset tambahan dari user (Settings)

        # State posisi Spotify terkini
        self._last_spotify_pos: float  = 0.0
        self._last_spotify_time: float = 0.0  # perf_counter saat data diterima

        # Lerp correction state
        self._lerp_velocity: float = 0.0      # ms/s, positif = percepat, negatif = perlambat
        self._lerp_remaining: float = 0.0     # ms drift yang tersisa untuk dikoreksi
        self._last_tick_time: float = 0.0     # perf_counter tick terakhir

        # Sync check interval
        self._last_sync_check: float = 0.0    # perf_counter sync check terakhir

        # Per-track offset (dari DB)
        self._saved_offset_ms: float = 0.0
        self._track_id: Optional[int] = None

        # Statistik untuk debug
        self._correction_count: int = 0
        self._total_drift_corrected: float = 0.0
        self._samples_before_stable: list[float] = []
        self._is_stable: bool = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def reset(self, track_id: Optional[int] = None) -> None:
        """Reset saat lagu berganti atau seek."""
        with self._lock:
            self._last_spotify_pos  = 0.0
            self._last_spotify_time = 0.0
            self._lerp_velocity     = 0.0
            self._lerp_remaining    = 0.0
            self._last_tick_time    = 0.0
            self._last_sync_check   = 0.0
            self._track_id          = track_id
            self._saved_offset_ms   = 0.0
            self._correction_count  = 0
            self._total_drift_corrected = 0.0
            self._samples_before_stable = []
            self._is_stable         = False

    def load_saved_offset(self, offset_ms: float) -> None:
        """
        Terapkan offset yang tersimpan dari DB sesi sebelumnya.
        Dipanggil satu kali setelah timeline dimulai.
        """
        with self._lock:
            self._saved_offset_ms = offset_ms
        if abs(offset_ms) > _DRIFT_NOISE_MS:
            app_logger.info(f"[SmartSync] Loaded saved offset: {offset_ms:+.0f}ms")

    def record_spotify_position(self, spotify_pos_ms: float) -> None:
        """
        Update posisi Spotify terkini (dipanggil dari PLAYBACK_UPDATED event).
        Menyimpan posisi + waktu saat ini untuk extrapolasi real-time.
        """
        with self._lock:
            self._last_spotify_pos  = spotify_pos_ms
            self._last_spotify_time = time.perf_counter()

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled
        state = "enabled" if enabled else "disabled"
        app_logger.info(f"[SmartSync] Auto-sync {state}.")

    def set_manual_offset(self, offset_ms: float) -> None:
        """
        Set offset manual dari user (Settings slider).
        Otomatis trigger re-anchor.
        """
        with self._lock:
            old = self._manual_offset_ms
            self._manual_offset_ms = float(offset_ms)
        if abs(offset_ms - old) > 5:
            app_logger.info(f"[SmartSync] Manual offset set: {offset_ms:+.0f}ms")
            # Reset lerp agar segera apply offset baru
            with self._lock:
                self._lerp_velocity  = 0.0
                self._lerp_remaining = 0.0

    @property
    def manual_offset_ms(self) -> float:
        with self._lock:
            return self._manual_offset_ms

    @property
    def is_stable(self) -> bool:
        """True jika engine sudah mengumpulkan cukup data untuk sync akurat."""
        with self._lock:
            return self._is_stable

    @property
    def total_corrected_ms(self) -> float:
        """Total koreksi yang sudah diterapkan (untuk disimpan ke DB)."""
        with self._lock:
            return self._total_drift_corrected

    # ── Tick (dipanggil setiap 50ms dari scheduler) ────────────────────────────

    def tick(self) -> None:
        """
        Dipanggil setiap 50ms. Dua tugas:
        1. Apply lerp correction yang sedang berjalan.
        2. Setiap SYNC_INTERVAL_MS: cek drift dan mulai correction baru jika perlu.
        """
        now = time.perf_counter()

        with self._lock:
            enabled          = self._enabled
            last_tick        = self._last_tick_time
            last_check       = self._last_sync_check
            lerp_vel         = self._lerp_velocity
            lerp_rem         = self._lerp_remaining
            last_spotify_pos = self._last_spotify_pos
            last_spotify_t   = self._last_spotify_time
            manual_off       = self._manual_offset_ms
            saved_off        = self._saved_offset_ms

        if not enabled:
            with self._lock:
                self._last_tick_time = now
            return

        dt = (now - last_tick) if last_tick > 0 else 0.0
        with self._lock:
            self._last_tick_time = now

        # 1. Apply lerp correction
        if abs(lerp_rem) > _DRIFT_NOISE_MS and abs(lerp_vel) > 0:
            correction_this_tick = lerp_vel * dt  # ms
            # Jangan over-correct
            if abs(correction_this_tick) > abs(lerp_rem):
                correction_this_tick = lerp_rem

            # Geser timer secara halus (soft_shift = tanpa reset current_index)
            self._engine.soft_shift(correction_this_tick)

            with self._lock:
                self._lerp_remaining -= correction_this_tick
                # Jika sudah selesai, stop lerp
                if abs(self._lerp_remaining) < _DRIFT_NOISE_MS:
                    self._lerp_velocity  = 0.0
                    self._lerp_remaining = 0.0

        # 2. Periodic drift check
        elapsed_since_check = (now - last_check) * 1000.0  # ms
        if elapsed_since_check < _SYNC_INTERVAL_MS:
            return
        with self._lock:
            self._last_sync_check = now

        # Tidak ada data Spotify → skip
        if last_spotify_t <= 0 or last_spotify_pos <= 0:
            return

        # Extrapolasi posisi Spotify ke "sekarang"
        elapsed_since_poll_ms = (now - last_spotify_t) * 1000.0
        extrapolated_spotify  = last_spotify_pos + elapsed_since_poll_ms

        # Ambil posisi timer saat ini
        timer_pos = self._engine.position_ms
        if timer_pos <= 0:
            return

        # Hitung drift bersih (termasuk manual offset dan saved offset)
        effective_target = extrapolated_spotify + manual_off + saved_off
        raw_drift = effective_target - timer_pos

        # Filter outlier (kemungkinan seek user atau bug GSMTC)
        if abs(raw_drift) > _OUTLIER_MS:
            app_logger.debug(f"[SmartSync] Outlier ignored: drift={raw_drift:+.0f}ms")
            return

        # Kumpulkan sampel stabilisasi awal
        with self._lock:
            if not self._is_stable:
                self._samples_before_stable.append(raw_drift)
                if len(self._samples_before_stable) >= _STABLE_SAMPLES:
                    self._is_stable = True
                    avg = sum(self._samples_before_stable) / len(self._samples_before_stable)
                    app_logger.info(f"[SmartSync] Engine stable. Initial avg drift: {avg:+.0f}ms")

        # Noise filter
        if abs(raw_drift) < _DRIFT_NOISE_MS:
            return

        # Pilih strategi koreksi
        self._apply_correction(raw_drift)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _apply_correction(self, drift_ms: float) -> None:
        """
        Putuskan strategi koreksi berdasarkan magnitude drift.
        """
        abs_drift = abs(drift_ms)

        if abs_drift >= _HARD_SEEK_MS:
            # Hard seek — langsung lompat (user mungkin seek atau lag besar)
            new_pos = self._engine.position_ms + drift_ms
            self._engine.seek(max(0.0, new_pos))
            with self._lock:
                self._lerp_velocity  = 0.0
                self._lerp_remaining = 0.0
                self._correction_count += 1
                self._total_drift_corrected += drift_ms
            app_logger.info(
                f"[SmartSync] Hard-seek: drift={drift_ms:+.0f}ms"
            )

        elif abs_drift >= _DRIFT_NOISE_MS:
            # Lerp correction — koreksi halus
            # Kecepatan lerp: proporsional terhadap drift, diklem ke [MIN, MAX]
            speed = max(
                _LERP_MIN_SPEED_MS_S,
                min(_LERP_MAX_SPEED_MS_S, abs_drift * 1.5)
            )
            velocity = speed if drift_ms > 0 else -speed

            with self._lock:
                # Jika lerp sedang berjalan dengan arah sama, update saja
                if self._lerp_velocity * velocity > 0:
                    self._lerp_remaining += drift_ms  # tambah sisa
                else:
                    # Arah baru, reset lerp
                    self._lerp_velocity  = velocity
                    self._lerp_remaining = drift_ms
                self._correction_count += 1
                self._total_drift_corrected += drift_ms

            app_logger.debug(
                f"[SmartSync] Lerp: drift={drift_ms:+.0f}ms "
                f"speed={velocity:+.0f}ms/s"
            )

    # ── Fallback: ambil posisi dari WindowsMediaProvider langsung ───────────────

    def fetch_fresh_anchor(self) -> Optional[float]:
        """
        Ambil posisi paling akurat dari WindowsMediaProvider saat ini.
        Digunakan saat timeline pertama kali dimulai.
        """
        if self._win_media is None:
            return None
        try:
            pb = self._win_media.fetch_playback()
            if pb and pb.progress_ms > 0 and pb.state.name == "PLAYING":
                return float(pb.progress_ms)
        except Exception:
            pass
        return None
