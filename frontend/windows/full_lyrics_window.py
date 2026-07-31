"""
Full Lyrics Window
==================
Jendela lengkap menampilkan semua lirik dengan auto-scroll.
Dibuka via shortcut Ctrl+Shift+L atau System Tray.
"""

from __future__ import annotations

from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from backend.models.models import SubtitleLine, TrackInfo, TrackTimeline
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.logger.app_logger import app_logger

_BG       = "#0d0d1a"
_CARD     = "#13131f"
_ACCENT   = "#e94560"
_TEXT     = "#ffffff"
_TEXT_DIM = "#6b6b8a"
_ACTIVE   = "#e94560"

_STYLESHEET = f"""
QDialog {{
    background: {_BG};
    color: {_TEXT};
    font-family: 'Segoe UI', Inter, sans-serif;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QLabel#lbl_track {{
    font-size: 18px;
    font-weight: bold;
    color: {_TEXT};
}}
QLabel#lbl_artist {{
    font-size: 13px;
    color: {_TEXT_DIM};
}}
QPushButton {{
    background: transparent;
    color: {_TEXT_DIM};
    border: 1px solid #33334a;
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    color: {_TEXT};
    border-color: {_ACCENT};
}}
"""


class LyricsLineWidget(QLabel):
    def __init__(self, line: SubtitleLine, parent=None):
        super().__init__(parent)
        self._line = line
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._is_active = False
        self._update_style()

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self._update_style()

    def _update_style(self) -> None:
        if self._is_active:
            self.setStyleSheet(
                f"color: {_ACTIVE}; font-size: 16px; font-weight: bold; "
                f"padding: 8px 24px; background: #1a0a10; border-radius: 6px;"
            )
        else:
            self.setStyleSheet(
                f"color: {_TEXT_DIM}; font-size: 14px; font-weight: normal; "
                f"padding: 6px 24px;"
            )

        # Tampilkan terjemahan jika ada
        if self._line.translated_text:
            self.setText(
                f"{self._line.original_text}\n"
                f"<small>{self._line.translated_text}</small>"
            )
            self.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.setText(self._line.original_text)


class FullLyricsWindow(QDialog):
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._bus = event_bus
        self._line_widgets: List[LyricsLineWidget] = []
        self._current_index: int = -1
        self._auto_scroll = True

        self.setWindowTitle("EchoLyrics — Full Lyrics")
        self.setMinimumSize(480, 600)
        self.setStyleSheet(_STYLESHEET)
        self._build_ui()
        self._subscribe()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"background: {_CARD}; padding: 16px;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        self.lbl_track = QLabel("No track playing")
        self.lbl_track.setObjectName("lbl_track")
        self.lbl_artist = QLabel("")
        self.lbl_artist.setObjectName("lbl_artist")
        header_layout.addWidget(self.lbl_track)
        header_layout.addWidget(self.lbl_artist)
        layout.addWidget(header)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 8, 16, 8)
        self.btn_autoscroll = QPushButton("Auto-scroll: ON")
        self.btn_autoscroll.clicked.connect(self._toggle_autoscroll)
        btn_row.addWidget(self.btn_autoscroll)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Lyrics scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._lyrics_container = QWidget()
        self._lyrics_layout = QVBoxLayout(self._lyrics_container)
        self._lyrics_layout.setContentsMargins(0, 16, 0, 80)
        self._lyrics_layout.setSpacing(4)
        self._lyrics_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._lyrics_container)
        layout.addWidget(self._scroll, 1)

    def _subscribe(self) -> None:
        self._bus.subscribe(EventType.TIMELINE_READY, self._on_timeline_ready)
        self._bus.subscribe(EventType.QUEUE_UPDATED, self._on_queue_updated)
        self._bus.subscribe(EventType.TRACK_CHANGED, self._on_track_changed)

    def _on_track_changed(self, playback) -> None:
        if playback and playback.track:
            self.lbl_track.setText(playback.track.title)
            self.lbl_artist.setText(playback.track.artist)
        self._clear_lyrics()

    def _on_timeline_ready(self, timeline: Optional[TrackTimeline]) -> None:
        if not timeline:
            return
        self._build_lyrics_ui(timeline.lines)

    def _on_queue_updated(self, queue) -> None:
        if not queue or not queue.current:
            return
        idx = queue.current_index
        self._highlight(idx)

    def _clear_lyrics(self) -> None:
        for w in self._line_widgets:
            w.deleteLater()
        self._line_widgets.clear()
        self._current_index = -1

    def _build_lyrics_ui(self, lines: List[SubtitleLine]) -> None:
        self._clear_lyrics()
        for line in lines:
            w = LyricsLineWidget(line)
            self._lyrics_layout.addWidget(w)
            self._line_widgets.append(w)

    def _highlight(self, index: int) -> None:
        if index == self._current_index:
            return
        # Deactivate previous
        if 0 <= self._current_index < len(self._line_widgets):
            self._line_widgets[self._current_index].set_active(False)
        # Activate new
        self._current_index = index
        if 0 <= index < len(self._line_widgets):
            self._line_widgets[index].set_active(True)
            if self._auto_scroll:
                self._scroll_to(index)

    def _scroll_to(self, index: int) -> None:
        widget = self._line_widgets[index]
        self._scroll.ensureWidgetVisible(widget, 0, 100)

    def _toggle_autoscroll(self) -> None:
        self._auto_scroll = not self._auto_scroll
        state = "ON" if self._auto_scroll else "OFF"
        self.btn_autoscroll.setText(f"Auto-scroll: {state}")
