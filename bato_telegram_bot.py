async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start"""
    welcome_text = """🤖 BATO MANGA DOWNLOADER BOT v3.1

✨ Support 57 Domain Operational Bato!

📖 CARA PAKAI:
1. Copy link chapter dari Bato
2. Paste link ke chat ini  
3. Bot akan download & kirim PDF

📝 SUPPORT SEMUA FORMAT:
✅ https://bato.si/chapter/123456 (v4)
✅ https://bato.ing/chapter/123456 (v4)
✅ https://nto.to/chapter/789012
✅ https://comiko.org/title/xxx/yyy-ch_1
✅ Semua 57 domain operational!

🔧 FITUR v3.1:
✅ Real-time progress tracking
  📥 Download: ▰▰▰▰▰▱▱▱▱▱ 50%
  📄 PDF: Processing 5/10... 50%
✅ Stitching modes (NEW!)
  • Normal: 15000px chunks
  • Short: 5000px chunks (fast!)
  • Skip: No stitching (fastest!)
✅ Prioritas v4 domains (terbaru)
✅ 5 strategi ekstraksi gambar
✅ Auto test 20+ domain
✅ PDF full-width tanpa margin

⌨️ COMMAND:
/start - Pesan ini
/help - Panduan lengkap
/mode - Pilih stitching mode
/domains - List 57 domain
/test - Test domain v4
/debug [url] - Debug mode

💬 @moonread_channel
"""
    await update.message.reply_text(welcome_text)
