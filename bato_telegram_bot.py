#!/usr/bin/env python3
"""
Bato Manga Downloader Telegram Bot v3.1 - WITH STITCHING MODES
Support SENODE dan semua format URL Bato
Multi-strategy image extraction
3 Stitching modes: Normal, Short, Skip
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

# STITCHING MODES - User configurable
STITCH_MODES = {
    'normal': {'height': 15000, 'desc': 'Normal (15000px chunks)', 'emoji': '📄'},
    'short': {'height': 5000, 'desc': 'Short (5000px chunks - faster!)', 'emoji': '⚡'},
    'skip': {'height': 0, 'desc': 'Skip (No stitching - fastest!)', 'emoji': '🚀'}
}
DEFAULT_STITCH_MODE = 'normal'

# User preferences storage (in-memory)
user_preferences = {}

# ALL BATO MIRROR DOMAINS (PRIORITIZED - Updated Jan 2025)
# v4 domains first (newest), then operational domains
BATO_DOMAINS = [
    # V4 DOMAINS (PRIORITY - Newest version)
    "bato.si", "bato.ing",
    
    # Short .to domains (all operational)
    "ato.to", "dto.to", "fto.to", "hto.to", "jto.to", "lto.to", "mto.to", 
    "nto.to", "vto.to", "wto.to", "xto.to", "yto.to",
    "vba.to", "wba.to", "xba.to", "yba.to", "zba.to",
    "kuku.to", "okok.to", "ruru.to", "xdxd.to",
    
    # bato.* domains (all operational)
    "bato.ac", "bato.bz", "bato.cc", "bato.cx", "bato.id", 
    "bato.pw", "bato.sh", "bato.to", "bato.vc", 
    "bato.day", "bato.red", "bato.run",
    
    # Full name domains (all operational)
    "batoto.in", "batoto.tv",
    "batotoo.com", "batotwo.com", "battwo.com",
    "batpub.com", "batread.com",
    "xbato.com", "xbato.net", "xbato.org",
    "zbato.com", "zbato.net", "zbato.org",
    "comiko.net", "comiko.org",
    "mangatoto.com", "mangatoto.net", "mangatoto.org",
    "batocomic.com", "batocomic.net", "batocomic.org",
    "readtoto.com", "readtoto.net", "readtoto.org",
]

# ============ HELPER FUNCTIONS ============

def sanitize_filename(name):
    """Clean filename"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^\x00-\x7F]+', '', name)  # Remove non-ASCII
    return name[:200]

def natural_sort_key(filename):
    """Natural sorting"""
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', filename)]

def rewrite_image_url(url):
    """Rewrite image URL"""
    if not url:
        return url
    # k -> n rewrite
    if re.match(r'^(https://k).*\.(png|jpg|jpeg|webp)(\?.*)?$', url, re.I):
        return url.replace("https://k", "https://n", 1)
    return url

def find_working_domain():
    """Find working domain - prioritize v4 domains"""
    # Try v4 domains first (bato.si, bato.ing)
    for domain in ["bato.si", "bato.ing"]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"✓ Using v4 domain: {domain}")
                return domain
        except:
            continue
    
    # Fallback to other operational domains
    for domain in BATO_DOMAINS[2:15]:  # Skip first 2 (already tried)
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"✓ Using fallback domain: {domain}")
                return domain
        except:
            continue
    
    # Ultimate fallback
    return "bato.si"

