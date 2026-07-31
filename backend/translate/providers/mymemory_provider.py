"""
MyMemory Translation Provider (Fallback)
=========================================
Provider cadangan gratis dari mymemory.translated.net.
Dipakai saat Google Translate GTX gagal/rate limited.

Keunggulan:
- Gratis tanpa API key (5.000 kata/hari tanpa registrasi)
- Dengan email gratis: 10.000 kata/hari
- Batch support: kirim semua teks sekaligus
- Sangat stabil, jarang down
"""

from __future__ import annotations

import requests
from typing import List

from backend.translate.providers.base_provider import BaseTranslationProvider
from backend.logger.app_logger import app_logger

_URL     = "https://api.mymemory.translated.net/get"
_TIMEOUT = 8
_SEP     = " ||||| "   # Separator sama dengan Google provider


class MyMemoryProvider(BaseTranslationProvider):
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    @property
    def name(self) -> str:
        return "MyMemory"

    def initialize(self) -> bool:
        return True

    def translate(
        self,
        texts: List[str],
        source_lang: str = "en",
        target_lang: str = "id"
    ) -> List[str]:
        """
        Terjemahkan semua teks dalam satu batch.
        MyMemory support hingga 500 karakter per request, jadi bagi jika perlu.
        """
        if not texts:
            return []

        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts   = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts[:]

        # MyMemory lebih baik diterjemahkan per-batch kecil (max ~200 char per request)
        results = list(texts)
        translated = self._translate_in_chunks(non_empty_texts, source_lang, target_lang)

        for idx, trans in zip(non_empty_indices, translated):
            if trans and trans.strip():
                results[idx] = trans.strip()

        return results

    def _translate_in_chunks(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        chunk_size: int = 10
    ) -> List[str]:
        """Terjemahkan dalam kelompok kecil untuk menghindari limit per-request."""
        all_results = []
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            combined = _SEP.join(chunk)

            try:
                params = {
                    "q":       combined,
                    "langpair": f"{source_lang}|{target_lang}",
                }
                resp = self._session.get(_URL, params=params, timeout=_TIMEOUT)

                if resp.status_code != 200:
                    app_logger.warning(f"[MyMemory] HTTP {resp.status_code}")
                    all_results.extend(chunk)   # fallback: kembalikan asli
                    continue

                data = resp.json()
                translated_text = data.get("responseData", {}).get("translatedText", "")

                if not translated_text:
                    all_results.extend(chunk)
                    continue

                # Coba pisahkan kembali dengan separator
                parts = None
                for sep_variant in [_SEP, " ||| || ||| ", "||||| ", " |||||"]:
                    split = translated_text.split(sep_variant)
                    if len(split) == len(chunk):
                        parts = split
                        break

                if parts:
                    all_results.extend(parts)
                else:
                    # Jika gagal pisah, terjemahkan satu per satu sebagai last resort
                    for text in chunk:
                        single = self._translate_single(text, source_lang, target_lang)
                        all_results.append(single)

            except Exception as e:
                app_logger.warning(f"[MyMemory] Chunk error: {e}")
                all_results.extend(chunk)   # fallback: kembalikan teks asli

        return all_results

    def _translate_single(self, text: str, source_lang: str, target_lang: str) -> str:
        """Terjemahkan satu teks, dipakai sebagai last resort."""
        try:
            params = {
                "q":        text,
                "langpair": f"{source_lang}|{target_lang}",
            }
            resp = self._session.get(_URL, params=params, timeout=_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("responseData", {}).get("translatedText", text)
        except Exception:
            pass
        return text
