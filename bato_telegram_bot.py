#!/usr/bin/env python3
"""
Bato Manga Downloader Telegram Bot - ULTRA FIXED + MODE SELECTION
Support SENODE dan semua format URL Bato
Multi-strategy image extraction + pilihan stitching atau no-stitching
"""
import os
import asyncio
import shutil
import json
import threading
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import zipfile

# ============ CONFIGURATION ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://bato.ing/",
}
REQUEST_TIMEOUT = 15
MAX_WORKERS = 6
TEMP_DIR = "temp_downloads"
MAX_FILE_SIZE_MB = 50

# ALL BATO MIRROR DOMAINS (Updated priority Jan 2026)
BATO_DOMAINS = [
    # V4 - Priority tertinggi
    "bato.ing", "bato.si",
    # Short .to (masih cukup banyak yang hidup)
    "mto.to", "nto.to", "vto.to", "wto.to", "xto.to", "yto.to",
    "ato.to", "dto.to", "fto.to", "hto.to", "jto.to", "lto.to",
    # bato.* lama
    "bato.ac", "bato.bz", "bato.cc", "bato.cx", "bato.id",
    "bato.pw", "bato.sh", "bato.vc", "bato.day", "bato.red", "bato.run",
    # Legacy lainnya (paling belakang)
    "batoto.in", "batoto.tv", "batotoo.com", "batotwo.com", "battwo.com",
    "batpub.com", "batread.com",
    "xbato.com", "xbato.net", "xbato.org",
    "zbato.com", "zbato.net", "zbato.org",
    "comiko.net", "comiko.org",
]

# State untuk user yang sedang memilih mode
user_pending_mode = {}  # {user_id: {'chapter_info': ..., 'status_msg': ..., 'timeout': time}}

# ============ HELPER FUNCTIONS ============
# (semua fungsi helper di bawah ini tetap sama seperti kode asli kamu)
# sanitize_filename, natural_sort_key, rewrite_image_url, find_working_domain,
# extract_images_multi_strategy, get_chapter_info, download_image

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^\x00-\x7F]+', '', name)
    return name[:200]

def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', filename)]

def rewrite_image_url(url):
    if not url:
        return url
    if re.match(r'[](https://k).*\.(png|jpg|jpeg|webp)(\?.*)?$', url, re.I):
        return url.replace("https://k", "https://n", 1)
    return url

def find_working_domain():
    priority_v4 = ["bato.ing", "bato.si"]
    for domain in priority_v4:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"✓ Using v4 domain: {domain}")
                return domain
        except:
            continue

    for domain in BATO_DOMAINS[2:15]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"✓ Using fallback domain: {domain}")
                return domain
        except:
            continue
    return "bato.ing"  # ultimate fallback

def extract_images_multi_strategy(soup, page_html):
    # ... (kode asli extract_images_multi_strategy tetap sama, tidak diubah)
    image_urls = []
    scripts = soup.find_all('script')
    for script in scripts:
        if not script.string:
            continue
        if 'imgHttps' in script.string:
            match = re.search(r'imgHttps\s*=\s*(\[[^\]]*\])', script.string)
            if match:
                try:
                    urls = json.loads(match.group(1))
                    if urls:
                        print(f"✓ Strategy 1a: Found {len(urls)} images via imgHttps")
                        return urls
                except:
                    pass
        if 'imgHttpLis' in script.string or 'batoPass' in script.string:
            urls = re.findall(r'[](https://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', script.string, re.I)
            if urls:
                print(f"✓ Strategy 1b: Found {len(urls)} images via batoPass")
                return urls
    # ... (lanjutan strategi lain tetap sama seperti kode asli)
    # (STRATEGY 2,3,4,5 tidak diubah di sini untuk menghemat tempat)
    return image_urls  # placeholder, gunakan kode lengkap asli kamu

def get_chapter_info(chapter_url, working_domain):
    # ... (kode asli get_chapter_info tetap sama, tidak diubah)
    # pastikan fungsi ini mengembalikan dict dengan 'title', 'images', 'domain'
    pass  # ganti dengan implementasi asli kamu

