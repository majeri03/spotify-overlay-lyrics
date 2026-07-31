"""
LRC Parser
==========
Mengubah teks LRC menjadi list SubtitleLine.
Format: [MM:SS.xx] atau [MM:SS.xxx] teks
"""

from __future__ import annotations

import re
from typing import List, Optional

from backend.models.models import SubtitleLine

_LRC_PATTERN = re.compile(r"^\[(\d{1,2}):(\d{2})\.(\d{2,3})\](.*)")


def parse_lrc(lrc_text: str) -> List[SubtitleLine]:
    """
    Parse teks LRC menjadi list SubtitleLine terurut berdasarkan timestamp.
    """
    lines: List[SubtitleLine] = []
    raw_lines = lrc_text.splitlines()

    for raw in raw_lines:
        raw = raw.strip()
        m = _LRC_PATTERN.match(raw)
        if not m:
            continue
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        centisecs_raw = m.group(3)
        # Normalisasi ke milidetik
        if len(centisecs_raw) == 2:
            ms = int(centisecs_raw) * 10
        else:
            ms = int(centisecs_raw)

        timestamp_ms = (minutes * 60 + seconds) * 1000 + ms
        text = m.group(4).strip()

        # Skip metadata lines seperti [ar:Artist] dsb
        if not text or text.startswith("["):
            continue

        lines.append(SubtitleLine(
            index=0,  # akan di-set ulang
            timestamp_ms=timestamp_ms,
            end_timestamp_ms=0,  # akan dihitung oleh TimelineEngine
            original_text=text,
        ))

    # Sort berdasarkan timestamp
    lines.sort(key=lambda l: l.timestamp_ms)

    # Set index dan end_timestamp
    for i, line in enumerate(lines):
        line.index = i
        line.previous_index = i - 1 if i > 0 else -1
        line.next_index = i + 1 if i < len(lines) - 1 else -1

    return lines