def extract_images_multi_strategy(soup, page_html):
    """
    Multiple strategies to extract image URLs
    Strategy priority:
    1. imgHttps array in script
    2. batoPass/imgHttpLis pattern
    3. All HTTPS image URLs in scripts
    4. img tags with data-src
    5. img tags with src
    """
    image_urls = []
    
    # STRATEGY 1: imgHttps array
    scripts = soup.find_all('script')
    for script in scripts:
        if not script.string:
            continue
        
        # Method 1a: imgHttps = [...]
        if 'imgHttps' in script.string:
            match = re.search(r'imgHttps\s*=\s*(\[[^\]]*\])', script.string)
            if match:
                try:
                    urls = json.loads(match.group(1))
                    if urls:
                        print(f"✓ Strategy 1a: Found {len(urls)} images via imgHttps array")
                        return urls
                except:
                    pass
        
        # Method 1b: imgHttpLis or batoPass patterns
        if 'imgHttpLis' in script.string or 'batoPass' in script.string:
            # Find all image URLs in this script
            urls = re.findall(r'"(https://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', script.string, re.I)
            if urls:
                print(f"✓ Strategy 1b: Found {len(urls)} images via batoPass pattern")
                return urls
    
    # STRATEGY 2: All HTTPS image URLs in any script
    for script in scripts:
        if script.string:
            urls = re.findall(r'https://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'<>]*)?', 
                            script.string, re.I)
            if urls:
                # Deduplicate
                unique_urls = list(dict.fromkeys(urls))
                if len(unique_urls) >= 3:  # Reasonable chapter has at least 3 images
                    print(f"✓ Strategy 2: Found {len(unique_urls)} images via script scanning")
                    return unique_urls
    
    # STRATEGY 3: img tags with data-src
    for img in soup.find_all('img'):
        src = img.get('data-src')
        if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            if src.startswith('http'):
                image_urls.append(src)
    
    if image_urls:
        print(f"✓ Strategy 3: Found {len(image_urls)} images via img[data-src]")
        return image_urls
    
    # STRATEGY 4: img tags with src
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            if src.startswith('http') and 'logo' not in src.lower() and 'icon' not in src.lower():
                image_urls.append(src)
    
    if image_urls:
        print(f"✓ Strategy 4: Found {len(image_urls)} images via img[src]")
        return image_urls
    
    # STRATEGY 5: Regex scan entire HTML
    all_urls = re.findall(r'https://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'<>]*)?', 
                          page_html, re.I)
    if all_urls:
        # Filter out common non-manga images
        filtered = [u for u in all_urls if not any(x in u.lower() for x in ['logo', 'icon', 'avatar', 'banner'])]
        unique = list(dict.fromkeys(filtered))
        if unique:
            print(f"✓ Strategy 5: Found {len(unique)} images via HTML regex scan")
            return unique
    
    return []

def get_chapter_info(chapter_url, working_domain):
    """
    Get chapter info with aggressive domain switching and multi-strategy extraction
    """
    print(f"\n{'='*60}")
    print(f"🔍 FETCHING: {chapter_url}")
    
    original_url = chapter_url
    tried_domains = []
    last_error = None
    
    # PRIORITY ORDER:
    # 1. Try v4 domains first (bato.si, bato.ing)
    # 2. Try current domain if not v4
    # 3. Try all other operational domains
    priority_domains = ["bato.si", "bato.ing"]
    current_domain_list = [working_domain] if working_domain not in priority_domains else []
    other_domains = [d for d in BATO_DOMAINS if d not in priority_domains and d != working_domain]
    
    test_domains = priority_domains + current_domain_list + other_domains[:20]
    
    for test_domain in test_domains:
        # Replace domain in URL
        current_url = original_url
        for d in BATO_DOMAINS:
            if d in current_url:
                current_url = current_url.replace(d, test_domain)
                break
        
        tried_domains.append(test_domain)
        print(f"🌐 Trying: {test_domain}")
        
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            
            if response.status_code == 404:
                print(f"  ❌ 404 Not Found")
                continue
            
            if response.status_code != 200:
                print(f"  ⚠️ HTTP {response.status_code}")
                continue
            
            # Check if it's actually a Bato page
            if 'bato' not in response.text.lower() and 'chapter' not in response.text.lower():
                print(f"  ⚠️ Not a Bato page")
                continue
            
            print(f"  ✅ Connected! Extracting images...")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract images with multi-strategy
            image_urls = extract_images_multi_strategy(soup, response.text)
            
            if not image_urls:
                print(f"  ⚠️ No images found")
                continue
            
            # Rewrite URLs
            image_urls = [rewrite_image_url(url) for url in image_urls]
            
            # Get chapter title
            title_elem = (soup.find('h3', class_='nav-title') or 
                         soup.find('h1') or 
                         soup.find('title'))
            chapter_title = title_elem.get_text(strip=True) if title_elem else "Chapter"
            chapter_title = re.sub(r'[^\x00-\x7F]+', '', chapter_title)
            
            print(f"  ✅ SUCCESS!")
            print(f"  📄 Title: {chapter_title}")
            print(f"  🖼️ Images: {len(image_urls)}")
            print(f"{'='*60}\n")
            
            return {
                'title': chapter_title,
                'url': current_url,
                'images': image_urls,
                'domain': test_domain
            }
            
        except requests.Timeout:
            print(f"  ⏱️ Timeout")
            last_error = "Connection timeout"
            continue
        except requests.RequestException as e:
            print(f"  ❌ Request error: {str(e)[:50]}")
            last_error = str(e)
            continue
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
            last_error = str(e)
            continue
    
    # Failed on all domains
    print(f"{'='*60}")
    print(f"❌ FAILED on all domains: {', '.join(tried_domains[:5])}{'...' if len(tried_domains) > 5 else ''}")
    print(f"{'='*60}\n")
    
    raise Exception(f"Chapter tidak ditemukan di {len(tried_domains)} domain. "
                   f"Kemungkinan: (1) Chapter tidak ada, (2) Format URL salah, "
                   f"(3) Semua domain down. Last error: {last_error}")

