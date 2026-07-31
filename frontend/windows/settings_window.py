"""
Settings Window
===============
Jendela pengaturan EchoLyrics dengan desain modern dan dark mode.
Tab: General, Spotify, Overlay, Theme, Font, Animation, Translation, Cache, About
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QSlider, QComboBox, QCheckBox,
    QPushButton, QLineEdit, QGroupBox, QSpinBox,
    QFormLayout, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QPainter

from backend.config.config_manager import ConfigManager
from backend.logger.app_logger import app_logger

_DARK_BG    = "#1a1a2e"
_DARK_CARD  = "#16213e"
_DARK_INPUT = "#0f3460"
_ACCENT     = "#e94560"
_TEXT       = "#eaeaea"
_TEXT_DIM   = "#a0a0b0"

_STYLESHEET = f"""
QDialog {{
    background-color: {_DARK_BG};
    color: {_TEXT};
    font-family: 'Segoe UI', Inter, sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: none;
    background: {_DARK_CARD};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT_DIM};
    padding: 10px 20px;
    border-radius: 6px;
    margin: 2px;
}}
QTabBar::tab:selected {{
    background: {_ACCENT};
    color: white;
    font-weight: bold;
}}
QLabel {{
    color: {_TEXT};
}}
QLineEdit, QSpinBox, QComboBox {{
    background: {_DARK_INPUT};
    color: {_TEXT};
    border: 1px solid #334;
    border-radius: 6px;
    padding: 6px 10px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {_ACCENT};
}}
QPushButton {{
    background: {_ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: #ff6b6b;
}}
QPushButton#btn_secondary {{
    background: {_DARK_INPUT};
}}
QPushButton#btn_secondary:hover {{
    background: #1a4a80;
}}
QCheckBox {{
    color: {_TEXT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #444;
    background: {_DARK_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {_ACCENT};
    border: 2px solid {_ACCENT};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #334;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}
QGroupBox {{
    color: {_TEXT_DIM};
    border: 1px solid #334;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
"""


class SettingsWindow(QDialog):
    settings_applied = Signal(dict)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("EchoLyrics — Settings")
        self.setMinimumSize(680, 520)
        self.setModal(False)
        self.setStyleSheet(_STYLESHEET)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title bar
        title_lbl = QLabel("⚙  EchoLyrics Settings")
        title_lbl.setStyleSheet(f"font-size:18px; font-weight:bold; color:{_TEXT}; margin-bottom:8px;")
        layout.addWidget(title_lbl)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(),     "General")
        tabs.addTab(self._build_spotify_tab(),     "Spotify")
        tabs.addTab(self._build_overlay_tab(),     "Overlay")
        tabs.addTab(self._build_font_tab(),        "Font")
        tabs.addTab(self._build_translation_tab(), "Translation")
        tabs.addTab(self._build_cache_tab(),       "Cache")
        tabs.addTab(self._build_about_tab(),       "About")
        layout.addWidget(tabs, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)

        btn_apply = QPushButton("Apply & Save")
        btn_apply.clicked.connect(self._apply_settings)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

    # ──────────────────────────────────────────────────────────
    # Tab: General
    # ──────────────────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)

        self.chk_startup = QCheckBox("Jalankan saat Windows startup")
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["dark", "light"])

        form.addRow("Startup:", self.chk_startup)
        form.addRow("Tema:", self.cmb_theme)
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: Spotify
    # ──────────────────────────────────────────────────────────

    def _build_spotify_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)

        note = QLabel("ℹ  Daftarkan aplikasi di Spotify Developer Dashboard\n"
                       "   lalu masukkan Client ID dan Client Secret.")
        note.setStyleSheet(f"color:{_TEXT_DIM}; font-size:12px;")
        note.setWordWrap(True)
        form.addRow(note)

        self.txt_client_id = QLineEdit()
        self.txt_client_id.setPlaceholderText("Spotify Client ID")

        self.txt_client_secret = QLineEdit()
        self.txt_client_secret.setPlaceholderText("Spotify Client Secret")
        self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Client ID:", self.txt_client_id)
        form.addRow("Client Secret:", self.txt_client_secret)

        btn_login = QPushButton("🔑  Login Spotify")
        btn_login.clicked.connect(self._do_spotify_login)
        form.addRow(btn_login)
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: Overlay
    # ──────────────────────────────────────────────────────────

    def _build_overlay_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)

        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(10, 100)
        self.sld_opacity.setValue(100)
        self.lbl_opacity = QLabel("100%")
        self.sld_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity.setText(f"{v}%")
        )

        self.chk_glow = QCheckBox("Aktifkan Glow Effect")
        self.sld_glow = QSlider(Qt.Orientation.Horizontal)
        self.sld_glow.setRange(0, 100)
        self.sld_glow.setValue(35)
        self.lbl_glow = QLabel("35%")
        self.sld_glow.valueChanged.connect(
            lambda v: self.lbl_glow.setText(f"{v}%")
        )

        self.chk_click_through = QCheckBox("Click Through (mouse menembus overlay)")

        self.cmb_position = QComboBox()
        self.cmb_position.addItems([
            "bottom_center", "top_center", "center",
            "top_left", "top_right", "bottom_left", "bottom_right"
        ])

        self.cmb_subtitle_mode = QComboBox()
        self.cmb_subtitle_mode.addItems(["compact", "standard", "extended"])

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.sld_opacity)
        opacity_row.addWidget(self.lbl_opacity)

        glow_row = QHBoxLayout()
        glow_row.addWidget(self.sld_glow)
        glow_row.addWidget(self.lbl_glow)

        form.addRow("Opacity:", opacity_row)
        form.addRow(self.chk_glow)
        form.addRow("Glow Intensity:", glow_row)
        form.addRow(self.chk_click_through)
        form.addRow("Posisi Subtitle:", self.cmb_position)
        form.addRow("Mode Subtitle:", self.cmb_subtitle_mode)
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: Font
    # ──────────────────────────────────────────────────────────

    def _build_font_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)

        self.spn_font_en = QSpinBox()
        self.spn_font_en.setRange(12, 80)
        self.spn_font_en.setValue(32)
        self.spn_font_en.setSuffix(" px")

        self.spn_font_id = QSpinBox()
        self.spn_font_id.setRange(10, 60)
        self.spn_font_id.setValue(24)
        self.spn_font_id.setSuffix(" px")

        self.spn_anim = QSpinBox()
        self.spn_anim.setRange(50, 1000)
        self.spn_anim.setValue(200)
        self.spn_anim.setSuffix(" ms")

        form.addRow("Ukuran Font (English):", self.spn_font_en)
        form.addRow("Ukuran Font (Terjemahan):", self.spn_font_id)
        form.addRow("Kecepatan Animasi:", self.spn_anim)
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: Translation
    # ──────────────────────────────────────────────────────────

    def _build_translation_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)

        self.chk_translation = QCheckBox("Aktifkan Terjemahan")

        self.cmb_trans_provider = QComboBox()
        self.cmb_trans_provider.addItems([
            "libretranslate", "openai", "deepl", "google"
        ])

        self.cmb_trans_style = QComboBox()
        self.cmb_trans_style.addItems(["natural", "literal", "poetic"])

        form.addRow(self.chk_translation)
        form.addRow("Provider:", self.cmb_trans_provider)
        form.addRow("Gaya Terjemahan:", self.cmb_trans_style)
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: Cache
    # ──────────────────────────────────────────────────────────

    def _build_cache_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel("Cache menyimpan lirik dan terjemahan agar\n"
                      "tidak perlu mengunduh ulang.")
        lbl.setStyleSheet(f"color:{_TEXT_DIM}; font-size:12px;")
        layout.addWidget(lbl)

        btn_clear = QPushButton("🗑  Hapus Semua Cache")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.clicked.connect(self._clear_cache)
        layout.addWidget(btn_clear)

        layout.addStretch()
        return w

    # ──────────────────────────────────────────────────────────
    # Tab: About
    # ──────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("♪ EchoLyrics")
        logo.setStyleSheet(
            f"font-size:28px; font-weight:bold; color:{_ACCENT};"
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        ver = QLabel("Version 1.0.0")
        ver.setStyleSheet(f"color:{_TEXT_DIM}; font-size:13px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel(
            "Subtitle overlay pintar untuk Spotify.\n"
            "Lirik sinkron dengan terjemahan Bahasa Indonesia.\n\n"
            "Dibuat dengan ♥ menggunakan Python & PySide6."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color:{_TEXT}; font-size:13px; line-height:1.6;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()
        return w

    # ──────────────────────────────────────────────────────────
    # Load / Save
    # ──────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        cfg = self._config
        self.chk_startup.setChecked(bool(cfg.get("startup_with_windows")))
        self.cmb_theme.setCurrentText(cfg.get("theme", "dark"))
        self.txt_client_id.setText(cfg.get("spotify_client_id", ""))
        self.txt_client_secret.setText(cfg.get("spotify_client_secret", ""))
        self.sld_opacity.setValue(cfg.get("overlay_opacity", 100))
        self.chk_glow.setChecked(bool(cfg.get("glow_enabled", 1)))
        self.sld_glow.setValue(cfg.get("glow_opacity", 35))
        self.chk_click_through.setChecked(bool(cfg.get("click_through", 1)))
        self.cmb_position.setCurrentText(cfg.get("subtitle_position", "bottom_center"))
        self.cmb_subtitle_mode.setCurrentText(cfg.get("subtitle_mode", "standard"))
        self.spn_font_en.setValue(cfg.get("font_size_english", 32))
        self.spn_font_id.setValue(cfg.get("font_size_translation", 24))
        self.spn_anim.setValue(cfg.get("animation_speed_ms", 200))
        self.chk_translation.setChecked(bool(cfg.get("translation_enabled", 1)))
        self.cmb_trans_provider.setCurrentText(cfg.get("translation_provider", "libretranslate"))
        self.cmb_trans_style.setCurrentText(cfg.get("translation_style", "natural"))

    def _apply_settings(self) -> None:
        cfg = self._config
        cfg.set("startup_with_windows", int(self.chk_startup.isChecked()))
        cfg.set("theme", self.cmb_theme.currentText())
        cfg.set("spotify_client_id", self.txt_client_id.text())
        cfg.set("spotify_client_secret", self.txt_client_secret.text())
        cfg.set("overlay_opacity", self.sld_opacity.value())
        cfg.set("glow_enabled", int(self.chk_glow.isChecked()))
        cfg.set("glow_opacity", self.sld_glow.value())
        cfg.set("click_through", int(self.chk_click_through.isChecked()))
        cfg.set("subtitle_position", self.cmb_position.currentText())
        cfg.set("subtitle_mode", self.cmb_subtitle_mode.currentText())
        cfg.set("font_size_english", self.spn_font_en.value())
        cfg.set("font_size_translation", self.spn_font_id.value())
        cfg.set("animation_speed_ms", self.spn_anim.value())
        cfg.set("translation_enabled", int(self.chk_translation.isChecked()))
        cfg.set("translation_provider", self.cmb_trans_provider.currentText())
        cfg.set("translation_style", self.cmb_trans_style.currentText())

        self.settings_applied.emit(cfg.get_all())
        self.accept()
        app_logger.info("[Settings] Settings saved.")

    def _do_spotify_login(self) -> None:
        # Simpan credentials terlebih dahulu
        self._config.set("spotify_client_id", self.txt_client_id.text())
        self._config.set("spotify_client_secret", self.txt_client_secret.text())
        app_logger.info("[Settings] Spotify login triggered from settings.")
        # Signal ke app untuk trigger login
        self.settings_applied.emit({"action": "spotify_login"})

    def _clear_cache(self) -> None:
        self.settings_applied.emit({"action": "clear_cache"})
        app_logger.info("[Settings] Clear cache requested.")
