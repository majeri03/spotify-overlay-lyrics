"""
Hash Utilities
==============
SHA256 cache key generator berdasarkan artist + title + duration.
"""

import hashlib


def make_cache_key(artist: str, title: str, duration_ms: int) -> str:
    """Generate SHA256 cache key untuk track."""
    raw = f"{artist.lower().strip()}|{title.lower().strip()}|{duration_ms}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_lyrics_hash(lyrics_lines: list[str]) -> str:
    """Generate hash dari semua baris lirik."""
    combined = "\n".join(l.strip() for l in lyrics_lines)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def make_translation_cache_key(
    artist: str, title: str, duration_ms: int, lyrics_hash: str
) -> str:
    """Cache key untuk translation — lebih spesifik dari track key."""
    raw = f"{artist.lower().strip()}|{title.lower().strip()}|{duration_ms}|{lyrics_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
