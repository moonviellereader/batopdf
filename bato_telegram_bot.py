#!/usr/bin/env python3
"""
Bato Manga Downloader Telegram Bot
Download manga dari bato.ing dan semua domain mirror-nya
Kirim hasil dalam bentuk PDF full-width
"""

import os
import asyncio
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from io import BytesIO
import zipfile

# ============ CONFIGURATION ============
# Bot token - bisa dari environment variable atau hardcode
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")  # Ganti dengan token dari @BotFather

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BatoDownloader/1.0)"}
REQUEST_TIMEOUT = 10
MAX_WORKERS = 6
TEMP_DIR = "temp_downloads"
MAX_FILE_SIZE_MB = 50  # Telegram limit 50MB

# ALL BATO MIRROR DOMAINS
BATO_DOMAINS = [
    "bato.ing", "bato.si", "fto.to", "ato.to", "dto.to", "hto.to", 
    "jto.to", "lto.to", "mto.to", "nto.to", "vto.to", "wto.to", 
    "xto.to", "yto.to", "vba.to", "wba.to", "xba.to", "yba.to", 
    "zba.to", "kuku.to", "okok.to", "ruru.to", "xdxd.to",
    "bato.to", "bato.ac", "bato.bz", "bato.cc", "bato.cx", 
    "bato.id", "bato.pw", "bato.sh", "bato.vc", "bato.day", 
    "bato.red", "bato.run", "batoto.in", "batoto.tv",
    "batotoo.com", "batotwo.com", "battwo.com", "batpub.com",
    "batread.com", "xbato.com", "xbato.net", "xbato.org",
    "zbato.com", "zbato.net", "zbato.org", "comiko.net",
    "comiko.org", "mangatoto.com", "mangatoto.net",
    "mangatoto.org", "batocomic.com", "batocomic.net",
    "batocomic.org", "readtoto.com", "readtoto.net", "readtoto.org"
]

# ============ HELPER FUNCTIONS ============

def sanitize_filename(name):
    """Clean filename untuk Windows/Linux"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name[:200]

def natural_sort_key(filename):
    """Natural sorting untuk angka"""
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', filename)]

def find_working_domain():
    """Cari domain bato yang aktif"""
    for domain in BATO_DOMAINS[:10]:  # Test 10 domain pertama
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                return domain
        except:
            continue
    return "bato.ing"  # Default

def get_chapter_info(chapter_url, domain):
    """Ambil info chapter dan URL gambar"""
    try:
        # Ganti domain jika perlu
        for d in BATO_DOMAINS:
            if d in chapter_url:
                chapter_url = chapter_url.replace(d, domain)
                break
        
        response = requests.get(chapter_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cari script yang berisi image URLs
        image_urls = []
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'const imgHttps' in script.string:
                matches = re.findall(r'"(https://[^"]+)"', script.string)
                image_urls.extend(matches)
                break
        
        # Cari chapter title
        title_elem = soup.find('h3', class_='nav-title')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Chapter"
        
        return {
            'title': chapter_title,
            'url': chapter_url,
            'images': image_urls
        }
    except Exception as e:
        raise Exception(f"Gagal mengambil chapter: {str(e)}")

def download_image(url, save_path):
    """Download single image"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except:
        return False

