import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiohttp import web

# -------------------------------------------------------------------
# КОНФИГУРАЦИЯ БОТА ПОД УКРАИНУ
# -------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PRICE_UAH = 149                         # Оптимальная цена полного разбора в гривнах (UAH)

if not BOT_TOKEN:
    logging.warning("⚠️ Внимание: BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

clients_db = {}


# -------------------------------------------------------------------
# ЛОГИКА РАСЧЁТА (Матрица Судьбы - 22 Аркана)
# -------------------------------------------------------------------
def calculate_arcanum(number: int) -> int:
    while number > 22:
        number = sum(int(digit) for digit in str(number))
    return number

def process_matrix(birth_date_str: str) -> dict:
    day, month, year = map(int, birth_date_str.split('.'))
    
    arc_day = calculate_arcanum(day)
    arc_month = calculate_arcanum(month)
    arc_year = calculate_arcanum(year)
    arc_center = calculate_arcanum(arc_day + arc_month + arc_year)
    
    return {
        "day": arc_day,
        "month": arc_month,
        "year": arc_year,
        "center": arc_center
    }


# -------------------------------------------------------------------
# 1. СТАРТ
# -------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    ref_code = None
    if len(args) > 1:
        ref_code = args[1]

    if user_id not in clients_db:
        clients_db[user_id] = {
            "ref_code": ref_code,
            "birth_date": None,
            "has_paid": False
        }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Розрахувати Матрицю Долі", callback_data="start_calc")]
    ])
    
    await message.answer(
        f"✨ **Привіт, {message.from_user.first_name}!**\n\n"
        "Я допоможу тобі розшифрувати твою **Матрицю Долі** всього за 1 хвилину.\n\n"
        "Дізнайся про свої приховані таланти, фінансовий код та головний кармічний блок, "
        "який заважає вийти на новий рівень доходів.\n\n"
        "👇 Натисни кнопку нижче, щоб розпочати:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# -------------------------------------------------------------------
# 2. ЗБІР ДАТИ НАРОВОДЖЕННЯ
# -------------------------------------------------------------------
@dp.callback_query(F.data == "start_calc")
async def ask_birthdate(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 **Введи свою дату народження** у форматі `ДД.ММ.РРРР`\n"
        "*(Наприклад: 14.05.1998)*",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(F.text.regexp(r'^\d{2}\.\d{2}\.\d{4}$'))
async def process_date(message: Message):
    user_id = message.from_user.id
    birth_date = message.text
    
    try:
        datetime.strptime(birth_date, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Некоректна дата. Напиши у форматі `ДД.ММ.РРРР` (наприклад: 14.05.1998)")
        return

    if user_id in clients_db:
        clients_db[user_id]["birth_date"] = birth_date

    matrix = process_matrix(birth_date)

    msg = await message.answer("⏳ *Триває розрахунок арканів та матриці долі...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await msg.edit_text("🔍 *Аналіз фінансового каналу та кармічного вузла...*", parse_mode="Markdown")
    await asyncio.sleep(2)

    teaser_text = (
        f"✅ **Розрахунок для дати {birth_date} завершено!**\n\n"
        f"👑 **Твій Головний Аркан:** `{matrix['day']}`\n"
        f"💰 **Аркан Фінансового Каналу:** `{matrix['year']}`\n\n"
        "📌 **Короткий тизер розбору:**\n"
        f"• Ти маєш потужний потенціал за арканом `{matrix['day']}`, але твій фінансовий канал (`{matrix['year']}`) "
        "зараз перебуває у **перекритому стані**.\n"
        "• Головна причина — непророблена родова карма та блоки у сприйнятті грошей.\n\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "🔥 **У повному розборі на 12 сторінок ти дізнаєшся:**\n"
        "1. Повний фінансовий код та сфери з максимальним доходом.\n"
        "2. Кармічні блоки та як їх зняти за 3 простих кроки.\n"
        "3. Прогноз долених подій на 2026–2027 роки.\n"
        "4. Ідеальну сумісність у коханні та бізнесі.\n\n"
        f"🏷 **Спеціальна ціна:** ~~800 грн.~~ 👉 **{PRICE_UAH} грн.**\n"
        "⏱ *Знижка діє тільки 15 хвилин!*"
    )

    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Отримати повний розбір ({PRICE_UAH} грн)", callback_data="buy_report")]
    ])

    await msg.edit_text(teaser_text, parse_mode="Markdown", reply_markup=pay_keyboard)


# -------------------------------------------------------------------
# 3. ВИДАЧА ПЛАТНОГО ПРОДУКТУ
# -------------------------------------------------------------------
@dp.callback_query(F.data == "buy_report")
async def process_payment(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = clients_db.get(user_id, {})
    
    clients_db[user_id]["has_paid"] = True
    
    birth_date = user_data.get("birth_date", "14.05.1998")
    matrix = process_matrix(birth_date)

    paid_report_text = (
        "🎉 **Дякуємо за покупку! Твій повний розбір готовий.**\n\n"
        f"📊 **Аналіз Матриці для {birth_date}:**\n"
        f"• Аркан Особистості (Центр): `{matrix['center']}`\n"
        f"• Особистий Талант: `{matrix['month']}`\n"
        f"• Фінансовий Ключ: `{matrix['year']}`\n\n"
        "📖 **1. Фінансовий потенціал:**\n"
        "Твій ключ до успіху полягає в комунікації та делегуванні. "
        "Не намагайся робити все самостійно. Твоя енергія розкривається у партнерстві.\n\n"
        "🔮 **2. Прогноз на 2026–2027 роки:**\n"
        "Період сильної трансформації. Сприятливий час для запуску власних проектів, "
        "зміни сфери діяльності та інвестицій у нові навички.\n\n"
        "📜 *(Тут надсилається повний розбір у форматі тексту або підкріплюється готовий PDF-файл)*"
    )

    await callback.message.edit_text(paid_report_text, parse_mode="Markdown")
    await callback.answer()


# -------------------------------------------------------------------
# МИНИ-ВЕБ-СЕРВЕР ДЛЯ РАБОТЫ НА БЕСПЛАТНОМ ТАРИФЕ RENDER (Web Service)
# -------------------------------------------------------------------
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")


# -------------------------------------------------------------------
# ЗАПУСК
# -------------------------------------------------------------------
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Клієнтський бот (Україна) запущений!")
    
    # Запускаем веб-сервер для Render Web Service
    await start_web_server()
    
    # Запускаем поллинг бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
