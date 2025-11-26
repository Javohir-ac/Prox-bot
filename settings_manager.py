import json
import os

class SettingsManager:
    def __init__(self, settings_file='bot_settings.json'):
        self.settings_file = settings_file
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Sozlamalarni yuklash"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._default_settings()
        return self._default_settings()
    
    def _default_settings(self):
        """Standart sozlamalar"""
        return {
            "welcome_message_enabled": True,
            "stickers_enabled": True,
            "voice_response_enabled": True,
            "group_mode_enabled": True,
            "max_message_length": 4000,
            "response_temperature": 0.7,
            "max_tokens": 1500,
            "admin_notifications": True
        }
    
    def _save_settings(self):
        """Sozlamalarni saqlash"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def get(self, key, default=None):
        """Sozlamani olish"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Sozlamani o'zgartirish"""
        self.settings[key] = value
        self._save_settings()
    
    def toggle(self, key):
        """Boolean sozlamani o'zgartirish (on/off)"""
        if key in self.settings and isinstance(self.settings[key], bool):
            self.settings[key] = not self.settings[key]
            self._save_settings()
            return self.settings[key]
        return None
    
    def get_all(self):
        """Barcha sozlamalarni olish"""
        return self.settings.copy()
    
    def reset(self):
        """Sozlamalarni qayta tiklash"""
        self.settings = self._default_settings()
        self._save_settings()
