from keep_alive import keep_alive
keep_alive()

import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
BOT_TOKEN = "8684077959:AAGyJzIeM3JNjKoGeVX6klA-dPrXd1FjsA0"
ADMIN_ID = 88808651  # O'ZINGIZNING ID RAQAMINGIZ

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- TUGMALAR ---
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi taom qo'shish")],
        [KeyboardButton(text="📋 Menyuni ko'rish")]
    ], resize_keyboard=True
)

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍽 Bugungi menyu")],
        [KeyboardButton(text="🛒 Savatcha")]
    ], resize_keyboard=True
)

# --- FSM HOLATLAR ---
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
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                   (message.from_user.id, message.from_user.username, message.from_user.full_name))
    conn.commit()
    conn.close()

    if message.from_user.id == ADMIN_ID:
        await message.answer("Assalomu alaykum, Xo'jayin! ⚙️ Boshqaruv paneliga xush kelibsiz.", reply_markup=admin_keyboard)
    else:
        await message.answer(f"Xush kelibsiz, {message.from_user.first_name}! 🥗 Parhez taomlar yetkazib berish xizmatiga marhamat. Quyidagi menyudan foydalaning:", reply_markup=user_keyboard)

# ==========================================
#        MIJOZLAR UCHUN MENYU QISMI
# ==========================================
@dp.message(F.text == "🍽 Bugungi menyu")
async def show_menu_user(message: types.Message):
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, portion, price, photo_id FROM menu WHERE is_active=1")
    foods = cursor.fetchall()
    conn.close()

    if not foods:
        await message.answer("😕 Hozircha menyu bo'sh. Oshpazlarimiz taom tayyorlashmoqda!")
        return

    await message.answer("🍽 <b>Bugungi parhez taomlarimiz:</b>", parse_mode="HTML")

    # Bazadagi har bir taomni bittalab mijozga yuborish
    for food in foods:
        food_id, name, portion, price, photo_id = food
        
        # Har bir taom tagidagi chiroyli "Savatga qo'shish" tugmasi
        add_cart_btn = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_{food_id}")]]
        )
        caption = f"🍲 <b>{name}</b>\n⚖️ Hajmi: {portion}\n💸 Narxi: {price} so'm"
        await message.answer_photo(photo=photo_id, caption=caption, parse_mode="HTML", reply_markup=add_cart_btn)

# ==========================================
#        TAOM QO'SHISH JARAYONI (ADMIN)
# ==========================================

@dp.message(F.text == "➕ Yangi taom qo'shish")
async def add_food_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📸 Avval taomning chiroyli rasmini yuboring:")
    await state.set_state(MenuState.photo)

@dp.message(MenuState.photo, F.photo)
async def add_food_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✍️ Taomning nomini yozing:")
    await state.set_state(MenuState.name)

@dp.message(MenuState.name)
async def add_food_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("⚖️ Porsiya hajmini yozing:")
    await state.set_state(MenuState.portion)

@dp.message(MenuState.portion)
async def add_food_portion(message: types.Message, state: FSMContext):
    await state.update_data(portion=message.text)
    await message.answer("💰 Narxini faqat raqamlarda yozing:")
    await state.set_state(MenuState.price)

@dp.message(MenuState.price)
async def add_food_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try: price = int(message.text)
    except ValueError:
        await message.answer("❌ Narxni faqat raqamlar bilan yozing!")
        return

    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menu (name, portion, price, photo_id) VALUES (?, ?, ?, ?)",
                   (data['name'], data['portion'], price, data['photo']))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Taom menyuga muvaffaqiyatli qo'shildi!\n\n🍽 Nom: {data['name']}\n💸 Narx: {price} so'm")
    await state.clear()

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("🥗 Parhez oshxona boti muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
