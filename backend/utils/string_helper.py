"""
String Utilities
"""

import re


def clean_text(text: str) -> str:
    """Bersihkan teks dari karakter tidak diperlukan."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def truncate(text: str, max_len: int = 60) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def normalize_artist_name(artist: str) -> str:
    """Normalisasi nama artis untuk pencarian."""
    return artist.lower().strip()
