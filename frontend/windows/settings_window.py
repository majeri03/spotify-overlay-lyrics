"""
Settings Window — Apple Music Style, Frameless
===============================================
Jendela pengaturan EchoLyrics dengan desain premium.
Frameless (tanpa title bar OS), sidebar purple gelap,
Content kanan dalam glass cards.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QWidget, QPushButton, QLineEdit, QSpinBox,
    QScrollArea, QFrame, QSizePolicy, QAbstractButton,
    QStackedWidget, QButtonGroup, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint, QRectF
from typing import Optional
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush,
    QPainterPath, QCursor, QPen
)

from backend.config.config_manager import ConfigManager
from backend.logger.app_logger import app_logger


# ──────────────────────────────────────────────────────────────
# Palette
# ──────────────────────────────────────────────────────────────

_SIDEBAR_BG   = "#130e25"
_CONTENT_BG   = "#0d0a1e"
_ACCENT       = "#7c4dff"
_ACCENT2      = "#b39ddb"
_TEXT         = "#ede7f6"
_DIM          = "rgba(255,255,255,0.45)"
_CARD_BG      = "rgba(255,255,255,0.04)"
_CARD_BORDER  = "rgba(255,255,255,0.09)"
_INPUT_BG     = "rgba(255,255,255,0.07)"
_INPUT_BORDER = "rgba(255,255,255,0.14)"


# ──────────────────────────────────────────────────────────────
# Custom Widgets
# ──────────────────────────────────────────────────────────────

class ToggleSwitch(QWidget):
    """iOS-style toggle switch widget."""
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(46, 26)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Klik untuk mengaktifkan/nonaktifkan")

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool) -> None:
        self._checked = bool(val)
        self.update()

    def mousePressEvent(self, event) -> None:
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h // 2

        # Track background
        if self._checked:
            p.setBrush(QColor(124, 77, 255))
        else:
            p.setBrush(QColor(60, 50, 90))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Thumb circle
        d = h - 6
        cx = (w - 3 - d) if self._checked else 3
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(cx, 3, d, d)
        p.end()


class NavButton(QAbstractButton):
    """Sidebar navigation button dengan icon emoji + label."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon  = icon
        self._label = label
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(210, 48)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self.isChecked():
            # Active: purple pill highlight
            pill = QRect(8, 4, w - 16, h - 8)
            p.setBrush(QColor(124, 77, 255, 45))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(pill, 10, 10)
            # Left accent bar
            p.setBrush(QColor(124, 77, 255))
            p.drawRoundedRect(QRect(0, 10, 3, h - 20), 2, 2)
            icon_color  = QColor(179, 157, 219)
            label_color = QColor(237, 231, 246)
        elif self.underMouse():
            p.setBrush(QColor(255, 255, 255, 12))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRect(8, 4, w - 16, h - 8), 10, 10)
            icon_color  = QColor(255, 255, 255, 160)
            label_color = QColor(255, 255, 255, 180)
        else:
            icon_color  = QColor(255, 255, 255, 100)
            label_color = QColor(255, 255, 255, 120)

        # Icon — flat QPainter drawn
        ix, iy = 18, (h - 20) // 2
        self._draw_icon(p, self._icon, ix, iy, 20, icon_color)

        # Label
        f_label = QFont("Segoe UI", 12)
        f_label.setWeight(QFont.Weight.Medium)
        if self.isChecked():
            f_label.setWeight(QFont.Weight.DemiBold)
        p.setFont(f_label)
        p.setPen(label_color)
        p.drawText(QRect(50, 0, w - 54, h), int(Qt.AlignmentFlag.AlignVCenter), self._label)
        p.end()

    @staticmethod
    def _draw_icon(p: QPainter, icon_type: str, x: int, y: int, sz: int, color: QColor) -> None:
        """Gambar flat icon menggunakan QPainter geometry."""
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        cx, cy = x + sz // 2, y + sz // 2
        r = sz // 2

        if icon_type == "settings":   # Gear ⚙
            # Outer ring
            pw = QPen(color, 2.5)
            pw.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx - r + 5, cy - r + 5, sz - 10, sz - 10)
            # Teeth (8 short lines radiating out)
            import math
            p.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(8):
                angle = math.radians(i * 45)
                inner = r - 5
                outer = r
                p.drawLine(
                    int(cx + inner * math.cos(angle)),
                    int(cy + inner * math.sin(angle)),
                    int(cx + outer * math.cos(angle)),
                    int(cy + outer * math.sin(angle)),
                )

        elif icon_type == "spotify":  # Headphones
            pw = QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Arc top
            from PySide6.QtCore import QRectF
            p.drawArc(QRectF(cx - r + 2, cy - r + 1, sz - 4, sz - 4), 0 * 16, 180 * 16)
            # Left ear
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(cx - r + 1, cy + 1, 5, 8, 2, 2)
            # Right ear
            p.drawRoundedRect(cx + r - 6, cy + 1, 5, 8, 2, 2)

        elif icon_type == "overlay":  # Monitor
            pw = QPen(color, 1.8)
            p.setPen(pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Screen border
            p.drawRoundedRect(x + 1, y + 2, sz - 2, sz - 7, 2, 2)
            # Stand
            p.drawLine(cx, y + sz - 5, cx, y + sz - 2)
            p.drawLine(cx - 4, y + sz - 2, cx + 4, y + sz - 2)
            # Screen lines (content)
            p.setPen(QPen(color, 1.2))
            p.drawLine(x + 4, y + 8,  x + sz - 4, y + 8)
            p.drawLine(x + 4, y + 11, cx - 2,     y + 11)

        elif icon_type == "font":  # Aa
            f_a = QFont("Segoe UI", sz - 4)
            f_a.setWeight(QFont.Weight.Bold)
            p.setFont(f_a)
            p.setPen(color)
            p.drawText(QRect(x - 2, y - 2, sz + 4, sz + 4),
                       int(Qt.AlignmentFlag.AlignCenter), "Aa")

        elif icon_type == "translation":  # Globe
            pw = QPen(color, 1.6)
            p.setPen(pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx - r + 1, cy - r + 1, sz - 2, sz - 2)
            # Vertical line (meridian)
            p.drawLine(cx, cy - r + 1, cx, cy + r - 1)
            # Horizontal line (equator)
            p.drawLine(cx - r + 1, cy, cx + r - 1, cy)
            # Top arc (latitude)
            from PySide6.QtCore import QRectF
            p.drawArc(QRectF(cx - r + 4, cy - r + 3, sz - 8, sz - 6), 0 * 16, 180 * 16)

        elif icon_type == "cache":  # Database cylinder
            p.setPen(QPen(color, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            from PySide6.QtCore import QRectF
            # Body
            p.drawLine(x + 3, cy - 3, x + 3, cy + 5)
            p.drawLine(x + sz - 3, cy - 3, x + sz - 3, cy + 5)
            # Bottom arc
            p.drawArc(QRectF(x + 3, cy + 1, sz - 6, 6), 180 * 16, 180 * 16)
            # Top ellipses (3 stacked)
            for i, oy in enumerate([-6, -1, 4]):
                p.drawArc(QRectF(x + 3, cy + oy - 5, sz - 6, 6), 0, 360 * 16)

        elif icon_type == "about":  # Info circle
            pw = QPen(color, 1.8)
            p.setPen(pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx - r + 1, cy - r + 1, sz - 2, sz - 2)
            # Dot
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(cx - 1, cy - r + 5, 3, 3)
            # Stem
            p.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(cx, cy - 1, cx, cy + r - 4)

        p.restore()

    def enterEvent(self, event) -> None:
        self.update()

    def leaveEvent(self, event) -> None:
        self.update()


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────

class SettingsWindow(QDialog):
    settings_applied = Signal(dict)

    # Urutan nav items: (icon_type, label, page_index)
    _NAV = [
        ("settings",     "General",     0),
        ("spotify",      "Spotify",     1),
        ("overlay",      "Overlay",     2),
        ("font",         "Font",        3),
        ("translation",  "Translation", 4),
        ("cache",        "Cache",       5),
        ("about",        "About",       6),
    ]

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("")
        self.setMinimumSize(840, 600)
        self.resize(860, 620)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos: Optional[QPoint] = None
        self.setModal(False)
        self._nav_buttons: list[NavButton] = []
        self._build_ui()
        self._load_values()
        self._apply_stylesheet()

    # ──────────────────────────────────────────────────────────
    # Build Main UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Main split: sidebar + content
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content(), 1)

        root.addLayout(body, 1)
        root.addWidget(self._build_bottom_bar())

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setObjectName("sidebar")

        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Brand header (draggable)
        brand = QWidget()
        brand.setFixedHeight(72)
        brand.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        brand.mousePressEvent   = self._drag_press
        brand.mouseMoveEvent    = self._drag_move
        brand.mouseReleaseEvent = self._drag_release

        b_layout = QHBoxLayout(brand)
        b_layout.setContentsMargins(20, 14, 12, 10)
        b_layout.setSpacing(0)

        b_text = QVBoxLayout()
        b_text.setSpacing(2)
        logo_lbl = QLabel("♪ EchoLyrics")
        logo_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        sub_lbl = QLabel("Settings")
        sub_lbl.setFont(QFont("Segoe UI", 10))
        b_text.addWidget(logo_lbl)
        b_text.addWidget(sub_lbl)
        b_layout.addLayout(b_text, 1)

        # Close button
        btn_x = QPushButton("✕")
        btn_x.setFixedSize(26, 26)
        btn_x.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_x.clicked.connect(self.reject)
        btn_x.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.4);
                border: none; border-radius: 13px;
                font-size: 10px; font-weight: 700;
            }
            QPushButton:hover { background: rgba(220,60,80,0.7); color: white; }
        """)
        b_layout.addWidget(btn_x, 0, Qt.AlignmentFlag.AlignTop)
        vbox.addWidget(brand)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setObjectName("sidebar_div")
        vbox.addWidget(div)
        vbox.addSpacing(8)

        # Nav items
        group = QButtonGroup(self)
        group.setExclusive(True)

        for icon, label, page_idx in self._NAV:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda checked, idx=page_idx: self._switch_page(idx))
            group.addButton(btn)
            self._nav_buttons.append(btn)
            vbox.addWidget(btn)

        vbox.addStretch()

        # Version label bottom
        ver_lbl = QLabel("v1.0.0")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setObjectName("ver_lbl")
        vbox.addWidget(ver_lbl)
        vbox.addSpacing(16)

        return sidebar

    def _build_content(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("content_frame")

        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Page title bar
        self._page_title = QLabel("General")
        self._page_title.setObjectName("page_title")

        title_bar = QFrame()
        title_bar.setObjectName("title_bar")
        title_bar.setFixedHeight(60)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(28, 0, 28, 0)
        tb_layout.addWidget(self._page_title)
        vbox.addWidget(title_bar)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_general_page())
        self._stack.addWidget(self._build_spotify_page())
        self._stack.addWidget(self._build_overlay_page())
        self._stack.addWidget(self._build_font_page())
        self._stack.addWidget(self._build_translation_page())
        self._stack.addWidget(self._build_cache_page())
        self._stack.addWidget(self._build_about_page())
        vbox.addWidget(self._stack, 1)

        # Select first nav button by default
        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)

        return frame

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("bottom_bar")
        bar.setFixedHeight(60)

        row = QHBoxLayout(bar)
        row.setContentsMargins(28, 0, 28, 0)
        row.setSpacing(12)
        row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.setFixedSize(100, 36)
        btn_cancel.clicked.connect(self.reject)

        btn_apply = QPushButton("Apply & Save")
        btn_apply.setObjectName("btn_apply")
        btn_apply.setFixedSize(130, 36)
        btn_apply.clicked.connect(self._apply_settings)

        row.addWidget(btn_cancel)
        row.addWidget(btn_apply)

        return bar

    def _switch_page(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        titles = ["General", "Spotify", "Overlay", "Font",
                  "Translation", "Cache", "About"]
        if 0 <= idx < len(titles):
            self._page_title.setText(titles[idx])

    # ──────────────────────────────────────────────────────────
    # Page Builders
    # ──────────────────────────────────────────────────────────

    def _scroll_page(self) -> tuple[QScrollArea, QVBoxLayout]:
        """Buat scroll container untuk setiap page."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("page_scroll")

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        return scroll, layout

    def _card(self, title: str = "") -> tuple[QFrame, QVBoxLayout]:
        """Buat glass card dengan judul opsional."""
        card = QFrame()
        card.setObjectName("settings_card")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(14)

        if title:
            lbl = QLabel(title.upper())
            lbl.setObjectName("card_title")
            vbox.addWidget(lbl)

        return card, vbox

    def _row(self, label_text: str, widget: QWidget, hint: str = "") -> QWidget:
        """Label + widget dalam satu baris dengan responsif word-wrap."""
        row_w = QWidget()
        row_w.setObjectName("settings_row")
        h = QHBoxLayout(row_w)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(label_text)
        lbl.setObjectName("row_label")
        lbl.setWordWrap(True)
        col.addWidget(lbl)
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("row_hint")
            hint_lbl.setWordWrap(True)
            col.addWidget(hint_lbl)
        h.addLayout(col, 1)
        h.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row_w

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setObjectName("card_sep")
        return sep

    # ── General ──

    def _build_general_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("Startup & Behavior")
        self.tog_startup = ToggleSwitch()
        cv.addWidget(self._row("Jalankan saat Windows startup",
                               self.tog_startup,
                               "EchoLyrics otomatis mulai bersama Windows"))
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # ── Spotify ──

    def _build_spotify_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("Spotify API Credentials")
        info = QLabel(
            "Daftar di <b>Spotify Developer Dashboard</b> dan buat app baru.\n"
            "Salin Client ID dan Client Secret ke bawah."
        )
        info.setObjectName("card_info")
        info.setWordWrap(True)
        cv.addWidget(info)
        cv.addWidget(self._separator())

        self.txt_client_id = QLineEdit()
        self.txt_client_id.setPlaceholderText("Masukkan Client ID...")
        self.txt_client_id.setObjectName("settings_input")

        self.txt_client_secret = QLineEdit()
        self.txt_client_secret.setPlaceholderText("Masukkan Client Secret...")
        self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_client_secret.setObjectName("settings_input")

        cv.addWidget(self._row("Client ID", self.txt_client_id))
        cv.addWidget(self._separator())
        cv.addWidget(self._row("Client Secret", self.txt_client_secret))
        cv.addWidget(self._separator())

        btn_login = QPushButton("  🔑  Connect Spotify")
        btn_login.setObjectName("btn_spotify")
        btn_login.clicked.connect(self._do_spotify_login)
        cv.addWidget(btn_login)
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # ── Overlay ──

    def _build_overlay_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        # Opacity card
        card, cv = self._card("Display")

        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(10, 100)
        self.sld_opacity.setValue(100)
        self.sld_opacity.setObjectName("settings_slider")
        self.lbl_opacity = QLabel("100%")
        self.lbl_opacity.setObjectName("slider_val")
        self.lbl_opacity.setFixedWidth(42)
        self.lbl_opacity.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.sld_opacity.valueChanged.connect(lambda v: self.lbl_opacity.setText(f"{v}%"))

        opacity_row_w = QWidget()
        opacity_row_w.setObjectName("settings_row")
        opacity_row_w.setFixedWidth(240)
        oh = QHBoxLayout(opacity_row_w)
        oh.setContentsMargins(0, 0, 0, 0)
        oh.setSpacing(8)
        oh.addWidget(self.sld_opacity, 1)
        oh.addWidget(self.lbl_opacity)
        cv.addWidget(self._row("Opacity", opacity_row_w))
        cv.addWidget(self._separator())

        self.tog_click_through = ToggleSwitch()
        cv.addWidget(self._row("Click Through",
                               self.tog_click_through,
                               "Mouse menembus overlay, klik ke app di bawahnya"))
        cv.addWidget(self._separator())

        self.tog_glow = ToggleSwitch()
        cv.addWidget(self._row("Glow Effect", self.tog_glow,
                               "Efek cahaya di sekitar teks"))
        layout.addWidget(card)

        # Position card
        card2, cv2 = self._card("Position")
        self.cmb_position = QComboBox()
        self.cmb_position.setObjectName("settings_combo")
        self.cmb_position.setFixedWidth(180)
        self.cmb_position.addItems([
            "bottom_center", "top_center", "center",
            "top_left", "top_right", "bottom_left", "bottom_right"
        ])
        cv2.addWidget(self._row("Posisi Subtitle", self.cmb_position))
        cv2.addWidget(self._separator())

        self.cmb_subtitle_mode = QComboBox()
        self.cmb_subtitle_mode.setObjectName("settings_combo")
        self.cmb_subtitle_mode.setFixedWidth(180)
        self.cmb_subtitle_mode.addItems(["compact", "standard", "extended"])
        cv2.addWidget(self._row("Mode Subtitle", self.cmb_subtitle_mode))
        layout.addWidget(card2)

        # ── Auto-Sync card ──
        card3, cv3 = self._card("Auto-Sync")

        self.tog_auto_sync = ToggleSwitch(checked=True)
        # Real-time: toggle langsung kirim ke SmartSyncEngine
        self.tog_auto_sync.toggled.connect(
            lambda enabled: self.settings_applied.emit({
                "action": "autosync_toggle",
                "enabled": enabled
            })
        )
        cv3.addWidget(self._row(
            "Sinkronisasi Otomatis",
            self.tog_auto_sync,
            "Engine sinkronisasi kontinu — koreksi drift secara real-time tanpa input manual"
        ))
        cv3.addWidget(self._separator())

        # Manual offset slider: -3000ms to +3000ms
        self.sld_sync_offset = QSlider(Qt.Orientation.Horizontal)
        self.sld_sync_offset.setRange(-3000, 3000)
        self.sld_sync_offset.setValue(0)
        self.sld_sync_offset.setObjectName("settings_slider")
        self.lbl_sync_offset = QLabel("0 ms")
        self.lbl_sync_offset.setObjectName("slider_val")
        self.lbl_sync_offset.setFixedWidth(60)
        self.lbl_sync_offset.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Real-time: setiap perubahan slider langsung kirim offset ke SmartSyncEngine
        def _on_slider_changed(v: int) -> None:
            self.lbl_sync_offset.setText(f"{v:+d} ms")
            self.settings_applied.emit({"action": "manual_offset", "offset_ms": v})

        self.sld_sync_offset.valueChanged.connect(_on_slider_changed)

        sync_row_w = QWidget()
        sync_row_w.setObjectName("settings_row")
        sync_row_w.setFixedWidth(260)
        sh = QHBoxLayout(sync_row_w)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(8)
        sh.addWidget(self.sld_sync_offset, 1)
        sh.addWidget(self.lbl_sync_offset)
        cv3.addWidget(self._row(
            "Fine-Tune Manual",
            sync_row_w,
            "Koreksi tambahan jika lirik masih tidak pas (0 = biarkan engine atur otomatis)"
        ))
        cv3.addWidget(self._separator())

        # Tombol Force Resync — anchor ulang ke posisi audio sekarang juga
        self.btn_force_resync = QPushButton("⟳  Sinkron Sekarang")
        self.btn_force_resync.setObjectName("btn_spotify")
        self.btn_force_resync.setFixedHeight(34)
        self.btn_force_resync.setFixedWidth(180)
        self.btn_force_resync.clicked.connect(self._on_force_resync)
        cv3.addWidget(self._row(
            "Paksa Sinkron",
            self.btn_force_resync,
            "Re-anchor lirik ke posisi audio sekarang juga (berguna setelah skip/seek)"
        ))
        cv3.addWidget(self._separator())

        self.btn_reset_sync = QPushButton("Hapus Kalibrasi Lagu Ini")
        self.btn_reset_sync.setObjectName("btn_danger")
        self.btn_reset_sync.setFixedHeight(34)
        self.btn_reset_sync.setFixedWidth(180)
        self.btn_reset_sync.clicked.connect(self._on_reset_sync)
        cv3.addWidget(self._row(
            "Reset Offset",
            self.btn_reset_sync,
            "Hapus offset tersimpan untuk lagu yang sedang diputar, mulai belajar ulang"
        ))
        layout.addWidget(card3)

        layout.addStretch()
        return scroll


    # ── Font ──

    def _build_font_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("Font Size")

        self.spn_font_en = QSpinBox()
        self.spn_font_en.setRange(12, 80)
        self.spn_font_en.setValue(32)
        self.spn_font_en.setSuffix(" px")
        self.spn_font_en.setObjectName("settings_spin")

        self.spn_font_id = QSpinBox()
        self.spn_font_id.setRange(10, 60)
        self.spn_font_id.setValue(24)
        self.spn_font_id.setSuffix(" px")
        self.spn_font_id.setObjectName("settings_spin")

        cv.addWidget(self._row("English Lyrics", self.spn_font_en,
                               "Ukuran font lirik utama"))
        cv.addWidget(self._separator())
        cv.addWidget(self._row("Terjemahan Indonesia", self.spn_font_id,
                               "Ukuran font terjemahan di bawahnya"))
        layout.addWidget(card)

        card2, cv2 = self._card("Animation")
        self.spn_anim = QSpinBox()
        self.spn_anim.setRange(50, 1000)
        self.spn_anim.setValue(200)
        self.spn_anim.setSuffix(" ms")
        self.spn_anim.setObjectName("settings_spin")
        cv2.addWidget(self._row("Kecepatan Transisi", self.spn_anim,
                               "Durasi animasi pergantian lirik"))
        layout.addWidget(card2)

        layout.addStretch()
        return scroll

    # ── Translation ──

    def _build_translation_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("Translation Settings")

        self.tog_translation = ToggleSwitch(checked=True)
        cv.addWidget(self._row("Aktifkan Terjemahan",
                               self.tog_translation,
                               "Tampilkan terjemahan Bahasa Indonesia"))
        cv.addWidget(self._separator())

        self.cmb_trans_provider = QComboBox()
        self.cmb_trans_provider.setObjectName("settings_combo")
        self.cmb_trans_provider.addItems(["google", "mymemory", "libretranslate"])
        cv.addWidget(self._row("Provider", self.cmb_trans_provider,
                               "google = gratis, tidak perlu API key"))
        cv.addWidget(self._separator())

        self.cmb_trans_style = QComboBox()
        self.cmb_trans_style.setObjectName("settings_combo")
        self.cmb_trans_style.addItems(["natural", "literal", "poetic"])
        cv.addWidget(self._row("Gaya Terjemahan", self.cmb_trans_style))
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # ── Cache & Tools ──

    def _build_cache_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("Cache Management")

        btn_clear_current = QPushButton("Hapus Cache Lagu Ini")
        btn_clear_current.setObjectName("btn_danger")
        btn_clear_current.setFixedHeight(34)
        btn_clear_current.setFixedWidth(180)
        btn_clear_current.clicked.connect(self._clear_current_cache)

        cv.addWidget(self._row("Hapus Cache Lagu Ini", btn_clear_current,
                               "Hapus lirik & terjemahan tersimpan khusus untuk lagu yang sedang diputar, lalu unduh ulang lirik baru"))
        cv.addWidget(self._separator())

        btn_clear_all = QPushButton("Hapus Semua Cache")
        btn_clear_all.setObjectName("btn_danger")
        btn_clear_all.setFixedHeight(34)
        btn_clear_all.setFixedWidth(180)
        btn_clear_all.clicked.connect(self._clear_cache)

        cv.addWidget(self._row("Hapus Semua Cache Database", btn_clear_all,
                               "Hapus seluruh lirik dan terjemahan dari database SQLite"))
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # ── About ──

    def _build_about_page(self) -> QScrollArea:
        scroll, layout = self._scroll_page()

        card, cv = self._card("About EchoLyrics")

        logo = QLabel("♪")
        logo.setStyleSheet("font-size: 42px; color: #7c4dff;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("EchoLyrics v1.0.0")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ver = QLabel("Build 2026.08.01 — High-Precision Auto-Sync Edition")
        ver.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.45);")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc = QLabel(
            "Overlay lirik Spotify real-time dengan terjemahan Bahasa Indonesia.\n"
            "Mendukung High-DPI, Auto-Sync Calibration, dan Apple Music Glass UI."
        )
        desc.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.65); margin-top: 8px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setObjectName("about_desc")

        cv.addWidget(logo)
        cv.addWidget(title)
        cv.addWidget(ver)
        cv.addSpacing(8)
        cv.addWidget(desc)
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # ──────────────────────────────────────────────────────────
    # Load / Save
    # ──────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        cfg = self._config
        self.tog_startup.setChecked(bool(cfg.get("startup_with_windows")))
        self.txt_client_id.setText(cfg.get("spotify_client_id", ""))
        self.txt_client_secret.setText(cfg.get("spotify_client_secret", ""))
        self.sld_opacity.setValue(cfg.get("overlay_opacity", 100))
        self.tog_glow.setChecked(bool(cfg.get("glow_enabled", 1)))
        self.tog_click_through.setChecked(bool(cfg.get("click_through", 1)))
        self.cmb_position.setCurrentText(cfg.get("subtitle_position", "bottom_center"))
        self.cmb_subtitle_mode.setCurrentText(cfg.get("subtitle_mode", "standard"))
        self.tog_auto_sync.setChecked(bool(cfg.get("auto_sync_enabled", 1)))
        raw_offset = cfg.get("manual_sync_offset_ms", 0)
        self.sld_sync_offset.setValue(max(-3000, min(3000, int(raw_offset))))
        self.spn_font_en.setValue(cfg.get("font_size_english", 32))
        self.spn_font_id.setValue(cfg.get("font_size_translation", 24))
        self.spn_anim.setValue(cfg.get("animation_speed_ms", 200))
        self.tog_translation.setChecked(bool(cfg.get("translation_enabled", 1)))
        self.cmb_trans_provider.setCurrentText(cfg.get("translation_provider", "google"))
        self.cmb_trans_style.setCurrentText(cfg.get("translation_style", "natural"))

    def _apply_settings(self) -> None:
        cfg = self._config
        cfg.set("startup_with_windows", int(self.tog_startup.isChecked()))
        cfg.set("spotify_client_id", self.txt_client_id.text())
        cfg.set("spotify_client_secret", self.txt_client_secret.text())
        cfg.set("overlay_opacity", self.sld_opacity.value())
        cfg.set("glow_enabled", int(self.tog_glow.isChecked()))
        cfg.set("click_through", int(self.tog_click_through.isChecked()))
        cfg.set("subtitle_position", self.cmb_position.currentText())
        cfg.set("subtitle_mode", self.cmb_subtitle_mode.currentText())
        cfg.set("auto_sync_enabled", int(self.tog_auto_sync.isChecked()))
        cfg.set("manual_sync_offset_ms", self.sld_sync_offset.value())
        cfg.set("font_size_english", self.spn_font_en.value())
        cfg.set("font_size_translation", self.spn_font_id.value())
        cfg.set("animation_speed_ms", self.spn_anim.value())
        cfg.set("translation_enabled", int(self.tog_translation.isChecked()))
        cfg.set("translation_provider", self.cmb_trans_provider.currentText())
        cfg.set("translation_style", self.cmb_trans_style.currentText())
        self.settings_applied.emit(cfg.get_all())
        self.accept()
        app_logger.info("[Settings] Settings saved.")

    def _on_reset_sync(self) -> None:
        self.sld_sync_offset.setValue(0)
        self.settings_applied.emit({"action": "reset_sync"})
        app_logger.info("[Settings] Reset sync requested.")

    def _on_force_resync(self) -> None:
        """Paksa re-anchor ke posisi audio sekarang."""
        self.settings_applied.emit({"action": "force_resync"})
        app_logger.info("[Settings] Force resync requested.")

    def _do_spotify_login(self) -> None:
        self._config.set("spotify_client_id", self.txt_client_id.text())
        self._config.set("spotify_client_secret", self.txt_client_secret.text())
        self.settings_applied.emit({"action": "spotify_login"})

    def _clear_cache(self) -> None:
        self.settings_applied.emit({"action": "clear_cache"})
        app_logger.info("[Settings] Clear cache requested.")

    def _clear_current_cache(self) -> None:
        self.settings_applied.emit({"action": "clear_current_cache"})
        app_logger.info("[Settings] Clear current track cache requested.")

    # ──────────────────────────────────────────────────────────
    # Painting: Custom background
    # ──────────────────────────────────────────────────────────

    # ── Drag support ──

    def _drag_press(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _drag_move(self, ev) -> None:
        if ev.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)

    def _drag_release(self, ev) -> None:
        self._drag_pos = None

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        rf   = QRectF(rect)

        # Rounded clip
        path = QPainterPath()
        path.addRoundedRect(rf, 12, 12)
        p.setClipPath(path)

        # Background gradient
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0, QColor(16, 11, 33))
        grad.setColorAt(1.0, QColor(10,  7, 22))
        p.fillRect(rect, QBrush(grad))

        # Top-left glow
        p.setBrush(QColor(100, 60, 200, 22))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-80, -80, 300, 300)

        # Thin border
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, rect.width()-1, rect.height()-1), 12, 12)
        p.end()
        super().paintEvent(event)

    # ──────────────────────────────────────────────────────────
    # Stylesheet (applied as global)
    # ──────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(f"""
        QDialog {{
            font-family: 'Segoe UI', Inter, Arial, sans-serif;
            font-size: 13px;
        }}

        /* ── Sidebar ── */
        QFrame#sidebar {{
            background-color: {_SIDEBAR_BG};
            border-right: 1px solid rgba(255,255,255,0.06);
        }}
        QLabel {{
            color: {_TEXT};
            background: transparent;
        }}
        QFrame#sidebar QLabel {{
            color: #b39ddb;
        }}
        QLabel[objectName="ver_lbl"] {{
            color: rgba(255,255,255,0.25);
            font-size: 11px;
        }}
        QFrame#sidebar_div {{
            background: rgba(255,255,255,0.06);
            margin: 0 12px;
        }}

        /* ── Content ── */
        QFrame#content_frame {{
            background: transparent;
        }}
        QFrame#title_bar {{
            background: rgba(255,255,255,0.025);
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        QLabel#page_title {{
            color: {_TEXT};
            font-size: 17px;
            font-weight: 700;
        }}

        /* ── Scroll page ── */
        QScrollArea#page_scroll {{
            background: transparent;
            border: none;
        }}
        QScrollArea#page_scroll QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255,255,255,0.12);
            border-radius: 2px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

        /* ── Cards ── */
        QFrame#settings_card {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
        }}
        QLabel#card_title {{
            color: rgba(255,255,255,0.3);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }}
        QFrame#card_sep {{
            background: rgba(255,255,255,0.07);
        }}
        QLabel#card_info {{
            color: rgba(255,255,255,0.5);
            font-size: 12px;
            line-height: 1.5;
        }}

        /* ── Row ── */
        QWidget#settings_row {{
            background: transparent;
        }}
        QLabel#row_label {{
            color: {_TEXT};
            font-size: 13px;
            font-weight: 500;
        }}
        QLabel#row_hint {{
            color: rgba(255,255,255,0.4);
            font-size: 11px;
        }}

        /* ── Inputs ── */
        QLineEdit#settings_input, QSpinBox#settings_spin, QComboBox#settings_combo {{
            background: rgba(255,255,255,0.07);
            color: {_TEXT};
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
            min-width: 160px;
        }}
        QLineEdit#settings_input:focus, QSpinBox#settings_spin:focus,
        QComboBox#settings_combo:focus {{
            border: 1px solid {_ACCENT};
            background: rgba(124,77,255,0.08);
        }}
        QComboBox#settings_combo::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        QComboBox#settings_combo QAbstractItemView {{
            background: #1e1535;
            color: {_TEXT};
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            selection-background-color: {_ACCENT};
        }}
        QSpinBox#settings_spin::up-button, QSpinBox#settings_spin::down-button {{
            background: rgba(255,255,255,0.08);
            border: none;
            width: 18px;
        }}

        /* ── Slider ── */
        QSlider#settings_slider::groove:horizontal {{
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
        }}
        QSlider#settings_slider::handle:horizontal {{
            background: {_ACCENT};
            width: 16px; height: 16px;
            border-radius: 8px;
            margin: -6px 0;
        }}
        QSlider#settings_slider::sub-page:horizontal {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #7c4dff, stop:1 #b39ddb);
            border-radius: 2px;
        }}
        QLabel#slider_val {{
            color: {_ACCENT2};
            font-size: 12px;
            font-weight: 600;
        }}

        /* ── Buttons ── */
        QPushButton#btn_apply {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #7c4dff, stop:1 #9c6bff);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
        }}
        QPushButton#btn_apply:hover {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #9058ff, stop:1 #b07dff);
        }}
        QPushButton#btn_cancel {{
            background: rgba(255,255,255,0.07);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            font-size: 13px;
        }}
        QPushButton#btn_cancel:hover {{
            background: rgba(255,255,255,0.12);
            color: white;
        }}
        QPushButton#btn_spotify {{
            background: #1db954;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            padding: 10px 16px;
        }}
        QPushButton#btn_spotify:hover {{ background: #1ed760; }}
        QPushButton#btn_danger {{
            background: rgba(233,69,96,0.15);
            color: #e94560;
            border: 1px solid rgba(233,69,96,0.3);
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            padding: 10px 16px;
        }}
        QPushButton#btn_danger:hover {{
            background: rgba(233,69,96,0.25);
        }}

        /* ── Bottom bar ── */
        QFrame#bottom_bar {{
            background: rgba(255,255,255,0.025);
            border-top: 1px solid rgba(255,255,255,0.05);
        }}

        /* ── About page ── */
        QLabel#about_logo {{ color: {_ACCENT}; }}
        QLabel#about_title {{ color: {_TEXT}; }}
        QLabel#about_ver {{
            color: rgba(255,255,255,0.4);
            font-size: 12px;
        }}
        QLabel#about_desc {{
            color: rgba(255,255,255,0.6);
            font-size: 13px;
            line-height: 1.6;
        }}
        """)
