import logging
import json
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.dispatcher.filters import Command

API_TOKEN = '7802876030:AAHzr5E3g1lIzhGrvB0stDzQjzvhYa8I1bw'
ADMIN_USERNAME = '@048goatt'
ADMIN_ID = 6803198967  # Заменить на свой Telegram ID, если потребуется точнее

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

CATEGORIES = ["Сумки", "Обувь", "Верхняя одежда", "Штаны", "Шорты", "Футболки", "Аксессуары"]
DATA_FILE = 'catalog.json'

# Хранилище временных данных для добавления
temp_storage = {}

# Кнопки выбора категорий
def category_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}") for cat in CATEGORIES]
    kb.add(*buttons)
    return kb

# Кнопка "Заказать"
def order_button(cat, idx):
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="🛒 Заказать", callback_data=f"order_{cat}_{idx}")
    )

# Загрузка каталога
def load_catalog():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {cat: [] for cat in CATEGORIES}

# Сохранение каталога
def save_catalog(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Напиши описание товара и пришли фото, чтобы добавить позицию в каталог.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME.lstrip("@"):
        await message.answer("Добавлять товары может только админ.")
        return

    file_id = message.photo[-1].file_id
    temp_storage[message.from_user.id] = {"photo": file_id}
    await message.answer("Отлично! Теперь пришли описание товара.")

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    if message.from_user.username != ADMIN_USERNAME.lstrip("@"):
        await message.answer("Добавлять товары может только админ.")
        return

    if user_id in temp_storage and "photo" in temp_storage[user_id]:
        temp_storage[user_id]["description"] = message.text
        await message.answer("Выбери категорию:", reply_markup=category_keyboard())
    else:
        await message.answer("Чтобы добавить товар, сначала отправь фото.")

@dp.callback_query_handler(lambda c: c.data.startswith('cat_'))
async def handle_category(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    category = callback_query.data.split("_", 1)[1]

    if user_id not in temp_storage:
        await callback_query.answer("Сначала отправь фото и описание товара.")
        return

    catalog = load_catalog()
    item = temp_storage.pop(user_id)
    catalog[category].append(item)
    save_catalog(catalog)

    await callback_query.message.answer("Товар добавлен в категорию ✅")

@dp.message_handler(commands=['каталог'])
async def show_catalog(message: types.Message):
    catalog = load_catalog()
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in CATEGORIES:
        kb.add(InlineKeyboardButton(text=cat, callback_data=f"show_{cat}"))
    await message.answer("Выбери категорию:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('show_'))
async def show_category_items(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_", 1)[1]
    catalog = load_catalog()
    items = catalog.get(category, [])
    if not items:
        await callback_query.message.answer(f"В категории {category} пока нет товаров.")
        return

    for idx, item in enumerate(items):
        await callback_query.message.answer_photo(
            photo=item["photo"],
            caption=item["description"],
            reply_markup=order_button(category, idx)
        )

@dp.callback_query_handler(lambda c: c.data.startswith('order_'))
async def handle_order(callback_query: types.CallbackQuery):
    _, cat, idx = callback_query.data.split("_")
    idx = int(idx)
    catalog = load_catalog()
    item = catalog[cat][idx]

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Новый запрос на заказ:
Категория: {cat}
Описание: {item['description']}
От: @{callback_query.from_user.username}"
    )
    await bot.send_photo(
        ADMIN_ID,
        photo=item["photo"]
    )
    await callback_query.message.answer("📩 Вас перенаправляют к продавцу для оформления заказа.")
    await callback_query.message.answer(f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