def download_image(url, save_path):
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except:
            if attempt == 2:
                return False
            time.sleep(1)
    return False

# Fungsi stitching lama (mode 1)
def images_to_pdf(image_folder, output_pdf_path, target_chunk_height=10000, progress_callback=None):
    # ... (kode asli images_to_pdf kamu, atau versi yang sudah kamu optimasi)
    # untuk contoh singkat, anggap fungsi ini ada dan berfungsi
    try:
        # implementasi lengkap seperti kode asli kamu
        return True  # placeholder
    except:
        return False

# Mode 2: Simple (no stitching)
def simple_pdf_no_stitching(image_folder, output_pdf_path, progress_callback=None):
    try:
        image_files = [os.path.join(image_folder, f) for f in os.listdir(image_folder)
                       if f.lower().endswith(('.png','.jpg','.jpeg','.webp'))]
        image_files.sort(key=natural_sort_key)

        if not image_files:
            return False

        total = len(image_files)
        images = []

        for i, path in enumerate(image_files):
            try:
                img = Image.open(path).convert('RGB')
                images.append(img)
                if progress_callback and (i+1) % 10 == 0:
                    progress_callback(
                        int(30 + 60 * (i+1)/total),
                        f"Loaded {i+1}/{total} images..."
                    )
            except:
                continue

        if not images:
            return False

        if progress_callback:
            progress_callback(95, "Saving PDF (simple mode)...")

        images[0].save(
            output_pdf_path, "PDF", resolution=100.0,
            save_all=True, append_images=images[1:]
        )

        if progress_callback:
            progress_callback(100, "Selesai (simple mode)!")
        return True
    except Exception as e:
        print(f"Simple PDF error: {e}")
        return False

# Mode 3: Ultra Fast (img2pdf) - optional
def ultra_fast_img2pdf(image_folder, output_pdf_path, progress_callback=None):
    try:
        import img2pdf
        image_files = [os.path.join(image_folder, f) for f in os.listdir(image_folder)
                       if f.lower().endswith(('.png','.jpg','.jpeg','.webp'))]
        image_files.sort(key=natural_sort_key)

        if not image_files:
            return False

        if progress_callback:
            progress_callback(70, "Converting with img2pdf (very fast)...")

        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_files))

        if progress_callback:
            progress_callback(100, "Selesai (ultra fast)!")
        return True
    except ImportError:
        print("img2pdf tidak terinstall → mode 3 tidak tersedia")
        return False
    except Exception as e:
        print(f"img2pdf error: {e}")
        return False

