from keep_alive import keep_alive
keep_alive()

import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
# DIQQAT: Token va ID ni o'zingiznikiga almashtirishni unutmang!
BOT_TOKEN = "8684077959:AAGyJzIeM3JNjKoGeVX6klA-dPrXd1FjsA0"
ADMIN_ID = 88808651  # O'ZINGIZNING TELEGRAM ID RAQAMINGIZNI YOZING

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ADMIN TUGMALARI ---
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi taom qo'shish")],
        [KeyboardButton(text="📋 Menyuni ko'rish")]
    ],
    resize_keyboard=True
)

# --- FSM HOLATLAR (Anketa qadamlari) ---
class MenuState(StatesGroup):
    photo = State()
    name = State()
    portion = State()
    price = State()

# --- BAZA YARATISH ---
def init_db():
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, portion TEXT, price INTEGER, photo_id TEXT, is_active INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total_price INTEGER, comment TEXT, status TEXT DEFAULT 'yangi')''')
    conn.commit()
    conn.close()

# --- START KOMANDASI ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Mijozni bazaga saqlash
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                   (message.from_user.id, message.from_user.username, message.from_user.full_name))
    conn.commit()
    conn.close()

    if message.from_user.id == ADMIN_ID:
        await message.answer("Assalomu alaykum, Xo'jayin! ⚙️ Boshqaruv paneliga xush kelibsiz. Nima ish qilamiz?", reply_markup=admin_keyboard)
    else:
        await message.answer(f"Xush kelibsiz, {message.from_user.first_name}! 🥗 Parhez taomlar yetkazib berish xizmatiga marhamat.")

# ==========================================
#        TAOM QO'SHISH JARAYONI (ADMIN)
# ==========================================

# 1-qadam: Tugma bosilganda
@dp.message(F.text == "➕ Yangi taom qo'shish")
async def add_food_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return # Faqat admin uchun
    await message.answer("📸 Yaxshi, yangi taom qo'shamiz! \n\nAvval taomning chiroyli rasmini yuboring:")
    await state.set_state(MenuState.photo)

# 2-qadam: Rasm qabul qilish
@dp.message(MenuState.photo, F.photo)
async def add_food_photo(message: types.Message, state: FSMContext):
    # Rasmning ID sini xotiraga saqlaymiz
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✍️ Zo'r! Endi taomning nomini yozing (Masalan: Pishib chiqqan tovuq to'shi):")
    await state.set_state(MenuState.name)

# 3-qadam: Nomini qabul qilish
@dp.message(MenuState.name)
async def add_food_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("⚖️ Porsiya hajmini yozing (Masalan: 200 gr yoki 1 porse):")
    await state.set_state(MenuState.portion)

# 4-qadam: Hajmini qabul qilish
@dp.message(MenuState.portion)
async def add_food_portion(message: types.Message, state: FSMContext):
    await state.update_data(portion=message.text)
    await message.answer("💰 Narxini faqat raqamlarda yozing (Masalan: 25000):")
    await state.set_state(MenuState.price)

# 5-qadam: Narxni qabul qilish va Bazaga saqlash
@dp.message(MenuState.price)
async def add_food_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        price = int(message.text) # Matnni songa aylantiramiz
    except ValueError:
        await message.answer("❌ Iltimos, narxni faqat raqamlar bilan yozing (so'z qo'shmang)!")
        return

    # Bazaga yozamiz
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menu (name, portion, price, photo_id) VALUES (?, ?, ?, ?)",
                   (data['name'], data['portion'], price, data['photo']))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Taom menyuga muvaffaqiyatli qo'shildi!\n\n🍽 Nom: {data['name']}\n⚖️ Hajm: {data['portion']}\n💸 Narx: {price} so'm")
    await state.clear() # Anketani tozalaymiz

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("🥗 Parhez oshxona boti muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
