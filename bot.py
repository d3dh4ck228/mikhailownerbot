import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

# ============ ВАШИ НАСТРОЙКИ ============
BOT_TOKEN = "9158873028:AAHxl7b87R62J1Y2LPeUpAQIkXKQKyvCh6s"
ADMIN_ID  = 7552760595
# =======================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния формы
class Form(StatesGroup):
    messenger = State()
    phone     = State()
    currency  = State()

MESSENGERS = ["WhatsApp", "Viber", "Telegram", "IMO", "MAX"]
CURRENCIES = ["RUB ₽", "USD $", "EUR €", "UAH ₴", "KZT ₸", "BYN Br", "GBP £", "TRY ₺", "CNY ¥", "AED د.إ"]

# ---------- /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Сделать заявку", callback_data="start_form")]
    ])
    await message.answer(
        "👋 Привет!\n\n"
        "Это бот для оформления заявки.\n"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=kb,
    )

# ---------- Шаг 1: мессенджер ----------
@dp.callback_query(F.data == "start_form")
async def choose_messenger(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.messenger)
    rows = [[InlineKeyboardButton(text=m, callback_data=f"msg:{m}")] for m in MESSENGERS]
    await callback.message.edit_text(
        "📱 <b>Шаг 1 из 3</b>\n\nВыбери мессенджер:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await callback.answer()

@dp.callback_query(Form.messenger, F.data.startswith("msg:"))
async def save_messenger(callback: CallbackQuery, state: FSMContext):
    messenger = callback.data.split(":", 1)[1]
    await state.update_data(messenger=messenger)
    await state.set_state(Form.phone)

    # ReplyKeyboard с кнопкой "Поделиться контактом" + отмена
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="✍️ Ввести вручную")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.edit_text(
        f"✅ Мессенджер: <b>{messenger}</b>\n\n"
        f"📞 <b>Шаг 2 из 3</b>\n\n"
        f"Отправь свой номер телефона — нажми кнопку ниже, чтобы поделиться контактом, "
        f"или введи вручную в формате <code>+7 999 123-45-67</code>.",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()

# ---------- Шаг 2: телефон ----------
@dp.message(Form.phone, F.contact)
async def save_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await ask_currency(message, state)

@dp.message(Form.phone, F.text)
async def save_phone_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "📲 Поделиться контактом":
        await message.answer("Нажми на кнопку «Поделиться контактом» под полем ввода 👇")
        return
    if text == "✍️ Ввести вручную":
        await message.answer("Введи номер в формате <code>+7 999 123-45-67</code>:", parse_mode="HTML")
        return

    digits = "".join(c for c in text if c.isdigit())
    if len(digits) < 6:
        await message.answer("❌ Слишком короткий номер. Попробуй ещё раз.")
        return

    await state.update_data(phone=text)
    await ask_currency(message, state)

async def ask_currency(message: Message, state: FSMContext):
    await state.set_state(Form.currency)
    rows = [[InlineKeyboardButton(text=c, callback_data=f"cur:{c}")] for c in CURRENCIES]
    await message.answer(
        "💱 <b>Шаг 3 из 3</b>\n\nВыбери валюту:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

# ---------- Шаг 3: валюта → отправка ----------
@dp.callback_query(Form.currency, F.data.startswith("cur:"))
async def save_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":", 1)[1]
    data = await state.get_data()
    await state.clear()

    messenger = data.get("messenger", "—")
    phone     = data.get("phone", "—")
    now       = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    # Заявка админу
    lead = (
        "🔐 <b>НОВАЯ ЗАЯВКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Мессенджер: <b>{messenger}</b>\n"
        f"📞 Номер: <code>{phone}</code>\n"
        f"💱 Валюта: <b>{currency}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {now}\n\n"
        f"👤 От: @{callback.from_user.username or callback.from_user.id} "
        f"(ID: <code>{callback.from_user.id}</code>)"
    )

    try:
        await bot.send_message(ADMIN_ID, lead, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить админу: {e}")

    # Ответ пользователю
    await callback.message.edit_text(
        "✅ <b>Заявка принята!</b>\n\n"
        "Мы свяжемся с тобой в ближайшее время.",
        parse_mode="HTML",
    )
    await callback.message.answer("Спасибо! 🙌", reply_markup=ReplyKeyboardRemove())
    await callback.answer("Готово!")

# ---------- Запуск ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())