def images_to_pdf(image_folder, output_pdf_path, target_chunk_height=25000):
    """Convert images ke PDF full-width (chunked)"""
    try:
        # Get semua image files dengan natural sorting
        image_files = []
        for fname in os.listdir(image_folder):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                image_files.append(os.path.join(image_folder, fname))
        
        image_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        
        if not image_files:
            return False
        
        # Find minimum width
        min_width = None
        for img_path in image_files:
            try:
                with Image.open(img_path) as img:
                    if min_width is None or img.width < min_width:
                        min_width = img.width
            except:
                pass
        
        if min_width is None:
            return False
        
        # Load dan resize semua images
        images = []
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                
                # Resize ke minimum width
                if img.width != min_width:
                    ratio = min_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((min_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert ke RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                images.append(img)
            except Exception as e:
                continue
        
        if not images:
            return False
        
        # Create chunks
        chunks = []
        current_chunk = []
        current_height = 0
        
        for img in images:
            if current_height + img.height > target_chunk_height and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [img]
                current_height = img.height
            else:
                current_chunk.append(img)
                current_height += img.height
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Create stitched images
        stitched_images = []
        for chunk in chunks:
            chunk_height = sum(img.height for img in chunk)
            stitched = Image.new('RGB', (min_width, chunk_height), (255, 255, 255))
            
            y_offset = 0
            for img in chunk:
                stitched.paste(img, (0, y_offset))
                y_offset += img.height
            
            stitched_images.append(stitched)
        
        # Save as PDF
        if stitched_images:
            first_image = stitched_images[0]
            other_images = stitched_images[1:] if len(stitched_images) > 1 else []
            first_image.save(output_pdf_path, 'PDF', resolution=100.0, save_all=True, append_images=other_images)
            return True
        
        return False
    except Exception as e:
        print(f"PDF conversion error: {e}")
        return False

# ============ BOT HANDLERS ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start"""
    welcome_text = """
🤖 **Bato Manga Downloader Bot**

Kirim link chapter dari Bato untuk download manga dalam bentuk PDF!

**Cara pakai:**
1️⃣ Copy link chapter dari bato.ing (atau mirror lainnya)
2️⃣ Paste link ke chat ini
3️⃣ Bot akan download & kirim PDF

**Contoh link:**
• `https://bato.ing/title/123456-manga-name/123457-ch_1`
• `https://bato.si/chapter/789012`

**Fitur:**
✅ Support semua domain Bato
✅ PDF full-width (tanpa margin)
✅ Auto chunked untuk chapter panjang
✅ Gratis & cepat!

**Command:**
/start - Lihat pesan ini
/help - Bantuan
/status - Status bot

**Support:** @moonread_channel
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help"""
    help_text = """
📖 **PANDUAN LENGKAP**

**1. Cara Download Chapter:**
Kirim link chapter, contoh:
`https://bato.ing/title/12345-manga/67890-ch_1`

Bot akan otomatis:
• Cek domain yang aktif
• Download semua gambar
• Convert ke PDF full-width
• Kirim ke kamu!

**2. Format PDF:**
• Full-width (seperti Oak Tree)
• Tanpa margin putih
• Chunked otomatis untuk chapter panjang
• Ukuran optimal untuk mobile

**3. Batasan:**
• Max 50MB per file (limit Telegram)
• Jika lebih, akan dikirim sebagai ZIP

**4. Domain Support:**
bato.ing, bato.si, bato.to, comiko.org, dll
(70+ domain mirror!)

**Butuh bantuan?**
Hubungi @moonread_channel
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /status"""
    working_domain = find_working_domain()
    status_text = f"""
✅ **Bot Status: ONLINE**

🌐 Domain aktif: `{working_domain}`
📁 Temp folder: OK
🤖 Version: 1.0

Bot siap menerima request! 🚀
"""
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk URL chapter"""
    url = update.message.text.strip()
    
    # Check apakah valid bato URL
    is_bato_url = any(domain in url for domain in BATO_DOMAINS)
    if not is_bato_url or 'chapter' not in url.lower():
        await update.message.reply_text(
            "❌ Link tidak valid!\n\n"
            "Kirim link chapter dari Bato, contoh:\n"
            "`https://bato.ing/title/123456-manga/123457-ch_1`",
            parse_mode='Markdown'
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("⏳ Memproses request...")
    
    try:
        # Find working domain
        await status_msg.edit_text("🔍 Mencari domain aktif...")
        working_domain = find_working_domain()
        
        # Get chapter info
        await status_msg.edit_text("📥 Mengambil informasi chapter...")
        chapter_info = get_chapter_info(url, working_domain)
        
        if not chapter_info['images']:
            await status_msg.edit_text("❌ Tidak ada gambar ditemukan!")
            return
        
        total_images = len(chapter_info['images'])
        chapter_title = sanitize_filename(chapter_info['title'])
        
        # Create temp directory
        user_id = update.effective_user.id
        temp_folder = os.path.join(TEMP_DIR, f"user_{user_id}_{chapter_title}")
        os.makedirs(temp_folder, exist_ok=True)
        
        # Download images
        await status_msg.edit_text(f"📥 Downloading {total_images} gambar...\n0/{total_images}")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        downloaded = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for idx, img_url in enumerate(chapter_info['images'], 1):
                save_path = os.path.join(temp_folder, f"{idx:04d}.jpg")
                future = executor.submit(download_image, img_url, save_path)
                futures.append(future)
            
            for future in futures:
                if future.result():
                    downloaded += 1
                    if downloaded % 10 == 0 or downloaded == total_images:
                        await status_msg.edit_text(
                            f"📥 Downloading gambar...\n{downloaded}/{total_images} ✓"
                        )
        
        if downloaded == 0:
            await status_msg.edit_text("❌ Gagal download gambar!")
            shutil.rmtree(temp_folder, ignore_errors=True)
            return
        
        # Convert to PDF
        await status_msg.edit_text(f"📄 Membuat PDF... ({downloaded} gambar)")
        pdf_path = os.path.join(TEMP_DIR, f"{chapter_title}.pdf")
        
        success = images_to_pdf(temp_folder, pdf_path)
        
        if not success:
            await status_msg.edit_text("❌ Gagal membuat PDF!")
            shutil.rmtree(temp_folder, ignore_errors=True)
            return
        
        # Check file size
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            # Send as ZIP instead
            await status_msg.edit_text(f"📦 File terlalu besar ({file_size_mb:.1f}MB), membuat ZIP...")
            zip_path = os.path.join(TEMP_DIR, f"{chapter_title}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(pdf_path, os.path.basename(pdf_path))
            
            await status_msg.edit_text("📤 Mengirim file...")
            
            with open(zip_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{chapter_title}.zip",
                    caption=f"✅ {chapter_info['title']}\n\n"
                            f"📊 {downloaded} gambar\n"
                            f"📦 Size: {file_size_mb:.1f}MB (compressed)\n\n"
                            f"⚠️ File dikompres karena >50MB"
                )
            
            os.remove(zip_path)
        else:
            # Send PDF
            await status_msg.edit_text("📤 Mengirim PDF...")
            
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{chapter_title}.pdf",
                    caption=f"✅ {chapter_info['title']}\n\n"
                            f"📄 PDF Full-Width\n"
                            f"📊 {downloaded} gambar\n"
                            f"📦 Size: {file_size_mb:.1f}MB\n\n"
                            f"Powered by @moonread_channel"
                )
        
        # Cleanup
        await status_msg.delete()
        shutil.rmtree(temp_folder, ignore_errors=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}\n\nCoba lagi atau hubungi admin.")
        print(f"Error: {e}")

# ============ MAIN ============

def main():
    """Start bot"""
    print("🤖 Starting Bato Manga Downloader Bot...")
    
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("✅ Bot running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
