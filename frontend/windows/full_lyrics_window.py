"""
Full Lyrics Window — Clean Apple Music Floating Lyrics
======================================================
- Clean floating text, TANPA kotak/pill/border di baris aktif.
- Baris aktif: Putih terang #FFFFFF (22px Bold), terjemahan emas #FFE066 di bawahnya.
- Baris tidak aktif: Tersusun bersih, tidak terlalu gelap.
- Scroll presisi: Baris aktif otomatis diposisikan tepat di 1/3 viewport.
- Header: Banner album art + 3-bar live equalizer.
"""

from __future__ import annotations

import random
import urllib.request
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame, QSizePolicy, QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QRect, QSize, QRectF, QThread, QObject, Slot
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush,
    QPainterPath, QCursor, QPen, QPixmap, QImage, QRadialGradient
)

from backend.models.models import SubtitleLine, TrackTimeline, SubtitleQueue, TrackInfo
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType


# ──────────────────────────────────────────────────────────────
# Album Art Loader
# ──────────────────────────────────────────────────────────────

class _AlbumArtLoader(QThread):
    loaded = Signal(QImage)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "EchoLyrics/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            img = QImage()
            img.loadFromData(data)
            if not img.isNull():
                self.loaded.emit(img)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
# Equalizer Widget
# ──────────────────────────────────────────────────────────────

