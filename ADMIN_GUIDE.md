# Admin Panel Qo'llanmasi

## Admin Turlari

### 1. Super Admin
- `.env` faylida `SUPER_ADMIN_ID` orqali belgilanadi
- Barcha huquqlarga ega
- Boshqa adminlarni qo'shishi va o'chirishi mumkin
- O'zgartirib bo'lmaydi

### 2. Oddiy Admin
- Super Admin tomonidan qo'shiladi
- Barcha admin funksiyalaridan foydalanishi mumkin
- Boshqa adminlarni qo'sha/o'chira olmaydi

## Admin Panel Funksiyalari

### 📊 Statistika
- Jami foydalanuvchilar soni
- Jami kod tekshiruvlar soni
- Bugungi statistika
- Oxirgi 7 kun statistikasi
- TOP 10 foydalanuvchilar

### 👥 Foydalanuvchilar
- Barcha foydalanuvchilar ro'yxati
- Har bir foydalanuvchi statistikasi
- Foydalanuvchi ID'lari

### 📢 Xabar yuborish (Broadcast)
- Barcha foydalanuvchilarga xabar yuborish
- Tasdiqlash tizimi
- Yuborish statistikasi
- Xatolar haqida ma'lumot

### ⚙️ Sozlamalar
- Salom xabari (yoniq/o'chiq)
- Stikerlar (yoniq/o'chiq)
- Ovozli javob (yoniq/o'chiq)
- Guruh rejimi (yoniq/o'chiq)
- Admin bildirishnomalar (yoniq/o'chiq)
- Maksimal xabar uzunligi
- Temperature (AI javob turi)
- Max tokens

### 👨‍💼 Adminlar (Faqat Super Admin)
- Adminlar ro'yxati
- Admin qo'shish
- Admin o'chirish

### 🔄 Botni qayta yuklash
- Botni qayta ishga tushirish
- Yangilanishlarni qo'llash

## Admin Qo'shish

### 1-usul: Admin Panel orqali

1. Super admin sifatida botga `/panel` yuboring
2. "👨‍💼 Adminlar" tugmasini bosing
3. "➕ Admin qo'shish" tugmasini bosing
4. Yangi admin Telegram ID'sini yuboring
5. Bot avtomatik yangi adminga xabar yuboradi

### 2-usul: admins.json faylini tahrirlash

```json
{
  "admins": [
    {
      "user_id": 123456789,
      "name": "Admin Ismi",
      "added_by": 5027595868,
      "added_at": "2024-01-01 12:00:00"
    }
  ]
}
```

## Admin O'chirish

1. Super admin sifatida botga `/panel` yuboring
2. "👨‍💼 Adminlar" tugmasini bosing
3. "➖ Admin o'chirish" tugmasini bosing
4. O'chirmoqchi bo'lgan adminni tanlang
5. Tasdiqlang

## Telegram ID'ni Topish

### Usul 1: @userinfobot
1. [@userinfobot](https://t.me/userinfobot) ga o'ting
2. `/start` yuboring
3. Bot sizning ID'ingizni ko'rsatadi

### Usul 2: @getmyid_bot
1. [@getmyid_bot](https://t.me/getmyid_bot) ga o'ting
2. `/start` yuboring
3. Bot sizning ID'ingizni ko'rsatadi

### Usul 3: Bot loglaridan
Bot ishga tushganda har bir xabar uchun user ID logga yoziladi.

## Xavfsizlik

### Super Admin ID
- `.env` faylida saqlang
- Hech kimga ko'rsatmang
- Git'ga commit qilmang

### Admin Huquqlari
- Faqat ishonchli odamlarga admin huquqi bering
- Adminlar barcha foydalanuvchilarga xabar yubora oladi
- Adminlar bot sozlamalarini o'zgartira oladi

### Tavsiyalar
- Adminlar sonini minimal ushlab turing
- Kerak bo'lmagan adminlarni o'chiring
- Admin qo'shish/o'chirish loglarini kuzatib boring

## Muammolarni Hal Qilish

### Admin panel ochilmayapti
- Telegram ID to'g'ri kiritilganligini tekshiring
- `.env` faylida `SUPER_ADMIN_ID` mavjudligini tekshiring
- Botni qayta ishga tushiring

### Admin qo'shilmayapti
- Faqat Super Admin qo'sha oladi
- Telegram ID to'g'ri formatda ekanligini tekshiring
- Foydalanuvchi botni ishga tushirgan bo'lishi kerak

### Admin o'chirilmayapti
- Faqat Super Admin o'chira oladi
- Super Adminni o'chirish mumkin emas

## Buyruqlar

- `/panel` - Admin panelni ochish
- `/start` - Botni qayta ishga tushirish
- `/help` - Yordam
- `/cancel` - Joriy amalni bekor qilish

## Fayllar

- `admins.json` - Adminlar ro'yxati
- `user_memory.json` - Foydalanuvchilar xotirasi
- `settings.json` - Bot sozlamalari
- `stickers.json` - Stikerlar bazasi
