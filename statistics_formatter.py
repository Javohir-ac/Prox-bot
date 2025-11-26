"""
Statistika formatlash funksiyasi
"""
from datetime import datetime, timedelta

def format_statistics(stats):
    """Statistikani chiroyli formatda qaytaradi"""
    
    # Umumiy statistika
    stats_text = "📊 <b>BOT STATISTIKASI</b>\n"
    stats_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    stats_text += f"👥 <b>Foydalanuvchilar:</b> {stats['total_users']} ta\n"
    stats_text += f"📊 <b>Jami so'rovlar:</b> {stats['total_requests']} ta\n\n"
    
    stats_text += "📋 <b>So'rovlar turi:</b>\n"
    stats_text += f"├ 📝 Yozma: {stats['total_text']} ta\n"
    stats_text += f"├ 📄 Fayl: {stats['total_files']} ta\n"
    stats_text += f"├ 🖼️ Rasm: {stats['total_images']} ta\n"
    stats_text += f"└ 🎤 Ovoz: {stats['total_voice']} ta\n\n"
    
    # Kod tahlil statistikasi
    if stats.get('total_code_reviews', 0) > 0:
        stats_text += "🔍 <b>Kod tahlil natijalari:</b>\n"
        stats_text += f"├ 📊 Jami: {stats['total_code_reviews']} ta\n"
        stats_text += f"├ ✅ Xatosiz: {stats['total_positive']} ta\n"
        stats_text += f"└ ❌ Xatoli: {stats['total_negative']} ta\n\n"
    
    # Fayl turlari statistikasi
    if stats['files_by_type']:
        stats_text += "📁 <b>Eng ko'p yuborilgan fayllar:</b>\n"
        sorted_files = sorted(stats['files_by_type'].items(), key=lambda x: x[1], reverse=True)
        for idx, (file_type, count) in enumerate(sorted_files[:5], 1):
            stats_text += f"{idx}. {file_type.upper()}: {count} ta\n"
        stats_text += "\n"
    
    # Bugungi statistika
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = stats['daily_stats'].get(today, 0)
    stats_text += f"📅 <b>Bugun:</b> {today_count} ta so'rov\n\n"
    
    # Oxirgi 7 kun statistikasi
    stats_text += "📈 <b>Oxirgi 7 kun:</b>\n"
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        count = stats['daily_stats'].get(date, 0)
        # Grafik ko'rinishda
        bar = "▓" * min(count, 20)  # Maksimal 20 ta belgi
        stats_text += f"{date}: {bar} {count}\n"
    
    stats_text += "\n🏆 <b>TOP 10 FAOL FOYDALANUVCHILAR:</b>\n"
    stats_text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    # Faqat faol foydalanuvchilarni ko'rsatish (total > 0)
    active_users = [u for u in stats['top_users'] if u['total'] > 0]
    
    if not active_users:
        stats_text += "<i>Hozircha faol foydalanuvchilar yo'q</i>\n"
    else:
        for idx, user in enumerate(active_users[:10], 1):
            stats_text += f"\n{idx}. <b>{user['name']}</b>\n"
            stats_text += f"   📊 Jami: {user['total']} ta\n"
            stats_text += f"   📝 Yozma: {user['text']} | 📄 Fayl: {user['file']} | 🖼️ Rasm: {user['image']}\n"
    
    return stats_text
