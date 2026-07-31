"""
LRCLIB Provider
===============
Mengambil lirik dari LRCLIB API (https://lrclib.net).
Dilengkapi dengan Smart Cleaner & Search Fallback untuk judul/artis ber-feat/koma.
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests

from backend.logger.app_logger import app_logger

_BASE_URL = "https://lrclib.net/api"
_TIMEOUT = 8
_RETRY = 2


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
    """Provider lirik dari LRCLIB.net."""

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
        Return teks LRC atau None jika tidak ditemukan.
        """
        # 1. Coba exact match terlebih dahulu
        params = {
            "artist_name": artist,
            "track_name": title,
        }
        if duration_ms > 0:
            params["duration"] = duration_ms // 1000
        if album:
            params["album_name"] = album

        try:
            resp = self._session.get(f"{_BASE_URL}/get", params=params, timeout=_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics") or data.get("plainLyrics")
                if synced:
                    app_logger.info(f"[LRCLIB] Found exact lyrics for: {artist} - {title}")
                    return synced
        except Exception:
            pass

        # 2. Fallback: Smart Clean + Search API
        clean_art = _clean_artist(artist)
        clean_ti = _clean_title(title)
        query = f"{clean_art} {clean_ti}".strip()

        app_logger.info(f"[LRCLIB] Exact match failed. Smart Search query: '{query}'...")

        try:
            resp = self._session.get(f"{_BASE_URL}/search", params={"q": query}, timeout=_TIMEOUT)
            if resp.status_code == 200:
                results = resp.json()
                # Prioritaskan syncedLyrics
                for item in results:
                    synced = item.get("syncedLyrics")
                    if synced:
                        app_logger.info(f"[LRCLIB] Found synced lyrics via Search for: {query}")
                        return synced
                # Second pass: plain lyrics
                for item in results:
                    plain = item.get("plainLyrics")
                    if plain:
                        app_logger.info(f"[LRCLIB] Found plain lyrics via Search for: {query}")
                        return plain
        except Exception as e:
            app_logger.error(f"[LRCLIB] Search fallback error: {e}")

        app_logger.warning(f"[LRCLIB] No lyrics found for: {artist} - {title}")
        return None

    def search(self, query: str) -> list:
        try:
            resp = self._session.get(f"{_BASE_URL}/search", params={"q": query}, timeout=_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []
