import os
from dotenv import load_dotenv
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_ad_notification(ad_id: int, details: dict):
    """Send a new ad notification to the owner via Telegram."""
    title = details.get("title", "Без назви")
    budget = details.get("budget", "Не вказано")
    employer = details.get("employer", "Не знайдено")
    categories = details.get("categories", "")
    description = details.get("description", "")
    url = details.get("url", "")

    text = (
        f"🆕 <b>Нове оголошення</b>\n\n"
        f"📌 <b>Назва:</b> {title}\n"
        f"💰 <b>Бюджет:</b> {budget}\n"
        f"👤 <b>Замовник:</b> {employer}\n"
        f"📂 <b>Категорії:</b> {categories}\n\n"
        f"📝 <b>Опис:</b> {description}\n\n"
        f"🔗 <a href=\"{url}\">Відкрити проєкт</a>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Згенерувати відповідь", callback_data=f"gen:{ad_id}")]
    ])

    async def _send():
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=False,
        )

    asyncio.run(_send())