def download_image(url, save_path):
    """Download single image with retry"""
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
            continue
    return False

def images_to_pdf(image_folder, output_pdf_path, target_chunk_height=15000, progress_callback=None):
    """
    Convert images to PDF with progress tracking
    OPTIMIZED: Supports variable chunk heights and skip mode
    target_chunk_height = 0 means skip stitching (1 image = 1 page)
    """
    try:
        # STEP 1: Get files (5%)
        if progress_callback:
            progress_callback(5, "Scanning images...")
        
        image_files = []
        for fname in os.listdir(image_folder):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                image_files.append(os.path.join(image_folder, fname))
        
        image_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        
        if not image_files:
            return False
        
        total_images = len(image_files)
        
        # SKIP MODE: No stitching, direct conversion
        if target_chunk_height == 0:
            if progress_callback:
                progress_callback(10, f"Skip mode: Converting {total_images} images directly...")
            
            # Load all images directly
            pdf_images = []
            for idx, img_path in enumerate(image_files):
                current_progress = 10 + int(85 * (idx + 1) / total_images)
                
                if progress_callback and (idx % 10 == 0 or idx == total_images - 1):
                    progress_callback(current_progress, f"Loading {idx+1}/{total_images}...")
                
                try:
                    img = Image.open(img_path)
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    pdf_images.append(img)
                except Exception as e:
                    if progress_callback:
                        progress_callback(current_progress, f"Skipped corrupted image {idx+1}")
                    continue
            
            if not pdf_images:
                return False
            
            # Save directly as PDF
            if progress_callback:
                progress_callback(95, f"Saving {len(pdf_images)} pages...")
            
            first_image = pdf_images[0]
            other_images = pdf_images[1:] if len(pdf_images) > 1 else []
            first_image.save(output_pdf_path, 'PDF', resolution=100.0, save_all=True, append_images=other_images)
            
            if progress_callback:
                progress_callback(100, f"Skip mode complete! {len(pdf_images)} pages")
            
            return True
        
        # NORMAL/SHORT MODE: Stitching with chunks
        # STEP 2: Quick width check (10%)
        if progress_callback:
            progress_callback(10, "Analyzing dimensions...")
        
        min_width = None
        max_width = None
        for img_path in image_files[:10]:  # Only check first 10 for speed
            try:
                with Image.open(img_path) as img:
                    if min_width is None or img.width < min_width:
                        min_width = img.width
                    if max_width is None or img.width > max_width:
                        max_width = img.width
            except:
                pass
        
        if min_width is None:
            return False
        
        # OPTIMIZATION: If all images similar width (within 5%), skip resize
        width_variance = abs(max_width - min_width) / min_width if min_width > 0 else 0
        skip_resize = width_variance < 0.05
        
        if progress_callback:
            if skip_resize:
                progress_callback(12, f"Images uniform width ({min_width}px) - skipping resize")
            else:
                progress_callback(12, f"Width variance detected - will resize")
        
        # STEP 3: Load and process images (10% - 60%)
        images = []
        for idx, img_path in enumerate(image_files):
            # Calculate progress: 10% + (50% * progress)
            current_progress = 12 + int(48 * (idx + 1) / total_images)
            
            # Update every 10 images to reduce message spam
            if progress_callback and (idx % 10 == 0 or idx == total_images - 1):
                progress_callback(current_progress, f"Loading image {idx+1}/{total_images}...")
            
            try:
                img = Image.open(img_path)
                
                # Only resize if needed
                if not skip_resize and img.width != min_width:
                    ratio = min_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((min_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to RGB
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
                if progress_callback:
                    progress_callback(current_progress, f"Skipped corrupted image {idx+1}")
                continue
        
        if not images:
            return False
        
        # STEP 4: Create chunks (65%)
        if progress_callback:
            progress_callback(65, "Creating chunks...")
        
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
        
        if progress_callback:
            avg_per_chunk = len(images) / len(chunks)
            progress_callback(67, f"Created {len(chunks)} chunks (~{avg_per_chunk:.0f} imgs each)")
        
        # STEP 5: Stitch chunks (70% - 90%)
        stitched_images = []
        for chunk_idx, chunk in enumerate(chunks):
            # Progress: 70% + (20% * progress)
            current_progress = 70 + int(20 * (chunk_idx + 1) / len(chunks))
            if progress_callback:
                progress_callback(current_progress, f"Stitching chunk {chunk_idx+1}/{len(chunks)} ({len(chunk)} imgs)...")
            
            chunk_height = sum(img.height for img in chunk)
            stitched = Image.new('RGB', (min_width, chunk_height), (255, 255, 255))
            
            y_offset = 0
            for img in chunk:
                stitched.paste(img, (0, y_offset))
                y_offset += img.height
            
            stitched_images.append(stitched)
        
        # STEP 6: Save as PDF (95%)
        if progress_callback:
            progress_callback(95, f"Saving PDF ({len(stitched_images)} pages)...")
        
        if stitched_images:
            first_image = stitched_images[0]
            other_images = stitched_images[1:] if len(stitched_images) > 1 else []
            first_image.save(output_pdf_path, 'PDF', resolution=100.0, save_all=True, append_images=other_images)
            
            if progress_callback:
                progress_callback(100, "PDF created!")
            
            return True
        
        return False
    except Exception as e:
        print(f"PDF error: {e}")
        if progress_callback:
            progress_callback(0, f"Error: {str(e)[:50]}")
        return False

# ============ BOT HANDLERS ============

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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """📖 PANDUAN LENGKAP v3.1

1️⃣ STITCHING MODES (NEW!):
Gunakan /mode untuk pilih mode:

📄 Normal (default):
  • Chunks: 15000px
  • Speed: Medium
  • Best for: Most chapters

⚡ Short:
  • Chunks: 5000px
  • Speed: Fast!
  • Best for: 100+ images

🚀 Skip:
  • No stitching!
  • Speed: Super fast!
  • Best for: 200+ images
  • Result: 1 image = 1 PDF page

💡 Perbandingan waktu (100 images):
  • Normal: ~30s
  • Short: ~15s
  • Skip: ~5s (langsung!)

2️⃣ MULTI-STRATEGY EXTRACTION:
Bot menggunakan 5 strategi untuk extract gambar:
• Strategy 1: imgHttps array
• Strategy 2: batoPass pattern
• Strategy 3: Script scanning
• Strategy 4: img[data-src]
• Strategy 5: HTML regex scan

3️⃣ AUTO DOMAIN SWITCHING:
Jika error 404, bot akan:
• Test domain working_domain
• Auto try 20+ domain lain
• Switch ke domain yang berhasil

4️⃣ REAL-TIME PROGRESS:
📥 Download: ▰▰▰▰▰▱▱▱▱▱ 50%
📄 PDF Creation: 
  ├─ Loading image 15/50...
  └─ 50 images total

5️⃣ DEBUG MODE:
/debug [url] - Lihat detail proses

💡 TIPS:
• Banyak gambar? Gunakan /mode → Skip
• Mode Skip = 1 image/page (fastest!)
• PDF progress update tiap 10 gambar
• Progress stuck? Bot masih bekerja!

💬 @moonread_channel
"""
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command"""
    working_domain = find_working_domain()
    
    # Count domains
    v4_count = 2  # bato.si, bato.ing
    total_count = len(BATO_DOMAINS)
    
    # Get user mode
    user_id = update.effective_user.id
    current_mode = user_preferences.get(user_id, DEFAULT_STITCH_MODE)
    mode_info = STITCH_MODES[current_mode]
    
    status_text = f"""✅ BOT v3.1 ONLINE

🌟 Priority: v4 domains (bato.si, bato.ing)
🌐 Current: {working_domain}
📊 Domains: {total_count} operational
🔧 Strategies: 5 extraction methods
🌍 Fallback: Auto-switch 20+ domains
📁 Temp: OK

{mode_info['emoji']} Stitch Mode: {mode_info['desc']}
(Change with /mode)

🚀 Ready to download!

Commands:
/mode - Change stitch mode
/domains - Show all 57 domains
/test - Test v4 domains  
/debug [url] - Debug mode
"""
    await update.message.reply_text(status_text)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test v4 domains"""
    msg = await update.message.reply_text("🔍 Testing v4 domains...")
    
    results = []
    
    # Test v4 domains (priority)
    results.append("🌟 V4 DOMAINS (Priority):")
    for domain in ["bato.si", "bato.ing"]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                results.append(f"✅ {domain} - ONLINE")
            else:
                results.append(f"⚠️ {domain} - HTTP {response.status_code}")
        except:
            results.append(f"❌ {domain} - OFFLINE")
    
    results.append("\n🔧 Testing fallback domains:")
    # Test next 8 domains
    for domain in BATO_DOMAINS[2:10]:
        try:
            url = f"https://{domain}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                results.append(f"✅ {domain}")
            else:
                results.append(f"⚠️ {domain} ({response.status_code})")
        except:
            results.append(f"❌ {domain}")
    
    results.append(f"\n📊 Total: {len(BATO_DOMAINS)} operational domains")
    results.append("Use /domains to see full list")
    
    await msg.edit_text("\n".join(results))

async def domains_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all operational domains"""
    msg = "🌐 57 OPERATIONAL BATO DOMAINS\n"
    msg += "="*40 + "\n\n"
    
    msg += "⭐ V4 DOMAINS (Priority):\n"
    msg += "• bato.si (v4)\n"
    msg += "• bato.ing (v4)\n\n"
    
    msg += "📌 Short .to Domains:\n"
    to_domains = [d for d in BATO_DOMAINS if d.endswith('.to') and len(d) < 10]
    for d in to_domains[:12]:
        msg += f"• {d}\n"
    msg += f"... +{len(to_domains)-12} more\n\n"
    
    msg += "📌 bato.* Domains:\n"
    bato_domains = [d for d in BATO_DOMAINS if d.startswith('bato.') and d not in ['bato.si', 'bato.ing']]
    for d in bato_domains[:8]:
        msg += f"• {d}\n"
    msg += f"... +{len(bato_domains)-8} more\n\n"
    
    msg += "📌 Other Domains:\n"
    other = [d for d in BATO_DOMAINS if not d.endswith('.to') and not d.startswith('bato.')]
    for d in other[:10]:
        msg += f"• {d}\n"
    msg += f"... +{len(other)-10} more\n\n"
    
    msg += f"✅ Total: {len(BATO_DOMAINS)} domains\n"
    msg += f"🤖 Bot auto-switches between them!"
    
    await update.message.reply_text(msg)

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug mode"""
    if not context.args:
        await update.message.reply_text("Usage: /debug [chapter_url]")
        return
    
    url = context.args[0]
    msg = await update.message.reply_text("🔍 Debug mode...")
    
    try:
        working_domain = find_working_domain()
        
        # Redirect print to capture
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        chapter_info = get_chapter_info(url, working_domain)
        
        # Get debug output
        debug_output = buffer.getvalue()
        sys.stdout = old_stdout
        
        result = f"🔍 DEBUG OUTPUT:\n\n{debug_output}\n\n"
        result += f"✅ SUCCESS!\n"
        result += f"📄 Title: {chapter_info['title']}\n"
        result += f"🖼️ Images: {len(chapter_info['images'])}\n"
        result += f"🌐 Domain: {chapter_info['domain']}"
        
        # Split if too long
        if len(result) > 4000:
            await msg.edit_text(result[:4000] + "\n\n... (truncated)")
        else:
            await msg.edit_text(result)
            
    except Exception as e:
        await msg.edit_text(f"❌ DEBUG ERROR:\n\n{str(e)}")

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change stitching mode"""
    user_id = update.effective_user.id
    current_mode = user_preferences.get(user_id, DEFAULT_STITCH_MODE)
    
    # If argument provided, set mode
    if context.args:
        mode_arg = context.args[0].lower()
        if mode_arg in STITCH_MODES:
            user_preferences[user_id] = mode_arg
            mode_info = STITCH_MODES[mode_arg]
            await update.message.reply_text(
                f"✅ Mode changed!\n\n"
                f"{mode_info['emoji']} {mode_info['desc']}\n\n"
                f"Your next download will use this mode."
            )
        else:
            await update.message.reply_text(
                f"❌ Invalid mode!\n\n"
                f"Available: normal, short, skip"
            )
        return
    
    # Show menu
    mode_text = "📄 STITCHING MODES\n"
    mode_text += "="*40 + "\n\n"
    
    for mode_key, mode_data in STITCH_MODES.items():
        is_current = "✅" if mode_key == current_mode else "  "
        mode_text += f"{is_current} {mode_data['emoji']} {mode_data['desc']}\n"
        
        if mode_key == 'normal':
            mode_text += "   • Chunks: 15000px\n"
            mode_text += "   • Speed: Medium\n"
            mode_text += "   • Best for: Most chapters\n"
            mode_text += "   • 100 images: ~30s\n\n"
        elif mode_key == 'short':
            mode_text += "   • Chunks: 5000px\n"
            mode_text += "   • Speed: Fast!\n"
            mode_text += "   • Best for: 100+ images\n"
            mode_text += "   • 100 images: ~15s\n\n"
        elif mode_key == 'skip':
            mode_text += "   • No stitching\n"
            mode_text += "   • Speed: Super fast!\n"
            mode_text += "   • 1 image = 1 PDF page\n"
            mode_text += "   • Best for: 200+ images\n"
            mode_text += "   • 100 images: ~5s\n\n"
    
    mode_text += "💡 To change mode:\n"
    mode_text += "/mode normal\n"
    mode_text += "/mode short\n"
    mode_text += "/mode skip\n\n"
    mode_text += f"Current: {STITCH_MODES[current_mode]['emoji']} {current_mode}"
    
    await update.message.reply_text(mode_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chapter URL"""
    url = update.message.text.strip()
    
    # Validate Bato URL
    is_bato_url = any(domain in url for domain in BATO_DOMAINS)
    
    if not is_bato_url:
        await update.message.reply_text(
            "❌ Bukan link Bato!\n\n"
            "Kirim link chapter dari bato.ing atau mirror-nya"
        )
        return
    
    status_msg = await update.message.reply_text("⏳ Processing...")
    
    # Track total time
    import time
    start_time = time.time()
    
    try:
        # Find working domain
        await status_msg.edit_text("🔍 Finding working domain...")
        working_domain = find_working_domain()
        
        # Get chapter info (with multi-strategy)
        await status_msg.edit_text("📥 Fetching chapter (multi-strategy)...")
        chapter_info = get_chapter_info(url, working_domain)
        
        if not chapter_info['images']:
            await status_msg.edit_text(
                "❌ No images found!\n\n"
                "Tried 5 extraction strategies.\n"
                "Chapter might not exist or format changed."
            )
            return
        
        total_images = len(chapter_info['images'])
        chapter_title = sanitize_filename(chapter_info['title'])
        
        # Create temp directory
        user_id = update.effective_user.id
        temp_folder = os.path.join(TEMP_DIR, f"user_{user_id}_{chapter_title}")
        os.makedirs(temp_folder, exist_ok=True)
        
        # Download images with progress bar
        await status_msg.edit_text(
            f"📥 Downloading {total_images} images... 0%\n"
            f"▱▱▱▱▱▱▱▱▱▱ 0/{total_images}"
        )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        downloaded = 0
        
        def create_progress_bar(current, total, length=10):
            """Create visual progress bar"""
            filled = int(length * current / total)
            bar = '▰' * filled + '▱' * (length - filled)
            return bar
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for idx, img_url in enumerate(chapter_info['images'], 1):
                save_path = os.path.join(temp_folder, f"page_{idx:04d}.jpg")
                future = executor.submit(download_image, img_url, save_path)
                futures.append(future)
            
            for future in futures:
                if future.result():
                    downloaded += 1
                    
                    # Calculate percentage
                    percent = int(100 * downloaded / total_images)
                    progress_bar = create_progress_bar(downloaded, total_images)
                    
                    # Update every 5 images or at completion
                    if downloaded % 5 == 0 or downloaded == total_images:
                        await status_msg.edit_text(
                            f"📥 Downloading... {percent}%\n"
                            f"{progress_bar} {downloaded}/{total_images}"
                        )
        
        if downloaded == 0:
            await status_msg.edit_text("❌ Failed to download images!")
            shutil.rmtree(temp_folder, ignore_errors=True)
            return
        
        # Convert to PDF with progress tracking
        pdf_path = os.path.join(TEMP_DIR, f"{chapter_title}.pdf")
        
        # Get user's stitch mode
        user_id = update.effective_user.id
        stitch_mode = user_preferences.get(user_id, DEFAULT_STITCH_MODE)
        mode_info = STITCH_MODES[stitch_mode]
        chunk_height = mode_info['height']
        
        # Estimate PDF time based on image count and mode
        if chunk_height == 0:  # Skip mode
            estimated_seconds = downloaded * 0.05  # ~0.05s per image (super fast)
        elif chunk_height <= 5000:  # Short mode
            estimated_seconds = downloaded * 0.15  # ~0.15s per image
        else:  # Normal mode
            estimated_seconds = downloaded * 0.3  # ~0.3s per image
        
        est_minutes = int(estimated_seconds / 60)
        est_text = f"~{est_minutes}min" if est_minutes > 0 else f"~{int(estimated_seconds)}s"
        
        await status_msg.edit_text(
            f"📄 Creating PDF (0%)...\n"
            f"├─ {mode_info['emoji']} Mode: {stitch_mode}\n"
            f"├─ {downloaded} images\n"
            f"└─ Est. time: {est_text}"
        )
        
        # Create a shared progress tracker
        import threading
        progress_data = {'percent': 0, 'message': 'Initializing...'}
        progress_lock = threading.Lock()
        
        def pdf_progress(percent, message):
            """Update progress data (thread-safe)"""
            with progress_lock:
                progress_data['percent'] = percent
                progress_data['message'] = message
        
        # Start PDF conversion in background
        # Use user's preferred chunk height
        pdf_thread = threading.Thread(
            target=lambda: images_to_pdf(temp_folder, pdf_path, target_chunk_height=chunk_height, progress_callback=pdf_progress)
        )
        pdf_thread.start()
        
        # Update status message periodically
        last_percent = 0
        while pdf_thread.is_alive():
            await asyncio.sleep(0.5)
            with progress_lock:
                current_percent = progress_data['percent']
                current_msg = progress_data['message']
            
            # Only update if progress changed
            if current_percent > last_percent:
                last_percent = current_percent
                await status_msg.edit_text(
                    f"📄 Creating PDF... {current_percent}%\n"
                    f"├─ {mode_info['emoji']} {stitch_mode} mode\n"
                    f"├─ {current_msg}\n"
                    f"└─ {downloaded} images total"
                )
        
        pdf_thread.join()
        
        # Check if PDF was created
        success = os.path.exists(pdf_path)
        
        if not success:
            await status_msg.edit_text("❌ PDF creation failed!")
            shutil.rmtree(temp_folder, ignore_errors=True)
            return
        
        # Check file size
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        # Calculate processing time
        total_time = time.time() - start_time
        time_text = f"{int(total_time)}s" if total_time < 60 else f"{int(total_time/60)}m {int(total_time%60)}s"
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"📦 Compressing... 0%\n"
                f"▱▱▱▱▱▱▱▱▱▱\n"
                f"Size: {file_size_mb:.1f}MB > 50MB limit"
            )
            zip_path = os.path.join(TEMP_DIR, f"{chapter_title}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                await status_msg.edit_text(
                    f"📦 Compressing... 50%\n"
                    f"▰▰▰▰▰▱▱▱▱▱\n"
                    f"Creating archive..."
                )
                zipf.write(pdf_path, os.path.basename(pdf_path))
            
            await status_msg.edit_text(
                f"📦 Compressed! 100%\n"
                f"▰▰▰▰▰▰▰▰▰▰\n"
                f"📤 Sending..."
            )
            
            with open(zip_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{chapter_title}.zip",
                    caption=f"✅ {chapter_info['title']}\n\n"
                            f"📊 {downloaded} images\n"
                            f"🌐 {chapter_info['domain']}\n"
                            f"📦 {file_size_mb:.1f}MB (zipped)\n"
                            f"⏱️ Processed in {time_text}\n\n"
                            f"⚠️ Compressed (>50MB limit)\n"
                            f"@moonread_channel"
                )
            
            os.remove(zip_path)
        else:
            await status_msg.edit_text("📤 Sending PDF...")
            
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{chapter_title}.pdf",
                    caption=f"✅ {chapter_info['title']}\n\n"
                            f"📄 PDF ({mode_info['emoji']} {stitch_mode} mode)\n"
                            f"📊 {downloaded} images\n"
                            f"🌐 {chapter_info['domain']}\n"
                            f"📦 {file_size_mb:.1f}MB\n"
                            f"⏱️ {time_text}\n\n"
                            f"💡 Change mode: /mode\n"
                            f"@moonread_channel"
                )
        
        # Cleanup
        await status_msg.delete()
        shutil.rmtree(temp_folder, ignore_errors=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ ERROR:\n{str(e)}\n\n"
            f"💡 Try:\n"
            f"• /test - Check domains\n"
            f"• /debug {url[:30]}... - Debug mode\n"
            f"• Different chapter URL"
        )
        print(f"Error: {e}")

# ============ MAIN ============

def main():
    """Start bot"""
    print("🤖 Bato Downloader Bot v3.1 - STITCHING MODES")
    print("="*60)
    print("Features:")
    print("  ✓ Real-time progress tracking (download & PDF)")
    print("  ✓ 3 stitching modes (Normal/Short/Skip)")
    print("  ✓ 5 extraction strategies")
    print("  ✓ 57 operational domains")
    print("  ✓ Auto domain switching")
    print("  ✓ Multi-format support")
    print("="*60)
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("domains", domains_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n✅ Bot running with stitching modes!")
    print("📊 Users can choose: Normal, Short, or Skip mode")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
