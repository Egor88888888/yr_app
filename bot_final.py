import json
import logging
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
# Используем переменную окружения для Railway
# Railway автоматически предоставляет этот URL, если домен сгенерирован
RAILWAY_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN")


# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с маркером версии."""
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}! (v4.3)\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из веб-приложения"""
    logger.info("--- v4.3: ЗАПУЩЕНА ФУНКЦИЯ WEB_APP_DATA ---")
    # ... (логика обработки заявки) ...
    user = update.effective_user
    data = json.loads(update.effective_message.web_app_data.data)
    
    await update.message.reply_text("✅ Спасибо, ваша заявка принята!")

    if ADMIN_CHAT_ID:
        try:
            problems_text = ", ".join(data.get('problems', ['Не указаны']))
            admin_message = (
                f"🔔 Новая заявка (v4.3)!\n"
                f"От: {data.get('name', 'Не указано')} ({user.id})\n"
                f"Телефон: {data.get('phone', 'Не указан')}\n"
                f"Проблемы: {problems_text}\n\n"
                f"Описание: {data.get('description', 'Не заполнено')}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
            logger.info("v4.3 | Уведомление УСПЕШНО отправлено администратору.")
        except Exception as e:
            logger.error(f"v4.3 | ОШИБКА при отправке уведомления администратору: {e}")


def main() -> None:
    """Основная функция для запуска бота."""
    if not TOKEN:
        logger.critical("ОШИБКА ЗАПУСКА: Переменная окружения YOUR_BOT_TOKEN не найдена!")
        return

    # --- НОВАЯ ДИАГНОСТИКА ---
    logger.info(f"Проверка переменной RAILWAY_PUBLIC_DOMAIN. Полученное значение: '{RAILWAY_URL}'")

    if not RAILWAY_URL:
        logger.critical("ОШИБКА ЗАПУСКА: Переменная RAILWAY_PUBLIC_DOMAIN не найдена! Убедитесь, что она добавлена в 'Variables' и что для сервиса сгенерирован домен в 'Settings' -> 'Networking'.")
        return
        
    webhook_full_url = f"https://{RAILWAY_URL}/{TOKEN}"
    logger.info(f"Полный URL для вебхука: {webhook_full_url}")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Бот (v4.3) будет запущен в режиме webhook на порту {port}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_full_url
    )


if __name__ == "__main__":
    main()
