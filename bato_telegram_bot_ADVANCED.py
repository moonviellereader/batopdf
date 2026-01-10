#!/usr/bin/env python3
"""
Bato Manga Downloader Telegram Bot - ADVANCED VERSION
Fitur tambahan:
- Batch download multiple chapters
- Queue system untuk handle multiple users
- Statistics tracking
- Admin commands
"""

import os
import asyncio
import shutil
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import zipfile
import json

# ============ CONFIGURATION ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_IDS = [123456789]  # Ganti dengan Telegram user ID kamu

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BatoDownloader/1.0)"}
REQUEST_TIMEOUT = 10
MAX_WORKERS = 6
TEMP_DIR = "temp_downloads"
MAX_FILE_SIZE_MB = 50
STATS_FILE = "bot_stats.json"

# Queue untuk handle multiple requests
download_queue = asyncio.Queue()
active_downloads = {}

# BATO DOMAINS (sama seperti versi basic)
BATO_DOMAINS = [
    "bato.ing", "bato.si", "fto.to", "ato.to", "dto.to", "hto.to",
    "jto.to", "lto.to", "mto.to", "nto.to", "vto.to", "wto.to",
    # ... (copy semua domain dari versi basic)
]

# ============ STATS FUNCTIONS ============

def load_stats():
    """Load statistics dari file"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {
        "total_downloads": 0,
        "total_users": set(),
        "downloads_by_user": {},
        "popular_manga": {},
        "start_date": datetime.now().isoformat()
    }

def save_stats(stats):
    """Save statistics ke file"""
    # Convert set to list for JSON
    stats_copy = stats.copy()
    stats_copy["total_users"] = list(stats["total_users"])
    with open(STATS_FILE, 'w') as f:
        json.dump(stats_copy, f, indent=2)

def update_stats(user_id, chapter_title):
    """Update download statistics"""
    stats = load_stats()
    stats["total_downloads"] += 1
    stats["total_users"].add(user_id)
    
    # Track per user
    user_key = str(user_id)
    stats["downloads_by_user"][user_key] = stats["downloads_by_user"].get(user_key, 0) + 1
    
    # Track popular manga
    stats["popular_manga"][chapter_title] = stats["popular_manga"].get(chapter_title, 0) + 1
    
    save_stats(stats)

# ============ HELPER FUNCTIONS ============
# (Copy semua helper functions dari versi basic)

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name[:200]

def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', filename)]

def find_working_domain():
    for domain in BATO_DOMAINS[:10]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                return domain
        except:
            continue
    return "bato.ing"

def get_chapter_info(chapter_url, domain):
    try:
        for d in BATO_DOMAINS:
            if d in chapter_url:
                chapter_url = chapter_url.replace(d, domain)
                break
        
        response = requests.get(chapter_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        image_urls = []
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'const imgHttps' in script.string:
                matches = re.findall(r'"(https://[^"]+)"', script.string)
                image_urls.extend(matches)
                break
        
        title_elem = soup.find('h3', class_='nav-title')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Chapter"
        
        return {
            'title': chapter_title,
            'url': chapter_url,
            'images': image_urls
        }
    except Exception as e:
        raise Exception(f"Gagal mengambil chapter: {str(e)}")

def get_manga_chapters(manga_url, domain):
    """Get all chapters from a manga page"""
    try:
        for d in BATO_DOMAINS:
            if d in manga_url:
                manga_url = manga_url.replace(d, domain)
                break
        
        response = requests.get(manga_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find manga title
        title_elem = soup.find('h3', class_='item-title')
        manga_title = title_elem.get_text(strip=True) if title_elem else "Unknown Manga"
        
        # Find all chapters
        chapters = []
        chapter_links = soup.find_all('a', class_='chapt')
        for link in chapter_links:
            chapter_url = link.get('href')
            if chapter_url:
                chapter_name = link.get_text(strip=True)
                chapters.append({
                    'title': chapter_name,
                    'url': f"https://{domain}{chapter_url}"
                })
        
        return {
            'manga_title': manga_title,
            'chapters': chapters
        }
    except Exception as e:
        raise Exception(f"Gagal mengambil daftar chapter: {str(e)}")

def download_image(url, save_path):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except:
        return False

def images_to_pdf(image_folder, output_pdf_path, target_chunk_height=25000):
    # (Copy function dari versi basic)
    pass  # Implementation sama

# ============ QUEUE SYSTEM ============

async def process_download_queue():
    """Background task untuk process download queue"""
    while True:
        try:
            task = await download_queue.get()
            user_id = task['user_id']
            chapter_url = task['chapter_url']
            update = task['update']
            context = task['context']
            
            # Mark as processing
            active_downloads[user_id] = task
            
            # Process download
            await process_single_download(update, context, chapter_url)
            
            # Remove from active
            del active_downloads[user_id]
            
            download_queue.task_done()
        except Exception as e:
            print(f"Queue error: {e}")
        
        await asyncio.sleep(1)

async def process_single_download(update, context, chapter_url):
    """Process single chapter download"""
    # (Implementation dari handle_message di versi basic)
    pass

# ============ BOT HANDLERS ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 Panduan", callback_data='help')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')],
        [InlineKeyboardButton("💬 Support", url='https://t.me/moonread_channel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 **Bato Manga Downloader Bot v2.0**

Download manga dari Bato dalam bentuk PDF!

**Features:**
✅ Single chapter download
✅ Batch download (multiple chapters)
✅ PDF full-width
✅ Fast & free!

**Cara pakai:**
1️⃣ Kirim link chapter untuk 1 chapter
2️⃣ Kirim link manga untuk pilih chapters
3️⃣ Terima PDF!

Powered by @moonread_channel
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    stats = load_stats()
    
    # Calculate uptime
    start_date = datetime.fromisoformat(stats["start_date"])
    uptime = datetime.now() - start_date
    
    # Top manga
    popular = sorted(stats["popular_manga"].items(), key=lambda x: x[1], reverse=True)[:5]
    top_manga = "\n".join([f"{i+1}. {manga} ({count}x)" 
                           for i, (manga, count) in enumerate(popular)])
    
    stats_text = f"""
