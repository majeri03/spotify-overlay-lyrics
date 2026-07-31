"""
Data Models
===========
Seluruh data object yang digunakan di EchoLyrics.
Tidak ada logic bisnis di sini — hanya struktur data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ──────────────────────────────────────────────────────────────
# Playback Models
# ──────────────────────────────────────────────────────────────

class PlaybackState(str, Enum):
    STOPPED         = "STOPPED"
    PLAYING         = "PLAYING"
    PAUSED          = "PAUSED"
    BUFFERING       = "BUFFERING"
    SEEKING         = "SEEKING"
    CHANGING_TRACK  = "CHANGING_TRACK"
    LOADING         = "LOADING"
    UNKNOWN         = "UNKNOWN"
    ERROR           = "ERROR"


@dataclass
class TrackInfo:
    """Informasi lagu dari Spotify."""
    spotify_id: str
    title: str
    artist: str
    album: str
    duration_ms: int
    isrc: str = ""
    image_url: str = ""
    language: str = ""
    explicit: bool = False

    @property
    def duration_sec(self) -> float:
        return self.duration_ms / 1000.0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrackInfo):
            return False
        return self.spotify_id == other.spotify_id

    def __hash__(self):
        return hash(self.spotify_id)


@dataclass
class PlaybackInfo:
    """Status playback Spotify saat ini."""
    track: Optional[TrackInfo] = None
    progress_ms: int = 0
    state: PlaybackState = PlaybackState.UNKNOWN
    device_name: str = ""
    device_id: str = ""
    timestamp: float = 0.0          # time.time() saat data diambil

    @property
    def progress_sec(self) -> float:
        return self.progress_ms / 1000.0


# ──────────────────────────────────────────────────────────────
# Subtitle / Lyrics Models
# ──────────────────────────────────────────────────────────────

class SubtitleState(str, Enum):
    UPCOMING = "UPCOMING"
    ACTIVE   = "ACTIVE"
    RECENT   = "RECENT"
    FINISHED = "FINISHED"


@dataclass
class SubtitleLine:
    """Satu baris subtitle dari LRC file."""
    index: int
    timestamp_ms: int           # Waktu mulai (ms)
    end_timestamp_ms: int       # Waktu selesai (ms)
    original_text: str
    translated_text: str = ""
    duration_ms: int = 0
    previous_index: int = -1
    next_index: int = -1
    state: SubtitleState = SubtitleState.UPCOMING

    @property
    def timestamp_sec(self) -> float:
        return self.timestamp_ms / 1000.0

    @property
    def end_timestamp_sec(self) -> float:
        return self.end_timestamp_ms / 1000.0


@dataclass
class TrackTimeline:
    """Timeline subtitle untuk satu lagu."""
    track: TrackInfo
    lines: List[SubtitleLine] = field(default_factory=list)
    is_complete: bool = False       # True jika translation sudah ada

    def __len__(self) -> int:
        return len(self.lines)


@dataclass
class SubtitleQueue:
    """Queue tiga subtitle: previous, current, next."""
    previous: Optional[SubtitleLine] = None
    current: Optional[SubtitleLine] = None
    next: Optional[SubtitleLine] = None
    animation_state: str = "idle"
    transition_progress: float = 0.0
    current_index: int = -1


# ──────────────────────────────────────────────────────────────
# Translation Models
# ──────────────────────────────────────────────────────────────

class ValidationResult(str, Enum):
    VALID   = "VALID"
    INVALID = "INVALID"
    PARTIAL = "PARTIAL"


@dataclass
class TranslationResult:
    """Hasil satu baris terjemahan."""
    original: str
    translated: str
    language: str           # ISO code, e.g. "id"
    confidence: float = 1.0
    provider: str = ""
    created_at: float = 0.0


# ──────────────────────────────────────────────────────────────
# Language Model
# ──────────────────────────────────────────────────────────────

@dataclass
class LanguageInfo:
    iso_code: str
    confidence: float
    provider: str = "langdetect"
    detected_time: float = 0.0
