# 🚀 ONE-CLICK DEPLOYMENT GUIDE

Deploy bot kamu ke cloud dalam 5 menit dengan panduan lengkap!

---

## 📱 OPSI 1: RAILWAY.APP (PALING MUDAH) ⭐⭐⭐⭐⭐

### Why Railway?
- ✅ Setup 5 menit
- ✅ Free 500 jam/bulan (enough for 24/7!)
- ✅ Auto-restart jika crash
- ✅ Simple dashboard
- ✅ Free domain

### Step-by-Step:

#### 1. Persiapan GitHub (Opsional)
```bash
# Buat repo baru di GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/bato-bot.git
git push -u origin main
```

Atau upload manual via web GitHub.

#### 2. Deploy ke Railway

**A. Tanpa GitHub (Upload Manual):**
1. Buka https://railway.app
2. Sign up dengan email
3. "New Project" → "Empty Project"
4. "Deploy from GitHub" → Upload ZIP semua file
5. Railway akan auto-detect Python!

**B. Dengan GitHub:**
1. https://railway.app → Login
2. "New Project" → "Deploy from GitHub repo"
3. Pilih repo kamu
4. Railway auto-detect `requirements.txt` & `Procfile`

#### 3. Add Environment Variable
1. Project → Variables
2. Add variable:
   - Name: `BOT_TOKEN`
   - Value: (paste token dari BotFather)
3. Save!

#### 4. Deploy!
- Railway akan otomatis build & deploy
- Tunggu 2-3 menit
- Cek logs: "View Logs"
- Jika sukses, akan muncul: "✅ Bot running!"

#### 5. Test Bot
- Buka Telegram
- Search bot kamu
- Send /start
- DONE! 🎉

### Monitoring:
- Logs: Project → Deployments → View Logs
- Metrics: Project → Metrics (CPU, RAM, Network)
- Restart: Settings → Restart

### Free Tier Limits:
- 500 execution hours/month
- $5 credit (enough for ~1 month 24/7)
- After credit runs out, bot will pause (you can add $5/month)

---

## 🔵 OPSI 2: RENDER.COM (Free Tier Terbatas)

### Why Render?
- ✅ Truly unlimited free tier
- ⚠️ Sleeps after 15 min inactivity
- ✅ Wakes up on first message (15-30s delay)

### Step-by-Step:

#### 1. Sign Up
- https://render.com
- Sign up gratis dengan GitHub

#### 2. New Background Worker
- Dashboard → "New +"
- "Background Worker"

#### 3. Connect Repository
**A. From GitHub:**
- Connect GitHub account
- Select repository

**B. From Public Repo:**
- Public Git URL: `https://github.com/username/bato-bot`

#### 4. Configure:
```
Name: bato-manga-bot
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python3 bato_telegram_bot.py
```

#### 5. Environment Variables:
- Add: `BOT_TOKEN` = your token

#### 6. Deploy:
- "Create Background Worker"
- Wait 5-10 minutes for first deploy

### Free Tier Notes:
- ⚠️ Spins down after 15 min inactive
- First message after sleep: 30s delay
- Good for low-traffic bots

---

## 🟢 OPSI 3: FLY.IO (Developer-Friendly)

### Why Fly.io?
- ✅ Free 3 VMs
- ✅ No sleep time
- ✅ Fast deployment
- ⚠️ Perlu install CLI

### Step-by-Step:

#### 1. Install Fly CLI:

**Windows:**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Mac/Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

#### 2. Sign Up & Login:
```bash
fly auth signup
fly auth login
```

#### 3. Create App:
```bash
cd /path/to/bot
fly launch
```

Follow prompts:
- App name: `bato-manga-bot`
- Region: Singapore (closest to Indonesia)
- PostgreSQL: No
- Deploy: Yes

#### 4. Set Environment:
```bash
fly secrets set BOT_TOKEN=your_token_here
```

#### 5. Deploy:
```bash
fly deploy
```

#### 6. Monitor:
```bash
fly logs
fly status
```

### Dockerfile (Auto-created):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "bato_telegram_bot.py"]
```

---

## 🟣 OPSI 4: HEROKU (Classic, Paid)

### ⚠️ Update: Heroku Free Tier Discontinued

Heroku sekarang berbayar (~$7/bulan untuk Eco Dyno).

**Jika tetap mau pakai:**

#### 1. Sign Up:
- https://heroku.com

#### 2. Install Heroku CLI:
```bash
# Mac
brew install heroku/brew/heroku

