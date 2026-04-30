# 🚖 Taxi Bot

Telegram boti uchun to'liq taksi xizmati tizimi.

## 🚀 Xususiyatlar

### 👤 Foydalanuvchi uchun:
- **Ro'yxatdan o'tish**: Ism va telefon raqam orqali
- **Yo'lovchi rejimi**: Yo'lovchilar sonini tanlash, manzil kiritish
- **Pochta xizmati**: Pochta va yuklarni yetkazish
- **Profil**: Shaxsiy ma'lumotlarni ko'rish

### 🚗 Haydovchi uchun:
- **Ariza topshirish**: Haydovchi bo'lish uchun ariza
- **Ariza holati**: Ariza holatini kuzatish
- **Admin tasdiqi**: Arizalarni ko'rish va tasdiqlash

### 📊 Admin uchun:
- **Arizalar ro'yxati**: Barcha haydovchi arizalarini ko'rish
- **Buyurtmalar boshqaruvi**: Taksi va pochta buyurtmalarini boshqarish

## 🛠️ O'rnatish

1. **Klonlash**:
```bash
git clone <repository-url>
cd taxibot
```

2. **Dependensiyalarni o'rnatish**:
```bash
pip install -r requirements.txt
```

3. **Bot tokenini sozlash**:
- `.env` faylini oching
- `YOUR_BOT_TOKEN_HERE` o'rniga o'zingizning bot tokeningizni yozing

4. **Botni ishga tushirish**:
```bash
python app.py
```

## 📋 Botdan foydalanish

### 1. Botni boshlash
- `/start` komandasini yuboring
- Ismingizni kiriting
- Telefon raqamingizni yuboring

### 2. Asosiy menyuda:
- **🚖 Yo'lovchi**: Taksi chaqirish
- **🚗 Taksi bo'lish**: Haydovchi bo'lish uchun ariza
- **📦 Pochta yuborish**: Pochta xizmati
- **👤 Profil**: Shaxsiy ma'lumotlar

### 3. Yo'lovchi rejimi:
- Yo'lovchilar sonini tanlang (1-4+)
- Manzilni kiriting yoki joylashuvni yuboring
- Buyurtmangiz qabul qilinadi

### 4. Pochta xizmati:
- Yetkazish manzilini kiriting
- Buyurtmangiz qabul qilinadi

## 🗄️ Ma'lumotlar bazasi

Bot SQLite ma'lumotlar bazasidan foydalanadi:

- `users`: Foydalanuvchi ma'lumotlari
- `driver_applications`: Haydovchi arizalari  
- `orders`: Barcha buyurtmalar (taksi va pochta)

## 🔧 Admin komandalari

- `/admin`: Barcha haydovchi arizalarini ko'rish

## 📞 Telegram Bot yaratish

1. [@BotFather](https://t.me/botfather) ga murojaat qiling
2. `/newbot` komandasini yuboring
3. Bot nomi va username ni kiriting
4. Tokenni oling va `.env` fayliga qo'ying

## 🌟 Qo'shimcha imkoniyatlar

- Joylashuvni avtomatik aniqlash
- Kontakt ma'lumotlarini avtomatik olish
- Real-time buyurtmalarni kuzatish
- Statuslarni kuzatish (kutilmoqda, tasdiqlangan, rad etilgan)

## 📝 Tillar

Bot to'liq o'zbek tilida ishlaydi.

## 🤝 Hamkorlik

Loyihaga hissa qo'shish istagida bo'lsangiz, iltimos, bog'laning.

## 📄 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.
