"""
Lyrics Validator
================
Memvalidasi hasil parsing LRC sebelum digunakan.
"""

from __future__ import annotations

from typing import List

from backend.models.models import SubtitleLine, ValidationResult
from backend.logger.app_logger import app_logger

_MIN_LINES = 5
_MAX_FIRST_TIMESTAMP_SEC = 30.0
_MAX_CONSECUTIVE_EMPTY = 3


def validate_lyrics(
    lines: List[SubtitleLine],
    duration_ms: int = 0
) -> ValidationResult:
    """
    Validasi list SubtitleLine.
    Return VALID, PARTIAL, atau INVALID.
    """
    if not lines:
        app_logger.warning("[Validator] Empty lyrics.")
        return ValidationResult.INVALID

    if len(lines) < _MIN_LINES:
        app_logger.warning(f"[Validator] Too few lines: {len(lines)}")
        return ValidationResult.INVALID

    # Timestamp pertama terlalu jauh?
    if lines[0].timestamp_ms / 1000.0 > _MAX_FIRST_TIMESTAMP_SEC:
        app_logger.warning(f"[Validator] First timestamp too late: {lines[0].timestamp_ms}ms")
        return ValidationResult.PARTIAL

    # Timestamp mundur?
    for i in range(1, len(lines)):
        if lines[i].timestamp_ms < lines[i-1].timestamp_ms:
            app_logger.warning(f"[Validator] Timestamp goes backward at index {i}")
            return ValidationResult.PARTIAL

    # Timestamp negatif?
    for line in lines:
        if line.timestamp_ms < 0:
            app_logger.warning("[Validator] Negative timestamp found.")
            return ValidationResult.INVALID

    # Durasi check
    if duration_ms > 0:
        last_ts = lines[-1].timestamp_ms
        if last_ts > duration_ms + 5000:  # 5s tolerance
            app_logger.warning(f"[Validator] Last timestamp {last_ts}ms exceeds duration {duration_ms}ms")
            return ValidationResult.PARTIAL

    return ValidationResult.VALID
