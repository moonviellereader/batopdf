# 🤖 Bato Manga Downloader - Telegram Bot

Bot Telegram untuk download manga dari Bato.ing dan semua domain mirror-nya. Hasil dalam bentuk PDF full-width (tanpa margin).

## ⚡ QUICK START (5 Menit)

### 1. Buat Bot
1. Chat @BotFather di Telegram
2. `/newbot` → Buat bot baru
3. Simpan token yang dikasih

### 2. Install & Run
```bash
pip install -r requirements.txt
python3 bato_telegram_bot.py
```

### 3. Edit Token
Buka `bato_telegram_bot.py`, ganti:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

### 4. Test!
Kirim link chapter ke bot kamu:
```
https://bato.ing/title/123456-manga/123457-ch_1
```

## 🚀 DEPLOY KE CLOUD (24/7)

### Railway.app (Recommended)
1. Upload semua file ke GitHub
2. https://railway.app → New Project
3. Deploy from GitHub
4. Add variable: `BOT_TOKEN` = your token
5. Done! Bot jalan 24/7 gratis

### Render.com
1. https://render.com → New Background Worker
2. Connect repo
3. Add environment variable: `BOT_TOKEN`
4. Deploy!

### PythonAnywhere
1. Upload files ke https://pythonanywhere.com
2. Install dependencies di console
3. Add scheduled task: `python3 bato_telegram_bot.py`

## 📖 FITUR

✅ Support 70+ domain Bato (bato.ing, bato.si, dll)  
✅ PDF full-width tanpa margin  
✅ Auto chunked untuk chapter panjang  
✅ Multi-threaded download (cepat!)  
✅ Gratis & open source  

## 🎯 CARA PAKAI (Untuk User)

1. Search bot di Telegram
2. `/start`
3. Kirim link chapter
4. Terima PDF!

## 📋 COMMANDS

- `/start` - Mulai bot
- `/help` - Bantuan lengkap
- `/status` - Cek status bot

## ⚙️ CONFIGURATION

Edit di `bato_telegram_bot.py`:

```python
MAX_WORKERS = 6          # Download speed (threads)
MAX_FILE_SIZE_MB = 50    # Telegram limit
target_chunk_height = 25000  # PDF chunk size
```

## 🔧 TROUBLESHOOTING

**Bot tidak respon?**
- Cek bot masih running
- Restart: `Ctrl+C` lalu `python3 bato_telegram_bot.py`

**Error "Invalid token"?**
- Copy ulang token dari @BotFather
- Pastikan tidak ada spasi

**Download gagal?**
- Coba link berbeda
- Cek `/status` untuk domain aktif

## 📁 FILE STRUCTURE

```
bato-telegram-bot/
├── bato_telegram_bot.py  # Main bot script
├── requirements.txt      # Dependencies
├── Procfile             # For Railway/Render
├── runtime.txt          # Python version
├── SETUP_GUIDE.md       # Panduan lengkap
└── README.md            # This file
```

## 🆕 UPDATE BOT

```bash
git pull
pip install -r requirements.txt --upgrade
# Restart bot
```

## 📞 SUPPORT

- Channel: @moonread_channel
- Issues: GitHub Issues
- Email: (your email)

## 📄 LICENSE

MIT License - Free to use & modify!

---

**Dibuat dengan ❤️ untuk komunitas manga Indonesia**
