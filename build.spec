# -*- mode: python ; coding: utf-8 -*-
"""
EchoLyrics — PyInstaller Build Spec
=====================================
Jalankan: pyinstaller build.spec --clean
Output:   dist/EchoLyrics.exe  (single file, tidak perlu Python terinstall)
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Resources: icon
        (str(ROOT / 'resources' / 'icon.ico'), 'resources'),
        # Docs (opsional)
        # (str(ROOT / 'docs'), 'docs'),
    ],
    hiddenimports=[
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        # Backend modules
        'backend.events.event_bus',
        'backend.events.event_types',
        'backend.spotify.windows_media_provider',
        'backend.spotify.spotify_service',
        'backend.spotify.playback',
        'backend.spotify.client',
        'backend.spotify.auth',
        'backend.spotify.token_manager',
        'backend.lyrics.lyrics_service',
        'backend.lyrics.lrclib_provider',
        'backend.lyrics.timeline_engine',
        'backend.lyrics.parser',
        'backend.lyrics.validator',
        'backend.lyrics.auto_sync',
        'backend.translate.translation_service',
        'backend.translate.providers.google_provider',
        'backend.translate.providers.mymemory_provider',
        'backend.translate.language_detector',
        'backend.translate.formatter',
        'backend.database.db_manager',
        'backend.database.migrations',
        'backend.database.repositories.track_repo',
        'backend.database.repositories.lyrics_repo',
        'backend.database.repositories.translation_repo',
        'backend.database.repositories.settings_repo',
        'backend.config.config_manager',
        'backend.models.models',
        'backend.logger.app_logger',
        'backend.scheduler.scheduler',
        'backend.utils.timer_helper',
        'frontend.overlay.overlay_window',
        'frontend.overlay.overlay_controller',
        'frontend.overlay.clickthrough',
        'frontend.tray.system_tray',
        'frontend.windows.settings_window',
        'frontend.windows.full_lyrics_window',
        'app.app',
        # Dependencies
        'langdetect',
        'cryptography',
        'cryptography.hazmat.primitives.ciphers.aead',
        'requests',
        'loguru',
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt6',
        'openai',
        'deepl',
        'httpx',
        'pytest',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EchoLyrics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # Tampil console window untuk debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'resources' / 'icon.ico'),   # Icon app
    version_file=None,
    uac_admin=False,
)
