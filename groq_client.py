import aiohttp
import asyncio
import config
import re
import logging

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.model = config.MODEL_NAME
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        # EasyOCR reader - lazy loading
        self._easyocr_reader = None
    
    def _get_easyocr_reader(self):
        """EasyOCR reader ni lazy loading bilan olish"""
        if self._easyocr_reader is None:
            try:
                import easyocr
                logger.info("🔄 EasyOCR yuklanmoqda...")
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False)  # CPU mode
                logger.info("✅ EasyOCR tayyor!")
            except Exception as e:
                logger.error(f"EasyOCR yuklashda xatolik: {e}")
                self._easyocr_reader = False  # Fallback to Tesseract
        return self._easyocr_reader

    
    def _get_humor_instruction(self, user_name):
        """Hazil va motivatsiya instruksiyasini qaytaradi"""
        if not user_name:
            return ""
            
        return f"""
JAVOB FORMATI - JUDA MUHIM:
Javobni 2 qismga bo'ling:

1. HAZIL QISMI (20% - 1 qator):
   - {user_name}ga murojaat qilib, mavzuga mos KULGILI va IJODIY hazil qiling
   - Har safar TURLI XIL hazil ishlating!
   
   HAZIL TURLARI (50+ variant):
   - "{user_name}, voy! 🔥 Bu savol mening sevimlarimdan!"
   - "{user_name}, zo'r! 💡 Miya ishlayapti, biroz kuting..."
   - "{user_name}, ajoyib! 🚀 Menga yoqdi!"
   - "{user_name}, qiziq! 🤔 Keling o'ylab ko'ramiz..."
   - "{user_name}, voy-voy! 😅 Bu qiyin-da, lekin hal qilamiz!"
   - "{user_name}, zo'r! 🎯 To'g'ri yo'ldasiz!"
   - "{user_name}, tomosha boshlandi! 🎬 Keling..."
   - "{user_name}, kod yozish vaqti! 💻 Klaviatura tayyor!" 
   - "{user_name}, bug'lar qo'rqsin! 🐛 Biz keldik!"
   
2. MA'LUMOT QISMI (80% - asosiy javob):
   - To'liq, batafsil va professional javob bering
   - Kod misollari, tushuntirishlar, tavsiyalar
   - Aniq va tushunarli bo'lsin

MUHIM: Har safar BOSHQA hazil ishlating! Takrorlanmasin!

JAVOB OXIRIDA ALBATTA MOTIVATSION JUMLA YOZING:

💡 "Har kuni 1% yaxshilansangiz, yil oxirida 37 marta yaxshiroq bo'lasiz!"

Motivatsion jumla qisqa va ilhomlantiradigan bo'lsin (1-2 qator)."""

    def _perform_ocr(self, args):
        """OCR jarayonini alohida thread'da bajarish uchun yordamchi funksiya"""
        image_path, i = args
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import cv2
            import numpy as np
            
            # Rasmni ochish
            image = Image.open(image_path)
            
            # PIL dan numpy array ga o'tkazish (OpenCV uchun)
            img_array = np.array(image)
            
            # QORA FON TEKSHIRUVI - grayscale qilishdan OLDIN
            # RGB rasmda o'rtacha yorug'likni tekshirish
            if len(img_array.shape) == 3:
                # RGB rasmda brightness tekshirish
                mean_brightness = np.mean(img_array)
                is_dark_theme = mean_brightness < 100  # Threshold pasaytirildi
                
                if is_dark_theme:
                    logger.info(f"🌙 Qora fon aniqlandi (brightness: {mean_brightness:.1f})")
                else:
                    logger.info(f"☀️ Och fon (brightness: {mean_brightness:.1f})")
                
                # Grayscale ga o'tkazish
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                # Agar qora fon bo'lsa, inversiya qilish
                if is_dark_theme:
                    img_array = cv2.bitwise_not(img_array)
                    logger.info("✅ Inversiya qilindi (qora → oq)")
            else:
                # Agar allaqachon grayscale bo'lsa
                mean_brightness = np.mean(img_array)
                is_dark_theme = mean_brightness < 100
                
                if is_dark_theme:
                    img_array = cv2.bitwise_not(img_array)
                    logger.info(f"🌙 Qora fon aniqlandi va inversiya qilindi (brightness: {mean_brightness:.1f})")
            
            # 1. Rasmni 3x kattalashtirish (OCR uchun juda yaxshi)
            scale_factor = 3
            width = int(img_array.shape[1] * scale_factor)
            height = int(img_array.shape[0] * scale_factor)
            img_array = cv2.resize(img_array, (width, height), interpolation=cv2.INTER_CUBIC)
            
            # 2. Denoising - noise ni olib tashlash
            img_array = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)
            
            # 3. Otsu's binarization - eng yaxshi threshold avtomatik topish
            _, img_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 4. Morphological operations - matnni aniqroq qilish
            kernel = np.ones((1, 1), np.uint8)
            img_array = cv2.dilate(img_array, kernel, iterations=1)
            img_array = cv2.erode(img_array, kernel, iterations=1)
            
            # 5. Contrast enhancement
            img_array = cv2.equalizeHist(img_array)
            
            # OCR - EasyOCR (primary) yoki Tesseract (fallback)
            extracted_text = ""
            
            # EasyOCR bilan urinish
            reader = self._get_easyocr_reader()
            if reader and reader is not False:
                try:
                    logger.info("🔍 EasyOCR bilan OCR...")
                    # EasyOCR numpy array bilan ishlaydi
                    result = reader.readtext(img_array, detail=0, paragraph=True)
                    if result:
                        extracted_text = '\n'.join(result)
                        logger.info(f"✅ EasyOCR muvaffaqiyatli: {len(extracted_text)} belgi")
                        logger.info(f"📝 OCR natijasi:\n{extracted_text}")  # DEBUG: OCR natijasini ko'rsatish
                except Exception as e:
                    logger.error(f"EasyOCR xatolik: {e}")
            
            # Agar EasyOCR ishlamasa, Tesseract ishlatamiz
            if not extracted_text.strip():
                logger.info("🔄 Tesseract bilan OCR (fallback)...")
                import pytesseract
                
                # Numpy array dan PIL Image ga qaytish
                image = Image.fromarray(img_array)
                
                # Sharpness oshirish
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)
                
                # Tesseract OCR
                try:
                    config1 = r'--oem 1 --psm 6'
                    extracted_text = pytesseract.image_to_string(image, lang='eng', config=config1)
                    if extracted_text.strip():
                        logger.info(f"✅ Tesseract muvaffaqiyatli: {len(extracted_text)} belgi")
                except Exception as e:
                    logger.error(f"Tesseract xatolik: {e}")
                    extracted_text = ""
            
            if not extracted_text.strip():
                return f"[Rasm {i+1}]: Matn topilmadi."
            else:
                # OCR post-processing: keng tarqalgan xatolarni tuzatish
                extracted_text = self._fix_ocr_errors(extracted_text)
                return f"[Rasm {i+1} DAN MATN]:\n{extracted_text}"
                
        except ImportError as e:
            logger.error(f"OCR import xatolik: {e}")
            return f"⚠️ OCR tizimi o'rnatilmagan: {str(e)}"
        except Exception as e:
            logger.error(f"OCR xatolik ({image_path}): {e}")
            return f"[Rasm {i+1}]: OCR xatolik: {str(e)[:200]}"
    
    def _fix_ocr_errors(self, text):
        """OCR orqali noto'g'ri o'qilgan belgilarni tuzatish"""
        if not text:
            return text
            
        # Keng tarqalgan OCR xatolari
        replacements = {
            # Raqam va harf chalkashuvi
            r'\b0([a-zA-Z])': r'O\1',  # 0 → O (harfda)
            r'([a-zA-Z])0\b': r'\1O',  # 0 → O (so'z oxirida)
            r'\bl([A-Z])': r'I\1',     # l → I (katta harf bilan)
            r'\b1l\b': 'Il',           # 1l → Il
            r'\bO0\b': 'OO',           # O0 → OO
            
            # Python keywords (case-insensitive) - KENGAYTIRILDI
            r'\baef\b': 'def',         # aef → def (eng keng tarqalgan!)
            r'\bdetf\b': 'def',
            r'\bdet\b': 'def',
            r'\bdeff\b': 'def',
            r'\bael\b': 'def',
            
            r'\bprlnt\b': 'print',
            r'\bprinf\b': 'print',
            r'\bprinl\b': 'print',
            r'\bpritn\b': 'print',
            r'\bprini\b': 'print',
            
            r'\blf\b': 'if',           # lf → if (eng keng tarqalgan!)
            r'\b1f\b': 'if',
            r'\blt\b': 'if',
            
            r'\bretum\b': 'return',
            r'\breturn\b': 'return',
            r'\bretutn\b': 'return',
            r'\breturm\b': 'return',
            
            r'\belae\b': 'else',
            r'\belsc\b': 'else',
            r'\belae\b': 'else',
            r'\belse\b': 'else',
            
            r'\blmport\b': 'import',
            r'\bimporl\b': 'import',
            r'\bimpor\b': 'import',
            r'\bimport\b': 'import',
            
            r'\bwhlle\b': 'while',
            r'\bwhlie\b': 'while',
            r'\bwhi1e\b': 'while',
            
            r'\belif\b': 'elif',
            r'\be1if\b': 'elif',
            
            r'\btry\b': 'try',
            r'\bexcept\b': 'except',
            r'\bexcepl\b': 'except',
            r'\bfinally\b': 'finally',
            r'\bfina11y\b': 'finally',
            
            r'\bclass\b': 'class',
            r'\bclaas\b': 'class',
            r'\bc1ass\b': 'class',
            
            r'\bfrom\b': 'from',
            r'\bfron\b': 'from',
            r'\bfrom\b': 'from',
            
            r'\bas\b': 'as',
            r'\bfor\b': 'for',
            r'\btor\b': 'for',
            r'\bin\b': 'in',
            r'\bis\b': 'is',
            r'\bor\b': 'or',
            r'\bnot\b': 'not',
            r'\bnol\b': 'not',
            r'\band\b': 'and',
            
            # JavaScript keywords
            r'\bconst\b': 'const',
            r'\bconsl\b': 'const',
            r'\blet\b': 'let',
            r'\b1et\b': 'let',
            r'\bvar\b': 'var',
            r'\bvar\b': 'var',
            r'\bfunction\b': 'function',
            r'\bfunctlon\b': 'function',
            r'\bfuncti0n\b': 'function',
            r'\basync\b': 'async',
            r'\bawait\b': 'await',
            r'\bconsole\b': 'console',
            r'\bconsoie\b': 'console',
            r'\bcons0le\b': 'console',
            r'\blog\b': 'log',
            r'\b1og\b': 'log',
            
            # Umumiy so'zlar
            r'\bdeviceia\b': 'device',
            r'\bdapt\b': 'adapt',
            r'\bdetlne\b': 'define',
            r'\bvarlable\b': 'variable',
            r'\bresult\b': 'result',
            r'\bresu1t\b': 'result',
        }
        
        # Har bir pattern uchun almashtirish
        for pattern, replacement in replacements.items():
            try:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            except:
                pass
        
        # Belgilarni tuzatish (newline'larni saqlab)
        text = text.replace('—', '-')  # Em dash
        text = text.replace('–', '-')  # En dash
        text = text.replace('"', '"')  # Smart quotes
        text = text.replace('"', '"')
        text = text.replace(''', "'")
        text = text.replace(''', "'")
        
        return text

    async def analyze_images(self, image_paths, user_name=None):
        """Bir nechta rasmni tahlil qiladi (OCR + Groq AI)"""
        import base64 # This import is not used in the new logic, but kept for consistency if it was intended for other parts.

        try:
            # OCR jarayonini parallel va asinxron bajarish
            loop = asyncio.get_running_loop()
            tasks = []
            
            for i, image_path in enumerate(image_paths):
                tasks.append(loop.run_in_executor(None, self._perform_ocr, (image_path, i)))
            
            # Barcha natijalarni kutish
            results = await asyncio.gather(*tasks)
            all_extracted_texts = list(results)
            
            # Agar OCR o'rnatilmagan bo'lsa, birinchi xatoni qaytarish
            if any("OCR tizimi o'rnatilmagan" in r for r in all_extracted_texts):
                return "⚠️ OCR tizimi o'rnatilmagan. Rasmni tahlil qilish uchun pytesseract va tesseract-ocr o'rnatish kerak."
            
            combined_text = "\n\n".join(all_extracted_texts)
            
            humor_instruction = self._get_humor_instruction(user_name)
            
            prompt = f"""Siz dasturlash mentori siz. Rasmdan OCR orqali olingan kodni tahlil qilasiz.

📸 OCR ORQALI OLINGAN KOD:
```
{combined_text}
```

🚨 **DIQQAT! OCR XATOLARI HAQIQIY XATO EMAS!** 🚨

OCR tizimi ko'pincha keyword'larni noto'g'ri o'qiydi:
- `def` → `aef`, `det`, `deff`, `detf` 
- `print` → `prlnt`, `prinf`, `prlnf`, `pritn`
- `if` → `lf`, `lt`, `1f`
- `return` → `returi`, `retum`, `retun`
- `else` → `elae`, `elsc`
- Raqam/harf: `0`↔`O`, `1`↔`l`↔`I`, `5`↔`S`

🎯 **SIZNING VAZIFANGIZ:**

**1-QADAM: OCR xatolarini tuzatib o'qing**
   - `aef` ko'rsangiz → `def` deb o'qing
   - `prlnt` ko'rsangiz → `print` deb o'qing
   - `lf` ko'rsangiz → `if` deb o'qing

**2-QADAM: Tuzatilgan kodga qarang**
   - Struktura to'g'rimi? (funksiya, if-else, loop)
   - Mantiq to'g'rimi? (algoritm ishlaydi?)
   - Sintaksis to'g'rimi? (qavs, `:`, indent)

**3-QADAM: Faqat HAQIQIY xatolarni toping**
   ✅ **XATO** deb yozing faqat:
   - Qavs yopilmagan: `print("hello"`
   - `:` yo'q: `if x > 5` (keyin kod)
   - Indent xato: funksiya ichida indent yo'q
   - Type xato: `"5" + 5` (string + int)
   - Mantiq xato: noto'g'ri algoritm
   
   ❌ **XATO** deb yozmang agar:
   - Faqat OCR keyword'larni noto'g'ri o'qigan bo'lsa
   - Kod strukturasi va mantiq to'g'ri bo'lsa
   
   ⚠️ MUHIM: Javobda OCR xatolarini ESLATMANG! Foydalanuvchi uchun keraksiz.

📋 TAHLIL FORMATI:

**1. KOD MAQSADI:**
   [Kod nima qilmoqchi? Qisqa tushuntirish]

**2. STRUKTURA:**
   ✅ To'g'ri / ❌ Xato bor
   [Agar xato bo'lsa: Aniq qayerda va nima xato? Kod misolini ` ` ichida yozing]

**3. MANTIQ:**
   ✅ To'g'ri / ❌ Xato bor
   [Agar xato bo'lsa: Mantiq qayerda buzilgan? Kod misolini ` ` ichida yozing]

**4. XATOLAR VA TUZATISH:**
   [Agar xato bo'lsa, har bir xatoni batafsil yozing:]
   
   ❌ **Xato 1:** [Xato tavsifi]
   ```
   # Noto'g'ri:
   [xatoli kod]
   
   # To'g'ri:
   [tuzatilgan kod]
   ```
   💡 **Tushuntirish:** [Nega bu xato va qanday tuzatish kerak]
   
   [Agar boshqa xatolar bo'lsa, davom eting...]

**5. TAVSIYALAR:**
   [Agar kod ishlaydi lekin yaxshilash mumkin bo'lsa:]
   💡 [Tavsiya 1]
   💡 [Tavsiya 2]

**6. XULOSA:**
   - ✅ Kod to'g'ri ishlaydi! [Agar xato yo'q bo'lsa]
   - ❌ Kod ishlamaydi, X ta xato bor [Agar xato bo'lsa]

**7. BAHO:** X/10
   - 9-10: Ajoyib! Xato yo'q
   - 7-8: Yaxshi, 1-2 kichik xato
   - 5-6: O'rtacha, 2-3 xato
   - 3-4: Ko'p xato bor

⚠️ MUHIM: Kod misollarini FAQAT ``` ``` (triple backtick) ichida yozing! Misol:
```
def hello():
    print("Salom")
```

💡 **ESLATMA:** Aniq tahlil uchun kodingizni fayl sifatida yuboring!

{humor_instruction}"""
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # Oddiy text model ishlatamiz (vision o'rniga)
            data = {
                'model': self.model,  # llama-3.3-70b-versatile
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Siz dasturlash mentori siz. OCR xatolarini (aef→def, prlnt→print, lf→if) ichki tuzatib o\'qing va faqat HAQIQIY dasturlash xatolarini toping. '
                                   'JUDA MUHIM: '
                                   '1) Kod misollarini FAQAT ``` ``` (triple backtick) ichida yozing '
                                   '2) HTML teglarni HECH QACHON ishlatmang (<pre>, <code>, <b>, <i> va h.k.) '
                                   '3) "TAVSIYALAR" qismida kod yozmang, faqat matnli tavsiya bering '
                                   '4) Faqat Markdown format ishlating'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.2,  # Aniqroq javoblar uchun
                'max_tokens': 3500  # Batafsil javoblar uchun (tavsiyalar va kod misollari)
            }
            
            async with aiohttp.ClientSession() as session:
                # Retry mexanizmi (429 xatolik uchun)
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        async with session.post(self.base_url, headers=headers, json=data, timeout=45) as response:
                            response.raise_for_status()
                            result = await response.json()
                            
                            if 'choices' not in result or not result['choices']:
                                return "❌ API dan javob olinmadi. Iltimos qaytadan urinib ko'ring."
                            
                            content = result['choices'][0]['message']['content']
                            return self._convert_to_telegram_format(content)
                            
                    except aiohttp.ClientResponseError as e:
                        status_code = e.status
                        error_detail = str(e)
                        
                        logger.error(f"Groq Vision API xatolik ({status_code}): {error_detail}")
                        
                        # 429 Too Many Requests - kutib qaytadan urinish
                        if status_code == 429:
                            wait_time = (retry + 1) * 5  # 5, 10, 15 soniya
                            logger.warning(f"⚠️ Rasm tahlili 429 xatolik. {wait_time} soniya kutilmoqda... (urinish {retry + 1}/{max_retries})")
                            if retry < max_retries - 1:
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                return "⚠️ <b>Juda ko'p so'rov yuborildi</b>\n\n" \
                                       "Groq API limiti tugadi. Iltimos:\n" \
                                       "• 1-2 daqiqa kuting\n" \
                                       "• Qaytadan urinib ko'ring\n\n" \
                                       "💡 <i>Agar muammo davom etsa, keyinroq urinib ko'ring.</i>"
                        
                        if status_code == 400:
                            return f"❌ Groq Vision API xatolik: Rasm formati yoki hajmi noto'g'ri.\n\nXatolik: {error_detail[:200]}"
                        elif status_code == 401:
                            return "❌ API kaliti noto'g'ri. Admin bilan bog'laning."
                        elif status_code == 500:
                            return "❌ Groq server xatoligi (500). Iltimos bir oz kuting va qaytadan urinib ko'ring."
                        elif status_code == 502:
                            return "❌ Groq server vaqtincha ishlamayapti (502). Iltimos keyinroq urinib ko'ring."
                        elif status_code == 503:
                            return "❌ Groq server yuklanish ostida (503). Iltimos bir oz kuting."
                        else:
                            return f"❌ API xatolik ({status_code}): {error_detail[:200]}"
                            
                    except asyncio.TimeoutError:
                        return "⏰ Javob olish vaqti tugadi. Iltimos qaytadan urinib ko'ring."
                    except Exception as e:
                        logger.error(f"API so'rovda kutilmagan xatolik: {e}")
                        if retry < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return f"❌ Kutilmagan xatolik: {str(e)[:200]}"
        
        except FileNotFoundError as e:
            logger.error(f"Rasm fayli topilmadi: {e}")
            return "❌ Rasm fayli topilmadi. Iltimos qaytadan urinib ko'ring."
        except Exception as e:
            logger.error(f"Rasmni tahlil qilishda xatolik: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Rasmni tahlil qilishda xatolik: {str(e)[:200]}..."
    
    async def analyze_code(self, code, filename, user_name=None):
        """Kod faylini tahlil qiladi"""
        file_ext = filename.split('.')[-1] if '.' in filename else 'txt'
        
        humor_instruction = self._get_humor_instruction(user_name)
        
        prompt = f"""Siz dasturlash mentori siz. Kodni tahlil qiling va FAQAT HAQIQIY xatolarni toping.

{f"O'quvchi: {user_name}" if user_name else ""}
Fayl: {filename}

Kod:
```{file_ext}
{code}
```

⚠️ JUDA MUHIM QOIDALAR:

**XATO** deb hisoblang FAQAT:
1. ❌ Sintaksis xato (kod ishlamaydi):
   - Qavs yopilmagan: `print("hello"`
   - `:` yo'q: `if x > 5`
   - Vergul yo'q: `def func(a b)` → `def func(a, b)`
   - Indent xato: funksiya ichida indent yo'q
   - Quote xato: `"hello'`

2. ❌ Mantiq xato (kod ishlaydi, lekin noto'g'ri):
   - Type xato: `"5" + 5`
   - O'zgaruvchi e'lon qilinmagan: `print(x)` (x yo'q)
   - Division by zero: `10 / 0`
   - Taqqoslash xato: `if x = 5` → `if x == 5`

**XATO EMAS** deb hisoblang:
✅ Kod ishlaydi va to'g'ri natija beradi
✅ Stil farqi (masalan: `i` o'rniga `index` ishlatish)
✅ Alternativ yechim (masalan: loop o'rniga list comprehension)
✅ Optimizatsiya kerak (lekin kod ishlaydi)

📋 TAHLIL FORMATI:

**1. KOD MAQSADI:**
   [Kod nima qiladi? Qisqa tushuntirish]

**2. SINTAKSIS TEKSHIRUVI:**
   ✅ Sintaksis to'g'ri / ❌ Xato bor
   [Agar xato bo'lsa: Aniq qayerda va nima xato?]

**3. MANTIQ TEKSHIRUVI:**
   ✅ Mantiq to'g'ri / ❌ Xato bor
   [Agar xato bo'lsa: Mantiq qayerda buzilgan?]

**4. XATOLAR VA TUZATISH:**
   [Agar xato bo'lsa, har bir xatoni batafsil yozing:]
   
   ⚠️ JUDA MUHIM - KOD YOZISH QOIDASI:
   Kod misollarini FAQAT ``` ``` (triple backtick) ichida yozing!
   Triple backtick TASHQARIDA kod yozmang!
   
   ANIQ MISOL (aynan shu formatda yozing):
   
   ❌ **Xato 1:** [Xato tavsifi]
   ```{file_ext}
   # Noto'g'ri:
   [xatoli kod qatori]
   
   # To'g'ri:
   [tuzatilgan kod qatori]
   ```
   💡 **Tushuntirish:** [Nega bu xato va qanday tuzatish kerak]
   
   ⚠️ NOTO'G'RI (ishlatmang):
   - Kod yozib, keyin </pre> qo'yish
   - Triple backtick ishlatmasdan kod yozish
   - HTML teglar ishlatish

**5. TAVSIYALAR:**
   [Agar kod ishlaydi lekin yaxshilash mumkin bo'lsa:]
   
   ⚠️ MUHIM: Bu qismda KOD YOZISH TAQIQLANGAN!
   Faqat MATNLI tavsiyalar bering, kod misoli YOZMANG!
   
   Misol (TO'G'RI):
   💡 Foydalanuvchi kiritgan ma'lumotlarni tekshirish uchun try-except ishlatish mumkin
   💡 O'zgaruvchilar nomini aniqroq qilish yaxshiroq
   
   Misol (NOTO'G'RI - ishlatmang):
   💡 Quyidagi kodni qo'shing: def check()...
   💡 Kod: print("hello")

**6. XULOSA:**
   - ✅ Kod to'g'ri ishlaydi! [Agar xato yo'q bo'lsa]
   - ❌ Kod ishlamaydi, X ta xato bor [Agar xato bo'lsa]

**7. BAHO:** X/10
   - 9-10: Ajoyib! Xato yo'q
   - 7-8: Yaxshi, 1-2 kichik xato
   - 5-6: O'rtacha, 2-3 xato
   - 3-4: Ko'p xato bor

⚠️ JUDA MUHIM - KOD FORMATI:
1. Kod misollarini FAQAT "4. XATOLAR VA TUZATISH" qismida yozing
2. Kod misollarini FAQAT ``` ``` (triple backtick) ichida yozing
3. "5. TAVSIYALAR" qismida KOD YOZMANG, faqat matnli tavsiya bering
4. HTML taglarni HECH QACHON ISHLATMANG (<pre>, <code>, <b> va h.k.)
5. Faqat Markdown format ishlating

MISOL - TO'G'RI (faqat "4. XATOLAR" qismida):
```python
def hello():
    print("Salom")
```

NOTO'G'RI (ishlatmang):
<pre>def hello():</pre>
<code>print("hello")</code>
def hello():  # Kod ``` ``` ichida emas!


{humor_instruction}"""



        response = await self._send_request(prompt)
        # _convert_to_telegram_format allaqachon _send_request ichida chaqirilgan
        return response
    
    async def generate_quiz(self, code, filename, user_name=None):
        """Kod uchun 5 ta quiz savol yaratadi"""
        # Fayl kengaytmasini aniqlash
        file_ext = filename.split('.')[-1] if '.' in filename else 'txt'
        
        prompt = f"""Siz ProX akademiyasining dasturlash mentori siz. Quyidagi kod uchun 5 ta SIFATLI quiz savol yarating:

{f"O'quvchi: {user_name}" if user_name else ""}
Fayl: {filename}

Kod:
```{file_ext}
{code}
```

⚠️ JUDA MUHIM QOIDALAR:

**SAVOL TURLARI** (har biridan 1 ta):
1. 📝 **Sintaksis** - Aniq qator raqami bilan (masalan: "3-qatorda qanday xato bor?")
2. 🔍 **Natija** - Aniq qiymat bilan (masalan: "5-qator qanday natija beradi?")
3. 🐛 **O'zgaruvchi** - Aniq o'zgaruvchi haqida (masalan: "x o'zgaruvchisi qanday qiymatga ega?")
4. 💡 **Funksiya** - Aniq funksiya haqida (masalan: "calculate() funksiyasi nima qaytaradi?")
5. 🧠 **Kod qismi** - Aniq kod qismi haqida (masalan: "7-9 qatorlar nima qiladi?")

**JUDA MUHIM - SAVOL QOIDALARI:**
- ✅ Savol ANIQ qator/o'zgaruvchi/funksiya haqida bo'lsin
- ✅ Qator raqamini ko'rsating (masalan: "3-qator", "5-9 qatorlar")
- ✅ O'zgaruvchi/funksiya nomini ko'rsating
- ✅ Faqat 1 ta to'g'ri javob bo'lsin
- ❌ "Qanday yaxshilash mumkin?" kabi umumiy savollar TAQIQLANGAN

**NOTO'G'RI SAVOLLAR (ishlatmang):**
❌ "Kodda qanday xato bor?" (qaysi qatorda?)
❌ "Kodni qanday yaxshilash mumkin?" (noaniq)
❌ "Bu funksiya nima qiladi?" (qaysi funksiya?)

**TO'G'RI SAVOLLAR:**
✅ "3-qatorda qanday xato bor?" (aniq qator)
✅ "calculate(5, 3) qanday natija beradi?" (aniq qiymat)
✅ "x o'zgaruvchisi 7-qatordan keyin qanday qiymatga ega?" (aniq)

**VARIANTLAR:**
- Barcha variantlar mantiqiy bo'lsin
- Faqat 1 ta to'g'ri javob bo'lsin
- Noto'g'ri variantlar ham ishonchli ko'rinsin (chalg'ituvchi)
- Qisqa va aniq bo'lsin (1 qator)

**TUSHUNTIRISH:**
- Nega bu javob to'g'ri?
- Noto'g'ri variantlar nega noto'g'ri?
- Qisqa va tushunarli (2-3 jumla)

**JSON FORMATI - JUDA MUHIM:**
{{
  "question": "Savol matni (aniq va qisqa)",
  "options": {{
    "A": "Variant A (qisqa)",
    "B": "Variant B (qisqa)", 
    "C": "Variant C (qisqa)",
    "D": "Variant D (qisqa)"
  }},
  "correct": "A",
  "explanation": "To'g'ri javob: A. Sabab: ... Noto'g'ri variantlar: B - ..., C - ..., D - ..."
}}

⚠️ **JSON QOIDALARI - JUDA MUHIM:**
1. String ichida qo'shtirnoq (") HECH QACHON ishlatmang!
2. Kod yozmaslik - faqat oddiy matn
3. Agar kod kerak bo'lsa, bitta qo'shtirnoq (') ishlating
4. Yoki qo'shtirnoqsiz yozing

**NOTO'G'RI (JSON xato):**
"if name == "" or age == "":" ❌ (ichida qo'shtirnoq)
"print("hello")" ❌ (ichida qo'shtirnoq)

**TO'G'RI:**
"if name yoki age bo'sh bo'lsa" ✅ (oddiy matn)
"print funksiyasi chaqiriladi" ✅ (oddiy matn)
"if name == '' or age == ''" ✅ (bitta qo'shtirnoq)

**MISOL (Python kod uchun):**
```json
[
  {{
    "question": "Quyidagi kod qanday natija beradi?",
    "options": {{
      "A": "1",
      "B": "2",
      "C": "3",
      "D": "Xato beradi"
    }},
    "correct": "B",
    "explanation": "To'g'ri javob: B. Python'da list index 0 dan boshlanadi, shuning uchun x[1] ikkinchi elementni qaytaradi."
  }}
]
```

⚠️ E'TIBOR: Savol va tushuntirishda kod yozmaslik yaxshiroq. Faqat oddiy matn ishlating.

JAVOB FORMATI:
[
  {{savol 1 - Sintaksis}},
  {{savol 2 - Natija}},
  {{savol 3 - Xato}},
  {{savol 4 - Best Practice}},
  {{savol 5 - Mantiq}}
]

⚠️ FAQAT JSON array qaytaring, boshqa hech narsa yo'q! Markdown kod bloklari ham kerak emas!"""

        # Quiz uchun maxsus so'rov (oddiy system prompt bilan)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'Siz dasturlash mentori siz. Faqat to\'g\'ri JSON formatida javob bering. '
                               'JUDA MUHIM QOIDALAR: '
                               '1. String ichida qo\'shtirnoq (") HECH QACHON ishlatmang! '
                               '2. Kod yozmaslik - faqat oddiy matn (masalan: "if name bo\'sh bo\'lsa") '
                               '3. Agar kod kerak bo\'lsa, bitta qo\'shtirnoq (\') ishlating '
                               '4. Savolda qator raqamini ko\'rsating (masalan: "3-qator", "5-9 qatorlar") '
                               '5. HTML taglarni ISHLATMANG!'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,  # Aniq JSON uchun past temperature
            'max_tokens': 3000
        }
        
        async with aiohttp.ClientSession() as session:
            # Retry mexanizmi (429 xatolik uchun)
            max_retries = 3
            for retry in range(max_retries):
                try:
                    async with session.post(self.base_url, headers=headers, json=data, timeout=30) as api_response:
                        api_response.raise_for_status()
                        result = await api_response.json()
                        
                        if 'choices' not in result or not result['choices']:
                            logger.error("API dan javob yo'q")
                            return None
                        
                        response = result['choices'][0]['message']['content']
                        logger.info(f"✅ Quiz AI javob olindi: {len(response)} belgi")
                        break  # Muvaffaqiyatli bo'lsa, loopdan chiqish
                        
                except aiohttp.ClientResponseError as e:
                    if e.status == 429:
                        wait_time = (retry + 1) * 5  # 5, 10, 15 soniya
                        logger.warning(f"⚠️ Quiz 429 xatolik. {wait_time} soniya kutilmoqda... (urinish {retry + 1}/{max_retries})")
                        if retry < max_retries - 1:
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error("Quiz yaratish muvaffaqiyatsiz (429)")
                            return None
                    else:
                        logger.error(f"Quiz API xatolik: {e.status} - {e.message}")
                        return None
                        
                except Exception as e:
                    logger.error(f"Quiz API xatolik: {e}")
                    if retry < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return None
        
        # JSON ni parse qilish
        try:
            import json
            import html
            import re
            
            logger.info(f"Quiz AI javob uzunligi: {len(response)} belgi")
            
            # HTML entities ni decode qilish (&quot; -> ")
            response = html.unescape(response.strip())
            
            # Markdown kod bloklarini olib tashlash
            if '```' in response:
                # ```json ... ``` yoki ``` ... ``` formatini topish
                match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
                if match:
                    response = match.group(1).strip()
                    logger.info("✅ Markdown kod bloki olib tashlandi")
            
            # Agar response [ bilan boshlanmasa, [ ni topish
            if not response.strip().startswith('['):
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    response = match.group(0)
                    logger.info("✅ JSON array topildi")
            
            # JSON ichidagi noto'g'ri escape qilingan qo'shtirnoqlarni tuzatish
            # Misol: "def add(a, b): return a + b" -> "def add(a, b): return a + b"
            # Bu juda murakkab, shuning uchun json.loads() ning strict=False parametrini ishlatamiz
            
            # Birinchi urinish - oddiy parse
            try:
                questions = json.loads(response)
                logger.info("✅ JSON muvaffaqiyatli parse qilindi")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Birinchi parse xatolik: {e}")
                
                # Ikkinchi urinish - noto'g'ri qo'shtirnoqlarni tuzatish
                # String ichidagi qo'shtirnoqlarni escape qilish
                # Bu juda murakkab, shuning uchun AI ga qaytadan so'raymiz
                logger.error(f"JSON parse xatolik. Response: {response[:1000]}")
                
                # Uchinchi urinish - json5 kutubxonasi (agar o'rnatilgan bo'lsa)
                try:
                    import json5
                    questions = json5.loads(response)
                    logger.info("✅ JSON5 bilan parse qilindi")
                except ImportError:
                    logger.error("json5 kutubxonasi o'rnatilmagan")
                    raise e
                except Exception as e2:
                    logger.error(f"JSON5 ham ishlamadi: {e2}")
                    raise e
            
            # Validatsiya
            if not isinstance(questions, list):
                logger.error(f"❌ Javob list emas: {type(questions)}")
                return None
            
            if len(questions) != 5:
                logger.warning(f"⚠️ {len(questions)} ta savol (5 ta bo'lishi kerak)")
                # Agar 5 tadan kam bo'lsa, hech bo'lmaganda 3 ta bo'lsin
                if len(questions) < 3:
                    logger.error("❌ Juda kam savol")
                    return None
            
            # Har bir savolni validatsiya qilish
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    logger.error(f"❌ Savol {i+1} dict emas")
                    return None
                
                required_keys = ['question', 'options', 'correct', 'explanation']
                for key in required_keys:
                    if key not in q:
                        logger.error(f"❌ Savol {i+1}da '{key}' yo'q")
                        return None
                
                # Options validatsiya
                if not isinstance(q['options'], dict):
                    logger.error(f"❌ Savol {i+1} options dict emas")
                    return None
                
                if len(q['options']) < 2:
                    logger.error(f"❌ Savol {i+1}da kam variant")
                    return None
            
            logger.info(f"✅ {len(questions)} ta savol muvaffaqiyatli yaratildi")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse xatolik: {e}")
            logger.error(f"Response (birinchi 500 belgi): {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"❌ Quiz parse qilishda xatolik: {e}")
            logger.error(f"Response (birinchi 500 belgi): {response[:500] if response else 'None'}")
            return None
    
    async def answer_question(self, question, user_name=None, user_context=None):
        """O'quvchi savoliga javob beradi"""
        
        # Oddiy salomlashuvlar va umumiy savollarni aniqlash
        casual_greetings = ['salom', 'assalom', 'qalaysan', 'qalesan', 'hi', 'hello', 'hey', 'nima gap', 'yaxshimisan']
        question_lower = question.lower().strip()
        
        # "Kim yaratgan" savolini aniqlash
        creator_keywords = ['kim yaratgan', 'kim yaratdi', 'kim qilgan', 'kim yasagan', 'yaratuvchi', 'creator', 'seni kim']
        is_creator_question = any(keyword in question_lower for keyword in creator_keywords)
        
        if is_creator_question:
            return """Meni Jahongir Raxmatullayev yaratdi! 🚀

Jahongir - ProX akademiyasining bosh mentorlaridan biri va bu botni akademiya o'quvchilariga yordam berish uchun yaratdi.

ProX akademiyasi haqida qisqacha:
📚 600 qadam dasturi:
   • 500 qadam - Dasturlash texnologiyalari
   • 50 qadam - Shaxsiy rivojlanish
   • 50 qadam - Ingliz tili va dasturni sotish

🎯 Maqsad: Nafaqat dasturchi, balki fikrlovchi va rivojlanuvchi shaxs yetishtirish!

Batafsil ma'lumot uchun "ProX akademiyasi haqida" deb yozing."""
        
        # "Tushunmadim" kabi savollarni aniqlash
        confusion_keywords = ['tushunmadim', 'tushunmayapman', 'qanday', 'qayerda', 'nima uchun', 'nimaga', 'qanday qilib', 'tushuntir']
        is_confusion = any(keyword in question_lower for keyword in confusion_keywords)
        
        if is_confusion:
            # Batafsil tushuntirish uchun alohida prompt
            return await self._detailed_explanation(question, user_name)
        
        # Agar oddiy salomlashuv bo'lsa, qisqa javob berish
        is_casual = any(greeting in question_lower for greeting in casual_greetings)
        
        if is_casual and len(question.split()) <= 3:
            casual_responses = [
                f"{user_name}, salom! 👋 Dasturlash bo'yicha savolingiz bormi?" if user_name else "Salom! 👋 Dasturlash bo'yicha savolingiz bormi?",
                f"{user_name}, yaxshiman! 😊 Sizga qanday yordam bera olaman?" if user_name else "Yaxshiman! 😊 Sizga qanday yordam bera olaman?",
                f"{user_name}, zo'r! 🚀 Dasturlash haqida gaplashamizmi?" if user_name else "Zo'r! 🚀 Dasturlash haqida gaplashamizmi?",
            ]
            import random
            return random.choice(casual_responses)
        
        humor_instruction = self._get_humor_instruction(user_name)
        
        # ProX akademiyasi haqida savollarni aniqlash
        academy_keywords = ['prox', 'akademiya', 'ustoz', 'mentor', 'javohir', 'jahongir', 'ozodbek', 'namoz', 'o\'qituvchi']
        is_academy_question = any(keyword in question_lower for keyword in academy_keywords)
        
        prompt = f"""Siz dasturlash mentori siz. O'quvchiga aniq va tushunarli javob bering.

{f"O'quvchi: {user_name}" if user_name else ""}
Savol: {question}

⚠️ QOIDALAR:

1. **ANIQ VA QISQA:** Ortiqcha gapirmang, to'g'ridan-to'g'ri javobga o'ting
2. **KOD MISOLLARI:** Har doim amaliy misol bering
3. **BOSQICHMA-BOSQICH:** Murakkab mavzularni qadamma-qadam tushuntiring
4. **TUSHUNARLI TIL:** Sodda va aniq til ishlating

📚 JAVOB BERISH MISOLLARI:

**MISOL 1 - TUSHUNCHA:**
Savol: "Python'da list nima?"
Javob:
List - bu bir nechta qiymatlarni saqlash uchun konteyner.

**Misol:**
```python
fruits = ["olma", "banan", "uzum"]
print(fruits[0])  # olma
```

**Asosiy xususiyatlar:**
- O'zgaruvchan (mutable)
- Tartiblangan (ordered)
- Har qanday tip saqlaydi

---

**MISOL 2 - KOD YOZISH:**
Savol: "Sonlar yig'indisini qanday topaman?"
Javob:
```python
# Variant 1: Loop
numbers = [1, 2, 3, 4, 5]
total = 0
for num in numbers:
    total += num
print(total)  # 15

# Variant 2: sum() funksiyasi
total = sum(numbers)
print(total)  # 15
```

---

**MISOL 3 - XATONI TUZATISH:**
Savol: "TypeError: can only concatenate str nima?"
Javob:
Bu xato string va raqamni qo'shishga uringanda chiqadi.

**Xato:**
```python
age = input("Yosh: ")  # "25" (string)
result = age + 5       # ❌ TypeError
```

**To'g'ri:**
```python
age = int(input("Yosh: "))  # 25 (int)
result = age + 5            # ✅ 30
```

---

**MISOL 4 - TAQQOSLASH:**
Savol: "List va tuple farqi nima?"
Javol:
| | List | Tuple |
|---|------|-------|
| O'zgaradi | ✅ Ha | ❌ Yo'q |
| Sintaksis | `[1, 2]` | `(1, 2)` |
| Tezlik | Sekinroq | Tezroq |

**Qachon ishlatish:**
- List: Ma'lumot o'zgarsa
- Tuple: Ma'lumot doimiy bo'lsa

---

📋 ENDI YUQORIDAGI SAVOLGA JAVOB BERING:

{humor_instruction}"""
        
        return await self._send_request(prompt)
    
    async def _detailed_explanation(self, question, user_name=None):
        """Batafsil tushuntirish uchun alohida funksiya"""
        humor_instruction = self._get_humor_instruction(user_name)
        
        prompt = f"""Siz dasturlash mentori siz. O'quvchi nimanidir tushunmagan, batafsil tushuntiring.

{f"O'quvchi: {user_name}" if user_name else ""}
Savol: {question}

⚠️ BATAFSIL TUSHUNTIRISH QOIDALARI:

1. **BOSHLANG'ICHDAN BOSHLANG:** Eng oddiy tushunchadan boshlab tushuntiring
2. **KO'P MISOLLAR:** Har bir qadamga misol bering
3. **VIZUAL:** Iloji boricha vizual misollar ishlating
4. **AMALIY:** Real hayotiy misollar keltiring

📚 BATAFSIL TUSHUNTIRISH FORMATI:

**1. ODDIY TUSHUNTIRISH** (1-2 jumla):
   [Eng sodda tilda nima ekanligini ayting]

**2. QANDAY ISHLAYDI:**
   Qadam 1: [birinchi qadam]
   Qadam 2: [ikkinchi qadam]
   Qadam 3: [uchinchi qadam]

**3. MISOL 1 - ODDIY:**
   ```python
   [eng oddiy misol]
   ```
   Natija: [nima bo'ladi]

**4. MISOL 2 - AMALIY:**
   ```python
   [real hayotiy misol]
   ```
   Natija: [nima bo'ladi]

**5. KO'P UCHRAYDIGAN XATOLAR:**
   ❌ [xato 1]
   ❌ [xato 2]

**6. MASLAHATLAR:**
   💡 [maslahat 1]
   💡 [maslahat 2]

{humor_instruction}"""


        
        return await self._send_request(prompt)
    
    async def _send_request(self, prompt):
        """Groq API ga so'rov yuboradi"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        system_prompt = """Siz ProX akademiyasining yordamchi dasturlash mentori siz. O'quvchilarga o'zbek tilida yordam berasiz.

ProX AKADEMIYASI HAQIDA:
- Botni yaratgan: Jahongir Raxmatullayev
- Bosh ustoz va asoschisi: Javohir Hakimov
- Bosh mentorlar: Jahongir Raxmatullayev, Mirgasimov Ozodbek, Kamolov Namoz

AKADEMIYA DASTURI - 600 QADAM:
1. Dasturlash texnologiyalari (500 qadam):
   - Frontend: HTML, CSS, JavaScript, React, Vue
   - Backend: Python, Node.js, Django, FastAPI
   - Database: SQL, MongoDB
   - DevOps: Git, Docker, CI/CD
   - Mobile: React Native, Flutter
   - Va boshqa zamonaviy texnologiyalar

2. Shaxsiy rivojlanish (50 qadam):
   - Fikrlash qobiliyati
   - Muammo yechish
   - Vaqtni boshqarish
   - Maqsad qo'yish
   - O'z-o'zini rivojlantirish
   - Atom odatlari asosida

3. Ingliz tili va kommunikatsiya (50 qadam):
   - Texnik ingliz tili
   - Gapirish ko'nikmalari
   - Prezentatsiya qilish
   - Dasturni sotish ko'nikmalari
   - Professional muloqot

AKADEMIYA MAQSADI:
- Nafaqat dasturchi, balki:
  ✅ Fikrlovchi shaxs
  ✅ Muammolarni yechadigan professional
  ✅ O'z mahsulotini sotadigan tadbirkor
  ✅ Ingliz tilida gaplashadigan mutaxassis
  ✅ Doimiy rivojlanuvchi inson

KOD TAHLILI QOIDALARI:
- Xatolarni BATAFSIL tushuntiring
- Kod misollarini FAQAT ``` ``` (triple backtick) ichida yozing
- Har bir xato uchun "Noto'g'ri" va "To'g'ri" kod misolini ko'rsating
- Tuzatish yo'lini aniq va tushunarli yozing
- Tavsiyalar bering (agar kod ishlaydi lekin yaxshilash mumkin bo'lsa)
- Javob to'liq va professional bo'lsin

JUDA MUHIM - FORMAT QOIDALARI:
1. Kod misollarini FAQAT ``` ``` ichida yozing
2. HTML taglarni HECH QACHON ishlatmang (<pre>, <code>, <b>, <i> va h.k.)
3. Faqat Markdown format: ``` ```, **, *, _
4. Javobda HTML bo'lmasligi kerak!

TO'G'RI:
```python
def hello():
    print("Salom")
```

NOTO'G'RI (ishlatmang):
<pre>def hello():</pre>
<code>print("hello")</code>
<b>Bold text</b>

JAVOB BERISH QOIDALARI:
- Agar ProX akademiyasi haqida savol berilsa, yuqoridagi ma'lumotlarni bering
- 600 qadam dasturi haqida so'rashsa, batafsil tushuntiring
- Har bir javob oxirida qisqa motivatsion jumla qo'shing (1-2 qator)"""

        # Alternative modellar - agar bitta ishlamasa, boshqasini sinash
        models_to_try = [
            self.model,  # llama-3.3-70b-versatile
            'llama-3.1-70b-versatile',  # Backup model
            'mixtral-8x7b-32768'  # Yana bir backup
        ]
        
        last_error = None
        
        async with aiohttp.ClientSession() as session:
            for model_name in models_to_try:
                data = {
                    'model': model_name,
                    'messages': [
                        {
                            'role': 'system',
                            'content': system_prompt
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.4,  # Aniqroq javoblar uchun (0.7 dan kamaytirildi)
                    'max_tokens': 3500  # Batafsil javoblar uchun (kod misollari va tavsiyalar)
                }
                
                # Retry mexanizmi (429 xatolik uchun)
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        async with session.post(self.base_url, headers=headers, json=data, timeout=45) as response:
                            response.raise_for_status()
                            result = await response.json()
                            
                            if 'choices' not in result or not result['choices']:
                                continue  # Keyingi modelni sinash
                            
                            content = result['choices'][0]['message']['content']
                            
                            # Markdown kod bloklarini Telegram formatiga o'zgartirish
                            content = self._convert_to_telegram_format(content)
                            
                            return content
                            
                    except aiohttp.ClientResponseError as e:
                        last_error = e
                        status_code = e.status
                        
                        # 429 Too Many Requests - kutib qaytadan urinish
                        if status_code == 429:
                            wait_time = (retry + 1) * 5  # 5, 10, 15 soniya
                            logger.warning(f"⚠️ 429 Too Many Requests. {wait_time} soniya kutilmoqda... (urinish {retry + 1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            continue  # Qaytadan urinish
                        
                        # Agar 500 xatolik bo'lsa, keyingi modelni sinash
                        if status_code in [500, 502, 503]:
                            logger.warning(f"Model {model_name} ishlamadi ({status_code}), keyingi modelni sinash...")
                            break  # Keyingi modelga o'tish
                        elif status_code == 400:
                            # 400 xatolik uchun keyingi modelni sinash
                            logger.warning(f"Model {model_name} 400 xatolik berdi, keyingi modelni sinash...")
                            break  # Keyingi modelga o'tish
                        else:
                            # Boshqa xatoliklar uchun to'xtatish
                            raise
                    except Exception as e:
                        last_error = e
                        if retry < max_retries - 1:
                            logger.warning(f"Xatolik: {e}. Qaytadan urinilmoqda...")
                            await asyncio.sleep(2)
                            continue
                        break
            
            # Agar hech bir model ishlamasa
            if last_error:
                if isinstance(last_error, aiohttp.ClientResponseError):
                    status_code = last_error.status
                    
                    # Xatolikni log'ga yozish
                    logger.error(f"Groq API xatolik: {status_code} - {last_error.message}")
                    
                    if status_code == 429:
                        return "⚠️ <b>Juda ko'p so'rov yuborildi</b>\n\n" \
                               "Groq API limiti tugadi. Iltimos:\n" \
                               "• 1-2 daqiqa kuting\n" \
                               "• Qaytadan urinib ko'ring\n\n" \
                               "💡 <i>Agar muammo davom etsa, keyinroq urinib ko'ring.</i>"
                    elif status_code == 400:
                        return "❌ <b>Noto'g'ri so'rov (400)</b>\n\n" \
                               "Sabablari:\n" \
                               "• Fayl juda uzun (token limiti)\n" \
                               "• Noto'g'ri format\n" \
                               "• Maxsus belgilar\n\n" \
                               "💡 <i>Kichikroq fayl yuboring yoki formatni tekshiring.</i>"
                    elif status_code == 401:
                        return "🔑 <b>API kaliti noto'g'ri!</b>\n\n" \
                               "Groq API kaliti muddati tugagan yoki noto'g'ri.\n\n" \
                               "Admin uchun:\n" \
                               "1. https://console.groq.com saytiga kiring\n" \
                               "2. Yangi API key yarating\n" \
                               "3. .env faylida GROQ_API_KEY ni yangilang\n" \
                               "4. Botni qaytadan ishga tushiring\n\n" \
                               "💡 <i>Hozirgi API key oxirida ortiqcha belgi bor edi (`) - tuzatildi!</i>"
                    elif status_code == 500:
                        return "❌ Groq server xatoligi (500). Barcha modellar sinaldi, lekin hech biri ishlamadi.\n\n💡 Iltimos keyinroq urinib ko'ring."
                    elif status_code == 502:
                        return "❌ Groq server vaqtincha ishlamayapti (502). Iltimos keyinroq urinib ko'ring."
                    elif status_code == 503:
                        return "❌ Groq server yuklanish ostida (503). Iltimos bir oz kuting."
                    elif status_code == 504:
                        return "❌ Groq server timeout (504). Iltimos qaytadan urinib ko'ring."
                    else:
                        return f"❌ Server xatoligi: {status_code}\n\nIltimos qaytadan urinib ko'ring yoki admin bilan bog'laning."
            
                return "⏰ Javob olish vaqti tugadi. Iltimos qaytadan urinib ko'ring."
            
            return "🔧 Kutilmagan xatolik. Iltimos qaytadan urinib ko'ring."
    
    def _convert_to_telegram_format(self, text):
        """Markdown kod bloklarini Telegram HTML formatiga o'zgartiradi"""
        import html as html_module
        
        # YANGI: AI tomonidan triple backtick ishlatmasdan yozilgan kodlarni aniqlash va o'rash
        def wrap_unwrapped_code_blocks(text):
            """AI tomonidan ``` ichiga yozilmagan kodlarni topib, ``` ichiga o'rash"""
            lines = text.split('\n')
            result_lines = []
            in_code_block = False
            code_buffer = []
            
            for i, line in enumerate(lines):
                # Triple backtick boshlanishi yoki tugashi
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    result_lines.append(line)
                    continue
                
                # Agar allaqachon kod bloki ichida bo'lsak
                if in_code_block:
                    result_lines.append(line)
                    continue
                
                # Kod pattern'larini aniqlash (Python, JS, va boshqalar)
                code_patterns = [
                    r'^\s*(def|class|import|from|if|elif|else|for|while|try|except|finally|with|async|await)\s+',
                    r'^\s*(function|const|let|var|if|else|for|while|try|catch|finally|async|await)\s+',
                    r'^\s*(public|private|protected|static|void|int|string|bool|class)\s+',
                    r'^\s*#\s*(Noto\'g\'ri|To\'g\'ri|Comment):',
                    r'^\s*//\s*(Noto\'g\'ri|To\'g\'ri|Comment):',
                ]
                
                # Agar qator kod pattern'iga mos kelsa
                is_code_line = any(re.match(pattern, line) for pattern in code_patterns)
                
                # Yoki agar qator indent bilan boshlanib, kod ko'rinishida bo'lsa
                is_indented_code = line.startswith('    ') or line.startswith('\t')
                
                # Kod bufferni boshqarish
                if is_code_line or (is_indented_code and code_buffer):
                    code_buffer.append(line)
                else:
                    # Agar kod buffer to'lgan bo'lsa, uni ``` ichiga o'rash
                    if code_buffer:
                        # Kod bufferdan oldin va keyin </pre> yoki boshqa teglar bo'lishi mumkin
                        # Ularni olib tashlash
                        result_lines.append('```')
                        result_lines.extend(code_buffer)
                        result_lines.append('```')
                        code_buffer = []
                    
                    result_lines.append(line)
            
            # Oxirgi kod bufferni qo'shish
            if code_buffer:
                result_lines.append('```')
                result_lines.extend(code_buffer)
                result_lines.append('```')
            
            return '\n'.join(result_lines)
        
        # AI javobini pre-processing qilish
        text = wrap_unwrapped_code_blocks(text)
        
        # YANGI: AI tomonidan noto'g'ri qo'shilgan HTML teglarni tozalash
        # 1. Yolg'iz closing taglarni olib tashlash (ochilmagan taglar)
        # Masalan: </pre>, </code>, </b> (agar mos opening tag bo'lmasa)
        def remove_orphan_closing_tags(text):
            """Ochilmagan closing taglarni olib tashlash"""
            # Barcha HTML teglarni topish
            tag_pattern = r'<(/?)(\w+)(?:\s[^>]*)?>|```'
            matches = list(re.finditer(tag_pattern, text))
            
            # Stack yordamida ochilmagan taglarni topish
            stack = []
            orphan_positions = []
            
            for match in matches:
                if match.group(0).startswith('```'):
                    # Triple backtick - ignore
                    continue
                    
                is_closing = match.group(1) == '/'
                tag_name = match.group(2).lower()
                
                if is_closing:
                    # Closing tag
                    if stack and stack[-1][1] == tag_name:
                        stack.pop()
                    else:
                        # Orphan closing tag
                        orphan_positions.append((match.start(), match.end()))
                else:
                    # Opening tag
                    stack.append((match.start(), tag_name))
            
            # Orphan taglarni olib tashlash (orqadan oldinga)
            for start, end in reversed(orphan_positions):
                text = text[:start] + text[end:]
            
            return text
        
        # AI javobini tozalash
        text = remove_orphan_closing_tags(text)
        
        # 0. Noto'g'ri HTML taglarni olib tashlash (Telegram qabul qilmaydi)
        # Telegram faqat: <b>, <i>, <u>, <s>, <code>, <pre>, <a> qabul qiladi
        unsupported_tags = [
            'html', 'head', 'body', 'div', 'span', 'p', 'br', 'hr',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
            'table', 'tr', 'td', 'th', 'strong', 'em', 'del', 'ins'
        ]
        
        for tag in unsupported_tags:
            # Opening tags
            text = re.sub(f'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
            # Closing tags
            text = re.sub(f'</{tag}>', '', text, flags=re.IGNORECASE)
        
        # <strong> -> <b>, <em> -> <i>, <del> -> <s>
        text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<del>(.*?)</del>', r'<s>\1</s>', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 1. Kod bloklarini almashtirish: ```kod``` -> <pre>kod</pre>
        # YAXSHILANGAN: Yanada kuchli regex pattern
        def replace_code_block(match):
            # match.group(1) - til nomi (agar mavjud bo'lsa)
            # match.group(2) - kod matni
            lang = match.group(1) if match.group(1) else ''
            content = match.group(2) if match.group(2) else match.group(1)
            
            if not content:
                return match.group(0)  # Agar content bo'sh bo'lsa, o'zgartirilmagan qaytarish
            
            content = content.strip()
            
            # HTML escape (xavfsizlik uchun) - quote=False (bitta qo'shtirnoqni saqlab qolish)
            content = html_module.escape(content, quote=False)
            
            # Telegram monospace format - oddiy <pre>
            return f'<pre>{content}</pre>'
        
        # Yanada ishonchli regex pattern:
        # 1) ```lang\ncode\n``` formatini tutadi
        # 2) ```\ncode\n``` formatini tutadi  
        # 3) ```code``` formatini tutadi
        text = re.sub(
            r'```(?:(\w+)\s*)?\n?(.*?)```',
            replace_code_block,
            text,
            flags=re.DOTALL
        )
        
        # 2. Inline code: `kod` -> <code>kod</code>
        # YAXSHILANGAN: Faqat bitta backtick ichidagi kodni tutish
        def replace_inline_code(match):
            code = match.group(1)
            if not code.strip():
                return match.group(0)  # Bo'sh kod bo'lsa, o'zgartirilmagan qaytarish
            code = html_module.escape(code, quote=False)
            return f'<code>{code}</code>'
        
        # Faqat bitta backtick ichidagi kodni tutish (triple backtick emas)
        text = re.sub(r'(?<!`)(?<!`)`([^`\n]+?)`(?!`)(?!`)', replace_inline_code, text)
        
        # 3. Bold: **text** -> <b>text</b>
        def replace_bold(match):
            content = match.group(1)
            return f'<b>{content}</b>'
        
        text = re.sub(r'\*\*(.+?)\*\*', replace_bold, text)
        
        # 4. Bold: ## text -> <b>text</b>
        text = re.sub(r'^##\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        
        # 5. Maxsus belgilarni tozalash (agar HTML tag ichida bo'lmasa)
        # & belgilarini tekshirish (agar entity bo'lmasa)
        text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', text)
        
        return text
