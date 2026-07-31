"""
Spotify Auth
============
OAuth 2.0 Authorization Code Flow untuk Spotify.
Membuka browser untuk login, menangkap redirect dengan local HTTP server.
"""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Tuple

import requests

from backend.logger.app_logger import app_logger

# ──────────────────────────────────────────────────────────────
SCOPES = " ".join([
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-read-email",
    "user-read-private",
])

REDIRECT_URI = "http://127.0.0.1:8765/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
TIMEOUT = 120  # seconds to wait for user login


# ──────────────────────────────────────────────────────────────
# Local callback server
# ──────────────────────────────────────────────────────────────

class _CallbackHandler(BaseHTTPRequestHandler):
    """Menerima redirect dari Spotify OAuth."""
    code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            self._respond("✅ Login berhasil! Kamu bisa menutup tab ini.")
        elif "error" in params:
            _CallbackHandler.error = params["error"][0]
            self._respond("❌ Login gagal. Silakan coba lagi.")
        else:
            self._respond("⏳ Menunggu...")

    def _respond(self, message: str):
        html = f"""<html><body style="font-family:sans-serif;text-align:center;padding:60px">
        <h2>{message}</h2></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # Suppress server logs


# ──────────────────────────────────────────────────────────────
# SpotifyAuth
# ──────────────────────────────────────────────────────────────

class SpotifyAuth:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def _auth_header(self) -> dict:
        creds = f"{self._client_id}:{self._client_secret}"
        encoded = base64.b64encode(creds.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def get_auth_url(self) -> str:
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        }
        return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    def login_with_browser(self) -> Optional[Tuple[str, str, int]]:
        """
        Buka browser, tunggu callback, return (access_token, refresh_token, expires_in).
        Return None jika gagal.
        """
        _CallbackHandler.code = None
        _CallbackHandler.error = None

        server = HTTPServer(("127.0.0.1", 8765), _CallbackHandler)
        server.timeout = 1.0

        auth_url = self.get_auth_url()
        app_logger.info(f"[Auth] Opening browser: {auth_url}")
        webbrowser.open(auth_url)

        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            server.handle_request()
            if _CallbackHandler.code:
                break
            if _CallbackHandler.error:
                app_logger.error(f"[Auth] OAuth error: {_CallbackHandler.error}")
                return None

        server.server_close()

        if not _CallbackHandler.code:
            app_logger.error("[Auth] Timeout waiting for OAuth callback.")
            return None

        return self._exchange_code(_CallbackHandler.code)

    def _exchange_code(self, code: str) -> Optional[Tuple[str, str, int]]:
        """Tukar authorization code dengan token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        try:
            resp = requests.post(TOKEN_URL, data=data, headers=self._auth_header(), timeout=10)
            resp.raise_for_status()
            j = resp.json()
            app_logger.info("[Auth] Token exchange success.")
            return j["access_token"], j["refresh_token"], j["expires_in"]
        except Exception as e:
            app_logger.error(f"[Auth] Token exchange failed: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, int]]:
        """Perbarui access token menggunakan refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        try:
            resp = requests.post(TOKEN_URL, data=data, headers=self._auth_header(), timeout=10)
            resp.raise_for_status()
            j = resp.json()
            app_logger.info("[Auth] Token refreshed.")
            return j["access_token"], j["expires_in"]
        except Exception as e:
            app_logger.error(f"[Auth] Token refresh failed: {e}")
            return None
