"""
Spotify Client
==============
HTTP wrapper untuk Spotify Web API.
Menangani retry, timeout, dan error mapping.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from backend.logger.app_logger import app_logger

_BASE_URL = "https://api.spotify.com/v1"
_TIMEOUT = 5       # seconds
_RETRY_COUNT = 3


class SpotifyAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"[{status_code}] {message}")


class TokenExpiredException(SpotifyAPIError): pass
class RateLimitException(SpotifyAPIError): pass
class SpotifyUnavailableException(SpotifyAPIError): pass


class SpotifyClient:
    """
    Thin HTTP client untuk Spotify API.
    Tidak memiliki business logic — hanya HTTP + retry.
    """

    def __init__(self, access_token_getter) -> None:
        """
        access_token_getter: callable yang mengembalikan access token terkini.
        """
        self._get_token = access_token_getter
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Lakukan GET request ke Spotify API dengan retry.
        Return JSON dict atau None jika gagal.
        """
        url = f"{_BASE_URL}{endpoint}"
        delay = 1.0

        for attempt in range(_RETRY_COUNT):
            try:
                resp = self._session.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=_TIMEOUT
                )

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 204:
                    return {}  # No content (valid)

                if resp.status_code == 401:
                    raise TokenExpiredException(401, "Token expired")

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2))
                    app_logger.warning(f"[SpotifyClient] Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                if resp.status_code in (500, 502, 503):
                    raise SpotifyUnavailableException(resp.status_code, "Spotify unavailable")

                if resp.status_code == 403:
                    app_logger.debug("[SpotifyClient] HTTP 403 Forbidden (Spotify Free) — Using Windows Media Provider.")
                    return None

                app_logger.warning(f"[SpotifyClient] HTTP {resp.status_code}: {endpoint}")
                return None

            except TokenExpiredException:
                raise
            except (requests.Timeout, requests.ConnectionError) as e:
                app_logger.warning(f"[SpotifyClient] Attempt {attempt+1} failed: {e}")
                if attempt < _RETRY_COUNT - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        app_logger.error(f"[SpotifyClient] All retries failed for {endpoint}")
        return None
