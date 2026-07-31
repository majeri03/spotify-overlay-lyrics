"""
Token Manager
=============
Mengelola OAuth token Spotify dengan enkripsi AES-256-GCM.
Token disimpan di: %LOCALAPPDATA%\\EchoLyrics\\config\\token.dat
"""

from __future__ import annotations

import base64
import json
import os
import platform
import time
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from backend.logger.app_logger import app_logger

_APP_NAME = "EchoLyrics"
_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
_CONFIG_DIR = os.path.join(_LOCAL_APPDATA, _APP_NAME, "config")
_TOKEN_FILE = os.path.join(_CONFIG_DIR, "token.dat")

# ──────────────────────────────────────────────────────────────
# Key derivation dari machine identifier
# ──────────────────────────────────────────────────────────────

def _get_machine_id() -> bytes:
    """Ambil ID unik mesin sebagai salt enkripsi."""
    try:
        import subprocess
        result = subprocess.run(
            ["wmic", "csproduct", "get", "UUID"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "UUID" not in l]
        if lines:
            return lines[0].encode("utf-8")
    except Exception:
        pass
    # Fallback: username
    return (os.environ.get("USERNAME", "echolyrics") + platform.node()).encode("utf-8")


def _derive_key(salt: bytes = b"echolyrics_salt_v1") -> bytes:
    """Derive 32-byte AES key dari machine ID."""
    machine_id = _get_machine_id()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(machine_id)


# ──────────────────────────────────────────────────────────────
# TokenManager
# ──────────────────────────────────────────────────────────────

class TokenManager:
    """Menyimpan dan memuat Spotify OAuth token dengan enkripsi."""

    def __init__(self) -> None:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        self._key = _derive_key()
        self._aesgcm = AESGCM(self._key)
        self._token_data: Optional[dict] = None

    # ── Encrypt / Decrypt ──────────────────────────────────────

    def _encrypt(self, data: dict) -> bytes:
        nonce = os.urandom(12)
        plaintext = json.dumps(data).encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        # Simpan nonce + ciphertext
        return base64.b64encode(nonce + ciphertext)

    def _decrypt(self, blob: bytes) -> Optional[dict]:
        try:
            raw = base64.b64decode(blob)
            nonce = raw[:12]
            ciphertext = raw[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode("utf-8"))
        except Exception as e:
            app_logger.error(f"[TokenManager] Decrypt failed: {e}")
            return None

    # ── Save / Load ────────────────────────────────────────────

    def save(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in,
        }
        encrypted = self._encrypt(data)
        with open(_TOKEN_FILE, "wb") as f:
            f.write(encrypted)
        self._token_data = data
        app_logger.info("[TokenManager] Token saved (encrypted).")

    def load(self) -> Optional[dict]:
        if self._token_data:
            return self._token_data
        if not os.path.exists(_TOKEN_FILE):
            return None
        with open(_TOKEN_FILE, "rb") as f:
            blob = f.read()
        data = self._decrypt(blob)
        self._token_data = data
        return data

    def clear(self) -> None:
        self._token_data = None
        if os.path.exists(_TOKEN_FILE):
            os.remove(_TOKEN_FILE)

    # ── Validation ─────────────────────────────────────────────

    def is_valid(self) -> bool:
        data = self.load()
        if not data:
            return False
        return time.time() < data.get("expires_at", 0) - 60  # 60s buffer

    def get_access_token(self) -> Optional[str]:
        data = self.load()
        return data.get("access_token") if data else None

    def get_refresh_token(self) -> Optional[str]:
        data = self.load()
        return data.get("refresh_token") if data else None

    def is_expired(self) -> bool:
        data = self.load()
        if not data:
            return True
        return time.time() >= data.get("expires_at", 0) - 60
