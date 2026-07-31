"""
Overlay Window
==============
Window utama overlay — frameless, transparent, always on top, click-through.
Menampilkan 3 baris subtitle: previous (dim), current (full), next (faint).
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QBrush,
    QPainterPath, QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import QWidget, QApplication

from backend.models.models import SubtitleLine, SubtitleQueue
from backend.logger.app_logger import app_logger

# Import click-through
try:
    from frontend.overlay.clickthrough import enable_click_through, disable_click_through
    _HAS_WIN32 = True
except Exception:
    _HAS_WIN32 = False
    def enable_click_through(w): pass
    def disable_click_through(w): pass


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

_FONT_FAMILY    = "Inter, Segoe UI, Noto Sans, Arial"
_FONT_SIZE_EN   = 32
_FONT_SIZE_ID   = 24
_MARGIN_BOTTOM  = 180
_MARGIN_H       = 100
_MAX_WIDTH_RATIO = 0.70

_OPACITY_CURRENT  = 1.00
_OPACITY_PREVIOUS = 0.55
_OPACITY_NEXT     = 0.30

_GLOW_RADIUS  = 10
_GLOW_OPACITY = 0.35
_SHADOW_OPACITY = 0.20

_ANIM_FADE_MS  = 200
_ANIM_SLIDE_MS = 180


class OverlayWindow(QWidget):
    """
    Overlay subtitle window — transparan, selalu di atas, click-through.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: Optional[SubtitleQueue] = None
        self._click_through_enabled = True
        self._theme = "dark"
        self._font_size_en = _FONT_SIZE_EN
        self._font_size_id = _FONT_SIZE_ID
        self._glow_enabled = True
        self._opacity_level = 1.0
        self._edit_mode = False
        self._drag_pos = None

        self._setup_window()
        self._setup_fonts()
        self._position_window()

    # ──────────────────────────────────────────────────────────
    # Window Setup
    # ──────────────────────────────────────────────────────────

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

    def set_edit_mode(self, enabled: bool) -> None:
        """Aktifkan/Matikan mode geser subtitle."""
        self._edit_mode = enabled
        if enabled:
            if _HAS_WIN32:
                disable_click_through(self)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            if self._click_through_enabled and _HAS_WIN32:
                enable_click_through(self)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def toggle_edit_mode(self) -> bool:
        self.set_edit_mode(not self._edit_mode)
        return self._edit_mode

    def mousePressEvent(self, event) -> None:
        if self._edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif self._edit_mode and event.button() == Qt.MouseButton.RightButton:
            # Klik kanan untuk kunci kembali
            self.set_edit_mode(False)
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._edit_mode and event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._edit_mode:
            self._drag_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

    def _setup_fonts(self) -> None:
        self._font_en = QFont()
        self._font_en.setFamilies(_FONT_FAMILY.split(", "))
        self._font_en.setPixelSize(self._font_size_en)
        self._font_en.setWeight(QFont.Weight.DemiBold)

        self._font_id = QFont()
        self._font_id.setFamilies(_FONT_FAMILY.split(", "))
        self._font_id.setPixelSize(self._font_size_id)
        self._font_id.setWeight(QFont.Weight.Normal)

    def _position_window(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        rect = screen.geometry()
        self.setGeometry(rect)

    def show_overlay(self) -> None:
        self.show()
        self._apply_click_through()
        app_logger.debug("[OverlayWindow] Shown.")

    def hide_overlay(self) -> None:
        self.hide()
        app_logger.debug("[OverlayWindow] Hidden.")

    def _apply_click_through(self) -> None:
        if self._click_through_enabled and _HAS_WIN32:
            enable_click_through(self)
        elif _HAS_WIN32:
            disable_click_through(self)

    # ──────────────────────────────────────────────────────────
    # Update Subtitle
    # ──────────────────────────────────────────────────────────

    def update_queue(self, queue: Optional[SubtitleQueue]) -> None:
        """Update subtitle queue dan trigger repaint."""
        self._queue = queue
        self.update()  # schedule repaint

    def clear(self) -> None:
        self._queue = None
        self.update()

    # ──────────────────────────────────────────────────────────
    # Painting
    # ──────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        screen_rect = self.rect()
        max_width = int(screen_rect.width() * _MAX_WIDTH_RATIO)
        cx = screen_rect.center().x()
        base_y = screen_rect.height() - _MARGIN_BOTTOM

        # Gambar Mode Edit Indicator jika aktif
        if self._edit_mode:
            painter.setPen(QPen(QColor(233, 69, 96, 200), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(26, 26, 46, 180))
            box_rect = QRect(cx - max_width // 2, base_y - 120, max_width, 120)
            painter.drawRoundedRect(box_rect, 12, 12)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(self._font_id)
            hint_text = "🖐 Mode Edit — Tahan & Geser mouse ke posisi mana saja (Klik Kanan untuk Mengunci)"
            painter.drawText(box_rect, int(Qt.AlignmentFlag.AlignCenter), hint_text)

        if not self._queue:
            painter.end()
            return

        # Tata letak vertikal (dari bawah ke atas):
        y_cursor = base_y

        # Gambar Current
        if self._queue.current:
            y_cursor = self._draw_subtitle(
                painter, self._queue.current,
                cx, y_cursor, max_width,
                _OPACITY_CURRENT, anchor="bottom"
            )

        # Gambar Previous (di atas current)
        if self._queue.previous:
            self._draw_subtitle(
                painter, self._queue.previous,
                cx, y_cursor - 8, max_width,
                _OPACITY_PREVIOUS, anchor="bottom"
            )

        painter.end()

    def _draw_subtitle(
        self,
        painter: QPainter,
        line: SubtitleLine,
        cx: int,
        y: int,
        max_width: int,
        opacity: float,
        anchor: str = "bottom"
    ) -> int:
        """
        Gambar satu baris subtitle (original + translation).
        Return Y baru (top of this subtitle block).
        """
        if not line.original_text:
            return y

        # Tentukan warna berdasarkan tema
        if self._theme == "dark":
            color_en = QColor(255, 255, 255)
            color_id = QColor(200, 200, 200)
            glow_col = QColor(255, 255, 255)
        else:
            color_en = QColor(20, 20, 20)
            color_id = QColor(60, 60, 60)
            glow_col = QColor(0, 0, 0)

        color_en.setAlphaF(opacity)
        color_id.setAlphaF(opacity * 0.85)

        # Hitung dimensi teks
        fm_en = QFontMetrics(self._font_en)
        fm_id = QFontMetrics(self._font_id)

        en_text = self._wrap_text(line.original_text, fm_en, max_width)
        en_rect = fm_en.boundingRect(
            0, 0, max_width, 1000,
            int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),
            en_text
        )

        has_translation = bool(line.translated_text)
        id_text = ""
        id_rect_h = 0
        if has_translation:
            id_text = self._wrap_text(line.translated_text, fm_id, max_width)
            id_rect = fm_id.boundingRect(
                0, 0, max_width, 1000,
                int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),
                id_text
            )
            id_rect_h = id_rect.height() + 6  # 6px gap

        total_height = en_rect.height() + id_rect_h

        if anchor == "bottom":
            block_bottom = y
            block_top = y - total_height
        else:
            block_top = y
            block_bottom = y + total_height

        # Draw English text
        en_y = block_top
        en_draw_rect = QRect(cx - max_width // 2, en_y, max_width, en_rect.height())

        if self._glow_enabled:
            self._draw_glow(painter, en_draw_rect, glow_col, opacity)

        painter.setFont(self._font_en)
        painter.setPen(color_en)
        painter.drawText(
            en_draw_rect,
            int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),
            en_text
        )

        # Draw translation
        if has_translation:
            id_y = block_top + en_rect.height() + 6
            id_draw_rect = QRect(cx - max_width // 2, id_y, max_width, id_rect_h)

            if self._glow_enabled:
                self._draw_glow(painter, id_draw_rect, glow_col, opacity * 0.7)

            painter.setFont(self._font_id)
            painter.setPen(color_id)
            painter.drawText(
                id_draw_rect,
                int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),
                id_text
            )

        return block_top

    def _draw_glow(
        self,
        painter: QPainter,
        rect: QRect,
        color: QColor,
        opacity: float
    ) -> None:
        """Multi-pass soft glow di belakang teks."""
        for radius in [4, 8, 12, 16]:
            glow = QColor(color)
            alpha = int(255 * _GLOW_OPACITY * opacity * (1.0 - radius / 20.0))
            glow.setAlpha(max(0, alpha))
            painter.setPen(QPen(glow, radius))
            expanded = rect.adjusted(-radius, -radius, radius, radius)
            painter.drawRoundedRect(expanded, radius // 2, radius // 2)

    def _wrap_text(self, text: str, fm: QFontMetrics, max_width: int) -> str:
        """Text wrapping sederhana — Qt wordwrap yang sesungguhnya."""
        return text  # Qt drawText dengan TextWordWrap sudah handle ini

    # ──────────────────────────────────────────────────────────
    # Settings
    # ──────────────────────────────────────────────────────────

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

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
