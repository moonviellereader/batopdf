# 🤖 PANDUAN SETUP TELEGRAM BOT - Bato Manga Downloader

## 📋 DAFTAR ISI
1. [Buat Bot di Telegram](#1-buat-bot-di-telegram)
2. [Setup di Komputer/Server](#2-setup-di-komputerserver)
3. [Deploy ke Cloud (GRATIS)](#3-deploy-ke-cloud-gratis)
4. [Cara Pakai Bot](#4-cara-pakai-bot)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. BUAT BOT DI TELEGRAM

### Step 1: Buka BotFather
1. Buka Telegram
2. Search: **@BotFather**
3. Klik Start

### Step 2: Buat Bot Baru
1. Kirim: `/newbot`
2. Masukkan nama bot (contoh: `Moonread Manga Bot`)
3. Masukkan username (harus diakhiri "bot", contoh: `moonread_manga_bot`)

### Step 3: Simpan Token
BotFather akan kasih token seperti ini:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
```
**SIMPAN TOKEN INI!** Jangan kasih ke orang lain!

### Step 4: Customize Bot (Opsional)
```
/setdescription - Deskripsi bot
/setabouttext - About bot
/setuserpic - Upload foto profil bot
```

---

## 2. SETUP DI KOMPUTER/SERVER

### A. Install Python (Jika belum ada)
- **Windows**: Download dari https://python.org
- **Linux/Mac**: Biasanya sudah terinstall

Cek dengan:
```bash
python3 --version
```

### B. Install Dependencies

#### Windows:
```cmd
cd path\to\bot\folder
pip install -r requirements.txt
```

#### Linux/Mac:
```bash
cd /path/to/bot/folder
pip3 install -r requirements.txt
```

### C. Edit File Bot

1. Buka `bato_telegram_bot.py`
2. Cari baris ini di bagian atas:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```
3. Ganti dengan token dari BotFather:
```python
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
```
4. Save file

### D. Jalankan Bot

#### Windows:
```cmd
python bato_telegram_bot.py
```

#### Linux/Mac:
```bash
python3 bato_telegram_bot.py
```

Jika sukses, akan muncul:
```
🤖 Starting Bato Manga Downloader Bot...
✅ Bot running! Press Ctrl+C to stop.
```

**CATATAN:** Bot hanya jalan selama program berjalan. Jika komputer dimatikan, bot akan mati.

---

## 3. DEPLOY KE CLOUD (GRATIS)

Biar bot jalan 24/7 tanpa komputer nyala terus!

### OPSI A: Railway.app (RECOMMENDED) ⭐

#### Step 1: Buat Procfile
Buat file baru bernama `Procfile` (tanpa ekstensi) dengan isi:
```
worker: python3 bato_telegram_bot.py
```

#### Step 2: Buat runtime.txt
Buat file baru bernama `runtime.txt` dengan isi:
```
python-3.11.7
```

#### Step 3: Deploy ke Railway
1. Buka https://railway.app
2. Login dengan GitHub
3. Klik "New Project" → "Deploy from GitHub repo"
4. Upload semua file:
   - `bato_telegram_bot.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
5. Di Variables, tambahkan:
   - Key: `BOT_TOKEN`
   - Value: Token dari BotFather
6. Klik Deploy!

**Free tier:** 500 jam/bulan (cukup untuk 24/7!)

---

### OPSI B: Render.com

#### Step 1: Persiapan File
Pastikan punya file:
- `bato_telegram_bot.py`
- `requirements.txt`
- Edit bot jangan hardcode token, tapi pakai environment variable:

```python
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
```

#### Step 2: Deploy
1. Buka https://render.com
2. Sign up gratis
3. New → Background Worker
4. Connect GitHub repo atau upload manual
5. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python3 bato_telegram_bot.py`
6. Environment Variables:
   - `BOT_TOKEN` = token dari BotFather
7. Deploy!

**Free tier:** Unlimited (tapi suspend setelah 15 menit idle)

---

### OPSI C: PythonAnywhere (Paling Mudah)

#### Step 1: Sign Up
1. Buka https://pythonanywhere.com
2. Sign up gratis

#### Step 2: Upload Files
1. Dashboard → Files
2. Upload:
   - `bato_telegram_bot.py`
   - `requirements.txt`

#### Step 3: Install Dependencies
1. Dashboard → Consoles → Bash
2. Jalankan:
```bash
pip3 install --user -r requirements.txt
```

#### Step 4: Jalankan Bot
1. Dashboard → Tasks
2. Add new task:
   - Time: @reboot
   - Command: `python3 /home/username/bato_telegram_bot.py`
3. Save!

**Free tier:** 1 always-on task

---

### OPSI D: VPS Gratis (Oracle Cloud)

1. Daftar https://oracle.com/cloud/free
2. Buat VM Ubuntu gratis (Always Free tier)
3. SSH ke server:
```bash
ssh ubuntu@your-server-ip
```
4. Install Python & dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install -r requirements.txt
```
5. Jalankan bot:
```bash
nohup python3 bato_telegram_bot.py &
```

---

## 4. CARA PAKAI BOT

### Untuk User:
1. Search bot di Telegram (username yang kamu buat)
2. Klik Start
3. Kirim link chapter, contoh:
   ```
   https://bato.ing/title/123456-manga-name/123457-ch_1
   ```
4. Bot akan otomatis download & kirim PDF!

### Commands:
- `/start` - Mulai bot
- `/help` - Panduan lengkap
- `/status` - Cek status bot

---

## 5. TROUBLESHOOTING

### Problem: Bot tidak respon
**Solusi:**
- Cek bot masih running (`python3 bato_telegram_bot.py`)
- Cek token benar
- Restart bot

### Problem: Error "Invalid token"
**Solusi:**
- Copy ulang token dari @BotFather
- Pastikan tidak ada spasi di awal/akhir token

### Problem: Error "Module not found"
**Solusi:**
```bash
pip3 install -r requirements.txt --upgrade
```

### Problem: PDF terlalu besar (>50MB)
**Solusi:**
- Bot akan otomatis kirim sebagai ZIP
- Atau edit di kode untuk split PDF

### Problem: Download gagal
**Solusi:**
- Tunggu beberapa menit (server bato mungkin lambat)
- Coba link yang berbeda
- Cek `/status` untuk cek domain aktif

---

## 6. CUSTOMIZATION

### Ubah Ukuran Chunk PDF:
Di file `bato_telegram_bot.py`, cari:
```python
def images_to_pdf(image_folder, output_pdf_path, target_chunk_height=25000):
```
Ubah `25000` jadi lebih kecil (misal `15000`) untuk file lebih kecil.

### Ubah Max Workers (Speed):
```python
MAX_WORKERS = 6  # Ubah jadi 10 untuk lebih cepat (butuh RAM lebih)
```

### Tambah Watermark:
Bisa tambahkan teks di setiap gambar sebelum convert ke PDF.

---

## 7. SHARE BOT KE USER

Setelah deploy, share ke user dengan cara:
1. Kirim link: `https://t.me/your_bot_username`
2. Atau kasih QR code
3. Promosi di channel Telegram

---

## 8. MONITORING

### Cek Log Error:
Jika deploy di Railway/Render, cek di dashboard → Logs

### Track Usage:
Tambahkan logging untuk track berapa user & download:
```python
print(f"[{datetime.now()}] User {user_id} downloaded: {chapter_title}")
```

---

## 9. UPGRADE (Berbayar)

Jika bot ramai, upgrade ke:
- **Railway Pro:** $5/bulan (unlimited)
- **Render Paid:** $7/bulan (auto-scale)
- **VPS DigitalOcean:** $6/bulan

---

## 📞 SUPPORT

Jika ada masalah:
1. Cek troubleshooting di atas
2. Restart bot
3. Hubungi @moonread_channel

---

## ✅ CHECKLIST DEPLOY

- [ ] Buat bot di @BotFather
- [ ] Simpan token
- [ ] Download file bot
- [ ] Install dependencies
- [ ] Edit token di file
- [ ] Test lokal
- [ ] Deploy ke cloud
- [ ] Share ke user!

---

**SELAMAT!** Bot kamu sudah siap dipakai! 🎉

Share link bot: `https://t.me/your_bot_username`
