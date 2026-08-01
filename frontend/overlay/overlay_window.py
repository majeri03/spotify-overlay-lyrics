"""
Overlay Window — Adaptive Color + Box Area Fitting + Screen Sampling
====================================================================
Fitur:
  • Teks lirik terpusat & ter-wrap sempurna di dalam area QRect (box).
  • Ukuran font menyesuaikan lebar box (responsive scaling).
  • Deteksi kecerahan layar langsung di bawah area box (posisi mana saja).
  • Mode Edit dengan 8 handle resize (NW, N, NE, W, E, SW, S, SE + Move).
  • Teks bersih tanpa border tebal — soft shadow lembut.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt, QRect, QTimer, QPoint, QSize
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QImage, QCursor
)
from PySide6.QtWidgets import QWidget, QApplication

from backend.models.models import SubtitleLine, SubtitleQueue

try:
    from frontend.overlay.clickthrough import enable_click_through, disable_click_through
    _HAS_WIN32 = True
except Exception:
    _HAS_WIN32 = False
    def enable_click_through(w): pass
    def disable_click_through(w): pass


_FONT_FAMILY      = "Inter, Segoe UI, Noto Sans, Arial"
_DEFAULT_FONT_EN  = 30
_DEFAULT_FONT_ID  = 22
_BRIGHT_THRESHOLD = 140

_HANDLE_SIZE = 10
_HANDLE_HIT  = 16


class _Handle(Enum):
    NONE = 0
    MOVE = 1
    N = 2; S = 3; E = 4; W = 5
    NW = 6; NE = 7; SW = 8; SE = 9


class OverlayWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: Optional[SubtitleQueue] = None
        self._click_through_enabled = True
        self._font_size_en = _DEFAULT_FONT_EN
        self._font_size_id = _DEFAULT_FONT_ID
        self._glow_enabled = True
        self._opacity_level = 1.0
        self._edit_mode = False

        self._is_dark_bg: bool = True

        # Posisi & ukuran area teks kustom (None = default center bottom)
        self._text_rect: Optional[QRect] = None
        self._drag_handle: _Handle = _Handle.NONE
        self._drag_origin: Optional[QPoint] = None
        self._rect_at_drag: Optional[QRect] = None

        self._setup_window()
        self._setup_fonts()
        self._position_window()

        self._brightness_timer = QTimer(self)
        self._brightness_timer.timeout.connect(self._sample_brightness)
        self._brightness_timer.start(1200)

    def _setup_window(self) -> None:
        flags = (
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(self._opacity_level)

    def _setup_fonts(self) -> None:
        self._font_en = QFont()
        self._font_en.setFamilies(_FONT_FAMILY.split(", "))
        self._font_en.setPixelSize(self._font_size_en)
        self._font_en.setWeight(QFont.Weight.Bold)

        self._font_id = QFont()
        self._font_id.setFamilies(_FONT_FAMILY.split(", "))
        self._font_id.setPixelSize(self._font_size_id)
        self._font_id.setWeight(QFont.Weight.Medium)

    def _position_window(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def show_overlay(self) -> None:
        self.show()
        self._apply_click_through()

    def hide_overlay(self) -> None:
        self.hide()

    def _apply_click_through(self) -> None:
        if self._click_through_enabled and _HAS_WIN32:
            enable_click_through(self)
        elif _HAS_WIN32:
            disable_click_through(self)

    # ── Text Rect (area lirik) ──

    def _get_text_rect(self) -> QRect:
        if self._text_rect is not None:
            return self._text_rect
        sw, sh = self.width(), self.height()
        w = int(sw * 0.65)
        h = 160
        x = (sw - w) // 2
        y = sh - 180 - h
        return QRect(x, y, w, h)

    def get_text_rect_config(self) -> dict:
        r = self._get_text_rect()
        return {"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height()}

    def set_text_rect_config(self, cfg: dict) -> None:
        if cfg and "x" in cfg:
            self._text_rect = QRect(cfg["x"], cfg["y"], cfg["w"], cfg["h"])
            self.update()

    # ── Brightness Sampling Akurat di Area Text Rect ──

    def _sample_brightness(self) -> None:
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return
            r = self._get_text_rect()

            # Screenshot tepat di bawah area lirik kustom user
            pixmap = screen.grabWindow(0, max(0, r.x()), max(0, r.y()), r.width(), r.height())
            img = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
            if img.isNull() or img.width() == 0 or img.height() == 0:
                return

            total = 0.0
            count = 0
            iw, ih = img.width(), img.height()
            step_x = max(1, iw // 20)
            step_y = max(1, ih // 10)

            for x in range(0, iw, step_x):
                for y in range(0, ih, step_y):
                    c = img.pixel(x, y)
                    red = (c >> 16) & 0xFF
                    green = (c >> 8) & 0xFF
                    blue = c & 0xFF
                    total += 0.299 * red + 0.587 * green + 0.114 * blue
                    count += 1

            if count:
                avg = total / count
                new_dark = avg < _BRIGHT_THRESHOLD
                if new_dark != self._is_dark_bg:
                    self._is_dark_bg = new_dark
                    self.update()
        except Exception:
            pass

    # ── Edit Mode ──

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        if enabled:
            if _HAS_WIN32:
                disable_click_through(self)
            if self._text_rect is None:
                self._text_rect = self._get_text_rect()
        else:
            if self._click_through_enabled and _HAS_WIN32:
                enable_click_through(self)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def toggle_edit_mode(self) -> bool:
        self.set_edit_mode(not self._edit_mode)
        return self._edit_mode

    def _handle_at(self, pos: QPoint) -> _Handle:
        r = self._get_text_rect()
        hs = _HANDLE_HIT
        l, t, ri, b = r.left(), r.top(), r.right(), r.bottom()

        if abs(pos.x() - l) < hs and abs(pos.y() - t) < hs:   return _Handle.NW
        if abs(pos.x() - ri) < hs and abs(pos.y() - t) < hs:  return _Handle.NE
        if abs(pos.x() - l) < hs and abs(pos.y() - b) < hs:   return _Handle.SW
        if abs(pos.x() - ri) < hs and abs(pos.y() - b) < hs:  return _Handle.SE
        if abs(pos.y() - t) < hs and l < pos.x() < ri:        return _Handle.N
        if abs(pos.y() - b) < hs and l < pos.x() < ri:        return _Handle.S
        if abs(pos.x() - l) < hs and t < pos.y() < b:         return _Handle.W
        if abs(pos.x() - ri) < hs and t < pos.y() < b:        return _Handle.E
        if r.contains(pos):                                     return _Handle.MOVE
        return _Handle.NONE

    _CURSORS = {
        _Handle.NONE: Qt.CursorShape.ArrowCursor,
        _Handle.MOVE: Qt.CursorShape.SizeAllCursor,
        _Handle.N:    Qt.CursorShape.SizeVerCursor,
        _Handle.S:    Qt.CursorShape.SizeVerCursor,
        _Handle.E:    Qt.CursorShape.SizeHorCursor,
        _Handle.W:    Qt.CursorShape.SizeHorCursor,
        _Handle.NW:   Qt.CursorShape.SizeFDiagCursor,
        _Handle.NE:   Qt.CursorShape.SizeBDiagCursor,
        _Handle.SW:   Qt.CursorShape.SizeBDiagCursor,
        _Handle.SE:   Qt.CursorShape.SizeFDiagCursor,
    }

    def mousePressEvent(self, event) -> None:
        if not self._edit_mode:
            return
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton:
            self.set_edit_mode(False)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            h = self._handle_at(pos)
            if h != _Handle.NONE:
                self._drag_handle = h
                self._drag_origin = event.globalPosition().toPoint()
                self._rect_at_drag = QRect(self._get_text_rect())
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not self._edit_mode:
            return
        pos = event.position().toPoint()

        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_handle == _Handle.NONE:
            h = self._handle_at(pos)
            self.setCursor(self._CURSORS.get(h, Qt.CursorShape.ArrowCursor))
            return

        delta = event.globalPosition().toPoint() - self._drag_origin
        dx, dy = delta.x(), delta.y()
        r = QRect(self._rect_at_drag)
        MIN_W, MIN_H = 180, 60

        h = self._drag_handle
        if   h == _Handle.MOVE: r.translate(dx, dy)
        elif h == _Handle.N:    r.setTop(min(r.top() + dy, r.bottom() - MIN_H))
        elif h == _Handle.S:    r.setBottom(max(r.bottom() + dy, r.top() + MIN_H))
        elif h == _Handle.W:    r.setLeft(min(r.left() + dx, r.right() - MIN_W))
        elif h == _Handle.E:    r.setRight(max(r.right() + dx, r.left() + MIN_W))
        elif h == _Handle.NW:
            r.setTop(min(r.top() + dy, r.bottom() - MIN_H))
            r.setLeft(min(r.left() + dx, r.right() - MIN_W))
        elif h == _Handle.NE:
            r.setTop(min(r.top() + dy, r.bottom() - MIN_H))
            r.setRight(max(r.right() + dx, r.left() + MIN_W))
        elif h == _Handle.SW:
            r.setBottom(max(r.bottom() + dy, r.top() + MIN_H))
            r.setLeft(min(r.left() + dx, r.right() - MIN_W))
        elif h == _Handle.SE:
            r.setBottom(max(r.bottom() + dy, r.top() + MIN_H))
            r.setRight(max(r.right() + dx, r.left() + MIN_W))

        self._text_rect = r
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._edit_mode:
            self._drag_handle = _Handle.NONE
            self._drag_origin = None
            self._rect_at_drag = None
            event.accept()

    # ── Data ──

    def update_queue(self, queue: Optional[SubtitleQueue]) -> None:
        self._queue = queue
        self.update()

    def clear(self) -> None:
        self._queue = None
        self.update()

    # ── Paint ──

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        tr = self._get_text_rect()

        if self._edit_mode:
            self._draw_edit_ui(painter, tr)

        if not self._queue or not (self._queue.current or self._queue.previous):
            painter.end()
            return

        # Auto font scaling berdasarkan lebar box
        scale_factor = min(1.3, max(0.65, tr.width() / 600.0))
        font_en_sz = max(16, int(self._font_size_en * scale_factor))
        font_id_sz = max(12, int(self._font_size_id * scale_factor))

        font_en = QFont(self._font_en)
        font_en.setPixelSize(font_en_sz)

        font_id = QFont(self._font_id)
        font_id.setPixelSize(font_id_sz)

        # Hitung tinggi total lirik agar berada persis di tengah vertikal box
        fm_en = QFontMetrics(font_en)
        fm_id = QFontMetrics(font_id)
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        max_w = tr.width() - 16

        curr_en_h = 0
        curr_id_h = 0
        if self._queue.current and self._queue.current.original_text:
            b = fm_en.boundingRect(0, 0, max_w, 2000, flags, self._queue.current.original_text)
            curr_en_h = b.height()
            if self._queue.current.translated_text:
                b2 = fm_id.boundingRect(0, 0, max_w, 2000, flags, self._queue.current.translated_text)
                curr_id_h = b2.height() + 4

        prev_en_h = 0
        if self._queue.previous and self._queue.previous.original_text:
            b_prev = fm_en.boundingRect(0, 0, max_w, 2000, flags, self._queue.previous.original_text)
            prev_en_h = b_prev.height() + 6

        total_h = prev_en_h + curr_en_h + curr_id_h
        y_start = tr.y() + max(4, (tr.height() - total_h) // 2)

        # Warm bright colors / Dark colors
        if self._is_dark_bg:
            col_en = QColor(255, 255, 255, 255)
            col_id = QColor(255, 255, 255, 170)
            col_prev = QColor(255, 255, 255, 110)
            shad = QColor(0, 0, 0, 140)
        else:
            col_en = QColor(10, 10, 25, 255)
            col_id = QColor(10, 10, 25, 170)
            col_prev = QColor(10, 10, 25, 110)
            shad = QColor(255, 255, 255, 120)

        # Gambar Previous Line (di atas)
        if prev_en_h > 0 and self._queue.previous:
            prev_r = QRect(tr.x() + 8, y_start, max_w, prev_en_h)
            self._draw_text(painter, font_en, prev_r, self._queue.previous.original_text, col_prev, shad)
            y_start += prev_en_h

        # Gambar Current Line (utama)
        if curr_en_h > 0 and self._queue.current:
            curr_en_r = QRect(tr.x() + 8, y_start, max_w, curr_en_h)
            self._draw_text(painter, font_en, curr_en_r, self._queue.current.original_text, col_en, shad)
            y_start += curr_en_h

            if curr_id_h > 0 and self._queue.current.translated_text:
                curr_id_r = QRect(tr.x() + 8, y_start + 4, max_w, curr_id_h - 4)
                self._draw_text(painter, font_id, curr_id_r, self._queue.current.translated_text, col_id, shad)

        painter.end()

    def _draw_edit_ui(self, painter: QPainter, r: QRect) -> None:
        painter.setBrush(QColor(35, 18, 70, 75))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(r, 8, 8)

        pen = QPen(QColor(165, 120, 255, 220), 1.5, Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 3])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(r, 8, 8)

        hs = _HANDLE_SIZE
        handle_pts = [
            (r.left(), r.top()), (r.center().x(), r.top()), (r.right(), r.top()),
            (r.left(), r.center().y()), (r.right(), r.center().y()),
            (r.left(), r.bottom()), (r.center().x(), r.bottom()), (r.right(), r.bottom()),
        ]
        painter.setPen(QPen(QColor(124, 77, 255), 1.5))
        painter.setBrush(QColor(210, 180, 255, 240))
        for hx, hy in handle_pts:
            painter.drawEllipse(hx - hs//2, hy - hs//2, hs, hs)

        # Label ukuran & posisi
        f = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(f)
        label = f" ↔ {r.width()}px  ↕ {r.height()}px   📍 ({r.x()}, {r.y()}) "
        lm = QFontMetrics(f)
        lb = lm.boundingRect(label)
        lx = r.center().x() - lb.width() // 2
        ly = r.top() - 10

        painter.setBrush(QColor(18, 9, 40, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(lx - 4, ly - lb.height(), lb.width() + 8, lb.height() + 6, 6, 6)
        painter.setPen(QColor(220, 195, 255))
        painter.drawText(lx, ly, label)

        fi = QFont("Segoe UI", 9)
        painter.setFont(fi)
        painter.setPen(QColor(200, 180, 240, 200))
        ins = "Drag tengah untuk pindah · Drag sudut/tepi untuk resize · Klik kanan selesai"
        im = QFontMetrics(fi)
        ib = im.boundingRect(ins)
        ix = r.center().x() - ib.width() // 2
        iy = r.bottom() + 20
        painter.drawText(ix, iy, ins)

    def _draw_text(self, painter, font, rect, text, color, shadow) -> None:
        painter.setFont(font)
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        # Soft shadow 1.5px
        painter.setPen(shadow)
        painter.drawText(rect.translated(0, 2), flags, text)
        painter.setPen(color)
        painter.drawText(rect, flags, text)

    # ── Compatibility Settings ──

    def set_theme(self, theme: str) -> None: pass
    def set_font_sizes(self, en: int, id_: int) -> None:
        self._font_size_en = en
        self._font_size_id = id_
        self._setup_fonts()
        self.update()
    def set_glow(self, enabled: bool) -> None:
        self._glow_enabled = enabled
        self.update()
    def set_click_through(self, enabled: bool) -> None:
        self._click_through_enabled = enabled
        self._apply_click_through()
    def set_opacity(self, value: float) -> None:
        self._opacity_level = max(0.1, min(1.0, value))
        self.setWindowOpacity(self._opacity_level)
