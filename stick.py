import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stiker ID'larini saqlash uchun fayl
STICKERS_FILE = 'stickers.json'

def load_stickers():
    """Saqlangan stikerlarni yuklash"""
    if os.path.exists(STICKERS_FILE):
        with open(STICKERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'thinking': [], 'coding': [], 'success': [], 'joke': [], 'other': []}

def save_stickers(stickers):
    """Stikerlarni faylga saqlash"""
    with open(STICKERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stickers, f, indent=2, ensure_ascii=False)

stickers_db = load_stickers()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start buyrug'i"""
    await update.message.reply_text(
        "🎨 Stiker yig'ish boti!\n\n"
        "Menga stiker yuboring, men uni saqlayaman.\n\n"
        "Buyruqlar:\n"
        "/list - Barcha stikerlar\n"
        "/category <nom> - Kategoriya tanlash\n"
        "/clear - Hammasini o'chirish"
    )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stikerni qabul qilish"""
    sticker = update.message.sticker
    sticker_id = sticker.file_id
    
    # Hozirgi kategoriya
    category = context.user_data.get('category', 'other')
    
    # Stikerni saqlash
    if sticker_id not in stickers_db[category]:
        stickers_db[category].append(sticker_id)
        save_stickers(stickers_db)
        await update.message.reply_text(f"✅ Stiker saqlandi: {category}")
    else:
        await update.message.reply_text(f"⚠️ Bu stiker allaqachon mavjud: {category}")

async def list_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha stikerlarni ko'rsatish"""
    text = "📋 Saqlangan stikerlar:\n\n"
    for category, stickers in stickers_db.items():
        text += f"{category}: {len(stickers)} ta\n"
    await update.message.reply_text(text)

async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kategoriya tanlash"""
    if context.args:
        category = context.args[0]
        if category in stickers_db:
            context.user_data['category'] = category
            await update.message.reply_text(f"✅ Kategoriya: {category}")
        else:
            await update.message.reply_text(f"❌ Noto'g'ri kategoriya. Mavjud: {', '.join(stickers_db.keys())}")
    else:
        await update.message.reply_text("Kategoriya nomini kiriting: /category <nom>")

async def clear_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hammasini o'chirish"""
    global stickers_db
    stickers_db = {'thinking': [], 'coding': [], 'success': [], 'joke': [], 'other': []}
    save_stickers(stickers_db)
    await update.message.reply_text("✅ Barcha stikerlar o'chirildi!")

def main():
    """Botni ishga tushirish"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_stickers))
    application.add_handler(CommandHandler("category", set_category))
    application.add_handler(CommandHandler("clear", clear_stickers))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    
    print("✅ Stiker bot ishga tushdi!")
    application.run_polling()

if __name__ == '__main__':
    main()
