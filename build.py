"""
EchoLyrics — Build Script
===========================
Script otomatis untuk build Windows executable.

Cara pakai:
    python build.py

Output:
    dist/EchoLyrics.exe  — Single file executable (tidak butuh Python)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build_tmp"


def run(cmd: list, **kwargs):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def check_pyinstaller():
    """Install PyInstaller jika belum ada."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} sudah terinstall.")
    except ImportError:
        print("[...] PyInstaller belum ada, menginstall...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])


def clean():
    """Hapus folder build lama."""
    for folder in [DIST, BUILD]:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"[...] Cleaned: {folder}")


def build():
    """Jalankan PyInstaller."""
    run([
        sys.executable, "-m", "PyInstaller",
        "build.spec",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        "--log-level=WARN",
    ], cwd=ROOT)


def report():
    """Laporan hasil build."""
    exe = DIST / "EchoLyrics.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1024 / 1024
        print(f"\n{'='*50}")
        print(f"  BUILD BERHASIL!")
        print(f"{'='*50}")
        print(f"  File : {exe}")
        print(f"  Size : {size_mb:.1f} MB")
        print(f"\n  Jalankan: {exe}")
        print(f"{'='*50}\n")
    else:
        print("\nERROR: dist/EchoLyrics.exe tidak ditemukan!")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("  EchoLyrics Windows Build")
    print("=" * 50)

    check_pyinstaller()
    clean()
    build()
    report()
