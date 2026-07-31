# 📋 Panduan Setup & Testing EchoLyrics

## Status Install

### Cek Semua Dependency

Jalankan di terminal dari folder `e:\projects\jlyrics`:

```powershell
pip show PySide6 loguru cryptography requests langdetect pywin32
```

Jika semua sudah tampil, lanjut ke langkah berikutnya.

---

## 🎯 Setup Awal (WAJIB)

### Step 1 — Daftar Spotify App

1. Buka browser → [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Login dengan akun Spotify kamu
3. Klik **"Create app"**
4. Isi:
   - **App name**: `EchoLyrics`
   - **App description**: `Lyrics overlay app`
   - **Redirect URIs**: `http://127.0.0.1:8765/callback` ← **Gunakan 127.0.0.1**
5. Centang **Web API**
6. Klik **Save**
7. Klik **Settings** → salin **Client ID** dan **Client Secret**

---

### Step 2 — Jalankan Aplikasi

```powershell
cd e:\projects\jlyrics
python main.py
```

Saat pertama kali:
- Ikon `♪` hijau muncul di System Tray (pojok kanan bawah taskbar)
- Jendela Settings terbuka otomatis (karena Client ID belum diset)

---

### Step 3 — Isi Spotify Credentials

Di jendela Settings yang terbuka:
1. Klik tab **"Spotify"**
2. Isi **Client ID** → paste dari dashboard Spotify
3. Isi **Client Secret** → paste dari dashboard Spotify
4. Klik **"🔑 Login Spotify"**
5. Browser akan terbuka → Login → Klik **"Agree"**
6. Browser menampilkan "✅ Login berhasil!" → tutup tab

---

### Step 4 — Mulai Mendengarkan

1. Buka **Spotify Desktop** (bukan web)
2. Putar lagu apapun
3. Dalam 2-3 detik, **subtitle akan muncul di layar**!
4. Baris Indonesia muncul di bawah baris English

---

## 🧪 Testing Tanpa PySide6 (Backend Only)

Jika PySide6 belum selesai download, kamu bisa test backend:

```powershell
cd e:\projects\jlyrics
python tests/test_basic.py
```

**Expected output:**
```
=== Test 1: LRC Parser ===
Parsed 7 lines
  [12.50s] I found a love for me
  ...

=== Test 2: Validator ===
Validation result: ValidationResult.VALID

=== Test 3: Timeline Engine ===
Timeline built: 7 lines

After seek to 36s: current = ''Cause we were just kids when we fell in love'

=== All Tests PASSED! ===
```

---

## 🔬 Test LRCLIB (Perlu Internet)

```python
# Buat file test_lrclib.py di folder tests/
import sys
sys.path.insert(0, r'e:\projects\jlyrics')
from backend.lyrics.lrclib_provider import LRCLibProvider

provider = LRCLibProvider()
lrc = provider.fetch(
    artist="Ed Sheeran",
    title="Perfect",
    duration_ms=255000
)
if lrc:
    print("LRCLIB berhasil!")
    print(lrc[:300])
else:
    print("Tidak ditemukan")
```

Jalankan: `python tests/test_lrclib.py`

---

## 🖥️ Test Database

```python
import sys
sys.path.insert(0, r'e:\projects\jlyrics')
from backend.database.db_manager import DatabaseManager

db = DatabaseManager.instance()
tables = db.execute_read("SELECT name FROM sqlite_master WHERE type='table'")
for t in tables:
    print("Table:", t['name'])
```

Database tersimpan di: `%LOCALAPPDATA%\EchoLyrics\cache\echolyrics.db`

---

## ⌨️ Shortcut Keyboard

| Shortcut | Fungsi |
|----------|--------|
| Klik kanan tray → Show Overlay | Tampilkan subtitle |
| Klik kanan tray → Hide Overlay | Sembunyikan subtitle |
| Klik kanan tray → Settings | Buka pengaturan |
| Klik kanan tray → Full Lyrics | Jendela lirik lengkap |
| Klik kanan tray → Refresh Spotify | Reconnect Spotify |
| Klik kanan tray → Clear Cache | Hapus semua cache |
| Klik kanan tray → Exit | Keluar |
| Double-click ikon tray | Buka Settings |

---

## 🐛 Troubleshooting

### Subtitle tidak muncul
- Pastikan **Spotify Desktop** berjalan (bukan web player)
- Pastikan **login Spotify** sudah dilakukan
- Klik kanan tray → **Refresh Spotify**
- Cek log: `logs/YYYY-MM-DD.log`

### "No module named PySide6"
PySide6 masih download (168 MB), tunggu sebentar lalu coba lagi:
```powershell
pip show PySide6
python main.py
```

### Error login Spotify
- Pastikan Redirect URI **persis**: `http://localhost:8765/callback`
- Pastikan port 8765 tidak diblok firewall

### Lirik tidak ditemukan
- Beberapa lagu langka tidak ada di LRCLIB
- Untuk lagu Indonesia/lokal, coverage lebih sedikit
- Cek log: `logs/YYYY-MM-DD.log`

---

## 📁 Struktur Database

Database di `%LOCALAPPDATA%\EchoLyrics\cache\echolyrics.db`:

| Tabel | Isi |
|-------|-----|
| `tracks` | Metadata lagu yang pernah diputar |
| `lyrics` | Baris lirik dengan timestamp |
| `translations` | Terjemahan Bahasa Indonesia |
| `settings` | Semua pengaturan aplikasi |
| `cache` | Cache metadata |
| `providers` | Provider lirik (LRCLIB, dll) |
| `migration_history` | Versi database |

---

## 🔄 Reset Aplikasi

Hapus database (semua cache hilang):
```powershell
Remove-Item "$env:LOCALAPPDATA\EchoLyrics\cache\echolyrics.db"
```

Hapus token Spotify (perlu login ulang):
```powershell
Remove-Item "$env:LOCALAPPDATA\EchoLyrics\config\token.dat"
```

---

## ✅ Checklist Sebelum Jalankan

- [ ] `pip show PySide6` → terinstall
- [ ] `pip show loguru cryptography requests langdetect` → semua terinstall
- [ ] Spotify app sudah dibuat di dashboard
- [ ] Client ID dan Secret sudah disiapkan
- [ ] Spotify Desktop sudah terinstall di komputer
