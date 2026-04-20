from keep_alive import keep_alive
keep_alive()

import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

# --- SOZLAMALAR ---
BOT_TOKEN = "8684077959:AAGyJzIeM3JNjKoGeVX6klA-dPrXd1FjsA0"
ADMIN_ID = 88808651  # O'ZINGIZNING TELEGRAM ID RAQAMINGIZNI YOZING

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASINI YARATISH ---
def init_db():
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    
    # 1. Mijozlar ro'yxati 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT
        )
    ''')
    
    # 2. Menyudagi taomlar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            portion TEXT,
            price INTEGER,
            photo_id TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # 3. Buyurtmalar va Izohlar jurnali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            items TEXT,
            total_price INTEGER,
            comment TEXT,      -- Mijozning maxsus izohi uchun joy
            status TEXT DEFAULT 'yangi'
        )
    ''')
    conn.commit()
    conn.close()

# --- START KOMANDASI (KUTIB OLISH) ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Mijozni xotiraga yozib qoyish (Ertalab xabar tarqatish uchun)
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                   (message.from_user.id, message.from_user.username, message.from_user.full_name))
    conn.commit()
    conn.close()

    # Admin kirganda
    if message.from_user.id == ADMIN_ID:
        await message.answer("Assalomu alaykum, Xo'jayin! ⚙️ Boshqaruv paneliga xush kelibsiz.\n\n(Tez orada bu yerga menyu va buyurtmalarni boshqarish tugmalarini qo'shamiz).")
    
    # Mijoz kirganda
    else:
        await message.answer(f"Xush kelibsiz, {message.from_user.first_name}! 🥗 Parhez taomlar yetkazib berish xizmatiga marhamat.\n\n(Tez orada bu yerga 'Bugungi menyu' tugmasini qo'shamiz).")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()  # Bazani tayyorlash
    print("🥗 Parhez oshxona boti muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
