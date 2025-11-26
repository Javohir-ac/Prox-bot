import json
import os
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import threading
import time

class UserMemory:
    def __init__(self, memory_file='user_memories.json'):
        self.memory_file = memory_file
        self.memories = self._load_memories()
        self._lock = threading.Lock()  # Thread-safe operatsiyalar uchun
        self._save_queue = []  # Saqlash navbati
        self._last_save = time.time()
        self._save_interval = 30  # Har 30 soniyada saqlash
    
    def _load_memories(self) -> Dict:
        """Xotiralarni yuklash"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_memories(self):
        """Xotiralarni saqlash - optimizatsiya qilingan"""
        current_time = time.time()
        
        # Har 30 soniyada bir marta saqlash (millionlab foydalanuvchilar uchun)
        if current_time - self._last_save < self._save_interval:
            return
        
        with self._lock:
            try:
                # Backup yaratish
                if os.path.exists(self.memory_file):
                    backup_file = f"{self.memory_file}.backup"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(self.memory_file, backup_file)
                
                # Yangi faylni saqlash
                with open(self.memory_file, 'w', encoding='utf-8') as f:
                    json.dump(self.memories, f, ensure_ascii=False, indent=2)
                
                self._last_save = current_time
                
                # Backup'ni o'chirish
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                    
            except Exception as e:
                # Xatolik bo'lsa, backup'dan qayta tiklash
                backup_file = f"{self.memory_file}.backup"
                if os.path.exists(backup_file):
                    os.rename(backup_file, self.memory_file)
                raise e
    
    def force_save(self):
        """Majburiy saqlash"""
        self._last_save = 0
        self._save_memories()
    
    def _ensure_user_exists(self, user_id: int, user_name: str = "Unknown"):
        """Foydalanuvchi ma'lumotlarini yaratish"""
        user_id_str = str(user_id)
        if user_id_str not in self.memories:
            self.memories[user_id_str] = {
                'name': user_name,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'requests': {
                    'total': 0,
                    'text': 0,  # Yozma so'rovlar
                    'file': 0,  # Fayl yuborishlar
                    'image': 0,  # Rasm yuborishlar
                    'voice': 0,  # Ovozli xabarlar
                    'daily': {},  # {'2025-11-18': 5}
                },
                'files_by_type': {
                    # 'python': 5, 'javascript': 3, ...
                },
                'code_reviews': {
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'daily': {},  # {'2025-11-18': 5}
                    'history': []  # [{'date': '...', 'result': 'positive/negative'}]
                }
            }
    
    def add_code_review(self, user_id: int, user_name: str = "Unknown", result: str = "neutral"):
        """Kod tekshirish statistikasini yangilash
        result: 'positive' (xatosiz), 'negative' (xatoli), 'neutral'
        """
        with self._lock:  # Thread-safe
            user_id_str = str(user_id)
            self._ensure_user_exists(user_id, user_name)
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Umumiy statistika
            self.memories[user_id_str]['code_reviews']['total'] += 1
            self.memories[user_id_str]['name'] = user_name  # Ismni yangilash
            
            # Ijobiy/salbiy statistika
            if result == 'positive':
                self.memories[user_id_str]['code_reviews']['positive'] += 1
            elif result == 'negative':
                self.memories[user_id_str]['code_reviews']['negative'] += 1
            
            # Kunlik statistika
            if today not in self.memories[user_id_str]['code_reviews']['daily']:
                self.memories[user_id_str]['code_reviews']['daily'][today] = 0
            self.memories[user_id_str]['code_reviews']['daily'][today] += 1
            
            # Tarix - faqat oxirgi 50 ta (millionlab foydalanuvchilar uchun)
            if 'history' not in self.memories[user_id_str]['code_reviews']:
                self.memories[user_id_str]['code_reviews']['history'] = []
            
            self.memories[user_id_str]['code_reviews']['history'].append({
                'date': datetime.now().isoformat(),
                'result': result
            })
            
            # Faqat oxirgi 50 ta tarixni saqlash (xotira tejash)
            if len(self.memories[user_id_str]['code_reviews']['history']) > 50:
                self.memories[user_id_str]['code_reviews']['history'] = \
                    self.memories[user_id_str]['code_reviews']['history'][-50:]
        
        self._save_memories()
    
    def get_statistics(self) -> Dict:
        """Umumiy statistikani olish"""
        total_users = len(self.memories)
        total_requests = 0
        total_text = 0
        total_files = 0
        total_images = 0
        total_voice = 0
        
        # Kod tahlil statistikasi
        total_code_reviews = 0
        total_positive = 0
        total_negative = 0
        
        # Kunlik statistika
        daily_stats = defaultdict(int)
        
        # Fayl turlari statistikasi
        files_by_type = defaultdict(int)
        
        # Top foydalanuvchilar
        top_users = []
        
        for user_id, data in self.memories.items():
            # Eski foydalanuvchilar uchun default qiymatlar
            requests = data.get('requests', {
                'total': 0,
                'text': 0,
                'file': 0,
                'image': 0,
                'voice': 0,
                'daily': {}
            })
            
            total_requests += requests.get('total', 0)
            total_text += requests.get('text', 0)
            total_files += requests.get('file', 0)
            total_images += requests.get('image', 0)
            total_voice += requests.get('voice', 0)
            
            # Kunlik statistika
            for date, count in requests.get('daily', {}).items():
                daily_stats[date] += count
            
            # Fayl turlari
            for file_type, count in data.get('files_by_type', {}).items():
                files_by_type[file_type] += count
            
            # Kod tahlil statistikasi
            code_reviews = data.get('code_reviews', {})
            total_code_reviews += code_reviews.get('total', 0)
            total_positive += code_reviews.get('positive', 0)
            total_negative += code_reviews.get('negative', 0)
            
            # Top foydalanuvchilar uchun
            top_users.append({
                'user_id': user_id,
                'name': data.get('name', 'Unknown'),
                'total': requests.get('total', 0),
                'text': requests.get('text', 0),
                'file': requests.get('file', 0),
                'image': requests.get('image', 0),
                'voice': requests.get('voice', 0),
                'code_reviews_total': code_reviews.get('total', 0),
                'code_reviews_positive': code_reviews.get('positive', 0),
                'code_reviews_negative': code_reviews.get('negative', 0),
                'first_seen': data.get('first_seen', ''),
                'last_seen': data.get('last_seen', ''),
                'files_by_type': data.get('files_by_type', {})
            })
        
        # Top foydalanuvchilarni saralash
        top_users.sort(key=lambda x: x['total'], reverse=True)
        
        return {
            'total_users': total_users,
            'total_requests': total_requests,
            'total_text': total_text,
            'total_files': total_files,
            'total_images': total_images,
            'total_voice': total_voice,
            'total_code_reviews': total_code_reviews,
            'total_positive': total_positive,
            'total_negative': total_negative,
            'daily_stats': dict(daily_stats),
            'files_by_type': dict(files_by_type),
            'top_users': top_users
        }
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Bitta foydalanuvchi statistikasini olish"""
        user_id_str = str(user_id)
        if user_id_str not in self.memories:
            return None
        
        data = self.memories[user_id_str]
        reviews = data.get('code_reviews', {})
        
        return {
            'name': data.get('name', 'Unknown'),
            'first_seen': data.get('first_seen', ''),
            'total': reviews.get('total', 0),
            'positive': reviews.get('positive', 0),
            'negative': reviews.get('negative', 0),
            'daily': reviews.get('daily', {}),
            'history': reviews.get('history', [])
        }
    
    def add_request(self, user_id: int, user_name: str, request_type: str, file_type: str = None):
        """So'rov statistikasini yangilash
        request_type: 'text', 'file', 'image', 'voice'
        file_type: 'python', 'javascript', 'java', 'cpp', 'html', 'css', etc.
        """
        with self._lock:
            user_id_str = str(user_id)
            self._ensure_user_exists(user_id, user_name)
            
            # Eski foydalanuvchilar uchun yangi struktura qo'shish
            if 'requests' not in self.memories[user_id_str]:
                self.memories[user_id_str]['requests'] = {
                    'total': 0,
                    'text': 0,
                    'file': 0,
                    'image': 0,
                    'voice': 0,
                    'daily': {},
                }
            
            if 'files_by_type' not in self.memories[user_id_str]:
                self.memories[user_id_str]['files_by_type'] = {}
            
            if 'last_seen' not in self.memories[user_id_str]:
                self.memories[user_id_str]['last_seen'] = datetime.now().isoformat()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Umumiy statistika
            self.memories[user_id_str]['requests']['total'] += 1
            self.memories[user_id_str]['requests'][request_type] += 1
            self.memories[user_id_str]['name'] = user_name  # Ismni yangilash
            self.memories[user_id_str]['last_seen'] = datetime.now().isoformat()
            
            # Kunlik statistika
            if today not in self.memories[user_id_str]['requests']['daily']:
                self.memories[user_id_str]['requests']['daily'][today] = 0
            self.memories[user_id_str]['requests']['daily'][today] += 1
            
            # Fayl turi statistikasi
            if file_type:
                if file_type not in self.memories[user_id_str]['files_by_type']:
                    self.memories[user_id_str]['files_by_type'][file_type] = 0
                self.memories[user_id_str]['files_by_type'][file_type] += 1
        
        self._save_memories()
    
    def add_conversation(self, user_id: int, user_name: str, question: str, answer: str):
        """Suhbatni xotiraga qo'shish (hozircha o'chirilgan)"""
        pass
    
    def add_voice_message(self, user_id: int):
        """Ovozli xabar statistikasini yangilash (hozircha o'chirilgan)"""
        pass
    
    def get_user_context(self, user_id: int) -> str:
        """User haqida kontekst olish (hozircha o'chirilgan)"""
        return ""
    
    def get_greeting_context(self, user_id: int) -> str:
        """Salomlashuv uchun kontekst (hozircha o'chirilgan)"""
        return ""
