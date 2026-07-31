"""
Event Types
===========
Daftar seluruh event yang digunakan oleh EchoLyrics.
Seluruh komunikasi antar modul melalui Event Bus menggunakan konstanta ini.
"""

from enum import Enum, auto


class EventType(str, Enum):
    # ── Spotify Events ─────────────────────────────────────
    TRACK_CHANGED       = "TRACK_CHANGED"
    TRACK_PAUSED        = "TRACK_PAUSED"
    TRACK_RESUMED       = "TRACK_RESUMED"
    TRACK_SEEKED        = "TRACK_SEEKED"
    TRACK_ENDED         = "TRACK_ENDED"
    SPOTIFY_CONNECTED   = "SPOTIFY_CONNECTED"
    SPOTIFY_DISCONNECTED= "SPOTIFY_DISCONNECTED"
    SPOTIFY_WAITING     = "SPOTIFY_WAITING"
    SPOTIFY_ERROR       = "SPOTIFY_ERROR"
    PLAYBACK_UPDATED    = "PLAYBACK_UPDATED"   # Dipanggil tiap poll (sync posisi)

    # ── Lyrics Events ──────────────────────────────────────
    LYRICS_FOUND        = "LYRICS_FOUND"
    LYRICS_NOT_FOUND    = "LYRICS_NOT_FOUND"
    LYRICS_FAILED       = "LYRICS_FAILED"
    TRACK_LOADED        = "TRACK_LOADED"
    TIMELINE_READY      = "TIMELINE_READY"
    QUEUE_UPDATED       = "QUEUE_UPDATED"
    CURRENT_CHANGED     = "CURRENT_CHANGED"
    SUBTITLE_FINISHED   = "SUBTITLE_FINISHED"
    TIMELINE_RESET      = "TIMELINE_RESET"
    LYRICS_RELOADED     = "LYRICS_RELOADED"

    # ── Cache Events ───────────────────────────────────────
    CACHE_HIT           = "CACHE_HIT"
    CACHE_MISS          = "CACHE_MISS"

    # ── Translation Events ─────────────────────────────────
    TRANSLATION_STARTED = "TRANSLATION_STARTED"
    TRANSLATION_READY   = "TRANSLATION_READY"
    TRANSLATION_FAILED  = "TRANSLATION_FAILED"
    TRANSLATION_FINISHED= "TRANSLATION_FINISHED"
    PROVIDER_CHANGED    = "PROVIDER_CHANGED"
    QUALITY_WARNING     = "QUALITY_WARNING"

    # ── Overlay Events ─────────────────────────────────────
    OVERLAY_SHOW        = "OVERLAY_SHOW"
    OVERLAY_HIDE        = "OVERLAY_HIDE"
    SUBTITLE_CHANGED    = "SUBTITLE_CHANGED"
    ANIMATION_STARTED   = "ANIMATION_STARTED"
    ANIMATION_FINISHED  = "ANIMATION_FINISHED"
    THEME_CHANGED       = "THEME_CHANGED"
    FONT_CHANGED        = "FONT_CHANGED"
    POSITION_CHANGED    = "POSITION_CHANGED"
    MONITOR_CHANGED     = "MONITOR_CHANGED"
    CLICKTHROUGH_CHANGED= "CLICKTHROUGH_CHANGED"

    # ── UI / Settings ──────────────────────────────────────
    SHOW_PANEL          = "SHOW_PANEL"
    SETTINGS_CHANGED    = "SETTINGS_CHANGED"
    DISPLAY_SUBTITLE    = "DISPLAY_SUBTITLE"

    # ── Application ────────────────────────────────────────
    APPLICATION_START   = "APPLICATION_START"
    APPLICATION_EXIT    = "APPLICATION_EXIT"
    APPLICATION_WAITING = "APPLICATION_WAITING"