# Windows (download installer)
https://devcenter.heroku.com/articles/heroku-cli
```

#### 3. Login:
```bash
heroku login
```

#### 4. Create App:
```bash
heroku create bato-manga-bot
```

#### 5. Deploy:
```bash
git push heroku main
```

#### 6. Set Config:
```bash
heroku config:set BOT_TOKEN=your_token
```

#### 7. Scale Worker:
```bash
heroku ps:scale worker=1
```

**Cost:** $7/month for Eco Dyno

---

## 🟠 OPSI 5: ORACLE CLOUD (100% FREE FOREVER!)

### Why Oracle?
- ✅ Always Free tier (FOREVER!)
- ✅ 2 VMs gratis
- ✅ Full control (root access)
- ⚠️ Setup agak teknis

### Step-by-Step:

#### 1. Sign Up:
- https://cloud.oracle.com/free
- Butuh kartu kredit (tapi tidak akan dicharge)

#### 2. Create VM:
- Compute → Instances → Create Instance
- Image: Ubuntu 22.04
- Shape: VM.Standard.E2.1.Micro (Always Free)
- Assign Public IP: Yes

#### 3. Connect via SSH:
```bash
ssh -i your_key.pem ubuntu@your_vm_ip
```

#### 4. Install Python & Dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

#### 5. Upload Bot Files:
```bash
# From local machine:
scp -i your_key.pem -r /path/to/bot ubuntu@vm_ip:/home/ubuntu/
```

#### 6. Install Requirements:
```bash
cd /home/ubuntu/bot
pip3 install -r requirements.txt
```

#### 7. Set Token:
```bash
export BOT_TOKEN="your_token_here"
# Or edit .env file
```

#### 8. Run Bot (Background):
```bash
nohup python3 bato_telegram_bot.py > bot.log 2>&1 &
```

#### 9. Auto-restart on boot:
```bash
# Create systemd service
sudo nano /etc/systemd/system/batobot.service
```

```ini
[Unit]
Description=Bato Manga Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot
Environment="BOT_TOKEN=your_token_here"
ExecStart=/usr/bin/python3 /home/ubuntu/bot/bato_telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable batobot
sudo systemctl start batobot
sudo systemctl status batobot
```

### Monitor:
```bash
# Logs
tail -f bot.log

# Check process
ps aux | grep bato

# Restart
sudo systemctl restart batobot
```

---

## 🔴 OPSI 6: PYTHONANYWHERE (Untuk Pemula)

### Why PythonAnywhere?
- ✅ Web-based (no terminal)
- ✅ Free tier available
- ⚠️ Limited to 100 seconds CPU/day (free)

### Step-by-Step:

#### 1. Sign Up:
- https://pythonanywhere.com
- Create free account

#### 2. Upload Files:
- Files tab → Upload
- Upload all bot files

#### 3. Open Console:
- Consoles → Bash

#### 4. Install Dependencies:
```bash
pip3 install --user -r requirements.txt
```

#### 5. Run Bot:
```bash
python3 bato_telegram_bot.py
```

#### 6. Keep Running (Always On):
⚠️ Free tier: Bot stops when you close browser
💰 Paid ($5/month): Always-on task available

---

## 📊 COMPARISON TABLE

| Platform | Free Tier | Setup | Speed | Best For |
|----------|-----------|--------|-------|----------|
| **Railway** | 500h/month | ⭐⭐⭐⭐⭐ | Fast | **RECOMMENDED** |
| **Render** | Unlimited* | ⭐⭐⭐⭐ | Medium | Low traffic |
| **Fly.io** | 3 VMs | ⭐⭐⭐ | Fast | Developers |
| **Oracle** | Forever | ⭐⭐ | Fast | Long-term |
| **Heroku** | None | ⭐⭐⭐⭐ | Fast | Paid only |
| **PythonAnywhere** | Limited | ⭐⭐⭐⭐⭐ | Slow | Beginners |

*Sleeps after 15 min inactivity

---

## ✅ REKOMENDASI

### Pemula & Quick Start:
→ **RAILWAY.APP** (5 menit, tinggal upload!)

### Developer & Long-term:
→ **ORACLE CLOUD** (gratis forever, full control)

### Low Traffic:
→ **RENDER.COM** (truly unlimited free)

---

## 🔧 POST-DEPLOYMENT CHECKLIST

- [ ] Bot responds to /start
- [ ] Test download chapter
- [ ] Check logs for errors
- [ ] Set up monitoring
- [ ] Share bot link to friends!

---

## 🆘 TROUBLESHOOTING

### Bot tidak start:
```bash
# Check logs
railway logs
# atau
fly logs
# atau
tail -f bot.log
```

### Error "Module not found":
```bash
pip install -r requirements.txt --upgrade
```

### Out of memory:
- Reduce `MAX_WORKERS` in config (6 → 3)
- Use smaller `target_chunk_height` (25000 → 15000)

---

**Happy Deploying! 🚀**

Questions? @moonread_channel
