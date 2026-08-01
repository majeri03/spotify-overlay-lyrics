"""
LRCLIB Provider — Duration-Aware Smart Matching
================================================
Mengambil lirik dari LRCLIB API (https://lrclib.net).
Dilengkapi dengan:
  • Duration-aware selection: Memilih lirik yang durasinya paling cocok dengan lagu Spotify.
  • Smart Cleaner & Search Fallback untuk judul/artis ber-feat/koma.
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests

from backend.logger.app_logger import app_logger

_BASE_URL = "https://lrclib.net/api"
_TIMEOUT  = 8


def _clean_artist(artist: str) -> str:
    """Ambil nama artis utama sebelum koma atau feat."""
    if not artist:
        return ""
    clean = re.split(r"[,&]|\bfeat\b|\bft\b", artist, flags=re.IGNORECASE)[0]
    return clean.strip()


def _clean_title(title: str) -> str:
    """Hapus (feat. ...), [feat. ...], (Official Video), dll."""
    if not title:
        return ""
    clean = re.sub(
        r"[\(\[\{].*?(feat|ft|with|remastered|official|video|audio).*?[\)\]\}]",
        "",
        title,
        flags=re.IGNORECASE
    )
    return clean.strip()


class LRCLibProvider:
    """Provider lirik dari LRCLIB.net dengan Duration-Aware Matching."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "EchoLyrics/1.0 (https://github.com/echolyrics)"
        })

    def fetch(
        self,
        artist: str,
        title: str,
        duration_ms: int = 0,
        album: str = ""
    ) -> Optional[str]:
        """
        Cari dan ambil synchronized lyrics (LRC format).
        Menyesuaikan durasi lagu Spotify dengan durasi lirik LRCLIB agar sinkron.
        """
        target_sec = duration_ms // 1000 if duration_ms > 0 else 0

        # 1. Coba exact match terlebih dahulu
        params = {
            "artist_name": artist,
            "track_name": title,
        }
        if target_sec > 0:
            params["duration"] = target_sec
        if album:
            params["album_name"] = album

        try:
            resp = self._session.get(f"{_BASE_URL}/get", params=params, timeout=_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics") or data.get("plainLyrics")
                if synced:
                    app_logger.info(f"[LRCLIB] Exact match success for: {artist} - {title}")
                    return synced
        except Exception:
            pass

        # 2. Fallback: Smart Clean + Search API + Duration Matching
        clean_art = _clean_artist(artist)
        clean_ti  = _clean_title(title)
        query     = f"{clean_art} {clean_ti}".strip()

        app_logger.info(f"[LRCLIB] Searching fallback for: '{query}' (Target duration: {target_sec}s)...")

        try:
            resp = self._session.get(f"{_BASE_URL}/search", params={"q": query}, timeout=_TIMEOUT)
            if resp.status_code == 200:
                results = resp.json()
                if not results:
                    app_logger.warning(f"[LRCLIB] No search results for: {query}")
                    return None

                # Cari hasil yang memilik syncedLyrics dan durasi PALING MENDEKATI lagu Spotify
                best_synced = None
                best_diff = float("inf")

                for item in results:
                    synced = item.get("syncedLyrics")
                    if not synced:
                        continue

                    item_dur = item.get("duration", 0) or 0
                    if target_sec > 0 and item_dur > 0:
                        diff = abs(item_dur - target_sec)
                        # Pilih yang perbedaan durasinya terkecil (maksimal selisih 15 detik)
                        if diff < best_diff and diff <= 15:
                            best_diff = diff
                            best_synced = synced
                    elif best_synced is None:
                        best_synced = synced

                if best_synced:
                    app_logger.info(f"[LRCLIB] Found synced lyrics matching duration (diff={best_diff:.1f}s) for: {query}")
                    return best_synced

                # Fallback jika tidak ada yang cocok durasinya, ambil synced pertama
                for item in results:
                    if item.get("syncedLyrics"):
                        app_logger.info(f"[LRCLIB] Fallback to first synced lyrics for: {query}")
                        return item.get("syncedLyrics")

                # Fallback terakhir: plain text
                for item in results:
                    if item.get("plainLyrics"):
                        return item.get("plainLyrics")

        except Exception as e:
            app_logger.error(f"[LRCLIB] Search fallback error: {e}")

        app_logger.warning(f"[LRCLIB] No lyrics found for: {artist} - {title}")
        return None
