"""
Language Detector
=================
Mendeteksi bahasa dari teks menggunakan langdetect.

Perubahan: threshold dinaikkan ke 0.95 dan logika diperbaiki agar
tidak salah-skip lagu Inggris yang terdeteksi sebagai Indonesia.
"""

from __future__ import annotations

import time
from typing import Optional

from backend.models.models import LanguageInfo
from backend.logger.app_logger import app_logger

_SAMPLE_CHARS = 300   # Ambil lebih banyak karakter untuk deteksi lebih akurat
# Hanya skip terjemahan jika SANGAT yakin (95%) bahwa sudah bahasa target
_SKIP_THRESHOLD = 0.95


def detect_language(text: str) -> LanguageInfo:
    """
    Deteksi bahasa dari teks.
    Return LanguageInfo dengan iso_code dan confidence.
    """
    sample = text[:_SAMPLE_CHARS].strip()
    if not sample:
        return LanguageInfo(iso_code="unknown", confidence=0.0)

    try:
        from langdetect import detect_langs
        results = detect_langs(sample)
        if results:
            best = results[0]
            return LanguageInfo(
                iso_code=best.lang,
                confidence=best.prob,
                provider="langdetect",
                detected_time=time.time(),
            )
    except Exception as e:
        app_logger.warning(f"[LanguageDetector] Error: {e}")

    # Fallback: asumsikan English agar terjemahan tetap berjalan
    return LanguageInfo(iso_code="en", confidence=0.5, provider="fallback")


def is_already_target(lang_info: LanguageInfo, target: str = "id") -> bool:
    """
    Cek apakah teks sudah dalam bahasa target (tidak perlu terjemahan).

    Hanya return True jika:
    - Bahasa terdeteksi SAMA dengan target (id)
    - Confidence sangat tinggi (>= 95%)

    Ini mencegah lagu Inggris yang "mirip" kata Indonesia terlewat terjemahan.
    """
    is_target = lang_info.iso_code == target
    is_confident = lang_info.confidence >= _SKIP_THRESHOLD
    result = is_target and is_confident
    if result:
        app_logger.info(
            f"[LanguageDetector] Skip translation: already {target} "
            f"(conf={lang_info.confidence:.2f})"
        )
    return result
