"""
LibreTranslate Provider
=======================
Free, self-hostable translation provider.
Default endpoint: https://libretranslate.com
"""

from __future__ import annotations

import time
from typing import List, Optional

import requests

from backend.translate.providers.base_provider import BaseTranslationProvider
from backend.logger.app_logger import app_logger

_DEFAULT_URL = "https://libretranslate.com"
_TIMEOUT = 30


class LibreTranslateProvider(BaseTranslationProvider):
    name = "libretranslate"

    def __init__(
        self,
        api_url: str = _DEFAULT_URL,
        api_key: str = ""
    ) -> None:
        self._url = api_url.rstrip("/")
        self._api_key = api_key
        self._session = requests.Session()

    def initialize(self) -> bool:
        return self.health_check()

    def health_check(self) -> bool:
        try:
            resp = self._session.get(f"{self._url}/languages", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def translate(
        self,
        texts: List[str],
        source_lang: str = "en",
        target_lang: str = "id"
    ) -> List[str]:
        """
        Terjemahkan batch teks menggunakan LibreTranslate.
        Kirim satu per satu karena LibreTranslate tidak selalu support batch.
        """
        results = []
        for text in texts:
            translated = self._translate_one(text, source_lang, target_lang)
            results.append(translated or text)
        return results

    def _translate_one(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[str]:
        if not text.strip():
            return text

        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if self._api_key:
            payload["api_key"] = self._api_key

        try:
            resp = self._session.post(
                f"{self._url}/translate",
                json=payload,
                timeout=_TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("translatedText", text)
            else:
                app_logger.warning(f"[LibreTranslate] HTTP {resp.status_code}")
        except Exception as e:
            app_logger.error(f"[LibreTranslate] Error: {e}")
        return None
