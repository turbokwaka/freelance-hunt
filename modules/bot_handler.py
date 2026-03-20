"""
bot_handler.py — Persistent Telegram bot handler.
Run this script as a separate process: python modules/bot_handler.py

Handles the "Згенерувати відповідь" inline button:
1. Asks the user to send extra text (or /skip)
2. Calls Gemini with BASE_PROMPT + ad details + optional user text
3. Sends the generated proposal back
"""

import os
import sys
from pprint import pprint

import django

from .load_django import *

from parser_app.models import Ad

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai
from asgiref.sync import sync_to_async

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_PROMPT = ("""
Ти досвідчений фрилансер, Python-розробник, який спеціалізується на парсингу веб-сайтів (веб-скрапінгу) та створенні ботів. На основі опису проєкту нижче напиши коротку, переконливу і реалістичну ставку замовнику.

ТВОЇ ПРАВИЛА ТА СТИЛЬ:
1. Привітайся (якщо в даних є ім'я замовника, звернись на ім'я).
2. Пиши лаконічно, "без води" та корпоративного пафосу. Тон: впевнений, професійний, але живий.
3. Одразу згадуй релевантний досвід (наприклад: парсинг інтернет-магазинів, вивантаження в Google Sheets/Excel, створення Telegram-ботів).
4. Зазначай стек технологій, який плануєш використати (наприклад: Python, BeautifulSoup4, aiohttp, curl_cffi для обходу анти-бот систем, Google Sheets API).
5. Будь реалістом: якщо для точної оцінки треба побачити сайти-донори, прямо скажи про це.
6. Завершуй закликом до дії (наприклад, пропозицією обговорити деталі в особистих повідомленнях).

ОСЬ ПРИКЛАДИ ТВІЙОГО ІДЕАЛЬНОГО ТОНУ (орієнтуйся на них):
Приклад 1: Добрий день. Готовий виконати проєкт. Інструмент парсингу залежатиме від сайту, необхідно з ними ознайомитись. Від цього ж залежатиме і ціна - зараз можу вказати лише абсолютний мінімум.
Приклад 2: Вітаю. Маю великий досвід у розробці парсерів для збору даних з інтернет-магазинів, включаючи збір назв товарів, цін, посилань та статусу наявності з вивантаженням у Google Sheets. Працюю з Python. Готовий реалізувати парсер для 3–5 магазинів. Пропоную перейти в особисті повідомлення.
Приклад 3: Вітаю! Недавно писав парсер інтернет-магазинів для моніторингу цін та наявності товарів - робив трекінг змін на сайті та надсилав повідомлення в телеграм-бот. Стек: Python (BeautifulSoup4, FastAPI) та Google Sheets API. У випадку чого розумію, як працюють анти-бот системи на сайтах :)

Адаптуй свою відповідь під конкретний опис проєкту, але зберігай цей вайб.
"""
)

# Налаштування Gemini
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
}
gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config,
    system_instruction="Ти досвідчений фрілансер. Відповідай українською мовою."
)

# ConversationHandler states
WAITING_EXTRA_TEXT = 1

# Temp storage: user_id -> ad_id
pending_generation: dict[int, int] = {}


def is_owner(user_id: int) -> bool:
    return user_id == TELEGRAM_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Дарова")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        if query.message:
            await query.message.reply_text("⛔ Доступ заборонено.")
        return ConversationHandler.END

    data = query.data  # "gen:<ad_id>"
    if not data or not data.startswith("gen:"):
        return ConversationHandler.END

    ad_id = int(data.split(":", 1)[1])
    pending_generation[query.from_user.id] = ad_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустити (базовий промпт)", callback_data=f"skip:{ad_id}")]
    ])

    if query.message:
        await query.message.reply_text(
            "💬 Надішли додатковий текст до промпту (наприклад, свій стек або побажання),\n"
            "або натисни «Пропустити» щоб використати тільки базовий промпт.",
            reply_markup=keyboard,
        )
    return WAITING_EXTRA_TEXT


async def skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return ConversationHandler.END

    data = query.data  # "skip:<ad_id>"
    ad_id = int(data.split(":", 1)[1])
    pending_generation.pop(query.from_user.id, None)

    if query.message:
        await query.message.reply_text("⏳ Генерую відповідь (Gemini)...")
    await _generate_and_send(update.effective_chat.id, ad_id, extra_text="", context=context)
    return ConversationHandler.END


async def receive_extra_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update.effective_user.id):
        return ConversationHandler.END

    ad_id = pending_generation.pop(update.effective_user.id, None)
    if ad_id is None:
        await update.message.reply_text("⚠️ Не знайдено активного запиту. Натисни кнопку знову.")
        return ConversationHandler.END

    extra_text = update.message.text.strip()
    await update.message.reply_text("⏳ Генерую відповідь (Gemini)...")
    await _generate_and_send(update.effective_chat.id, ad_id, extra_text=extra_text, context=context)
    return ConversationHandler.END


async def _generate_and_send(chat_id: int, ad_id: int, extra_text: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        ad = await sync_to_async(Ad.objects.get)(pk=ad_id)
    except Ad.DoesNotExist:
        await context.bot.send_message(chat_id=chat_id, text="❌ Оголошення не знайдено в базі даних.")
        return

    ad_details = (
        f"Назва: {ad.title}\n"
        f"Бюджет: {ad.budget}\n"
        f"Замовник: {ad.employer}\n"
        f"Категорії: {ad.categories}\n"
        f"Опис: {ad.description}\n"
        f"Посилання: {ad.url}"
    )

    full_prompt = BASE_PROMPT
    if extra_text:
        full_prompt += f"\n\nДодатковий контекст від фрілансера:\n{extra_text}"
    full_prompt += f"\n\n---\n{ad_details}"

    try:
        # Асинхронний виклик Gemini
        response = await gemini_model.generate_content_async(full_prompt)
        pprint(response)
        answer = response.text.strip()

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ <b>Згенерована відповідь:</b>\n\n{answer}",
            parse_mode="HTML",
        )
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Помилка Gemini API: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pending_generation.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern=r"^gen:\d+$")],
        states={
            WAITING_EXTRA_TEXT: [
                CallbackQueryHandler(skip_callback, pattern=r"^skip:\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_extra_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))

    print("🤖 Бот запущено. Очікування повідомлень (Gemini Engine)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()