class _EqualizerWidget(QWidget):
    """3 bar animasi naik turun."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 14)
        self._heights = [0.4, 0.7, 0.5]
        self._targets = [0.8, 0.4, 0.9]
        self._playing = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        if not playing:
            self._heights = [0.25, 0.25, 0.25]
        self.update()

    def _tick(self) -> None:
        if not self._playing:
            return
        for i in range(3):
            diff = self._targets[i] - self._heights[i]
            self._heights[i] += diff * 0.35
            if abs(diff) < 0.05:
                self._targets[i] = random.uniform(0.2, 1.0)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = 3
        gap   = 2
        total_w = 3 * bar_w + 2 * gap
        start_x = (w - total_w) // 2

        for i, frac in enumerate(self._heights):
            bh = max(2, int(frac * h))
            bx = start_x + i * (bar_w + gap)
            by = h - bh

            grad = QLinearGradient(bx, by, bx, h)
            grad.setColorAt(0.0, QColor(200, 160, 255))
            grad.setColorAt(1.0, QColor(124,  77, 255))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bx, by, bar_w, bh, 1, 1)

        p.end()


# ──────────────────────────────────────────────────────────────
# Lyrics Line Widget — Floating Text Clean (Tanpa Kotak/Border)
# ──────────────────────────────────────────────────────────────

class LyricsLineWidget(QWidget):
    """
    Teks lirik melayang bersih Apple Music style.
    Tanpa kotak/pill/border di sekeliling teks aktif.
    """

    def __init__(self, line: SubtitleLine, parent=None):
        super().__init__(parent)
        self._line   = line
        self._active = False
        self._near   = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._font_active = QFont("Segoe UI, Inter", 22, QFont.Weight.Bold)
        self._font_near   = QFont("Segoe UI, Inter", 19, QFont.Weight.Medium)
        self._font_far    = QFont("Segoe UI, Inter", 18, QFont.Weight.Normal)
        self._font_trans  = QFont("Segoe UI, Inter", 15, QFont.Weight.Medium)

    def update_content(self, line: SubtitleLine) -> None:
        self._line = line
        self.update()
        self.updateGeometry()

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()
            self.updateGeometry()

    def set_near(self, near: bool) -> None:
        if self._near != near:
            self._near = near
            self.update()
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        """Hitung tinggi secara dinamis berdasarkan actual text metrics."""
        from PySide6.QtGui import QFontMetrics
        flags = int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft)
        # Gunakan lebar yang lebih realistis (min 300px)
        text_w = max(300, self.width() - 40) if self.width() > 0 else 360
        orig  = self._line.original_text or ""
        trans = self._line.translated_text or ""

        if self._active:
            fm = QFontMetrics(self._font_active)
            en_h = fm.boundingRect(0, 0, text_w, 9999, flags, orig).height()
            total = en_h + 8 + 16   # 8px gap atas, 16px padding bawah
            if trans:
                fm2 = QFontMetrics(self._font_trans)
                id_h = fm2.boundingRect(0, 0, text_w, 9999, flags, trans).height()
                total += id_h + 6  # 6px gap antara lirik dan subtitle
            return QSize(400, max(52, total))
        elif self._near:
            fm = QFontMetrics(self._font_near)
            en_h = fm.boundingRect(0, 0, text_w, 9999, flags, orig).height()
            return QSize(400, max(38, en_h + 14))
        else:
            fm = QFontMetrics(self._font_far)
            en_h = fm.boundingRect(0, 0, text_w, 9999, flags, orig).height()
            return QSize(400, max(32, en_h + 10))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w   = self.width()
        pad = 20
        text_w = w - pad * 2
        flags  = int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft)
        orig   = self._line.original_text or ""
        trans  = self._line.translated_text or ""

        if self._active:
            pt = 8
            # Aksen indikator ungu kecil di kiri
            p.setBrush(QColor(180, 140, 255, 255))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(0, pt + 4, 3, self.height() - pt * 2 - 8), 1.5, 1.5)

            # Lirik Utama — White Bold melayang bersih
            p.setFont(self._font_active)
            fm = p.fontMetrics()
            en_r = fm.boundingRect(QRect(0, 0, text_w, 9999), flags, orig)

            # Shadow lembut
            p.setPen(QColor(0, 0, 0, 160))
            p.drawText(QRect(pad + 1, pt + 1, text_w, en_r.height()), flags, orig)
            p.setPen(QColor(255, 255, 255, 255))
            p.drawText(QRect(pad, pt, text_w, en_r.height()), flags, orig)

            # Terjemahan — Emas #FFE066 (langsung di bawah lirik utama)
            if trans:
                trans_y = pt + en_r.height() + 6
                p.setFont(self._font_trans)
                fm2 = p.fontMetrics()
                id_r = fm2.boundingRect(QRect(0, 0, text_w, 9999), flags, trans)
                # Pastikan masih dalam widget
                avail_h = max(id_r.height(), self.height() - trans_y - 4)
                p.setPen(QColor(0, 0, 0, 140))
                p.drawText(QRect(pad + 1, trans_y + 1, text_w, avail_h), flags, trans)
                p.setPen(QColor(255, 224, 102, 240))
                p.drawText(QRect(pad, trans_y, text_w, avail_h), flags, trans)

        elif self._near:
            pt = 6
            p.setFont(self._font_near)
            fm = p.fontMetrics()
            en_r = fm.boundingRect(QRect(0, 0, text_w, 9999), flags, orig)
            p.setPen(QColor(255, 255, 255, 190))
            p.drawText(QRect(pad, pt, text_w, en_r.height()), flags, orig)

        else:
            pt = 4
            p.setFont(self._font_far)
            fm = p.fontMetrics()
            en_r = fm.boundingRect(QRect(0, 0, text_w, 9999), flags, orig)
            p.setPen(QColor(255, 255, 255, 125))
            p.drawText(QRect(pad, pt, text_w, en_r.height()), flags, orig)

        p.end()

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


# ──────────────────────────────────────────────────────────────
# Main Window Signals
# ──────────────────────────────────────────────────────────────

class FullLyricsSignals(QObject):
    sig_timeline_ready    = Signal(object)
    sig_translation_ready = Signal(object)
    sig_queue_updated     = Signal(object)
    sig_track_changed     = Signal(object)


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────

class FullLyricsWindow(QDialog):

    def __init__(self, event_bus: EventBus, timeline_engine=None, parent=None):
        super().__init__(parent)
        self._bus = event_bus
        self._timeline_engine = timeline_engine
        self._signals = FullLyricsSignals()
        self._line_widgets: List[LyricsLineWidget] = []
        self._current_index: int = -1
        self._auto_scroll = True
        self._drag_pos: Optional[QPoint] = None
        self._scroll_anim: Optional[QPropertyAnimation] = None
        self._art_loader: Optional[_AlbumArtLoader] = None
        self._album_pixmap: Optional[QPixmap] = None

        self._signals.sig_timeline_ready.connect(self._on_timeline_ready)
        self._signals.sig_translation_ready.connect(self._on_translation_ready)
        self._signals.sig_queue_updated.connect(self._on_queue_updated)
        self._signals.sig_track_changed.connect(self._on_track_changed)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("EchoLyrics")
        self.setMinimumSize(480, 640)
        self.resize(520, 700)

        self._enable_dwm_blur()
        self._build_ui()
        self._subscribe()
        self._populate_initial()
        # Timer untuk scroll awal setelah window & layout selesai di-render
        self._pending_scroll_index: int = -1

    def _enable_dwm_blur(self) -> None:
        try:
            import ctypes
            class ACCENT(ctypes.Structure):
                _fields_ = [("AccentState", ctypes.c_int),
                             ("AccentFlags", ctypes.c_int),
                             ("GradientColor", ctypes.c_int),
                             ("AnimationId", ctypes.c_int)]
            class WCAD(ctypes.Structure):
                _fields_ = [("Attribute", ctypes.c_int),
                             ("Data", ctypes.c_void_p),
                             ("SizeOfData", ctypes.c_size_t)]
            accent = ACCENT()
            accent.AccentState   = 3
            accent.AccentFlags   = 2
            accent.GradientColor = 0xE022103B
            wcad = WCAD()
            wcad.Attribute  = 19
            wcad.Data       = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            wcad.SizeOfData = ctypes.sizeof(accent)
            ctypes.windll.user32.SetWindowCompositionAttribute(
                int(self.winId()), ctypes.byref(wcad))
        except Exception:
            pass

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        tb = QWidget()
        tb.setFixedHeight(44)
        tb.setStyleSheet("background: transparent;")
        tb_row = QHBoxLayout(tb)
        tb_row.setContentsMargins(18, 0, 14, 0)
        tb_row.setSpacing(8)

        self._equalizer = _EqualizerWidget()
        self._equalizer.setStyleSheet("background: transparent;")
        tb_row.addWidget(self._equalizer)

        dot_lbl = QLabel("LYRICS")
        dot_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.45); font-size: 10px; font-weight: 700; "
            "letter-spacing: 2.5px; background: transparent;")
        tb_row.addWidget(dot_lbl)
        tb_row.addStretch()

        self._btn_scroll = QPushButton("↓ Auto")
        self._btn_scroll.setFixedSize(68, 24)
        self._btn_scroll.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_scroll.clicked.connect(self._toggle_autoscroll)
        self._btn_scroll.setStyleSheet("""
            QPushButton {
                background: rgba(124,77,255,0.22);
                color: rgba(255,255,255,0.85);
                border: 1px solid rgba(180,140,255,0.45);
                border-radius: 12px;
                font-size: 10px; font-weight: 700;
            }
            QPushButton:hover { background: rgba(124,77,255,0.4); color: white; }
        """)
        tb_row.addWidget(self._btn_scroll)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.hide)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.6);
                border: none; border-radius: 14px;
                font-size: 11px; font-weight: 700;
            }
            QPushButton:hover { background: rgba(233,69,96,0.85); color: white; }
        """)
        tb_row.addWidget(btn_close)
        root.addWidget(tb)

        tb.mousePressEvent   = self._tb_press
        tb.mouseMoveEvent    = self._tb_move
        tb.mouseReleaseEvent = self._tb_release
        tb.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

        # Banner
        self._banner = _AlbumBanner()
        self._banner.setFixedHeight(115)
        root.addWidget(self._banner)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.08); margin: 0 18px;")
        root.addWidget(div)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { background: transparent; width: 4px; }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.20); border-radius: 2px; min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._lyrics_layout = QVBoxLayout(self._container)
        self._lyrics_layout.setContentsMargins(0, 12, 0, 140)
        self._lyrics_layout.setSpacing(2)
        self._lyrics_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

        # Bottom fade
        self._fade = QWidget(self)
        self._fade.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(18,10,38,0), stop:1 rgba(18,10,38,245));
        """)
        self._fade.setFixedHeight(100)
        self._fade.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fade.setGeometry(0, self.height() - 100, self.width(), 100)

    # ── Drag ──

    def _tb_press(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _tb_move(self, ev) -> None:
        if ev.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)

    def _tb_release(self, ev) -> None:
        self._drag_pos = None

    # ── Paint ──

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        rf   = QRectF(rect)

        path = QPainterPath()
        path.addRoundedRect(rf, 16, 16)
        p.setClipPath(path)

        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0,  QColor(28, 16, 56, 240))
        grad.setColorAt(0.5,  QColor(18, 10, 38, 245))
        grad.setColorAt(1.0,  QColor(12,  7, 26, 250))
        p.fillRect(rect, QBrush(grad))

        if self._album_pixmap:
            scaled = self._album_pixmap.scaled(
                rect.width(), rect.height() // 2,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            p.setOpacity(0.14)
            p.drawPixmap(0, 0, scaled)
            p.setOpacity(1.0)

        rg = QRadialGradient(rect.width() - 40, 30, 220)
        rg.setColorAt(0.0, QColor(140, 80, 255, 35))
        rg.setColorAt(1.0, QColor(0,   0,   0,   0))
        p.fillRect(rect, QBrush(rg))

        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, rect.width()-1, rect.height()-1), 16, 16)
        p.end()

    # ── Events ──

    def _subscribe(self) -> None:
        self._bus.subscribe(
            EventType.TIMELINE_READY,
            lambda data: self._signals.sig_timeline_ready.emit(data)
        )
        self._bus.subscribe(
            EventType.TRANSLATION_READY,
            lambda data: self._signals.sig_translation_ready.emit(data)
        )
        self._bus.subscribe(
            EventType.QUEUE_UPDATED,
            lambda data: self._signals.sig_queue_updated.emit(data)
        )
        self._bus.subscribe(
            EventType.TRACK_CHANGED,
            lambda data: self._signals.sig_track_changed.emit(data)
        )

    def _populate_initial(self) -> None:
        """Isi lirik dari timeline yang sudah ada (saat window dibuka saat lagu sedang jalan)."""
        if not self._timeline_engine:
            return
        tl = getattr(self._timeline_engine, "timeline", None)
        if tl and getattr(tl, "track", None):
            self._update_track_info(tl.track)
            self._build_lyrics_ui(tl.lines)
            # Cari baris aktif saat ini dari posisi timer
            pos_ms = getattr(self._timeline_engine, "position_ms", 0)
            if pos_ms > 0 and tl.lines:
                import bisect
                timestamps = [ln.timestamp_ms for ln in tl.lines]
                idx = bisect.bisect_right(timestamps, pos_ms) - 1
                if idx >= 0:
                    self._pending_scroll_index = idx
                    # Highlight langsung (tanpa scroll dulu — scroll dilakukan di showEvent)
                    self._current_index = idx
                    for i, w in enumerate(self._line_widgets):
                        dist = abs(i - idx)
                        w.set_active(dist == 0)
                        w.set_near(1 <= dist <= 2)

    @Slot(object)
    def _on_track_changed(self, playback) -> None:
        if playback and playback.track:
            self._update_track_info(playback.track)
        else:
            self._banner.set_info("Menunggu lagu...", "")
            self._album_pixmap = None
            self.update()
        self._clear_lyrics()
        self._equalizer.set_playing(bool(playback and playback.track))

    @Slot(object)
    def _on_timeline_ready(self, tl) -> None:
        if not tl or not getattr(tl, "track", None):
            return
        self._update_track_info(tl.track)
        self._build_lyrics_ui(tl.lines)
        self._equalizer.set_playing(True)

    @Slot(object)
    def _on_translation_ready(self, tl) -> None:
        if not tl or not tl.lines:
            return
        if len(tl.lines) == len(self._line_widgets):
            for line, w in zip(tl.lines, self._line_widgets):
                w.update_content(line)
        else:
            self._build_lyrics_ui(tl.lines)

    @Slot(object)
    def _on_queue_updated(self, queue) -> None:
        if not queue or not queue.current:
            return
        idx = getattr(queue, "current_index", -1)
        if idx >= 0:
            self._highlight(idx)

    def _on_art_loaded(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        self._album_pixmap = pixmap
        self._banner.set_art(pixmap)
        self.update()

    def showEvent(self, event) -> None:
        """Saat window pertama kali ditampilkan, scroll langsung ke baris aktif."""
        super().showEvent(event)
        # Delay kecil agar Qt selesai layout widget terlebih dahulu
        idx = self._pending_scroll_index if self._pending_scroll_index >= 0 else self._current_index
        if idx >= 0:
            QTimer.singleShot(80, lambda: self._scroll_to(idx))

    def _update_track_info(self, track: TrackInfo) -> None:
        self._banner.set_info(track.title, track.artist)
        if track.image_url:
            self._load_album_art(track.image_url)
        self.update()

    def _load_album_art(self, url: str) -> None:
        if self._art_loader and self._art_loader.isRunning():
            self._art_loader.terminate()
        self._art_loader = _AlbumArtLoader(url)
        self._art_loader.loaded.connect(self._on_art_loaded)
        self._art_loader.start()

    def _on_art_loaded(self, pixmap: QPixmap) -> None:
        self._album_pixmap = pixmap
        self._banner.set_art(pixmap)
        self.update()

    # ── Lyrics & Auto-Scroll Presisi ──

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
        self._current_index = index
        # Reset pending scroll — sudah ada highlight baru
        self._pending_scroll_index = -1

        for i, w in enumerate(self._line_widgets):
            dist = abs(i - index)
            w.set_active(dist == 0)
            w.set_near(1 <= dist <= 2)

        if self._auto_scroll:
            # Selalu scroll meski window sedang hidden
            # (saat ditampilkan kembali, showEvent akan handle sisanya)
            if self.isVisible():
                QTimer.singleShot(40, lambda: self._scroll_to(index))
            else:
                self._pending_scroll_index = index

    def _scroll_to(self, index: int) -> None:
        if not (0 <= index < len(self._line_widgets)):
            return

        w = self._line_widgets[index]

        # Pastikan container sudah di-layout sebelum mapTo
        self._container.adjustSize()
        QApplication.processEvents()

        # Coba mapTo, jika hasilnya 0 dan index > 0, pakai kalkulasi manual
        y_map = w.mapTo(self._container, QPoint(0, 0)).y()
        if y_map == 0 and index > 0:
            # Hitung dari geometri langsung
            y_map = w.geometry().y()

        viewport_h = self._scroll.viewport().height()
        # Posisikan baris aktif di 1/3 bagian atas viewport
        target_y = y_map - (viewport_h // 3)
        target_y = max(0, target_y)
        target_y = min(target_y, self._scroll.verticalScrollBar().maximum())

        bar = self._scroll.verticalScrollBar()
        current = bar.value()
        if abs(current - target_y) < 4:
            return

        if self._scroll_anim and self._scroll_anim.state() == QPropertyAnimation.State.Running:
            self._scroll_anim.stop()

        self._scroll_anim = QPropertyAnimation(bar, b"value", self)
        self._scroll_anim.setDuration(380)
        self._scroll_anim.setStartValue(current)
        self._scroll_anim.setEndValue(target_y)
        self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_anim.start()

    def _toggle_autoscroll(self) -> None:
        self._auto_scroll = not self._auto_scroll
        self._btn_scroll.setText("↓ Auto" if self._auto_scroll else "⏸ Auto")
        if self._auto_scroll and self._current_index >= 0:
            self._scroll_to(self._current_index)


# ──────────────────────────────────────────────────────────────
# Album Banner Widget
# ──────────────────────────────────────────────────────────────

class _AlbumBanner(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 6, 20, 6)
        lay.setSpacing(16)

        self._art_lbl = QLabel()
        self._art_lbl.setFixedSize(80, 80)
        self._art_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art_lbl.setText("♪")
        self._art_lbl.setStyleSheet("""
            color: rgba(255,255,255,0.4);
            font-size: 28px;
            background: rgba(255,255,255,0.08);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.15);
        """)
        lay.addWidget(self._art_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._lbl_title = QLabel("Menunggu lagu...")
        self._lbl_title.setStyleSheet(
            "color: #FFFFFF; font-size: 17px; font-weight: 700; "
            "font-family: 'Segoe UI'; background: transparent;")
        self._lbl_title.setWordWrap(True)

        self._lbl_artist = QLabel("")
        self._lbl_artist.setStyleSheet(
            "color: rgba(255,255,255,0.60); font-size: 13px; font-weight: 500; "
            "font-family: 'Segoe UI'; background: transparent;")

        info_col.addWidget(self._lbl_title)
        info_col.addWidget(self._lbl_artist)
        lay.addLayout(info_col, 1)

    def set_info(self, title: str, artist: str) -> None:
        self._lbl_title.setText(title)
        self._lbl_artist.setText(artist)

    def set_art(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        if pixmap:
            scaled = pixmap.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (scaled.width()  - 80) // 2
            y = (scaled.height() - 80) // 2
            cropped = scaled.copy(x, y, 80, 80)
            self._art_lbl.setPixmap(cropped)
            self._art_lbl.setText("")
