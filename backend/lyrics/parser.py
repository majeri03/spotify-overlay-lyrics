"""
LRC Parser — Offset & Multi-Timestamp Support
==============================================
Mengubah teks LRC menjadi list SubtitleLine.
Format: [MM:SS.xx] atau [MM:SS.xxx] teks
Mendukung header [offset: +/-ms] untuk kalibrasi waktu otomatis.
"""

from __future__ import annotations

import re
from typing import List

from backend.models.models import SubtitleLine

_LRC_PATTERN = re.compile(r"^\[(\d{1,2}):(\d{2})\.(\d{2,3})\](.*)")
_OFFSET_PATTERN = re.compile(r"^\[offset:\s*([+-]?\d+)\]", re.IGNORECASE)


def parse_lrc(lrc_text: str) -> List[SubtitleLine]:
    """
    Parse teks LRC menjadi list SubtitleLine terurut berdasarkan timestamp.
    Memperhitungkan tag [offset: +/-ms] jika ada.
    """
    lines: List[SubtitleLine] = []
    raw_lines = lrc_text.splitlines()
    global_offset_ms = 0

    # 1. Cari tag [offset: ...]
    for raw in raw_lines:
        raw = raw.strip()
        m_off = _OFFSET_PATTERN.match(raw)
        if m_off:
            try:
                global_offset_ms = int(m_off.group(1))
            except ValueError:
                pass
            break

    # 2. Parse baris lirik
    for raw in raw_lines:
        raw = raw.strip()
        m = _LRC_PATTERN.match(raw)
        if not m:
            continue

        minutes = int(m.group(1))
        seconds = int(m.group(2))
        centisecs_raw = m.group(3)

        if len(centisecs_raw) == 2:
            ms = int(centisecs_raw) * 10
        else:
            ms = int(centisecs_raw)

        # Terapkan offset
        timestamp_ms = (minutes * 60 + seconds) * 1000 + ms + global_offset_ms
        timestamp_ms = max(0, timestamp_ms)
        text = m.group(4).strip()

        if not text or text.startswith("["):
            continue

        lines.append(SubtitleLine(
            index=0,
            timestamp_ms=timestamp_ms,
            end_timestamp_ms=0,
            original_text=text,
        ))

    lines.sort(key=lambda l: l.timestamp_ms)

    for i, line in enumerate(lines):
        line.index = i
        line.previous_index = i - 1 if i > 0 else -1
        line.next_index = i + 1 if i < len(lines) - 1 else -1

    return lines
