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
    # Yangi: Savatcha jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, food_id INTEGER, quantity INTEGER, PRIMARY KEY (user_id, food_id))''')
    conn.commit()
    conn.close()

# --- BAZADAN SAVATCHANI TEKSHIRISH ---
def get_cart_quantity(user_id, food_id):
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE user_id=? AND food_id=?", (user_id, food_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_cart(user_id, food_id, quantity):
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    if quantity > 0:
        cursor.execute("INSERT OR REPLACE INTO cart (user_id, food_id, quantity) VALUES (?, ?, ?)", (user_id, food_id, quantity))
    else:
        cursor.execute("DELETE FROM cart WHERE user_id=? AND food_id=?", (user_id, food_id))
    conn.commit()
    conn.close()

# --- DINAMIK TUGMALAR YASASH ---
def generate_food_keyboard(food_id, quantity):
    if quantity == 0:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_{food_id}")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➖", callback_data=f"minus_{food_id}"),
                InlineKeyboardButton(text=f"{quantity} ta", callback_data="ignore"),
                InlineKeyboardButton(text="➕", callback_data=f"plus_{food_id}")
            ]
        ])

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
        await message.answer("Xush kelibsiz! 🥗 Parhez taomlar yetkazib berish xizmatiga marhamat.", reply_markup=user_keyboard)

# ==========================================
#        MIJOZLAR UCHUN MENYU VA SAVATCHA
# ==========================================
@dp.message(F.text == "🍽 Bugungi menyu")
async def show_menu_user(message: types.Message):
    conn = sqlite3.connect("oshxona.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, portion, price, photo_id FROM menu WHERE is_active=1")
    foods = cursor.fetchall()
    conn.close()

    if not foods:
        await message.answer("😕 Hozircha menyu bo'sh.")
        return

    await message.answer("🍽 <b>Bugungi parhez taomlar:</b>", parse_mode="HTML")

    for food in foods:
        food_id, name, portion, price, photo_id = food
        qty = get_cart_quantity(message.from_user.id, food_id)
        
        caption = f"🍲 <b>{name}</b>\n⚖️ {portion}\n💸 {price} so'm"
        await message.answer_photo(photo=photo_id, caption=caption, parse_mode="HTML", reply_markup=generate_food_keyboard(food_id, qty))

# --- TUGMALARNI BOSHQARISH (CALLBACK) ---
@dp.callback_query(F.data.startswith("add_") | F.data.startswith("plus_") | F.data.startswith("minus_"))
async def process_cart_buttons(callback: types.CallbackQuery):
    action, food_id = callback.data.split("_")
    food_id = int(food_id)
    user_id = callback.from_user.id

    current_qty = get_cart_quantity(user_id, food_id)

    if action == "add" or action == "plus":
        current_qty += 1
    elif action == "minus" and current_qty > 0:
        current_qty -= 1

    # Bazani yangilash
    update_cart(user_id, food_id, current_qty)

    # Tugmani ekranda o'zgartirish (jonli effekt)
    new_keyboard = generate_food_keyboard(food_id, current_qty)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    except Exception:
        pass # Agar tugma o'zgarmagan bo'lsa, xato bermasligi uchun
    
    await callback.answer() # Yuklanish belgisini to'xtatish

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

    await message.answer(f"✅ Taom menyuga qo'shildi!\n\n🍽 Nom: {data['name']}\n💸 Narx: {price} so'm")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("🥗 Parhez oshxona boti muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "main":
    asyncio.run(main())
