"""
Google Translate Provider (GTX Free Endpoint) — Batch Mode
===========================================================
Mengirim SEMUA baris sekaligus dalam 1 request HTTP menggunakan separator khusus.
Jauh lebih cepat dan stabil dibanding 1 request per baris.

Teknik: gabungkan semua teks dengan separator unik, kirim 1x, parse hasilnya.
"""

from __future__ import annotations

import requests
from typing import List

from backend.translate.providers.base_provider import BaseTranslationProvider
from backend.logger.app_logger import app_logger

_URL     = "https://translate.googleapis.com/translate_a/single"
_TIMEOUT = 10
# Separator unik yang sangat tidak mungkin ada di dalam lirik
_SEP     = " ||||| "


class GoogleTranslateProvider(BaseTranslationProvider):
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    @property
    def name(self) -> str:
        return "GoogleTranslate"

    def initialize(self) -> bool:
        return True

    def translate(
        self,
        texts: List[str],
        source_lang: str = "en",
        target_lang: str = "id"
    ) -> List[str]:
        """
        Terjemahkan semua teks dalam SATU request HTTP.
        Jauh lebih cepat dan stabil vs satu-per-satu.
        """
        if not texts:
            return []

        # Filter teks kosong, catat posisinya
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts   = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts[:]   # Semua kosong, kembalikan apa adanya

        # Gabungkan dengan separator unik
        combined = _SEP.join(non_empty_texts)

        translated_parts = self._translate_batch(combined, source_lang, target_lang)

        # Susun kembali ke posisi asli
        results = list(texts)  # copy
        if translated_parts and len(translated_parts) == len(non_empty_texts):
            for idx, trans in zip(non_empty_indices, translated_parts):
                results[idx] = trans.strip() if trans.strip() else texts[idx]
        else:
            # Fallback: jika parse gagal, kembalikan teks asli
            app_logger.warning("[GoogleTranslate] Batch parse mismatch, returning originals.")

        return results

    def _translate_batch(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> List[str]:
        """Kirim 1 request dan pecah hasilnya kembali."""
        try:
            params = {
                "client": "gtx",
                "sl":     source_lang,
                "tl":     target_lang,
                "dt":     "t",
                "q":      text,
            }
            resp = self._session.get(_URL, params=params, timeout=_TIMEOUT)

            if resp.status_code != 200:
                app_logger.warning(f"[GoogleTranslate] HTTP {resp.status_code}")
                return []

            data = resp.json()
            if not data or not data[0]:
                return []

            # Gabungkan semua segmen hasil terjemahan
            raw = "".join(
                seg[0] for seg in data[0]
                if seg and seg[0]
            )

            # Pecah kembali berdasarkan separator
            # Separator bisa berubah sedikit oleh Google (spasi berbeda), pakai variasi
            for sep_variant in [_SEP, " ||| || ||| ", "||||| ", " |||||"]:
                parts = raw.split(sep_variant)
                if len(parts) > 1:
                    return parts

            # Jika separator tidak ditemukan, mungkin hanya 1 baris
            return [raw]

        except Exception as e:
            app_logger.warning(f"[GoogleTranslate] Batch error: {e}")
            return []
