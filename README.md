# 🤖 ProX Bot - Dasturlash Yordamchisi

ProX akademiyasi uchun AI-powered Telegram bot. Kod tahlili, ovozli xabarlar, rasm OCR va quiz funksiyalari bilan.

## ✨ Asosiy Funksiyalar

### 💬 Savol-Javob
- Dasturlash savollariga AI javob beradi
- O'zbek tilida qo'llab-quvvatlash
- Motivatsion xabarlar

### 📝 Kod Tahlili
- 100+ fayl formatini qo'llab-quvvatlash
- Xatolarni aniqlash va tuzatish
- Kod sifatini baholash
- Tavsiyalar berish

### 🎯 Quiz Tizimi
- Avtomatik quiz yaratish
- 5 ta savol (har xil turda)
- Real-time natijalar
- Progress tracking

### 🎤 Ovozli Xabarlar
- Speech-to-Text (Groq Whisper)
- Avtomatik til aniqlash (90+ til)
- ✅ O'zbek tilida gapirish mumkin
- ✅ Ingliz tilida gapirish mumkin
- ✅ Rus tilida gapirish mumkin
- ✅ Har qanday tilni avtomatik taniydi
- Matn bilan javob qaytaradi

### 📸 Rasm Tahlili (OCR)
- Kod screenshot'larini o'qish
- EasyOCR + Tesseract
- Qora fon qo'llab-quvvatlash
- Xatolarni avtomatik tuzatish

### 📊 Statistika
- Foydalanuvchilar statistikasi
- Excel formatda export
- Kunlik tahlil
- Fayl turlari bo'yicha

### 👨‍💼 Admin Panel
- Foydalanuvchilarni boshqarish
- Broadcast xabarlar
- Sozlamalar
- Bot qayta yuklash

## 🚀 O'rnatish

### 1. Repository'ni clone qilish
```bash
git clone https://github.com/your-username/proxbot.git
cd proxbot
```

### 2. Virtual environment yaratish
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Tesseract OCR o'rnatish
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
[Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki) dan yuklab oling.

### 5. .env fayl yaratish
```bash
cp .env.example .env
```

`.env` faylini tahrirlang:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
SUPER_ADMIN_ID=your_telegram_user_id
```

### 6. Botni ishga tushirish
```bash
python3 bot.py
```

## 🔑 API Kalitlarini Olish

### Telegram Bot Token
1. [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting
4. Token'ni nusxalang

### Groq API Key
1. [Groq Console](https://console.groq.com) ga kiring
2. API Keys bo'limiga o'ting
3. Yangi kalit yarating
4. Nusxalang

### Telegram User ID
1. [@userinfobot](https://t.me/userinfobot) ga o'ting
2. `/start` bosing
3. ID'ni nusxalang

## 📁 Loyiha Strukturasi

```
proxbot/
├── bot.py                    # Asosiy bot fayli
├── config.py                 # Konfiguratsiya
├── groq_client.py           # AI client
├── user_memory.py           # Foydalanuvchi ma'lumotlari
├── quiz_manager.py          # Quiz tizimi
├── quiz_handlers.py         # Quiz handlerlari
├── settings_manager.py      # Sozlamalar
├── admin_manager.py         # Admin boshqaruv
├── statistics_formatter.py  # Statistika formatlash
├── excel_generator.py       # Excel yaratish
├── requirements.txt         # Python kutubxonalari
├── .env                     # Environment variables
├── .gitignore              # Git ignore
└── README.md               # Bu fayl
```

## 🎮 Foydalanish

### Oddiy Foydalanuvchi
- `/start` - Botni boshlash
- `/help` - Yordam
- Savol yozing - AI javob beradi
- Kod fayl yuboring - Tahlil qiladi
- Ovozli xabar yuboring - Taniydi va javob beradi
- Rasm yuboring - OCR qiladi va tahlil qiladi

### Admin
- `/panel` - Admin panel
- `/stats` - Statistika
- Broadcast xabar yuborish
- Sozlamalarni o'zgartirish
- Adminlar boshqaruvi

## 🛠️ Qo'llab-quvvatlanadigan Fayl Turlari

**Frontend:**
- JavaScript: `.js`, `.jsx`, `.mjs`, `.cjs`
- TypeScript: `.ts`, `.tsx`
- CSS: `.css`, `.scss`, `.sass`, `.less`
- HTML: `.html`, `.htm`
- Vue: `.vue`
- Svelte: `.svelte`

**Backend:**
- Python: `.py`, `.pyw`, `.pyx`
- Java: `.java`
- C/C++: `.c`, `.cpp`, `.h`, `.hpp`
- C#: `.cs`
- Go: `.go`
- Rust: `.rs`
- PHP: `.php`
- Ruby: `.rb`
- Swift: `.swift`
- Kotlin: `.kt`
- Dart: `.dart`

**Config:**
- JSON: `.json`, `.json5`
- YAML: `.yaml`, `.yml`
- XML: `.xml`
- TOML: `.toml`
- ENV: `.env`

**Va 100+ boshqa formatlar!**

## 🌐 Deploy

### VPS/Server
```bash
# Serverga ulanish
ssh user@your-server

# Botni yuklash
git clone your-repo-url
cd proxbot

# O'rnatish
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Background'da ishga tushirish
nohup python3 bot.py > bot.log 2>&1 &
```

### Systemd Service (Avtomatik qayta ishga tushish)
```bash
sudo nano /etc/systemd/system/proxbot.service
```

```ini
[Unit]
Description=ProX Telegram Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/proxbot
Environment="PATH=/path/to/proxbot/venv/bin"
ExecStart=/path/to/proxbot/venv/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable proxbot
sudo systemctl start proxbot
sudo systemctl status proxbot
```

## 📊 Statistika

Bot quyidagi statistikalarni yig'adi:
- Jami foydalanuvchilar
- So'rovlar soni (yozma, fayl, rasm, ovoz)
- Kod tahlillari
- Kunlik faollik
- Fayl turlari

Excel formatda export qilish mumkin.

## 🔒 Xavfsizlik

- API kalitlari `.env` faylida saqlanadi
- `.gitignore` orqali himoyalangan
- Admin huquqlari bilan boshqarish
- Super Admin tizimi

## 🤝 Hissa Qo'shish

1. Fork qiling
2. Feature branch yarating (`git checkout -b feature/AmazingFeature`)
3. Commit qiling (`git commit -m 'Add some AmazingFeature'`)
4. Push qiling (`git push origin feature/AmazingFeature`)
5. Pull Request oching

## 📝 Litsenziya

MIT License - [LICENSE](LICENSE) faylini ko'ring

## 👨‍💻 Muallif

**ProX Academy**
- Telegram: [@prox_academy](https://t.me/prox_academy)
- Website: [prox.uz](https://prox.uz)

## 🙏 Minnatdorchilik

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Groq](https://groq.com)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [gTTS](https://github.com/pndurette/gTTS)

---

⭐ Agar loyiha yoqsa, star bering!
