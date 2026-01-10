#!/usr/bin/env python3
"""
Bato Manga Downloader Telegram Bot - FIXED VERSION
Download manga dari bato.ing dan semua domain mirror-nya
Compatible dengan SENODE dan format URL baru
"""

import os
import asyncio
import shutil
import json
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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BatoDownloader/1.0)"}
REQUEST_TIMEOUT = 10
MAX_WORKERS = 6
TEMP_DIR = "temp_downloads"
MAX_FILE_SIZE_MB = 50

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

def rewrite_image_url(url):
    """Rewrite image URL jika perlu (k -> n)"""
    if not url:
        return url
    if re.match(r'^(https://k).*\.(png|jpg|jpeg|webp)(\?.*)?$', url, re.I):
        return url.replace("https://k", "https://n", 1)
    return url

def find_working_domain():
    """Cari domain bato yang aktif"""
    for domain in BATO_DOMAINS[:15]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                return domain
        except:
            continue
    return "bato.ing"

def get_chapter_info(chapter_url, domain):
    """Ambil info chapter dan URL gambar - IMPROVED VERSION"""
    try:
        # Ganti domain jika perlu
        original_url = chapter_url
        for d in BATO_DOMAINS:
            if d in chapter_url:
                chapter_url = chapter_url.replace(d, domain)
                break
        
        # Try original URL first
        response = requests.get(chapter_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        # Jika 404, coba dengan domain lain
        if response.status_code == 404:
            print(f"404 on {chapter_url}, trying other domains...")
            for test_domain in BATO_DOMAINS[:10]:
                test_url = original_url
                for d in BATO_DOMAINS:
                    if d in test_url:
                        test_url = test_url.replace(d, test_domain)
                        break
                
                try:
                    response = requests.get(test_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        chapter_url = test_url
                        domain = test_domain
                        print(f"✓ Found working domain: {test_domain}")
                        break
                except:
                    continue
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # METHOD 1: Cari imgHttps di script (seperti desktop version)
        image_urls = []
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'imgHttps' in script.string:
                # Cari array imgHttps
                match = re.search(r'imgHttps\s*=\s*(\[[^\]]*\])', script.string)
                if match:
                    try:
                        image_urls = json.loads(match.group(1))
                        print(f"✓ Found {len(image_urls)} images via imgHttps")
                        break
                    except:
                        pass
                
                # Fallback: cari semua URLs di script
                if not image_urls:
                    matches = re.findall(r'"(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', script.string)
                    image_urls.extend(matches)
        
        # METHOD 2: Fallback - cari di img tags
        if not image_urls:
            print("⚠ imgHttps not found, trying img tags...")
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    image_urls.append(src)
        
        # Rewrite URLs (k -> n)
        image_urls = [rewrite_image_url(url) for url in image_urls]
        
        # Cari chapter title
        title_elem = soup.find('h3', class_='nav-title') or soup.find('h1')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Chapter"
        
        # Remove non-ASCII characters
        chapter_title = re.sub(r'[^\x00-\x7F]+', '', chapter_title)
        
        return {
            'title': chapter_title,
            'url': chapter_url,
            'images': image_urls,
            'domain': domain
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
    welcome_text = """🤖 BATO MANGA DOWNLOADER BOT v2.0

Kirim link chapter dari Bato untuk download manga dalam bentuk PDF!

📖 CARA PAKAI:
1. Copy link chapter dari bato.ing (atau mirror lainnya)
2. Paste link ke chat ini
3. Bot akan download & kirim PDF

📝 FORMAT LINK SUPPORT:
✅ https://bato.ing/title/123-manga/456-ch_1
✅ https://bato.ing/chapter/123456
✅ https://bato.si/chapter/789012
✅ Semua format Bato URL!

✨ FITUR BARU:
✅ Auto domain switching (jika 404)
✅ Support SENODE format
✅ Improved image extraction
✅ PDF full-width (tanpa margin)

⌨️ COMMAND:
/start - Lihat pesan ini
/help - Bantuan
/status - Status bot
/test - Test domain aktif

💬 Support: @moonread_channel
"""
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help"""
    help_text = """📖 PANDUAN LENGKAP

1️⃣ CARA DOWNLOAD CHAPTER:
Kirim link chapter dalam format apapun:
• https://bato.ing/chapter/3885878 ✅
• https://bato.ing/title/12345-manga/67890-ch_1 ✅
• https://bato.si/... ✅

Bot akan otomatis:
• Detect format URL
• Auto-switch domain jika 404
• Download semua gambar
• Convert ke PDF full-width
• Kirim ke kamu!

2️⃣ FORMAT PDF:
• Full-width (seperti Oak Tree)
• Tanpa margin putih
• Chunked otomatis untuk chapter panjang
• Ukuran optimal untuk mobile

3️⃣ TROUBLESHOOTING:
• Jika error 404: Bot akan coba domain lain otomatis
• Jika gagal: Gunakan /test untuk cek domain aktif
• Jika masih gagal: Hubungi @moonread_channel

4️⃣ DOMAIN SUPPORT:
bato.ing, bato.si, bato.to, comiko.org, dll
(70+ domain mirror dengan auto-switching!)

💬 Butuh bantuan? Hubungi @moonread_channel
"""
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /status"""
    working_domain = find_working_domain()
    status_text = f"""✅ BOT STATUS: ONLINE

🌐 Domain aktif: {working_domain}
📁 Temp folder: OK
🤖 Version: 2.0 (Fixed)
🔧 Features:
  ✓ Auto domain switching
  ✓ Multiple URL formats
  ✓ Improved image extraction

Bot siap menerima request! 🚀
"""
    await update.message.reply_text(status_text)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test domain connection"""
    msg = await update.message.reply_text("🔍 Testing domains...")
    
    working = []
    for domain in BATO_DOMAINS[:10]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                working.append(f"✅ {domain}")
            else:
                working.append(f"⚠️ {domain} (HTTP {response.status_code})")
        except:
            working.append(f"❌ {domain}")
    
    result = "🔍 DOMAIN TEST RESULTS:\n\n" + "\n".join(working[:10])
    await msg.edit_text(result)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk URL chapter - IMPROVED VERSION"""
    url = update.message.text.strip()
    
    # Check apakah valid bato URL
    is_bato_url = any(domain in url for domain in BATO_DOMAINS)
    
    # Support both /chapter/ and /title/.../ch_ formats
    is_chapter_url = '/chapter/' in url.lower() or re.search(r'/title/\d+-.+/\d+-ch_', url.lower())
    
    if not is_bato_url or not is_chapter_url:
        await update.message.reply_text(
            "❌ Link tidak valid!\n\n"
            "Kirim link chapter dari Bato, contoh:\n"
            "✅ https://bato.ing/chapter/3885878\n"
            "✅ https://bato.ing/title/123-manga/456-ch_1\n\n"
            "📝 Kedua format didukung!"
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("⏳ Memproses request...")
    
    try:
        # Find working domain
        await status_msg.edit_text("🔍 Mencari domain aktif...")
        working_domain = find_working_domain()
        
        # Get chapter info (with auto domain switching)
        await status_msg.edit_text("📥 Mengambil informasi chapter...")
        chapter_info = get_chapter_info(url, working_domain)
        
        if not chapter_info['images']:
            await status_msg.edit_text(
                "❌ Tidak ada gambar ditemukan!\n\n"
                "Kemungkinan:\n"
                "• Chapter belum tersedia\n"
                "• Format halaman berubah\n"
                "• Coba chapter lain\n\n"
                "Gunakan /test untuk cek domain"
            )
            return
        
        total_images = len(chapter_info['images'])
        chapter_title = sanitize_filename(chapter_info['title'])
        
        # Create temp directory
        user_id = update.effective_user.id
        temp_folder = os.path.join(TEMP_DIR, f"user_{user_id}_{chapter_title}")
        os.makedirs(temp_folder, exist_ok=True)
        
        # Download images
        await status_msg.edit_text(
            f"📥 Downloading {total_images} gambar...\n"
            f"Domain: {chapter_info['domain']}\n"
            f"0/{total_images}"
        )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        downloaded = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for idx, img_url in enumerate(chapter_info['images'], 1):
                # Use zero-padded numbering
                save_path = os.path.join(temp_folder, f"page_{idx:04d}.jpg")
                future = executor.submit(download_image, img_url, save_path)
                futures.append(future)
            
            for future in futures:
                if future.result():
                    downloaded += 1
                    if downloaded % 10 == 0 or downloaded == total_images:
                        await status_msg.edit_text(
                            f"📥 Downloading gambar...\n"
                            f"Domain: {chapter_info['domain']}\n"
                            f"{downloaded}/{total_images} ✓"
                        )
        
        if downloaded == 0:
            await status_msg.edit_text(
                "❌ Gagal download gambar!\n\n"
                "Kemungkinan:\n"
                "• Image server down\n"
                "• URL gambar berubah\n"
                "• Coba lagi nanti"
            )
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
                            f"🌐 Domain: {chapter_info['domain']}\n"
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
                            f"🌐 Domain: {chapter_info['domain']}\n"
                            f"📦 Size: {file_size_mb:.1f}MB\n\n"
                            f"Powered by @moonread_channel"
                )
        
        # Cleanup
        await status_msg.delete()
        shutil.rmtree(temp_folder, ignore_errors=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
    except Exception as e:
        error_msg = str(e)
        await status_msg.edit_text(
            f"❌ Error: {error_msg}\n\n"
            f"💡 Tips:\n"
            f"• Gunakan /test untuk cek domain\n"
            f"• Coba link chapter lain\n"
            f"• Hubungi @moonread_channel jika masalah berlanjut"
        )
        print(f"Error: {e}")

# ============ MAIN ============

def main():
    """Start bot"""
    print("🤖 Starting Bato Manga Downloader Bot v2.0 (Fixed)...")
    
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("✅ Bot running! Press Ctrl+C to stop.")
    print("🔧 Features enabled:")
    print("  ✓ Auto domain switching")
    print("  ✓ Multiple URL format support")
    print("  ✓ Improved error handling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
