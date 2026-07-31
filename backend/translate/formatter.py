"""
Translation Formatter
=====================
Normalisasi dan pembersihan teks hasil terjemahan.
"""

from __future__ import annotations

import re
import unicodedata


def format_translation(text: str) -> str:
    """Bersihkan dan normalisasi hasil terjemahan."""
    if not text:
        return ""

    # Unicode normalize
    text = unicodedata.normalize("NFC", text)

    # Hapus whitespace berlebih
    text = re.sub(r"\s+", " ", text)

    # Trim
    text = text.strip()

    # Replace smart quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    return text


def check_quality(original: str, translated: str) -> bool:
    """
    Cek kualitas terjemahan.
    Return False jika terjemahan tampak gagal.
    """
    if not translated or not translated.strip():
        return False

    if translated.strip().lower() == original.strip().lower():
        return False  # Sama persis → kemungkinan gagal

    if len(translated) < 1:
        return False

    if len(translated) > len(original) * 5:
        return False  # Terlalu panjang

    return True
