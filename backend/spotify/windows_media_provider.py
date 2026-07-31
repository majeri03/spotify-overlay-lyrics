"""
Windows Media Session Provider
==============================
Membaca informasi lagu yang sedang diputar di Windows (Spotify Free/Web, Chrome, Edge, VLC, dll)
menggunakan Windows System Media Transport Controls (GSMTC).

Catatan:
- Spotify Web (browser) sering melaporkan PositionMs yang tidak bergerak (stuck di nilai lama)
- Solusi: hitung posisi sendiri berdasarkan waktu nyata sejak lagu pertama terdeteksi
- PositionMs dari GSMTC hanya dipakai sebagai anchor saat lagu pertama terdeteksi atau berubah
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Optional

from backend.models.models import PlaybackInfo, PlaybackState, TrackInfo
from backend.logger.app_logger import app_logger

# PowerShell loop persisten — output tiap 500ms
_PS_LOOP_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSession, Windows.Media.Control, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties, Windows.Media.Control, ContentType=WindowsRuntime] | Out-Null

while ($true) {
    try {
        $manager = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
        $session = $manager.GetCurrentSession()
        if ($session) {
            $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
            $pos   = $session.GetTimelineProperties()
            $pb    = $session.GetPlaybackInfo()
            [PSCustomObject]@{
                Title      = $props.Title
                Artist     = $props.Artist
                Album      = $props.AlbumTitle
                PositionMs = [math]::Round($pos.Position.TotalMilliseconds)
                DurationMs = [math]::Round($pos.EndTime.TotalMilliseconds)
                Status     = $pb.PlaybackStatus.ToString()
                App        = $session.SourceAppUserModelId
            } | ConvertTo-Json -Compress
        } else {
            Write-Output '{}'
        }
    } catch {
        Write-Output '{}'
    }
    Start-Sleep -Milliseconds 500
}
"""


class WindowsMediaProvider:
    """
    Membaca media session Windows menggunakan PowerShell persisten.

    Mengatasi bug Spotify Web: PositionMs di GSMTC sering stuck.
    Solusi: pakai PositionMs sebagai anchor, hitung maju sendiri berdasarkan waktu nyata.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

        # State tracking
        self._last_title: str = ""
        self._last_artist: str = ""
        self._anchor_pos_ms: float = 0.0      # posisi saat anchor dibuat
        self._anchor_time: float = 0.0        # time.perf_counter() saat anchor
        self._last_status: str = "Stopped"
        self._last_album: str = ""
        self._last_dur_ms: int = 0
        self._last_raw_pos: int = 0           # posisi mentah dari GSMTC

        self._start()

    def _start(self) -> None:
        """Mulai proses PowerShell persisten di background."""
        try:
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_LOOP_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=False,
            )
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._read_loop,
                daemon=True,
                name="WinMediaReader"
            )
            self._reader_thread.start()
            app_logger.info("[WindowsMediaProvider] PowerShell persistent process started.")
        except Exception as e:
            app_logger.warning(f"[WindowsMediaProvider] Failed to start PS process: {e}")

    def _read_loop(self) -> None:
        """Baca stdout dari PowerShell secara terus-menerus."""
        while self._running and self._proc:
            try:
                raw = self._proc.stdout.readline()
                if not raw:
                    app_logger.warning("[WindowsMediaProvider] PS process died, restarting...")
                    time.sleep(1)
                    self._start()
                    break

                line = raw.decode("utf-8", errors="replace").strip()
                if not line or line == "{}":
                    with self._lock:
                        self._last_status = "Stopped"
                    continue

                try:
                    data = json.loads(line)
                    self._update_state(data)
                except json.JSONDecodeError:
                    pass

            except Exception as e:
                app_logger.debug(f"[WindowsMediaProvider] Read error: {e}")
                time.sleep(0.5)

    def _update_state(self, data: dict) -> None:
        """Update internal state dari data GSMTC terbaru."""
        title   = data.get("Title", "").strip()
        artist  = data.get("Artist", "").strip()
        album   = data.get("Album", "").strip()
        raw_pos = int(data.get("PositionMs", 0))
        dur_ms  = int(data.get("DurationMs", 0))
        status  = data.get("Status", "Playing")

        with self._lock:
            track_changed = (title != self._last_title or artist != self._last_artist)
            status_changed = (status != self._last_status)
            # Posisi melompat signifikan = user seek / lagu baru
            pos_jumped = abs(raw_pos - self._last_raw_pos) > 2000

            if track_changed or pos_jumped:
                # Reset anchor ke posisi baru
                self._anchor_pos_ms = float(raw_pos)
                self._anchor_time = time.perf_counter()
                app_logger.debug(f"[WindowsMediaProvider] Anchor reset: pos={raw_pos}ms "
                                 f"track_changed={track_changed} pos_jumped={pos_jumped}")

            elif status_changed and status == "Playing":
                # Resume dari pause — set anchor baru
                self._anchor_pos_ms = float(raw_pos)
                self._anchor_time = time.perf_counter()

            self._last_title = title
            self._last_artist = artist
            self._last_album = album
            self._last_dur_ms = dur_ms
            self._last_status = status
            self._last_raw_pos = raw_pos

    def fetch_playback(self) -> Optional[PlaybackInfo]:
        """
        Ambil data playback terkini.
        Posisi dihitung secara real-time dari anchor (bukan PositionMs GSMTC).
        """
        with self._lock:
            title   = self._last_title
            artist  = self._last_artist
            album   = self._last_album
            dur_ms  = self._last_dur_ms
            status  = self._last_status
            anchor_pos  = self._anchor_pos_ms
            anchor_time = self._anchor_time

        if not title or status == "Stopped":
            return None

        # Hitung posisi real-time
        if status == "Playing" and anchor_time > 0:
            elapsed_ms = (time.perf_counter() - anchor_time) * 1000.0
            pos_ms = int(anchor_pos + elapsed_ms)
        else:
            pos_ms = int(anchor_pos)

        spotify_id = f"local_{artist}_{title}"

        track = TrackInfo(
            spotify_id=spotify_id,
            title=title,
            artist=artist or "Unknown Artist",
            album=album,
            duration_ms=dur_ms,
        )

        state = PlaybackState.PLAYING if status == "Playing" else PlaybackState.PAUSED

        return PlaybackInfo(
            track=track,
            progress_ms=pos_ms,
            state=state,
            device_name="Windows Media",
            timestamp=time.time(),
        )

    def stop(self) -> None:
        """Hentikan proses PowerShell."""
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
