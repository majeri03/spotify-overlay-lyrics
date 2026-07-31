"""
Playback Controller
===================
Membaca status playback Spotify dan mendeteksi perubahan:
- Track Changed
- Paused
- Resumed
- Seeked
- Track Ended
"""

from __future__ import annotations

import time
from typing import Optional

from backend.models.models import PlaybackInfo, PlaybackState, TrackInfo
from backend.spotify.client import SpotifyClient, TokenExpiredException
from backend.spotify.windows_media_provider import WindowsMediaProvider
from backend.logger.app_logger import app_logger

_SEEK_THRESHOLD_MS = 3000  # Jika progress melompat >3 detik → seek


class PlaybackController:
    def __init__(self, client: SpotifyClient, windows_media_provider=None) -> None:
        self._client = client
        # Gunakan shared instance jika ada, buat baru hanya jika tidak ada
        if windows_media_provider is not None:
            self._win_media = windows_media_provider
        else:
            self._win_media = WindowsMediaProvider()
        self._last: Optional[PlaybackInfo] = None

    def fetch(self) -> Optional[PlaybackInfo]:
        """Ambil data playback terkini dari Spotify API (Fallback ke Windows Media)."""
        data = None
        try:
            data = self._client.get("/me/player")
        except TokenExpiredException:
            pass
        except Exception as e:
            app_logger.debug(f"[PlaybackCtrl] API fetch error: {e}")

        # Fallback ke Windows Media Session jika Web API gagal / 403
        if not data:
            return self._win_media.fetch_playback()

        item = data.get("item")
        if not item:
            return None

        is_playing = data.get("is_playing", False)
        progress_ms = data.get("progress_ms", 0) or 0
        device = data.get("device", {})

        track = TrackInfo(
            spotify_id=item.get("id", ""),
            title=item.get("name", ""),
            artist=", ".join(a["name"] for a in item.get("artists", [])),
            album=item.get("album", {}).get("name", ""),
            duration_ms=item.get("duration_ms", 0),
            isrc=item.get("external_ids", {}).get("isrc", ""),
            image_url=(
                item.get("album", {}).get("images", [{}])[0].get("url", "")
                if item.get("album", {}).get("images") else ""
            ),
        )

        state = PlaybackState.PLAYING if is_playing else PlaybackState.PAUSED

        return PlaybackInfo(
            track=track,
            progress_ms=progress_ms,
            state=state,
            device_name=device.get("name", ""),
            device_id=device.get("id", ""),
            timestamp=time.time(),
        )

    def detect_changes(
        self,
        current: Optional[PlaybackInfo]
    ) -> list[str]:
        """
        Bandingkan current vs last playback dan return list event yang terjadi.
        Event: TRACK_CHANGED, TRACK_PAUSED, TRACK_RESUMED, TRACK_SEEKED, TRACK_ENDED,
               SPOTIFY_DISCONNECTED
        """
        events = []
        last = self._last

        if current is None:
            if last is not None and last.state != PlaybackState.STOPPED:
                events.append("SPOTIFY_DISCONNECTED")
            self._last = current
            return events

        if last is None:
            # Pertama kali ada data
            events.append("TRACK_CHANGED")
            self._last = current
            return events

        # Track berubah?
        if last.track and current.track:
            if last.track.spotify_id != current.track.spotify_id:
                events.append("TRACK_CHANGED")
                self._last = current
                return events

        # Pause?
        if last.state == PlaybackState.PLAYING and current.state == PlaybackState.PAUSED:
            events.append("TRACK_PAUSED")

        # Resume?
        if last.state == PlaybackState.PAUSED and current.state == PlaybackState.PLAYING:
            events.append("TRACK_RESUMED")

        # Seek? (hanya saat playing)
        if current.state == PlaybackState.PLAYING and last.state == PlaybackState.PLAYING:
            expected = last.progress_ms + 1200  # ~1.2s polling interval
            diff = abs(current.progress_ms - expected)
            if diff > _SEEK_THRESHOLD_MS:
                events.append("TRACK_SEEKED")

        # Track ended?
        if current.track and current.track.duration_ms > 0:
            if current.progress_ms >= current.track.duration_ms - 500:
                events.append("TRACK_ENDED")

        self._last = current
        return events

    @property
    def last_playback(self) -> Optional[PlaybackInfo]:
        return self._last
