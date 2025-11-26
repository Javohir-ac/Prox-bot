import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

class QuizManager:
    """Quiz sessiyalarini boshqarish"""
    
    def __init__(self, session_file='quiz_sessions.json'):
        self.session_file = session_file
        self.sessions: Dict = {}
        self._lock = threading.Lock()
        self._load_sessions()
    
    def _load_sessions(self):
        """Sessiyalarni yuklash"""
        import logging
        logger = logging.getLogger(__name__)
        
        if os.path.exists(self.session_file):
            try:
                logger.info(f"📂 Sessiyalar yuklanmoqda: {self.session_file}")
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
                logger.info(f"✅ {len(self.sessions)} ta sessiya yuklandi")
            except Exception as e:
                logger.error(f"❌ Sessiyalarni yuklashda xatolik: {e}")
                self.sessions = {}
        else:
            logger.info(f"📂 Sessiya fayli topilmadi, yangi yaratiladi")
            self.sessions = {}
    
    def _save_sessions(self):
        """Sessiyalarni saqlash (lock allaqachon olingan deb hisoblanadi)"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"💾 Sessiyalar saqlanmoqda: {len(self.sessions)} ta sessiya")
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Sessiyalar saqlandi: {self.session_file}")
        except Exception as e:
            logger.error(f"❌ Sessiyalarni saqlashda xatolik: {e}")
            logger.exception("_save_sessions traceback:")
    
    def create_session(self, user_id: int, code: str, filename: str, questions: List[Dict]) -> bool:
        """Yangi quiz sessiya yaratish"""
        import logging
        logger = logging.getLogger(__name__)
        
        user_id_str = str(user_id)
        
        logger.info(f"🔄 create_session boshlandi: user_id={user_id}")
        
        with self._lock:
            self.sessions[user_id_str] = {
                'code': code,
                'filename': filename,
                'questions': questions,
                'current_q': 0,
                'score': 0,
                'answers': [],  # Foydalanuvchi javoblari
                'timestamp': datetime.now().isoformat(),
                'completed': False
            }
            logger.info(f"✅ Sessiya dictionary'ga qo'shildi: {user_id_str}")
            self._save_sessions()
            logger.info(f"✅ Sessiya faylga saqlandi")
        
        # Sessiyani tekshirish
        if user_id_str in self.sessions:
            logger.info(f"✅ Sessiya tasdiqlandi: {user_id_str}")
            return True
        else:
            logger.error(f"❌ Sessiya yaratilmadi: {user_id_str}")
            return False
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Sessiyani olish"""
        import logging
        logger = logging.getLogger(__name__)
        
        user_id_str = str(user_id)
        
        logger.info(f"🔄 get_session boshlandi: user_id={user_id}")
        logger.info(f"📊 Hozirgi sessiyalar: {list(self.sessions.keys())}")
        
        # Eski sessiyalarni tozalash (5 daqiqadan eski)
        self._cleanup_old_sessions()
        
        session = self.sessions.get(user_id_str)
        logger.info(f"📊 get_session natija: {session is not None}")
        
        return session
    
    def get_current_question(self, user_id: int) -> Optional[Dict]:
        """Joriy savolni olish"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔄 get_current_question boshlandi: user_id={user_id}")
            
            session = self.get_session(user_id)
            logger.info(f"📊 get_current_question: session={session is not None}")
            
            if not session:
                logger.error(f"❌ Sessiya topilmadi: user_id={user_id}")
                return None
                
            if session.get('completed', False):
                logger.error(f"❌ Sessiya tugagan: user_id={user_id}")
                return None
            
            current_idx = session.get('current_q', 0)
            questions = session.get('questions', [])
            questions_count = len(questions)
            logger.info(f"📊 current_idx={current_idx}, questions_count={questions_count}")
            
            if current_idx >= questions_count:
                logger.error(f"❌ Index xato: current_idx={current_idx} >= questions_count={questions_count}")
                return None
            
            question = questions[current_idx]
            logger.info(f"✅ Savol topildi: {question.get('question', 'N/A')[:30]}...")
            return question
            
        except Exception as e:
            logger.error(f"❌ get_current_question xatolik: {e}")
            logger.exception("get_current_question traceback:")
            return None
    
    def submit_answer(self, user_id: int, answer: str) -> Dict:
        """Javobni yuborish va tekshirish"""
        user_id_str = str(user_id)
        session = self.sessions.get(user_id_str)
        
        if not session or session['completed']:
            return {'error': 'Sessiya topilmadi yoki tugagan'}
        
        current_q = session['questions'][session['current_q']]
        is_correct = answer.upper() == current_q['correct'].upper()
        
        # Javobni saqlash
        session['answers'].append({
            'question_num': session['current_q'] + 1,
            'user_answer': answer,
            'correct_answer': current_q['correct'],
            'is_correct': is_correct
        })
        
        if is_correct:
            session['score'] += 1
        
        # Keyingi savolga o'tish
        session['current_q'] += 1
        
        # Oxirgi savol bo'lsa, sessiyani tugatish
        if session['current_q'] >= len(session['questions']):
            session['completed'] = True
        
        self._save_sessions()
        
        return {
            'is_correct': is_correct,
            'correct_answer': current_q['correct'],
            'explanation': current_q.get('explanation', ''),
            'score': session['score'],
            'total': len(session['questions']),
            'completed': session['completed']
        }
    
    def delete_session(self, user_id: int):
        """Sessiyani o'chirish"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔄 delete_session boshlandi: user_id={user_id}")
        user_id_str = str(user_id)
        
        logger.info(f"🔄 Lock olinmoqda...")
        with self._lock:
            logger.info(f"✅ Lock olindi")
            if user_id_str in self.sessions:
                logger.info(f"🔄 Sessiya o'chirilmoqda...")
                del self.sessions[user_id_str]
                logger.info(f"✅ Sessiya o'chirildi, saqlash boshlandi...")
                self._save_sessions()
                logger.info(f"✅ Saqlash tugadi")
            else:
                logger.warning(f"⚠️ Sessiya topilmadi: {user_id_str}")
        logger.info(f"✅ Lock bo'shatildi, delete_session tugadi")
    
    def _cleanup_old_sessions(self):
        """5 daqiqadan eski sessiyalarni o'chirish"""
        import logging
        logger = logging.getLogger(__name__)
        
        current_time = datetime.now()
        to_delete = []
        
        with self._lock:
            for user_id, session in self.sessions.items():
                try:
                    session_time = datetime.fromisoformat(session['timestamp'])
                    age_seconds = (current_time - session_time).total_seconds()
                    
                    # Faqat 5 daqiqadan (300 soniya) eski sessiyalarni o'chirish
                    if age_seconds > 300:
                        logger.info(f"🗑️ Eski sessiya topildi: {user_id} (yoshi: {age_seconds:.0f} soniya)")
                        to_delete.append(user_id)
                    else:
                        logger.debug(f"✅ Sessiya yangi: {user_id} (yoshi: {age_seconds:.0f} soniya)")
                except Exception as e:
                    logger.error(f"❌ Sessiya vaqtini tekshirishda xatolik: {user_id} - {e}")
            
            for user_id in to_delete:
                del self.sessions[user_id]
                logger.info(f"🗑️ Eski sessiya o'chirildi: {user_id}")
            
            if to_delete:
                self._save_sessions()
                logger.info(f"✅ {len(to_delete)} ta eski sessiya o'chirildi")
    
    def get_stats(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi statistikasini olish"""
        session = self.get_session(user_id)
        if not session:
            return None
        
        return {
            'score': session['score'],
            'total': len(session['questions']),
            'percentage': (session['score'] / len(session['questions'])) * 100 if session['questions'] else 0,
            'completed': session['completed']
        }