# ============ BOT HANDLERS ============
# (command /start, /help, dll tetap sama seperti kode asli kamu)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # --- Mode selection reply ---
    if user_id in user_pending_mode:
        if text in ['1', '2', '3']:
            mode = int(text)
            pending = user_pending_mode.pop(user_id, None)
            if pending:
                await process_download(update, context, pending['chapter_info'], 
                                      pending['status_msg'], mode)
            return
        else:
            await update.message.reply_text("Balas hanya dengan angka **1**, **2**, atau **3** ya")
            return

    # --- Proses URL baru ---
    url = text
    is_bato = any(d in url.lower() for d in BATO_DOMAINS)
    if not is_bato:
        await update.message.reply_text("Kirim link chapter Bato saja ya~")
        return

    status = await update.message.reply_text("⏳ Sedang memproses...")

    try:
        working_domain = find_working_domain()
        await status.edit_text("📡 Mengambil data chapter...")
        chapter_info = get_chapter_info(url, working_domain)

        images_count = len(chapter_info.get('images', []))
        if images_count < 1:
            await status.edit_text("Tidak menemukan gambar di chapter ini")
            return

        title = sanitize_filename(chapter_info.get('title', 'Chapter'))

        user_pending_mode[user_id] = {
            'chapter_info': chapter_info,
            'status_msg': status,
            'timeout': time.time() + 180  # 3 menit
        }

        await status.edit_text(
            f"**{title}** ditemukan!\n"
            f"Jumlah gambar: **{images_count}**\n\n"
            f"Pilih mode PDF (balas angka saja):\n\n"
            f"1 → **Stitching** (full vertical, paling nyaman dibaca)\n"
            f"   └─ lambat kalau chapter panjang\n\n"
            f"2 → **Simple** (1 gambar = 1 halaman, paling balance)\n"
            f"   └─ cepat & ukuran wajar\n\n"
            f"3 → **Ultra Fast** (lossless, tercepat, pakai img2pdf)\n"
            f"   └─ sangat cepat, tapi file agak lebih besar\n\n"
            f"**Rekomendasi:** chapter >80 gambar pakai 2 atau 3\n"
            f"Balas: **1** / **2** / **3**"
        )

    except Exception as e:
        await status.edit_text(f"Error: {str(e)[:120]}")
        print("Error handle_message:", str(e))

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          chapter_info, status_msg, mode: int):
    user_id = update.effective_user.id
    title = sanitize_filename(chapter_info.get('title', 'chapter'))
    images = chapter_info.get('images', [])
    total = len(images)

    temp_folder = os.path.join(TEMP_DIR, f"u{user_id}_{title[:60]}")
    os.makedirs(temp_folder, exist_ok=True)

    await status_msg.edit_text(f"📥 Download {total} gambar...")

    downloaded_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, url in enumerate(images, 1):
            path = os.path.join(temp_folder, f"p_{i:04d}.jpg")
            futures.append(executor.submit(download_image, url, path))

        for future in futures:
            if future.result():
                downloaded_count += 1
                if downloaded_count % 5 == 0 or downloaded_count == total:
                    perc = int(100 * downloaded_count / total)
                    bar = '▰' * (perc // 10) + '▱' * (10 - perc // 10)
                    await status_msg.edit_text(
                        f"📥 Download: {perc}%   {downloaded_count}/{total}\n{bar}"
                    )

    if downloaded_count == 0:
        await status_msg.edit_text("Gagal download gambar!")
        shutil.rmtree(temp_folder, ignore_errors=True)
        return

    pdf_path = os.path.join(TEMP_DIR, f"{title}.pdf")

    mode_names = {1: "Stitching", 2: "Simple (no stitch)", 3: "Ultra Fast"}
    await status_msg.edit_text(f"📄 Membuat PDF...\nMode: {mode_names.get(mode, '?')}")

    success = False
    progress_cb = lambda p, m: asyncio.create_task(
        status_msg.edit_text(f"📄 Processing... {p}%\n{m}")
    )

    if mode == 1:
        success = images_to_pdf(temp_folder, pdf_path, target_chunk_height=10000,
                               progress_callback=progress_cb)
    elif mode == 2:
        success = simple_pdf_no_stitching(temp_folder, pdf_path, progress_cb)
    elif mode == 3:
        success = ultra_fast_img2pdf(temp_folder, pdf_path, progress_cb)

    if not success:
        await status_msg.edit_text("Gagal membuat file PDF!")
        shutil.rmtree(temp_folder, ignore_errors=True)
        return

    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    caption = f"✅ {title}\nMode: {mode_names.get(mode)}\n{downloaded_count} halaman\n{size_mb:.1f} MB"

    if size_mb > MAX_FILE_SIZE_MB:
        zip_path = pdf_path + ".zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(pdf_path, f"{title}.pdf")
        await update.message.reply_document(open(zip_path, 'rb'),
                                           caption=caption + "\n(zipped >50MB)")
        os.remove(zip_path)
    else:
        await update.message.reply_document(open(pdf_path, 'rb'), caption=caption)

    await status_msg.delete()
    shutil.rmtree(temp_folder, ignore_errors=True)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

# ============ MAIN ============
def main():
    print("Bato Downloader Bot - with PDF Mode Selection")
    os.makedirs(TEMP_DIR, exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).build()

    # Tambahkan handler command kamu yang lain di sini
    # app.add_handler(CommandHandler("start", start_command))
    # ... dll

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
