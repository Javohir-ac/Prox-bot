import logging
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import config
from groq_client import GroqClient
from user_memory import UserMemory
from settings_manager import SettingsManager
from admin_manager import AdminManager
from quiz_manager import QuizManager
import quiz_handlers
from quiz_handlers import quiz_callback_handler, send_quiz_question
from statistics_formatter import format_statistics
from excel_generator import generate_statistics_excel
import json
import os
import sys
import random

from pathlib import Path
from gtts import gTTS
import base64
from datetime import datetime, timedelta
import asyncio

# Global buffer for photos
user_photo_buffer = {}

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Groq client
groq_client = GroqClient()

# User memory
user_memory = UserMemory()

# Settings manager
settings_manager = SettingsManager()

# Admin manager
admin_manager = AdminManager()

# Quiz manager
quiz_manager = QuizManager()

# Set quiz_manager in quiz_handlers module to use the same instance
quiz_handlers.quiz_manager = quiz_manager

# Super Admin ID (config.py dan)
SUPER_ADMIN_ID = config.SUPER_ADMIN_ID

# Stikerlarni yuklash
def load_stickers():
    """Saqlangan stikerlarni yuklash"""
    if os.path.exists('stickers.json'):
        with open('stickers.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'thinking': [], 'coding': [], 'success': [], 'joke': [], 'other': []}

stickers_db = load_stickers()

def get_random_sticker(category):
    """Tasodifiy stiker olish"""
    if category in stickers_db and stickers_db[category]:
        return random.choice(stickers_db[category])
    return None

async def send_long_message(update, message, parse_mode=None):
    """Uzun xabarlarni bo'lib yuborish"""
    MAX_LENGTH = settings_manager.get('max_message_length', 4000)
    
    # Topic ID ni olish (agar mavjud bo'lsa)
    message_thread_id = update.message.message_thread_id if update.message else None
    
    if len(message) <= MAX_LENGTH:
        try:
            await update.message.reply_text(
                message,
                parse_mode=parse_mode,
                message_thread_id=message_thread_id
            )
            return
        except Exception as e:
            logger.error(f"Xabar yuborishda xatolik: {e}")
            await update.message.reply_text(
                message,
                message_thread_id=message_thread_id
            )  # Parse mode'siz qaytadan urinish
            return
    
    # Xabarni bo'laklarga bo'lish
    parts = []
    current_part = ""
    
    lines = message.split('\n')
    for line in lines:
        if len(current_part + line + '\n') > MAX_LENGTH:
            if current_part:
                parts.append(current_part.strip())
                current_part = line + '\n'
            else:
                # Agar bitta qator ham juda uzun bo'lsa
                while len(line) > MAX_LENGTH:
                    parts.append(line[:MAX_LENGTH])
                    line = line[MAX_LENGTH:]
                current_part = line + '\n'
        else:
            current_part += line + '\n'
    
    if current_part:
        parts.append(current_part.strip())
    
    # Bo'laklarni yuborish
    for i, part in enumerate(parts):
        try:
            if i == 0:
                await update.message.reply_text(
                    part,
                    parse_mode=parse_mode,
                    message_thread_id=message_thread_id
                )
            else:
                await update.message.reply_text(
                    f"📄 Davomi ({i+1}/{len(parts)}):\n\n{part}",
                    parse_mode=parse_mode,
                    message_thread_id=message_thread_id
                )
        except Exception as e:
            logger.error(f"Bo'lak yuborishda xatolik: {e}")
            # Parse mode'siz qaytadan urinish
            if i == 0:
                await update.message.reply_text(
                    part,
                    message_thread_id=message_thread_id
                )
            else:
                await update.message.reply_text(
                    f"📄 Davomi ({i+1}/{len(parts)}):\n\n{part}",
                    message_thread_id=message_thread_id
                )

async def send_humor_reaction(update, context, message_text, user_name):
    """Xabar kelganda hazil yoki stiker bilan reaksiya qilish"""
    import random
    import asyncio
    
    # Topic ID ni olish
    message_thread_id = update.message.message_thread_id if update.message else None
    
    # Stiker yuborish (50% ehtimollik bilan)
    if settings_manager.get('stickers_enabled', True) and random.random() < 0.5:
        sticker_category = 'thinking'
        if 'kod' in str(message_text).lower() or message_text == "code_analysis":
            sticker_category = 'coding'
        elif 'rahmat' in str(message_text).lower():
            sticker_category = 'success'
            
        sticker_id = get_random_sticker(sticker_category)
        if sticker_id:
            try:
                await update.message.reply_sticker(
                    sticker_id,
                    message_thread_id=message_thread_id
                )
                # Stiker ketidan biroz kutish
                await asyncio.sleep(1)
            except:
                pass
    
    # Hazil reaksiya matnlari
    reactions = [
        f"🤔 {user_name}, qiziq savol! Hozir o'ylab ko'raman...",
        f"⚡ {user_name}, bir daqiqa! Miya ishga tushdi...",
        f"🔍 {user_name}, qani ko'raylikchi...",
        f"🤖 {user_name}, protsessorim qiziyapti! Hozir javob beraman...",
        f"📚 {user_name}, kitoblarni titkilayapman...",
        f"💡 {user_name}, ajoyib! Hozir tahlil qilaman...",
        f"👨‍💻 {user_name}, kodlarni tekshirayapman...",
        f"🚀 {user_name}, raketani o't oldirdik! Kuting...",
        f"🧠 {user_name}, neyron tarmoqlarim ishlayapti...",
        f"☕ {user_name}, kofe ichib olay, keyin javob beraman... Hazil! Hozir...",
        f"🐛 {user_name}, bug'larni qidirayapman...",
        f"🎨 {user_name}, ijodiy yondashamiz...",
        f"🎪 {user_name}, tomosha boshlandi!...",
        f"🎹 {user_name}, notalarni to'g'rilayapman...",
        f"🎮 {user_name}, level up! Hozir...",
        f"🌟 {user_name}, yulduzli savol!...",
        f"🔥 {user_name}, olov!...",
        f"💎 {user_name}, qimmatli savol!...",
        f"🎯 {user_name}, nishonga urdingiz!...",
        f"🎲 {user_name}, omadimizni sinaymiz!...",
    ]
    
    # Kod tahlili uchun maxsus reaksiyalar
    if message_text == "code_analysis":
        reactions = [
            f"🕵️‍♂️ {user_name}, kodni tintuv qilayapman...",
            f"🔬 {user_name}, mikroskop ostida tekshiramiz...",
            f"🚑 {user_name}, tez yordam yetib keldi! Kodni qutqaramiz...",
            f"🧹 {user_name}, supur-sidir qilamiz...",
            f"🏗️ {user_name}, fundamentni tekshiramiz...",
            f"🧙‍♂️ {user_name}, sehrli tayoqchamni qidirayapman...",
            f"🧛‍♂️ {user_name}, qonini ichmayman, xatosini topaman...",
            f"👮‍♂️ {user_name}, hujjatlarni tekshiramiz...",
            f"👨‍⚕️ {user_name}, tashxis qo'yamiz...",
            f"🧑‍🍳 {user_name}, nima pishiribsiz ekan?...",
        ]
    
    reaction = random.choice(reactions)
    return await update.message.reply_text(
        reaction,
        message_thread_id=message_thread_id
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ishga tushganda ko'rsatiladigan xabar"""
    chat_type = update.message.chat.type
    
    if chat_type == 'private':
        welcome_message = """
🤖 Assalomu alaykum! Men ProX akademiyasining yordamchi bot'iman.

Men sizga quyidagicha yordam bera olaman:
✅ Dasturlash savollaringizga javob beraman
✅ Kod fayllaringizni tekshiraman va xatolarni topaman
✅ Kod yozishda tavsiyalar beraman
✅ Ovozli xabarlaringizni o'zbek tilida tanib javob beraman 🎤
✅ Skrinshotlarni o'qiyman va tahlil qilaman 📸

📝 Foydalanish:
- Savolingizni yozing, men javob beraman
- Kod faylini yuboring, men tahlil qilaman
- Ovozli xabar yuboring, men tanib javob beraman
- Rasm/screenshot yuboring, men o'qib tahlil qilaman

/help - Yordam
/start - Botni qayta ishga tushirish
"""
    else:
        welcome_message = """
🤖 Assalomu alaykum! Men ProX akademiyasining yordamchi bot'iman.

👥 Guruhda foydalanish:
- Savollaringizda meni mention qiling: @{} savol
- Yoki mening xabarimga reply qiling
- Kod faylini yuborayotganda caption'da meni mention qiling
- Ovozli xabar uchun mening xabarimga reply qiling 🎤
- Rasm/screenshot uchun caption'da meni mention qiling 📸

/help - Yordam
""".format(context.bot.username)
    
    await update.message.reply_text(welcome_message)

async def show_settings_menu(update: Update):
    """Sozlamalar menyusini ko'rsatish"""
    settings = settings_manager.get_all()
    
    # Sozlamalar matni
    on_text = "✅ Yoniq"
    off_text = "❌ O'chiq"
    
    settings_text = "⚙️ *BOT SOZLAMALARI*\n\n"
    settings_text += f"🎉 Salom xabari: {on_text if settings['welcome_message_enabled'] else off_text}\n"
    settings_text += f"🎭 Stikerlar: {on_text if settings['stickers_enabled'] else off_text}\n"
    settings_text += f"🎤 Ovozli javob: {on_text if settings['voice_response_enabled'] else off_text}\n"
    settings_text += f"👥 Guruh rejimi: {on_text if settings['group_mode_enabled'] else off_text}\n"
    settings_text += f"🔔 Admin bildirishnomalar: {on_text if settings['admin_notifications'] else off_text}\n\n"
    settings_text += f"📏 Maksimal xabar uzunligi: {settings['max_message_length']}\n"
    settings_text += f"🌡️ Temperature: {settings['response_temperature']}\n"
    settings_text += f"🎯 Max tokens: {settings['max_tokens']}\n"
    
    # Inline tugmalar
    keyboard = [
        [
            InlineKeyboardButton("🎉 Salom xabari", callback_data="toggle_welcome"),
            InlineKeyboardButton("🎭 Stikerlar", callback_data="toggle_stickers")
        ],
        [
            InlineKeyboardButton("🎤 Ovozli javob", callback_data="toggle_voice"),
            InlineKeyboardButton("👥 Guruh rejimi", callback_data="toggle_group")
        ],
        [
            InlineKeyboardButton("🔔 Bildirishnomalar", callback_data="toggle_notifications")
        ],
        [
            InlineKeyboardButton("📏 Xabar uzunligi", callback_data="set_max_length"),
            InlineKeyboardButton("🌡️ Temperature", callback_data="set_temperature")
        ],
        [
            InlineKeyboardButton("🎯 Max tokens", callback_data="set_max_tokens")
        ],
        [
            InlineKeyboardButton("🔄 Qayta tiklash", callback_data="reset_settings"),
            InlineKeyboardButton("❌ Yopish", callback_data="close_settings")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            settings_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistika callback handler"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = query.from_user
    full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    
    # Faqat admin kirishi mumkin
    if not admin_manager.is_admin(user_id) and user_id != SUPER_ADMIN_ID:
        await query.answer("❌ Sizda huquq yo'q!", show_alert=True)
        return
    
    data = query.data
    
    if data == "download_excel":
        # Excel yuklab olish
        await query.answer("📥 Excel fayl tayyorlanmoqda...")
        
        try:
            stats = user_memory.get_statistics()
            
            # Excel fayl yaratish
            excel_filename = f'statistics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            generate_statistics_excel(stats, excel_filename)
            
            # Excel faylni yuborish
            with open(excel_filename, 'rb') as excel_file:
                await query.message.reply_document(
                    document=excel_file,
                    filename=f'ProX_Bot_Statistika_{datetime.now().strftime("%Y-%m-%d")}.xlsx',
                    caption='📊 <b>Bot statistikasi Excel formatda</b>\n\n'
                            '📁 Faylda:\n'
                            '• Umumiy statistika\n'
                            '• Foydalanuvchilar ro\'yxati\n'
                            '• Kunlik statistika\n'
                            '• Fayl turlari',
                    parse_mode='HTML'
                )
            
            # Faylni o'chirish
            os.remove(excel_filename)
            logger.info(f"Excel statistika yuborildi: {full_name}")
            
            # Tugmalarni olib tashlash
            await query.edit_message_reply_markup(reply_markup=None)
            
        except Exception as e:
            logger.error(f"Excel yaratishda xatolik: {e}")
            await query.message.reply_text(
                "⚠️ Excel fayl yaratishda xatolik yuz berdi.",
                parse_mode='HTML'
            )
    
    elif data == "close_stats":
        # Statistikani yopish (tugmalarni olib tashlash)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("✅ Yopildi")

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sozlamalar callback handler"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Faqat admin o'zgartirishi mumkin
    if not admin_manager.is_admin(user_id) and user_id != SUPER_ADMIN_ID:
        await query.answer("❌ Sizda huquq yo'q!", show_alert=True)
        return
    
    data = query.data
    
    # Toggle sozlamalar
    if data == "toggle_welcome":
        new_value = settings_manager.toggle("welcome_message_enabled")
        status = "Yoniq" if new_value else "O'chiq"
        await query.answer(f"Salom xabari: {status}")
        await show_settings_menu(update)
    
    elif data == "toggle_stickers":
        new_value = settings_manager.toggle("stickers_enabled")
        status = "Yoniq" if new_value else "O'chiq"
        await query.answer(f"Stikerlar: {status}")
        await show_settings_menu(update)
    
    elif data == "toggle_voice":
        new_value = settings_manager.toggle("voice_response_enabled")
        status = "Yoniq" if new_value else "O'chiq"
        await query.answer(f"Ovozli javob: {status}")
        await show_settings_menu(update)
    
    elif data == "toggle_group":
        new_value = settings_manager.toggle("group_mode_enabled")
        status = "Yoniq" if new_value else "O'chiq"
        await query.answer(f"Guruh rejimi: {status}")
        await show_settings_menu(update)
    
    elif data == "toggle_notifications":
        new_value = settings_manager.toggle("admin_notifications")
        status = "Yoniq" if new_value else "O'chiq"
        await query.answer(f"Bildirishnomalar: {status}")
        await show_settings_menu(update)
    
    # Raqamli sozlamalar
    elif data == "set_max_length":
        keyboard = [
            [InlineKeyboardButton("2000", callback_data="maxlen_2000"), InlineKeyboardButton("3000", callback_data="maxlen_3000")],
            [InlineKeyboardButton("4000", callback_data="maxlen_4000"), InlineKeyboardButton("5000", callback_data="maxlen_5000")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_settings")]
        ]
        await query.edit_message_text(
            "📏 Maksimal xabar uzunligini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("maxlen_"):
        value = int(data.split("_")[1])
        settings_manager.set("max_message_length", value)
        await query.answer(f"Xabar uzunligi: {value}")
        await show_settings_menu(update)
    
    elif data == "set_temperature":
        keyboard = [
            [InlineKeyboardButton("0.3", callback_data="temp_0.3"), InlineKeyboardButton("0.5", callback_data="temp_0.5")],
            [InlineKeyboardButton("0.7", callback_data="temp_0.7"), InlineKeyboardButton("0.9", callback_data="temp_0.9")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_settings")]
        ]
        await query.edit_message_text(
            "🌡️ Temperature qiymatini tanlang:\n\n0.3 - Aniq javoblar\n0.7 - Muvozanatli\n0.9 - Ijodiy javoblar",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("temp_"):
        value = float(data.split("_")[1])
        settings_manager.set("response_temperature", value)
        await query.answer(f"Temperature: {value}")
        await show_settings_menu(update)
    
    elif data == "set_max_tokens":
        keyboard = [
            [InlineKeyboardButton("1000", callback_data="tokens_1000"), InlineKeyboardButton("1500", callback_data="tokens_1500")],
            [InlineKeyboardButton("2000", callback_data="tokens_2000"), InlineKeyboardButton("3000", callback_data="tokens_3000")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_settings")]
        ]
        await query.edit_message_text(
            "🎯 Max tokens qiymatini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("tokens_"):
        value = int(data.split("_")[1])
        settings_manager.set("max_tokens", value)
        await query.answer(f"Max tokens: {value}")
        await show_settings_menu(update)
    
    elif data == "reset_settings":
        settings_manager.reset()
        await query.answer("✅ Sozlamalar qayta tiklandi!")
        await show_settings_menu(update)
    
    elif data == "back_to_settings":
        await show_settings_menu(update)
    
    elif data == "close_settings":
        await query.edit_message_text("✅ Sozlamalar yopildi")
    
    # Broadcast tasdiqlash
    elif data == "broadcast_confirm":
        broadcast_text = context.user_data.get('broadcast_text', '')
        if broadcast_text:
            await query.edit_message_text("📤 Xabar yuborilmoqda...")
            await broadcast_message(context, broadcast_text, query.from_user.id)
            context.user_data['broadcast_text'] = None
        else:
            await query.answer("❌ Xabar topilmadi!", show_alert=True)
    
    elif data == "broadcast_cancel":
        await query.edit_message_text("❌ Xabar yuborish bekor qilindi")
        context.user_data['broadcast_text'] = None
    
    # Botni qayta yuklash
    elif data == "restart_confirm":
        await query.edit_message_text(
            "🔄 *Bot qayta yuklanmoqda...*\n\n"
            "⏳ Bir necha soniya kuting...",
            parse_mode='HTML'
        )
        logger.info("Bot qayta yuklanmoqda...")
        
        # Application'ni to'xtatish
        import asyncio
        asyncio.create_task(restart_bot(context.application))
        
        return
    
    elif data == "restart_cancel":
        await query.edit_message_text("❌ Qayta yuklash bekor qilindi")
    
    # Admin boshqaruv
    elif data == "add_admin":
        # Faqat Super Admin
        if user_id != SUPER_ADMIN_ID:
            await query.answer("❌ Faqat Super Admin qo'sha oladi!", show_alert=True)
            return
        
        context.user_data['admin_action'] = 'add'
        await query.edit_message_text(
            "➕ *ADMIN QO'SHISH*\n\n"
            "Yangi admin ID'sini yuboring.\n\n"
            "Misol: `123456789`\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode='HTML'
        )
    
    elif data == "remove_admin":
        # Faqat Super Admin
        if user_id != SUPER_ADMIN_ID:
            await query.answer("❌ Faqat Super Admin o'chira oladi!", show_alert=True)
            return
        
        admins = admin_manager.get_all_admins()
        if not admins:
            await query.answer("❌ O'chiriladigan adminlar yo'q!", show_alert=True)
            return
        
        # Adminlarni tanlash uchun tugmalar
        keyboard = []
        for admin in admins:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {admin['name']} ({admin['user_id']})",
                    callback_data=f"remove_admin_{admin['user_id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_admins")])
        
        await query.edit_message_text(
            "➖ *ADMIN O'CHIRISH*\n\n"
            "O'chirmoqchi bo'lgan adminni tanlang:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("remove_admin_"):
        # Faqat Super Admin
        if user_id != SUPER_ADMIN_ID:
            await query.answer("❌ Faqat Super Admin o'chira oladi!", show_alert=True)
            return
        
        admin_id = int(data.split("_")[2])
        
        if admin_manager.remove_admin(admin_id):
            await query.answer("✅ Admin o'chirildi!", show_alert=True)
            
            # Adminlar ro'yxatini yangilash
            admins = admin_manager.get_all_admins()
            admins_text = f"👨‍💼 *ADMINLAR ({admin_manager.get_admin_count()} ta)*\n\n"
            admins_text += f"🔱 Super Admin: `{SUPER_ADMIN_ID}`\n\n"
            
            if admins:
                for idx, admin in enumerate(admins, 1):
                    admins_text += f"{idx}. *{admin['name']}*\n"
                    admins_text += f"   ID: `{admin['user_id']}`\n"
                    admins_text += f"   Qo'shilgan: {admin['added_at']}\n\n"
            else:
                admins_text += "_Hozircha qo'shimcha adminlar yo'q_\n\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
                [InlineKeyboardButton("➖ Admin o'chirish", callback_data="remove_admin")],
                [InlineKeyboardButton("❌ Yopish", callback_data="close_admins")]
            ]
            
            await query.edit_message_text(
                admins_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.answer("❌ Xatolik yuz berdi!", show_alert=True)
    
    elif data == "back_to_admins":
        admins = admin_manager.get_all_admins()
        admins_text = f"👨‍💼 *ADMINLAR ({admin_manager.get_admin_count()} ta)*\n\n"
        admins_text += f"🔱 Super Admin: `{SUPER_ADMIN_ID}`\n\n"
        
        if admins:
            for idx, admin in enumerate(admins, 1):
                admins_text += f"{idx}. *{admin['name']}*\n"
                admins_text += f"   ID: `{admin['user_id']}`\n"
                admins_text += f"   Qo'shilgan: {admin['added_at']}\n\n"
        else:
            admins_text += "_Hozircha qo'shimcha adminlar yo'q_\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Admin o'chirish", callback_data="remove_admin")],
            [InlineKeyboardButton("❌ Yopish", callback_data="close_admins")]
        ]
        
        await query.edit_message_text(
            admins_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "close_admins":
        await query.edit_message_text("✅ Adminlar ro'yxati yopildi")
    


async def restart_bot(application):
    """Botni qayta yuklash"""
    import asyncio
    
    # 2 soniya kutish
    await asyncio.sleep(2)
    
    # Botni to'xtatish
    await application.stop()
    await application.shutdown()
    
    # Python skriptini qayta ishga tushirish
    logger.info("Bot to'xtatildi, qayta ishga tushirilmoqda...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message_text: str, admin_id: int):
    """Barcha foydalanuvchilarga xabar yuborish"""
    import asyncio
    
    stats = user_memory.get_statistics()
    all_users = stats['top_users']
    
    if not all_users:
        await context.bot.send_message(
            chat_id=admin_id,
            text="❌ Hozircha foydalanuvchilar yo'q!"
        )
        return
    
    # Yuborish statistikasi
    total = len(all_users)
    success = 0
    failed = 0
    
    status_msg = await context.bot.send_message(
        chat_id=admin_id,
        text=f"📤 Xabar yuborilmoqda...\n\n0/{total} ta foydalanuvchi"
    )
    
    # Telegram limiti: 30 xabar/soniya
    batch_size = 30
    delay_between_batches = 1  # 1 soniya
    
    for i, user in enumerate(all_users):
        try:
            user_id = int(user['user_id'])
            
            # Xabarni yuborish
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Admin xabari:*\n\n{message_text}",
                parse_mode='HTML'
            )
            success += 1
            
        except Exception as e:
            logger.error(f"Xabar yuborishda xatolik ({user_id}): {e}")
            failed += 1
        
        # Har 30 ta xabardan keyin 1 soniya kutish
        if (i + 1) % batch_size == 0:
            # Statusni yangilash
            await status_msg.edit_text(
                f"📤 Xabar yuborilmoqda...\n\n"
                f"✅ Yuborildi: {success}\n"
                f"❌ Xatolik: {failed}\n"
                f"📊 Jami: {i + 1}/{total}"
            )
            await asyncio.sleep(delay_between_batches)
    
    # Yakuniy natija
    await status_msg.edit_text(
        f"✅ *XABAR YUBORISH YAKUNLANDI*\n\n"
        f"📊 Jami: {total} ta foydalanuvchi\n"
        f"✅ Muvaffaqiyatli: {success}\n"
        f"❌ Xatolik: {failed}",
        parse_mode='HTML'
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast yoki admin qo'shish rejimini bekor qilish"""
    if context.user_data.get('broadcast_mode'):
        context.user_data['broadcast_mode'] = False
        await update.message.reply_text("❌ Xabar yuborish bekor qilindi")
    elif context.user_data.get('admin_action'):
        context.user_data['admin_action'] = None
        await update.message.reply_text("❌ Admin qo'shish bekor qilindi")
    else:
        await update.message.reply_text("Hozirda bekor qilinadigan jarayon yo'q")

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel buyrug'i"""
    user_id = update.message.from_user.id
    
    # Faqat admin kirishi mumkin
    if not admin_manager.is_admin(user_id) and user_id != SUPER_ADMIN_ID:
        await update.message.reply_text("❌ Sizda admin huquqi yo'q!")
        return
    
    # Admin panel tugmalari
    keyboard = [
        ["📊 Statistika", "👥 Foydalanuvchilar"],
        ["📢 Xabar yuborish", "⚙️ Sozlamalar"],
        ["👨‍💼 Adminlar", "🔄 Botni qayta yuklash"],
        ["❌ Panelni yopish"]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Admin darajasini aniqlash
    admin_level = "Super Admin" if user_id == SUPER_ADMIN_ID else "Admin"
    
    await update.message.reply_text(
        f"🔐 *Admin Panel*\n\n"
        f"👤 Sizning darajangiz: *{admin_level}*\n\n"
        f"Kerakli bo'limni tanlang:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam buyrug'i"""
    chat_type = update.message.chat.type
    
    if chat_type == 'private':
        help_text = """
📚 Bot qanday ishlaydi:

1️⃣ Savol berish:
   Oddiy xabar yozing, men javob beraman.
   Misol: "Python'da list va tuple farqi nima?"

2️⃣ Kod tekshirish:
   Kod faylini (.py, .js, .java va boshqalar) yuboring.
   Men kodni tahlil qilib, xatolar va tavsiyalar beraman.

3️⃣ Ovozli xabar:
   🎤 Ovozli xabar yuboring, men o'zbek tilida tanib javob beraman.

4️⃣ Rasm/Screenshot:
   📸 Rasm yuboring, men o'qib tahlil qilaman.
   - Kod screenshot'i
   - Xato xabarlari
   - Diagrammalar

💡 Maslahatlar:
- Savollaringizni aniq va tushunarli yozing
- Kod yuborayotganda fayl nomini to'g'ri kiriting
- Ovozli xabar aniq va tiniq bo'lsin
- Screenshot aniq va o'qilishi oson bo'lsin

Savollaringiz bo'lsa, bemalol yozing! 😊
"""
    else:
        help_text = """
📚 Guruhda bot qanday ishlaydi:

1️⃣ Savol berish:
   Meni mention qiling: @{} Python'da list nima?
   Yoki mening javobimga reply qiling.

2️⃣ Kod tekshirish:
   Kod faylini yuboring va caption'da meni mention qiling:
   @{} bu kodni tekshir

3️⃣ Ovozli xabar:
   🎤 Mening xabarimga reply qilib ovozli xabar yuboring.

4️⃣ Rasm/Screenshot:
   📸 Rasm yuboring va caption'da meni mention qiling:
   @{} bu rasmni tahlil qil

💡 Maslahatlar:
- Guruhda bot faqat mention yoki reply orqali javob beradi
- Savollaringizni aniq va tushunarli yozing
- Ovozli xabar aniq va tiniq bo'lsin
- Screenshot aniq va o'qilishi oson bo'lsin

Savollaringiz bo'lsa, bemalol yozing! 😊
""".format(context.bot.username, context.bot.username)
    
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oddiy xabarlarga javob beradi"""
    user_message = update.message.text
    user = update.message.from_user
    user_name = user.first_name
    # To'liq ism (first_name + last_name)
    full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    chat_type = update.message.chat.type
    
    # Admin action (admin qo'shish)
    if (user.id == SUPER_ADMIN_ID and chat_type == 'private' and 
        context.user_data.get('admin_action') == 'add'):
        
        context.user_data['admin_action'] = None
        
        # ID ni tekshirish
        try:
            new_admin_id = int(user_message.strip())
            
            # O'zini qo'sha olmaydi
            if new_admin_id == SUPER_ADMIN_ID:
                await update.message.reply_text("❌ Super Admin allaqachon mavjud!")
                return
            
            # Foydalanuvchi ma'lumotlarini olish
            try:
                chat = await context.bot.get_chat(new_admin_id)
                admin_name = chat.first_name
                if chat.last_name:
                    admin_name += f" {chat.last_name}"
            except:
                admin_name = f"User {new_admin_id}"
            
            # Admin qo'shish
            if admin_manager.add_admin(new_admin_id, admin_name, user.id):
                await update.message.reply_text(
                    f"✅ *Admin qo'shildi!*\n\n"
                    f"👤 Ism: {admin_name}\n"
                    f"🆔 ID: `{new_admin_id}`",
                    parse_mode='HTML'
                )
                
                # Yangi adminga xabar yuborish
                try:
                    await context.bot.send_message(
                        chat_id=new_admin_id,
                        text=f"🎉 *Tabriklaymiz!*\n\n"
                             f"Siz ProX Akademiyasi botining admini bo'ldingiz!\n\n"
                             f"Admin panelga kirish: /panel",
                        parse_mode='HTML'
                    )
                except:
                    pass
            else:
                await update.message.reply_text("❌ Bu foydalanuvchi allaqachon admin!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID format! Faqat raqam kiriting.")
        return
    
    # Broadcast rejimini tekshirish
    if ((admin_manager.is_admin(user.id) or user.id == SUPER_ADMIN_ID) and 
        chat_type == 'private' and context.user_data.get('broadcast_mode')):
        # Broadcast xabarini yuborish
        context.user_data['broadcast_mode'] = False
        
        confirm_keyboard = [
            [InlineKeyboardButton("✅ Ha, yuborish", callback_data="broadcast_confirm")],
            [InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data="broadcast_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(confirm_keyboard)
        
        # Xabarni context'ga saqlash
        context.user_data['broadcast_text'] = user_message
        
        await update.message.reply_text(
            f"📢 *Xabar tayyorlandi:*\n\n{user_message}\n\n"
            f"Barcha foydalanuvchilarga yuborilsinmi?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Admin panel tugmalarini qayta ishlash
    if (admin_manager.is_admin(user.id) or user.id == SUPER_ADMIN_ID) and chat_type == 'private':
        if user_message == "📊 Statistika":
            stats = user_memory.get_statistics()
            
            # Statistikani formatlash
            stats_text = format_statistics(stats)
            
            # Inline tugmalar
            keyboard = [
                [InlineKeyboardButton("📥 Excel formatda yuklab olish", callback_data="download_excel")],
                [InlineKeyboardButton("❌ Yopish", callback_data="close_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Matn statistikani yuborish
            await update.message.reply_text(
                stats_text, 
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            return
        elif user_message == "👥 Foydalanuvchilar":
            stats = user_memory.get_statistics()
            
            if stats['total_users'] == 0:
                await update.message.reply_text("👥 Hozircha foydalanuvchilar yo'q")
                return
            
            users_text = f"👥 <b>FOYDALANUVCHILAR ({stats['total_users']} ta)</b>\n\n"
            
            # Barcha foydalanuvchilarni ko'rsatish
            all_users = stats['top_users']  # Allaqachon saralangan
            
            for idx, user in enumerate(all_users[:20], 1):  # Faqat 20 ta
                users_text += f"{idx}. <b>{user['name']}</b>\n"
                users_text += f"   ID: <code>{user['user_id']}</code>\n"
                users_text += f"   📊 Jami: {user['total']} | 📝 {user['text']} | 📄 {user['file']} | 🖼️ {user['image']}\n"
                
                # Fayl turlari
                if user['files_by_type']:
                    file_types = ', '.join([f"{k}({v})" for k, v in list(user['files_by_type'].items())[:3]])
                    users_text += f"   📁 Fayllar: {file_types}\n"
                
                users_text += "\n"
            
            if len(all_users) > 20:
                users_text += f"\n<i>... va yana {len(all_users) - 20} ta foydalanuvchi</i>"
            
            await update.message.reply_text(users_text, parse_mode='HTML')
            return
        elif user_message == "📢 Xabar yuborish":
            # Broadcast rejimini yoqish
            context.user_data['broadcast_mode'] = True
            await update.message.reply_text(
                "📢 *XABAR YUBORISH*\n\n"
                "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing.\n\n"
                "❌ Bekor qilish uchun /cancel yozing.",
                parse_mode='HTML'
            )
            return
        elif user_message == "⚙️ Sozlamalar":
            # Sozlamalar menyusini ko'rsatish
            await show_settings_menu(update)
            return
        elif user_message == "👨‍💼 Adminlar":
            # Adminlar ro'yxati
            admins = admin_manager.get_all_admins()
            
            admins_text = f"👨‍💼 *ADMINLAR ({admin_manager.get_admin_count()} ta)*\n\n"
            admins_text += f"🔱 Super Admin: `{SUPER_ADMIN_ID}`\n\n"
            
            if admins:
                for idx, admin in enumerate(admins, 1):
                    admins_text += f"{idx}. *{admin['name']}*\n"
                    admins_text += f"   ID: `{admin['user_id']}`\n"
                    admins_text += f"   Qo'shilgan: {admin['added_at']}\n\n"
            else:
                admins_text += "_Hozircha qo'shimcha adminlar yo'q_\n\n"
            
            # Faqat Super Admin admin qo'shishi/o'chirishi mumkin
            if user.id == SUPER_ADMIN_ID:
                keyboard = [
                    [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
                    [InlineKeyboardButton("➖ Admin o'chirish", callback_data="remove_admin")],
                    [InlineKeyboardButton("❌ Yopish", callback_data="close_admins")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(admins_text, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(admins_text, parse_mode='HTML')
            return
        elif user_message == "🔄 Botni qayta yuklash":
            # Tasdiqlash tugmalari
            keyboard = [
                [InlineKeyboardButton("✅ Ha, qayta yuklash", callback_data="restart_confirm")],
                [InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data="restart_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔄 *BOTNI QAYTA YUKLASH*\n\n"
                "⚠️ Bot bir necha soniya ishlamay qoladi.\n\n"
                "Davom etishni xohlaysizmi?",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return
        elif user_message == "❌ Panelni yopish":
            await update.message.reply_text(
                "✅ Panel yopildi",
                reply_markup=ReplyKeyboardRemove()
            )
            return
    
    # Guruhda faqat botga mention qilingan yoki reply qilingan xabarlarga javob berish
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username
        # Bot mention qilinganmi yoki botga reply qilinganmi tekshirish
        is_mentioned = f"@{bot_username}" in user_message if bot_username else False
        is_reply_to_bot = (update.message.reply_to_message and 
                          update.message.reply_to_message.from_user.id == context.bot.id)
        
        # Entities orqali ham mention tekshirish
        has_mention_entity = False
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    mentioned_text = user_message[entity.offset:entity.offset + entity.length]
                    if bot_username and mentioned_text == f"@{bot_username}":
                        has_mention_entity = True
                        break
        
        if not (is_mentioned or is_reply_to_bot or has_mention_entity):
            return  # Botga murojaat qilinmagan bo'lsa, javob bermaslik
        
        # Mention bo'lsa, bot username'ini xabardan olib tashlash
        if is_mentioned and bot_username:
            user_message = user_message.replace(f"@{bot_username}", "").strip()
    
    logger.info(f"Savol ({chat_type}): {full_name} - {user_message}")
    
    # Guruhda stiker yuborish (agar sozlamalarda yoniq bo'lsa)
    if chat_type in ['group', 'supergroup'] and settings_manager.get('stickers_enabled', True):
        sticker_id = get_random_sticker('thinking')
        if sticker_id:
            try:
                await update.message.reply_sticker(sticker_id)
            except Exception as e:
                logger.error(f"Stiker yuborishda xatolik: {e}")
    
    # "Javob tayyorlanmoqda..." xabari
    processing_msg = await send_humor_reaction(update, context, user_message, full_name)
    
    # Guruhda bo'lsa, to'liq ismini yuborish
    user_name_for_ai = full_name if chat_type in ['group', 'supergroup'] else None
    
    # User kontekstini olish
    user_context = user_memory.get_user_context(user.id)
    greeting_context = user_memory.get_greeting_context(user.id)
    
    # Groq API orqali javob olish
    response = await groq_client.answer_question(user_message, user_name_for_ai, greeting_context)
    
    # Yozma so'rov statistikasini yangilash
    user_memory.add_request(user.id, full_name, 'text')
    
    # Suhbatni xotiraga saqlash
    user_memory.add_conversation(user.id, full_name, user_message, response)
    
    # Processing xabarini o'chirish
    await processing_msg.delete()
    
    # Javobni yuborish (uzun bo'lsa bo'lib yuborish)
    await send_long_message(update, response, 'HTML')
    
    logger.info(f"Javob yuborildi: {full_name}")
    
    # FAQAT foydalanuvchi kod yuborgan bo'lsa quiz chiqarish
    # Oddiy savollarda quiz chiqarmaslik!
    # Kod yuborilganligini aniqlash: xabar uzun va dasturlash keyword'lari bor
    has_code_in_message = len(user_message) > 100 and any(keyword in user_message.lower() for keyword in ['def ', 'class ', 'function ', 'import ', 'print(', 'console.log', 'public ', 'private ', 'void ', 'int ', 'string ', 'return ', 'if ', 'for ', 'while ', 'const ', 'let ', 'var ', 'async ', 'await '])
    
    # FAQAT foydalanuvchi kod yuborgan bo'lsa quiz yaratish
    if has_code_in_message:
        try:
            # Foydalanuvchi yuborgan kodni olish
            combined_code = user_message.strip()
            
            # HTML entities ni decode qilish
            import html
            combined_code = html.unescape(combined_code)
            
            # Agar kod yetarlicha uzun bo'lsa (kamida 80 belgi)
            if len(combined_code.strip()) >= 80:
                # API rate limit uchun 2 soniya kutish
                logger.info("⏳ API rate limit uchun 2 soniya kutilmoqda...")
                await asyncio.sleep(2)
                
                # Avtomatik quiz boshlash (ruxsat so'ramasdan)
                await update.message.reply_text(
                    "🎯 Endi bilimingizni sinab ko'ramiz!",
                    message_thread_id=update.message.message_thread_id
                )
                
                quiz_msg = await update.message.reply_text(
                    "⏳ Quiz savollari tayyorlanmoqda...",
                    message_thread_id=update.message.message_thread_id
                )
                
                try:
                    # Quiz yaratish
                    questions = await groq_client.generate_quiz(combined_code, "kod_misoli.txt", full_name)
                    
                    if not questions:
                        await quiz_msg.edit_text("❌ Quiz yaratishda xatolik. Iltimos qaytadan urinib ko'ring.")
                        return
                    
                    # Sessiya yaratish
                    quiz_manager.create_session(user.id, combined_code, "kod_misoli.txt", questions)
                    
                    # "Tayyorlanmoqda" xabarini o'chirish
                    await quiz_msg.delete()
                    
                    # Birinchi savolni yuborish
                    await send_quiz_question(update.message, user.id)
                    
                except Exception as quiz_error:
                    logger.error(f"Text quiz yaratishda xatolik: {quiz_error}")
                    await quiz_msg.edit_text("❌ Quiz yaratishda xatolik yuz berdi.")
        except Exception as e:
            logger.error(f"Quiz taklif qilishda xatolik: {e}")
            pass

async def delayed_process_photos(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, user_name: str, full_name: str):
    """Rasmlarni biroz kutib keyin qayta ishlash"""
    try:
        await asyncio.sleep(2)
        await process_buffered_photos(context, user_id, chat_id, user_name, full_name)
    except asyncio.CancelledError:
        pass

async def process_buffered_photos(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, user_name: str, full_name: str):
    """Buferlangan rasmlarni qayta ishlash"""
    if user_id not in user_photo_buffer:
        return
        
    buffer_data = user_photo_buffer[user_id]
    photo_paths = buffer_data['paths']
    processing_msg = buffer_data['processing_msg']
    
    # Buferni tozalash (lekin fayllarni o'chirmaslik, ular tahlildan keyin o'chiriladi)
    del user_photo_buffer[user_id]
    
    try:
        # Guruhda bo'lsa, to'liq ismini yuborish
        user_name_for_ai = full_name if context.bot.username else None 
        
        # OCR orqali kodni olish (rasmlarni o'chirishdan oldin!)
        ocr_code = ""
        for i, image_path in enumerate(photo_paths):
            try:
                from PIL import Image
                import pytesseract
                import cv2
                import numpy as np
                
                image = Image.open(image_path)
                img_array = np.array(image)
                
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                extracted_text = pytesseract.image_to_string(img_array, lang='eng')
                if extracted_text.strip():
                    ocr_code += extracted_text + "\n\n"
            except:
                pass
        
        # Rasm so'rov statistikasini yangilash
        user_memory.add_request(user_id, full_name, 'image')
        
        # Rasmlarni tahlil qilish
        response = await groq_client.analyze_images(photo_paths, user_name)
        
        # Rasmlarni o'chirish
        for path in photo_paths:
            if os.path.exists(path):
                os.remove(path)
        
        # Xotiraga saqlash
        user_memory.add_conversation(user_id, full_name, f"{len(photo_paths)} ta rasm yubordi", response)
        
        # Processing xabarini o'chirish
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        
        # Javobni yuborish
        # Topic ID ni olish (agar mavjud bo'lsa)
        message_thread_id = buffer_data.get('message_thread_id')
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=response,
            parse_mode='HTML',
            message_thread_id=message_thread_id
        )
        
        logger.info(f"Rasm tahlili yuborildi: {full_name} ({len(photo_paths)} ta rasm)")
        
        # Avtomatik quiz boshlash (agar rasmda kod bo'lsa)
        try:
            # Agar kod topilsa, quiz yaratish
            if ocr_code.strip() and len(ocr_code.strip()) > 50:  # Kamida 50 ta belgi bo'lishi kerak
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏳ Quiz savollari tayyorlanmoqda...",
                    message_thread_id=message_thread_id
                )
                
                # Quiz yaratish
                questions = await groq_client.generate_quiz(ocr_code, "rasm_kodi.txt", full_name)
                
                if questions:
                    # Sessiya yaratish
                    quiz_manager.create_session(user_id, ocr_code, "rasm_kodi.txt", questions)
                    
                    # Birinchi savolni yuborish (context.bot orqali)
                    from quiz_handlers import send_quiz_question_via_bot
                    await send_quiz_question_via_bot(context.bot, chat_id, user_id, message_thread_id)
                    
                    logger.info(f"Rasm tahlili va quiz yuborildi: {full_name}")
        except Exception as quiz_error:
            logger.error(f"Quiz yaratishda xatolik: {quiz_error}")
            # Quiz xatosi asosiy jarayonga ta'sir qilmasin
            pass
        
    except Exception as e:
        logger.error(f"Rasmlarni qayta ishlashda xatolik: {e}")
        if processing_msg:
            try:
                await processing_msg.edit_text("❌ Rasmlarni qayta ishlashda xatolik yuz berdi. Qaytadan urinib ko'ring.")
            except:
                pass
        # Rasmlarni o'chirish
        for path in photo_paths:
            if os.path.exists(path):
                os.remove(path)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yuborilgan rasmlarni qayta ishlaydi (Buffer bilan)"""
    photo = update.message.photo[-1]  # Eng katta o'lchamdagi rasm
    user = update.message.from_user
    full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    chat_type = update.message.chat.type
    
    # Guruhda faqat botga reply qilingan rasmlarga javob berish
    if chat_type in ['group', 'supergroup']:
        is_reply_to_bot = (update.message.reply_to_message and 
                          update.message.reply_to_message.from_user.id == context.bot.id)
        # Guruhda caption'da bot mention qilinganmi tekshirish
        caption = update.message.caption or ""
        bot_username = context.bot.username
        is_mentioned = f"@{bot_username}" in caption if bot_username else False
        
        # Caption entities orqali ham mention tekshirish
        has_mention_entity = False
        if update.message.caption_entities:
            for entity in update.message.caption_entities:
                if entity.type == "mention":
                    mentioned_text = caption[entity.offset:entity.offset + entity.length]
                    if bot_username and mentioned_text == f"@{bot_username}":
                        has_mention_entity = True
                        break
        
        if not (is_reply_to_bot or is_mentioned or has_mention_entity):
            return
    
    logger.info(f"Rasm qabul qilindi ({chat_type}): {full_name}")
    
    # Photo path'ni aniqlash
    photo_path = f"photo_{photo.file_id}.jpg"
    
    # Rasmni yuklab olish
    photo_file = await context.bot.get_file(photo.file_id)
    await photo_file.download_to_drive(photo_path)
    
    # Buferga qo'shish
    if user.id not in user_photo_buffer:
        # Yangi bufer yaratish
        processing_msg = await update.message.reply_text(
            "🖼️ Rasm qabul qilindi, yana bormi? (2 soniya kutaman...)",
            message_thread_id=update.message.message_thread_id
        )
        
        user_photo_buffer[user.id] = {
            'paths': [photo_path],
            'processing_msg': processing_msg,
            'message_thread_id': update.message.message_thread_id,  # Topic ID ni saqlash
            'task': None
        }
    else:
        # Mavjud buferga qo'shish
        user_photo_buffer[user.id]['paths'].append(photo_path)
        # Eski taskni bekor qilish
        if user_photo_buffer[user.id]['task']:
            user_photo_buffer[user.id]['task'].cancel()
            
        # Xabarni yangilash
        try:
            count = len(user_photo_buffer[user.id]['paths'])
            await user_photo_buffer[user.id]['processing_msg'].edit_text(f"🖼️ {count} ta rasm qabul qilindi, yana bormi?...")
        except:
            pass
    
    # Yangi task yaratish (2 soniya)
    user_photo_buffer[user.id]['task'] = asyncio.create_task(
        delayed_process_photos(context, user.id, update.message.chat_id, full_name, full_name)
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yuborilgan fayllarni qayta ishlaydi"""
    document = update.message.document
    user = update.message.from_user
    user_name = user.first_name
    # To'liq ism (first_name + last_name)
    full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    chat_type = update.message.chat.type
    
    # Guruhda faqat botga reply qilingan fayllarni qayta ishlash
    if chat_type in ['group', 'supergroup']:
        is_reply_to_bot = (update.message.reply_to_message and 
                          update.message.reply_to_message.from_user.id == context.bot.id)
        # Guruhda caption'da bot mention qilinganmi tekshirish
        caption = update.message.caption or ""
        bot_username = context.bot.username
        is_mentioned = f"@{bot_username}" in caption if bot_username else False
        
        # Caption entities orqali ham mention tekshirish
        has_mention_entity = False
        if update.message.caption_entities:
            for entity in update.message.caption_entities:
                if entity.type == "mention":
                    mentioned_text = caption[entity.offset:entity.offset + entity.length]
                    if bot_username and mentioned_text == f"@{bot_username}":
                        has_mention_entity = True
                        break
        
        if not (is_reply_to_bot or is_mentioned or has_mention_entity):
            return  # Botga murojaat qilinmagan bo'lsa, qayta ishlamaslik
    
    # Fayl hajmini tekshirish
    if document.file_size > config.MAX_FILE_SIZE:
        await update.message.reply_text(
            "❌ Fayl hajmi juda katta. Maksimal 5MB bo'lishi kerak.",
            message_thread_id=update.message.message_thread_id
        )
        return
    
    # Fayl kengaytmasini tekshirish
    file_extension = '.' + document.file_name.split('.')[-1] if '.' in document.file_name else ''
    if file_extension not in config.ALLOWED_FILE_EXTENSIONS:
        await update.message.reply_text(
            f"❌ Bu fayl turi qo'llab-quvvatlanmaydi.\n"
            f"Qo'llab-quvvatlanadigan formatlar: {', '.join(config.ALLOWED_FILE_EXTENSIONS)}",
            message_thread_id=update.message.message_thread_id
        )
        return
    
    logger.info(f"Fayl qabul qilindi ({chat_type}): {full_name} - {document.file_name}")
    
    # Guruhda stiker yuborish (agar sozlamalarda yoniq bo'lsa)
    if chat_type in ['group', 'supergroup'] and settings_manager.get('stickers_enabled', True):
        sticker_id = get_random_sticker('coding')
        if sticker_id:
            try:
                await update.message.reply_sticker(
                    sticker_id,
                    message_thread_id=update.message.message_thread_id
                )
            except Exception as e:
                logger.error(f"Stiker yuborishda xatolik: {e}")
    
    # "Kod tahlil qilinmoqda..." xabari
    processing_msg = await send_humor_reaction(update, context, "code_analysis", full_name)
    
    try:
        # Faylni yuklab olish
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        # UTF-8 decode qilish (xatolik bo'lsa, boshqa encoding'larni sinash)
        try:
            code = file_content.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode xatolik, latin-1 bilan urinilmoqda...")
            try:
                code = file_content.decode('latin-1')
            except:
                logger.warning(f"Latin-1 ham ishlamadi, cp1252 bilan urinilmoqda...")
                code = file_content.decode('cp1252', errors='ignore')
        
        logger.info(f"✅ Fayl o'qildi: {len(code)} belgi")
        
        # Guruhda bo'lsa, to'liq ismini yuborish
        user_name_for_ai = full_name if chat_type in ['group', 'supergroup'] else None
        
        # Fayl turini aniqlash
        file_extension = document.file_name.split('.')[-1].lower() if '.' in document.file_name else 'unknown'
        file_type_map = {
            # Python
            'py': 'python', 'pyw': 'python', 'pyx': 'python', 'pyi': 'python',
            
            # JavaScript/TypeScript
            'js': 'javascript', 'jsx': 'react', 'mjs': 'javascript', 'cjs': 'javascript', 'es6': 'javascript',
            'ts': 'typescript', 'tsx': 'react-ts',
            
            # Web
            'html': 'html', 'htm': 'html', 'xhtml': 'html',
            'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less', 'styl': 'stylus',
            'vue': 'vue', 'svelte': 'svelte', 'astro': 'astro',
            
            # Java/Kotlin
            'java': 'java', 'jar': 'java',
            'kt': 'kotlin', 'kts': 'kotlin',
            
            # C/C++
            'c': 'c',
            'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'c++': 'cpp',
            'h': 'c-header', 'hpp': 'cpp-header', 'hxx': 'cpp-header', 'h++': 'cpp-header',
            
            # C#
            'cs': 'csharp', 'csx': 'csharp',
            
            # Go
            'go': 'go',
            
            # Rust
            'rs': 'rust',
            
            # PHP
            'php': 'php', 'phtml': 'php', 'php3': 'php', 'php4': 'php', 'php5': 'php',
            
            # Ruby
            'rb': 'ruby', 'erb': 'ruby', 'rake': 'ruby',
            
            # Swift
            'swift': 'swift',
            
            # Objective-C
            'm': 'objective-c', 'mm': 'objective-c++',
            
            # Dart
            'dart': 'dart',
            
            # Elixir
            'ex': 'elixir', 'exs': 'elixir',
            
            # Haskell
            'hs': 'haskell', 'lhs': 'haskell',
            
            # Shell
            'sh': 'bash', 'bash': 'bash', 'zsh': 'zsh', 'fish': 'fish',
            
            # SQL
            'sql': 'sql', 'mysql': 'mysql', 'pgsql': 'postgresql',
            
            # Config/Data
            'json': 'json', 'json5': 'json5', 'jsonc': 'jsonc',
            'xml': 'xml', 'xsd': 'xml', 'xsl': 'xml',
            'yaml': 'yaml', 'yml': 'yaml',
            'toml': 'toml',
            'ini': 'ini', 'cfg': 'config', 'conf': 'config',
            'env': 'env',
            'properties': 'properties',
            
            # Markdown/Text
            'md': 'markdown', 'markdown': 'markdown', 'mdown': 'markdown',
            'txt': 'text', 'text': 'text',
            'rst': 'rst', 'rest': 'rst',
            'adoc': 'asciidoc', 'asciidoc': 'asciidoc',
            
            # Assembly
            'asm': 'assembly', 's': 'assembly',
            
            # Lisp
            'lisp': 'lisp', 'cl': 'common-lisp', 'el': 'emacs-lisp',
            'clj': 'clojure', 'cljs': 'clojurescript', 'cljc': 'clojure',
            
            # Functional
            'ml': 'ocaml', 'mli': 'ocaml',
            'fs': 'fsharp', 'fsx': 'fsharp',
            'erl': 'erlang', 'hrl': 'erlang',
            
            # Other
            'r': 'r', 'rmd': 'rmarkdown',
            'lua': 'lua',
            'pl': 'perl', 'pm': 'perl',
            'scala': 'scala',
            'groovy': 'groovy', 'gradle': 'gradle',
            'vim': 'vimscript',
            'bat': 'batch', 'cmd': 'batch', 'ps1': 'powershell',
            'dockerfile': 'docker',
            'makefile': 'makefile',
            'proto': 'protobuf',
            'graphql': 'graphql', 'gql': 'graphql',
            'sol': 'solidity',
            'v': 'verilog', 'sv': 'systemverilog',
            'vhd': 'vhdl', 'vhdl': 'vhdl',
        }
        file_type = file_type_map.get(file_extension, file_extension)
        
        # Fayl so'rov statistikasini yangilash
        user_memory.add_request(user.id, full_name, 'file', file_type)
        
        # Kodni tahlil qilish
        logger.info(f"🔄 Kod tahlili boshlandi: {document.file_name}")
        response = await groq_client.analyze_code(code, document.file_name, user_name_for_ai)
        logger.info(f"✅ Kod tahlili tugadi: {len(response)} belgi")
        
        # Agar tahlil xatolik xabari bo'lsa, quiz yaratmaslik
        if response.startswith("⚠️") or response.startswith("❌") or response.startswith("🔑"):
            logger.warning(f"⚠️ Kod tahlili xatolik berdi, quiz yaratilmaydi")
            # Processing xabarini o'chirish
            await processing_msg.delete()
            # Xatolik xabarini yuborish
            await update.message.reply_text(
                response,
                parse_mode='HTML',
                message_thread_id=update.message.message_thread_id
            )
            return  # Quiz yaratmasdan to'xtatish
        
        # Natijani aniqlash (xatoli yoki xatosiz)
        result = 'neutral'
        response_lower = response.lower()
        if '❌' in response or 'xato' in response_lower or 'muammo' in response_lower:
            result = 'negative'
        elif '✅' in response or 'yaxshi' in response_lower or 'to\'g\'ri' in response_lower:
            result = 'positive'
        
        # Kod tekshirish statistikasini yangilash
        user_memory.add_code_review(user.id, full_name, result)
        user_memory.add_conversation(user.id, full_name, f"Kod tekshirish: {document.file_name}", response)
        
        # Processing xabarini o'chirish
        await processing_msg.delete()
        
        # Javobni yuborish (uzun bo'lsa bo'lib yuborish)
        full_response = f"📄 Fayl: {document.file_name}\n\n{response}"
        await send_long_message(update, full_response, 'HTML')
        
        # API rate limit uchun 2 soniya kutish
        logger.info("⏳ API rate limit uchun 2 soniya kutilmoqda...")
        await asyncio.sleep(2)
        
        # Avtomatik quiz boshlash
        quiz_msg = await update.message.reply_text(
            "⏳ Quiz savollari tayyorlanmoqda...",
            message_thread_id=update.message.message_thread_id
        )
        
        try:
            # Quiz yaratish
            logger.info(f"🔄 Quiz yaratish boshlandi: {full_name}")
            questions = await groq_client.generate_quiz(code, document.file_name, full_name)
            
            if not questions:
                await quiz_msg.edit_text("❌ Quiz yaratishda xatolik. Iltimos qaytadan urinib ko'ring.")
                logger.error(f"❌ Quiz yaratilmadi (None qaytdi): {full_name}")
                return
            
            logger.info(f"✅ {len(questions)} ta savol yaratildi")
            
            # Sessiya yaratish
            logger.info(f"🔄 Sessiya yaratilmoqda: user_id={user.id}")
            session_created = quiz_manager.create_session(user.id, code, document.file_name, questions)
            logger.info(f"✅ Sessiya yaratildi: {session_created}")
            
            # "Tayyorlanmoqda" xabarini o'chirish
            try:
                await quiz_msg.delete()
                logger.info("✅ 'Tayyorlanmoqda' xabari o'chirildi")
            except Exception as e:
                logger.warning(f"⚠️ Xabarni o'chirishda xatolik: {e}")
            
            # Birinchi savolni yuborish
            logger.info(f"🔄 Birinchi savol yuborilmoqda: user_id={user.id}")
            await send_quiz_question(update.message, user.id)
            
            logger.info(f"✅ Tahlil va quiz yuborildi: {full_name}")
            
        except Exception as quiz_error:
            logger.error(f"Quiz yaratishda xatolik: {quiz_error}")
            logger.exception("Quiz xatolik traceback:")
            await quiz_msg.edit_text(
                "❌ Quiz yaratishda xatolik yuz berdi.\n\n"
                "Kod tahlili muvaffaqiyatli bajarildi, lekin quiz savollari yaratilmadi."
            )
        
    except UnicodeDecodeError:
        await processing_msg.edit_text("❌ Faylni o'qishda xatolik. Fayl matn formatida bo'lishi kerak.")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Xatolik (handle_document): {e}")
        logger.exception("Full traceback:")
        
        # Xabarni yuborish (edit_text o'rniga reply_text)
        try:
            # 429 xatolik uchun maxsus xabar
            if "429" in error_msg or "Too Many Requests" in error_msg:
                await update.message.reply_text(
                    "⚠️ <b>Juda ko'p so'rov yuborildi</b>\n\n"
                    "Groq API limiti tugadi. Iltimos:\n"
                    "• 1-2 daqiqa kuting\n"
                    "• Qaytadan fayl yuboring\n\n"
                    "💡 <i>Bepul rejimda 10 so'rov/daqiqa limit bor.</i>",
                    parse_mode='HTML',
                    message_thread_id=update.message.message_thread_id
                )
            elif "400" in error_msg or "Bad Request" in error_msg:
                await update.message.reply_text(
                    "❌ <b>Faylni qayta ishlashda xatolik</b>\n\n"
                    "Sabablari:\n"
                    "• Fayl juda uzun (token limiti)\n"
                    "• Noto'g'ri format\n"
                    "• API xatolik\n\n"
                    "💡 Kichikroq fayl yuboring yoki qaytadan urinib ko'ring.",
                    parse_mode='HTML',
                    message_thread_id=update.message.message_thread_id
                )
            else:
                await update.message.reply_text(
                    "❌ Faylni qayta ishlashda xatolik yuz berdi. Qaytadan urinib ko'ring.",
                    message_thread_id=update.message.message_thread_id
                )
            
            # Processing xabarini o'chirish
            try:
                await processing_msg.delete()
            except:
                pass
        except Exception as send_error:
            logger.error(f"Xatolik xabarini yuborishda muammo: {send_error}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ovozli xabarlarni qayta ishlaydi"""
    voice = update.message.voice
    user = update.message.from_user
    full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    chat_type = update.message.chat.type
    
    # Guruhda faqat botga reply qilingan ovozli xabarlarga javob berish
    if chat_type in ['group', 'supergroup']:
        is_reply_to_bot = (update.message.reply_to_message and 
                          update.message.reply_to_message.from_user.id == context.bot.id)
        if not is_reply_to_bot:
            return
    
    logger.info(f"Ovozli xabar qabul qilindi ({chat_type}): {full_name}")
    
    # \"Ovoz qayta ishlanmoqda...\" xabari
    processing_msg = await update.message.reply_text(
        "🎤 Ovoz qayta ishlanmoqda...",
        message_thread_id=update.message.message_thread_id
    )
    
    voice_path = None
    try:
        # Ovozli xabarni yuklab olish
        voice_file = await context.bot.get_file(voice.file_id)
        voice_path = f"voice_{voice.file_id}.ogg"
        await voice_file.download_to_drive(voice_path)
        
        logger.info(f"Ovoz fayli yuklandi: {voice_path}")
        
        # Groq Whisper API orqali ovozni matnga o'girish
        transcription = await transcribe_audio(voice_path)
        
        # Faylni o'chirish
        if os.path.exists(voice_path):
            os.remove(voice_path)
            voice_path = None
        
        if not transcription:
            await processing_msg.edit_text("❌ Ovozni tanib bo'lmadi. Iltimos qaytadan urinib ko'ring.")
            return
        
        logger.info(f"Transkripsiya: {transcription}")
        
        # Guruhda bo'lsa, to'liq ismini yuborish
        user_name_for_ai = full_name if chat_type in ['group', 'supergroup'] else None
        
        # User kontekstini olish
        greeting_context = user_memory.get_greeting_context(user.id)
        
        # Groq API orqali javob olish
        response = await groq_client.answer_question(transcription, user_name_for_ai, greeting_context)
        
        # Ovozli xabar statistikasini yangilash
        user_memory.add_request(user.id, full_name, 'voice')
        user_memory.add_conversation(user.id, full_name, f"Ovozli: {transcription}", response)
        
        # Processing xabarini o'chirish
        await processing_msg.delete()
        
        # Ovozli xabarga MATN bilan javob berish
        logger.info("Matn javob yuborilmoqda")
        await send_long_message(update, response, 'HTML')
        
        logger.info(f"Ovozli xabarga javob yuborildi: {full_name}")
        
    except Exception as e:
        logger.error(f"Ovozli xabarni qayta ishlashda xatolik: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await processing_msg.edit_text("❌ Ovozli xabarni qayta ishlashda xatolik yuz berdi.")
        except:
            pass
        # Faylni o'chirish
        if voice_path and os.path.exists(voice_path):
            try:
                os.remove(voice_path)
            except:
                pass

async def transcribe_audio(audio_path):
    """Groq Whisper API orqali ovozni matnga o'giradi"""
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {config.GROQ_API_KEY}"
        }
        
        # Faylni o'qish
        with open(audio_path, 'rb') as f:
            file_content = f.read()
        
        # aiohttp orqali asinxron so'rov
        data = aiohttp.FormData()
        data.add_field('model', 'whisper-large-v3')
        # language parametrini olib tashlaymiz - avtomatik aniqlash uchun
        # Whisper o'zi tilni aniqlaydi (o'zbek, rus, ingliz, va 90+ til)
        data.add_field('response_format', 'text')
        data.add_field('file', file_content, filename=os.path.basename(audio_path), content_type='audio/ogg')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Whisper API xatolik: {response.status} - {error_text}")
                    return None
                text = await response.text()
                return text.strip()
            
    except Exception as e:
        logger.error(f"Transkripsiya xatoligi: {e}")
        return None

async def text_to_speech(text):
    """Matnni ovozga o'giradi (Google TTS)"""
    try:
        # Matnni qisqartirish (TTS limitlar uchun)
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        # Ovozli faylni yaratish
        output_path = f"tts_{random.randint(1000, 9999)}.mp3"
        
        # Tilni aniqlash - kirill harflar bo'lsa rus, aks holda ingliz
        def detect_language(text):
            # Kirill harflarni tekshirish
            cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
            latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
            
            # Agar kirill harflar ko'p bo'lsa - rus tili
            if cyrillic_chars > latin_chars:
                return 'ru'
            # Aks holda ingliz tili
            return 'en'
        
        lang = detect_language(text)
        logger.info(f"TTS tili aniqlandi: {lang}")
        
        # gTTS orqali ovoz yaratish
        # Bu ham blocking call
        loop = asyncio.get_running_loop()
        
        def sync_tts():
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            return output_path
            
        await loop.run_in_executor(None, sync_tts)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Text-to-speech xatoligi: {e}")
        return None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta ishlaydi"""
    import traceback
    logger.error(f"❌ Global xatolik: {context.error}")
    logger.error(f"❌ Traceback: {''.join(traceback.format_exception(None, context.error, context.error.__traceback__))}")
    
    if update:
        if update.message:
            try:
                await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
            except:
                pass
        elif update.callback_query:
            try:
                await update.callback_query.answer("❌ Xatolik yuz berdi!", show_alert=True)
            except:
                pass

def main():
    """Botni ishga tushiradi"""
    if not config.TELEGRAM_BOT_TOKEN or not config.GROQ_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN yoki GROQ_API_KEY topilmadi!")
        print("❌ Xatolik: .env faylida TELEGRAM_BOT_TOKEN va GROQ_API_KEY ni to'ldiring!")
        return
    
    # Application yaratish - yuqori yuklamaga optimizatsiya
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)  # Parallel xabarlarni qayta ishlash
        .connection_pool_size(8)   # Ulanish pool hajmi
        .pool_timeout(30.0)        # Pool timeout
        .connect_timeout(30.0)     # Ulanish timeout
        .read_timeout(30.0)        # O'qish timeout
        .write_timeout(30.0)       # Yozish timeout
        .build()
    )
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("panel", panel_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(quiz_callback_handler, pattern="^quiz_"))
    application.add_handler(CallbackQueryHandler(stats_callback, pattern="^(download_excel|close_stats)"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|set_|maxlen_|temp_|tokens_|reset_|back_|close_|broadcast_|restart_|add_admin|remove_admin)"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Xatolarni qayta ishlash
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    logger.info("Bot ishga tushdi...")
    print("✅ Bot ishga tushdi! To'xtatish uchun Ctrl+C bosing.")
    print("📝 Guruhda ishlashi uchun:")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
