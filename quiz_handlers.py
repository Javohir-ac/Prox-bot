from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from groq_client import GroqClient
import logging
import re

# Global instances (shared with bot.py)
groq_client = GroqClient()
logger = logging.getLogger(__name__)

# quiz_manager will be set from bot.py to avoid multiple instances
quiz_manager = None

def clean_html_tags(text):
    """HTML tag'larni tozalash"""
    if not text:
        return text
    
    # Barcha HTML tag'larni olib tashlash
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML entities ni decode qilish
    import html
    text = html.unescape(text)
    
    return text

async def quiz_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quiz tugmalari uchun callback handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        
        callback_data = query.data
        logger.info(f"🔔 Quiz callback qabul qilindi: {callback_data} (user: {full_name})")
        
        # Quiz boshlash
        if callback_data.startswith("quiz_start_"):
            user_id = int(callback_data.split("_")[-1])
            
            # Faqat o'zi boshlashi mumkin
            if user.id != user_id:
                await query.edit_message_text("❌ Bu quiz sizniki emas!")
                return
            
            # Kodni olish
            code = context.user_data.get('quiz_code')
            filename = context.user_data.get('quiz_filename', 'code.txt')
            
            if not code:
                await query.edit_message_text("❌ Kod topilmadi. Iltimos qaytadan fayl yuboring.")
                return
            
            # Quiz yaratish
            await query.edit_message_text("⏳ Quiz savollari tayyorlanmoqda...")
            
            questions = await groq_client.generate_quiz(code, filename, full_name)
            
            if not questions:
                await query.edit_message_text("❌ Quiz yaratishda xatolik. Iltimos qaytadan urinib ko'ring.")
                return
            
            # Sessiya yaratish
            quiz_manager.create_session(user.id, code, filename, questions)
            
            # Birinchi savolni yuborish
            await send_quiz_question(query, user.id)
        
        # Quiz bekor qilish
        elif callback_data == "quiz_cancel":
            await query.edit_message_text("✅ Quiz bekor qilindi.")
            # Kodni tozalash
            if 'quiz_code' in context.user_data:
                del context.user_data['quiz_code']
            if 'quiz_filename' in context.user_data:
                del context.user_data['quiz_filename']
        
        # Javob tanlash (A, B, C, D)
        elif callback_data.startswith("quiz_answer_"):
            logger.info(f"📝 Quiz javob qabul qilindi: {callback_data}")
            parts = callback_data.split("_")
            answer = parts[2]  # A, B, C, D
            user_id = int(parts[3])
            
            # Faqat o'zi javob berishi mumkin
            if user.id != user_id:
                await query.answer("❌ Bu quiz sizniki emas!", show_alert=True)
                return
            
            # Javobni tekshirish
            logger.info(f"🔄 Javob tekshirilmoqda: {answer}")
            result = quiz_manager.submit_answer(user.id, answer)
            logger.info(f"✅ Javob tekshirildi: {result.get('is_correct')}, completed: {result.get('completed')}")
            
            if 'error' in result:
                await query.edit_message_text(f"❌ {result['error']}")
                return
            
            # Natijani ko'rsatish
            # HTML tag'larni tozalash
            clean_explanation = clean_html_tags(result['explanation'])
            
            if result['is_correct']:
                feedback = f"✅ <b>To'g'ri javob!</b> 🎉\n\n"
                feedback += f"💡 <b>Tushuntirish:</b>\n{clean_explanation}"
            else:
                feedback = f"❌ <b>Noto'g'ri javob</b>\n\n"
                feedback += f"Sizning javobingiz: <b>{answer}</b>\n"
                feedback += f"✅ To'g'ri javob: <b>{result['correct_answer']}</b>\n\n"
                feedback += f"💡 <b>Tushuntirish:</b>\n{clean_explanation}"
            
            feedback += f"\n\n📊 <b>Natija:</b> {result['score']}/{result['total']}"
            
            # Progress bar qo'shish
            progress = "🟢" * result['score'] + "⚪" * (result['total'] - result['score'])
            feedback += f"\n{progress}"
            
            await query.edit_message_text(feedback, parse_mode='HTML')
            
            # Agar tugamagan bo'lsa, keyingi savolni darhol yuborish
            if not result['completed']:
                await send_quiz_question(query, user.id)
            else:
                # Quiz tugadi
                score = result['score']
                total = result['total']
                percentage = (score / total) * 100
                
                # Progress bar
                progress = "🟢" * score + "🔴" * (total - score)
                
                # Natijaga qarab emoji, xabar va tavsiya
                if score == total:
                    # 5/5 - Mukammal!
                    emoji = "🏆"
                    stars = "⭐⭐⭐⭐⭐"
                    message = "Mukammal! Barcha javoblar to'g'ri!"
                    advice = "Siz bu mavzuni mukammal o'rganibsiz! 🎓"
                elif score == total - 1:
                    # 4/5 - Ajoyib!
                    emoji = "🎉"
                    stars = "⭐⭐⭐⭐"
                    message = f"Ajoyib! {score} ta to'g'ri javob!"
                    advice = "Deyarli mukammal! Kichik xatolarni tuzating."
                elif score == total - 2:
                    # 3/5 - Yaxshi!
                    emoji = "👍"
                    stars = "⭐⭐⭐"
                    message = f"Yaxshi! {score} ta to'g'ri javob!"
                    advice = "Yaxshi boshlash! Yana bir bor takrorlang."
                elif score == total - 3:
                    # 2/5 - Yaxshi harakat!
                    emoji = "💪"
                    stars = "⭐⭐"
                    message = f"Yaxshi harakat! {score} ta to'g'ri!"
                    advice = "Asoslarni qaytadan o'rganing."
                elif score == 1:
                    # 1/5 - Ko'proq mashq!
                    emoji = "📚"
                    stars = "⭐"
                    message = f"{score} ta to'g'ri. Ko'proq mashq qiling!"
                    advice = "Bu mavzuni boshidan o'rganing."
                else:
                    # 0/5 - Hech qaysi to'g'ri emas
                    emoji = "😔"
                    stars = "❌"
                    message = "Hech qaysi to'g'ri emas."
                    advice = "Tashvishlanmang! Hamma ham birinchi marta qiynalib o'rganadi. Qaytadan urinib ko'ring!"
                
                final_message = f"""
{emoji} <b>Quiz Tugadi!</b>

📊 <b>Natija:</b> {score}/{total} ({percentage:.0f}%)
{progress}

{stars}

{message}

💡 <b>Tavsiya:</b> {advice}
"""
                
                logger.info(f"🎉 Quiz tugadi xabari yuborilmoqda...")
                await query.message.reply_text(final_message, parse_mode='HTML')
                logger.info(f"✅ Quiz tugadi xabari yuborildi")
                
                # Sessiyani o'chirish
                logger.info(f"🗑️ Sessiya o'chirilmoqda...")
                quiz_manager.delete_session(user.id)
                logger.info(f"✅ Sessiya o'chirildi")
                
                # Kodni tozalash
                if 'quiz_code' in context.user_data:
                    del context.user_data['quiz_code']
                if 'quiz_filename' in context.user_data:
                    del context.user_data['quiz_filename']
    
    except Exception as e:
        logger.error(f"❌ quiz_callback_handler xatolik: {e}")
        logger.exception("quiz_callback_handler traceback:")
        try:
            await query.edit_message_text(f"❌ Xatolik yuz berdi: {str(e)[:100]}")
        except:
            pass