📊 **Bot Statistics**

**Overall:**
• Total downloads: {stats['total_downloads']}
• Unique users: {len(stats['total_users'])}
• Uptime: {uptime.days} days

**Top 5 Manga:**
{top_manga if top_manga else 'No data yet'}

**Queue:**
• In queue: {download_queue.qsize()}
• Active: {len(active_downloads)}

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only commands"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ Admin only!")
        return
    
    # Admin panel
    keyboard = [
        [InlineKeyboardButton("📊 Full Stats", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 User List", callback_data='admin_users')],
        [InlineKeyboardButton("🔄 Restart Queue", callback_data='admin_restart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🔐 **Admin Panel**", 
                                   parse_mode='Markdown', 
                                   reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk URL (single chapter atau manga page)"""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check valid bato URL
    is_bato_url = any(domain in url for domain in BATO_DOMAINS)
    if not is_bato_url:
        await update.message.reply_text(
            "❌ Link tidak valid!\n\n"
            "Kirim link dari Bato:\n"
            "• Link chapter untuk 1 chapter\n"
            "• Link manga untuk batch download",
            parse_mode='Markdown'
        )
        return
    
    # Detect if it's a chapter or manga page
    if 'chapter' in url.lower() or '/ch_' in url or '-ch' in url:
        # Single chapter
        if user_id in active_downloads:
            await update.message.reply_text(
                "⏳ Kamu masih punya download yang berjalan!\n"
                "Tunggu selesai dulu ya."
            )
            return
        
        # Add to queue
        await download_queue.put({
            'user_id': user_id,
            'chapter_url': url,
            'update': update,
            'context': context
        })
        
        position = download_queue.qsize()
        await update.message.reply_text(
            f"✅ Ditambahkan ke antrian!\n"
            f"Posisi: {position}\n"
            f"Estimasi: ~{position * 2} menit"
        )
    else:
        # Manga page - batch download
        await handle_batch_download(update, context, url)

async def handle_batch_download(update: Update, context: ContextTypes.DEFAULT_TYPE, manga_url: str):
    """Handle batch download dari manga page"""
    status_msg = await update.message.reply_text("🔍 Mengambil daftar chapter...")
    
    try:
        working_domain = find_working_domain()
        manga_info = get_manga_chapters(manga_url, working_domain)
        
        # Show chapter selection
        keyboard = []
        for idx, chapter in enumerate(manga_info['chapters'][:20]):  # Max 20 chapters
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {chapter['title']}", 
                    callback_data=f"download_{idx}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Download All", callback_data="download_all")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(
            f"**{manga_info['manga_title']}**\n\n"
            f"Pilih chapter yang mau di-download:\n"
            f"(Showing {len(manga_info['chapters'][:20])} chapters)",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Store manga info in context
        context.user_data['manga_info'] = manga_info
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'help':
        # Show help
        pass
    elif data == 'stats':
        await stats_command(query.message, context)
    elif data.startswith('download_'):
        # Handle chapter selection
        pass
    elif data == 'admin_stats':
        # Show full stats for admin
        pass

# ============ MAIN ============

async def main():
    """Start bot dengan queue system"""
    print("🤖 Starting Advanced Bato Bot...")
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start queue processor
    asyncio.create_task(process_download_queue())
    
    print("✅ Bot running!")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
