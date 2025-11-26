import json
import os
from typing import List, Dict

class AdminManager:
    """Admin foydalanuvchilarni boshqarish"""
    
    def __init__(self, filename='admins.json'):
        self.filename = filename
        self.admins = self.load_admins()
    
    def load_admins(self) -> Dict:
        """Adminlarni yuklash"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Adminlarni yuklashda xatolik: {e}")
                return {'admins': []}
        return {'admins': []}
    
    def save_admins(self):
        """Adminlarni saqlash"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.admins, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Adminlarni saqlashda xatolik: {e}")
    
    def add_admin(self, user_id: int, name: str, added_by: int) -> bool:
        """Admin qo'shish"""
        user_id = int(user_id)
        
        # Allaqachon admin bo'lsa
        if self.is_admin(user_id):
            return False
        
        admin_data = {
            'user_id': user_id,
            'name': name,
            'added_by': added_by,
            'added_at': self._get_timestamp()
        }
        
        self.admins['admins'].append(admin_data)
        self.save_admins()
        return True
    
    def remove_admin(self, user_id: int) -> bool:
        """Adminni o'chirish"""
        user_id = int(user_id)
        
        for admin in self.admins['admins']:
            if admin['user_id'] == user_id:
                self.admins['admins'].remove(admin)
                self.save_admins()
                return True
        return False
    
    def is_admin(self, user_id: int) -> bool:
        """Foydalanuvchi admin ekanligini tekshirish"""
        user_id = int(user_id)
        return any(admin['user_id'] == user_id for admin in self.admins['admins'])
    
    def get_all_admins(self) -> List[Dict]:
        """Barcha adminlarni olish"""
        return self.admins['admins']
    
    def get_admin_count(self) -> int:
        """Adminlar sonini olish"""
        return len(self.admins['admins'])
    
    def _get_timestamp(self) -> str:
        """Hozirgi vaqt"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