async def send_quiz_question(query_or_message, user_id):
    """Quiz savolini yuborish"""
    try:
        logger.info(f"🔄 send_quiz_question chaqirildi: user_id={user_id}")
        
        question_data = quiz_manager.get_current_question(user_id)
        logger.info(f"📊 question_data: {question_data is not None}")
        
        if not question_data:
            logger.error(f"❌ Quiz savol topilmadi: user_id={user_id}")
            # Sessiyani tekshirish
            session = quiz_manager.get_session(user_id)
            if session:
                logger.error(f"❌ Sessiya bor lekin savol yo'q! current_q={session.get('current_q')}, questions_count={len(session.get('questions', []))}")
            else:
                logger.error(f"❌ Sessiya ham yo'q!")
            return
        
        session = quiz_manager.get_session(user_id)
        if not session:
            logger.error(f"❌ Quiz sessiya topilmadi: user_id={user_id}")
            return
            
        current_num = session['current_q'] + 1
        total = len(session['questions'])
        
        logger.info(f"📝 Quiz savol yuborilmoqda: {current_num}/{total} (user_id={user_id})")
        logger.info(f"📝 Savol: {question_data.get('question', 'N/A')[:50]}...")
        
        # HTML tag'larni tozalash
        clean_question = clean_html_tags(question_data['question'])
        
        # Savol matni
        question_text = f"❓ <b>Savol {current_num}/{total}</b>\n\n{clean_question}"
        
        # Tugmalar (A, B, C, D)
        keyboard = []
        for option_key in ['A', 'B', 'C', 'D']:
            option_text = question_data['options'].get(option_key, '')
            if option_text:
                # HTML tag'larni tozalash
                clean_option = clean_html_tags(option_text)
                keyboard.append([InlineKeyboardButton(
                    f"{option_key}: {clean_option}",
                    callback_data=f"quiz_answer_{option_key}_{user_id}"
                )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.info(f"🔄 Xabar yuborilmoqda... (keyboard: {len(keyboard)} ta tugma)")
        
        # Yuborish
        if hasattr(query_or_message, 'message'):
            # CallbackQuery
            logger.info("📤 CallbackQuery orqali yuborilmoqda")
            await query_or_message.message.reply_text(
                question_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            # Message
            logger.info("📤 Message orqali yuborilmoqda")
            await query_or_message.reply_text(
                question_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        logger.info("✅ Quiz savol muvaffaqiyatli yuborildi!")
        
    except Exception as e:
        logger.error(f"❌ send_quiz_question xatolik: {e}")
        logger.exception("send_quiz_question traceback:")


async def send_quiz_question_via_bot(bot, chat_id, user_id, message_thread_id=None):
    """Quiz savolini bot orqali yuborish (rasm tahlili uchun)"""
    question_data = quiz_manager.get_current_question(user_id)
    
    if not question_data:
        return
    
    session = quiz_manager.get_session(user_id)
    current_num = session['current_q'] + 1
    total = len(session['questions'])
    
    # HTML tag'larni tozalash
    clean_question = clean_html_tags(question_data['question'])
    
    # Savol matni
    question_text = f"❓ <b>Savol {current_num}/{total}</b>\n\n{clean_question}"
    
    # Tugmalar (A, B, C, D)
    keyboard = []
    for option_key in ['A', 'B', 'C', 'D']:
        option_text = question_data['options'].get(option_key, '')
        if option_text:
            # HTML tag'larni tozalash
            clean_option = clean_html_tags(option_text)
            keyboard.append([InlineKeyboardButton(
                f"{option_key}: {clean_option}",
                callback_data=f"quiz_answer_{option_key}_{user_id}"
            )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Bot orqali yuborish
    await bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=reply_markup,
        parse_mode='HTML',
        message_thread_id=message_thread_id
    )

