#!/usr/bin/env python3
"""
Eski user_memories.json formatini yangi formatga o'tkazish
"""
import json
import os
from datetime import datetime

def migrate_user_data():
    """Eski formatni yangi formatga o'tkazish"""
    
    memory_file = 'user_memories.json'
    
    if not os.path.exists(memory_file):
        print("✅ user_memories.json topilmadi, yangi fayl yaratiladi")
        return
    
    # Backup yaratish
    backup_file = f"{memory_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Eski ma'lumotlarni yuklash
        with open(memory_file, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        
        # Backup saqlash
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        
        print(f"📦 Backup yaratildi: {backup_file}")
        
        # Yangi formatga o'tkazish
        new_data = {}
        
        for user_id, user_info in old_data.items():
            # Yangi struktura
            new_data[user_id] = {
                'name': user_info.get('name', 'Unknown'),
                'first_seen': user_info.get('first_seen', datetime.now().isoformat()),
                'last_seen': user_info.get('last_seen', datetime.now().isoformat()),
                'requests': {
                    'total': 0,
                    'text': 0,
                    'file': 0,
                    'image': 0,
                    'voice': 0,
                    'daily': {},
                },
                'files_by_type': {},
                'code_reviews': user_info.get('code_reviews', {
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'daily': {},
                    'history': []
                })
            }
            
            # Eski code_reviews'dan requests'ga o'tkazish
            code_reviews = user_info.get('code_reviews', {})
            if code_reviews.get('total', 0) > 0:
                new_data[user_id]['requests']['total'] = code_reviews.get('total', 0)
                new_data[user_id]['requests']['file'] = code_reviews.get('total', 0)  # Eski ma'lumotlar faqat fayl edi
                new_data[user_id]['requests']['daily'] = code_reviews.get('daily', {})
            
            # Agar requests yo'q bo'lsa, default qiymatlar
            if 'requests' not in new_data[user_id]:
                new_data[user_id]['requests'] = {
                    'total': 0,
                    'text': 0,
                    'file': 0,
                    'image': 0,
                    'voice': 0,
                    'daily': {},
                }
        
        # Yangi ma'lumotlarni saqlash
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {len(new_data)} ta foydalanuvchi ma'lumotlari yangilandi")
        print(f"📁 Yangi format: {memory_file}")
        print(f"💾 Backup: {backup_file}")
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        # Xatolik bo'lsa, backup'dan qayta tiklash
        if os.path.exists(backup_file):
            os.rename(backup_file, memory_file)
            print(f"🔄 Backup'dan qayta tiklandi")

if __name__ == '__main__':
    print("🔄 User ma'lumotlarini yangi formatga o'tkazish...\n")
    migrate_user_data()
    print("\n✅ Tayyor!")
