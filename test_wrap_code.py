import re

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

# Test 1: Kod ``` ichida emas
test1 = """❌ **Xato 1:** Foydalanuvchi kiritgan ma'lumotlarni tekshirish yo'q.
# Noto'g'ri:
x = int(input("Birinchi sonni kiriting: "))

# To'g'ri:
try:
    x = int(input("Birinchi sonni kiriting: "))
except ValueError:
    print("Xato: son kiriting")</pre>
💡 **Tushuntirish:** Foydalanuvchi kiritgan ma'lumotlarni tekshirish uchun try-except ishlatish mumkin."""

# Test 2: Kod allaqachon ``` ichida
test2 = """```python
def hello():
    print("Salom")
```"""

# Test 3: Aralash
test3 = """**4. XATOLAR VA TUZATISH:**
❌ **Xato 1:** Test
# Noto'g'ri:
x = 5

# To'g'ri:
x = int(input())

**5. TAVSIYALAR:**
💡 Try-except ishlatish mumkin"""

print('=' * 60)
print('Test 1 (Kod ``` ichida emas):')
print('=' * 60)
print('OLDIN:')
print(test1)
print('\nKEYIN:')
result1 = wrap_unwrapped_code_blocks(test1)
print(result1)
print()

print('=' * 60)
print('Test 2 (Kod allaqachon ``` ichida):')
print('=' * 60)
print('OLDIN:')
print(test2)
print('\nKEYIN:')
result2 = wrap_unwrapped_code_blocks(test2)
print(result2)
print()

print('=' * 60)
print('Test 3 (Aralash):')
print('=' * 60)
print('OLDIN:')
print(test3)
print('\nKEYIN:')
result3 = wrap_unwrapped_code_blocks(test3)
print(result3)
print()

# Tekshirish
print('=' * 60)
print('TEKSHIRISH:')
print('=' * 60)
print(f"Test 1 - ``` qo'shildi: {result1.count('```') >= 2}")
print(f"Test 2 - ``` saqlanadi: {result2.count('```') == 2}")
print(f"Test 3 - Faqat kod qismiga ``` qo'shildi: {result3.count('```') >= 2}")
