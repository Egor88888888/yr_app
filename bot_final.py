import json
import logging
import os
import asyncio
from telegram import Update, WebAppInfo, MenuButton, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
# ИСПОЛЬЗУЕМ НАШУ УНИКАЛЬНУЮ ПЕРЕМЕННУЮ ДЛЯ ПУБЛИЧНОГО АДРЕСА
MY_PUBLIC_URL = os.environ.get("MY_RAILWAY_PUBLIC_URL")

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ОБРАБОТЧИКИ ---


async def setup_web_app(application: Application) -> None:
    """Настройка веб-приложения с кнопкой меню"""
    try:
        web_app_url = f"https://{MY_PUBLIC_URL}/index.html"
        web_app = WebAppInfo(url=web_app_url)
        menu_button = MenuButtonWebApp(
            text="📝 Оставить заявку", web_app=web_app)

        await application.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"Веб-приложение настроено: {web_app_url}")
    except Exception as e:
        logger.error(f"Ошибка настройки веб-приложения: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с маркером версии."""
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}! (v6.0)\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из веб-приложения"""
    logger.info("--- v6.0: Получена заявка, начинаю обработку ---")
    user = update.effective_user

    try:
        await update.message.reply_text("✅ Спасибо, ваша заявка принята! Скоро свяжемся с вами.")
        logger.info("v6.0 | Ответ клиенту отправлен.")
    except Exception as e:
        logger.error(f"v6.0 | ОШИБКА при ответе клиенту: {e}")
        return

    if not ADMIN_CHAT_ID:
        logger.warning(
            "v6.0 | ADMIN_CHAT_ID не найден. Уведомление не будет отправлено.")
        return

    try:
        data = json.loads(update.effective_message.web_app_data.data)
        problems_text = ", ".join(data.get('problems', ['Не указаны']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не заполнено')

        admin_message = (
            f"🔔 Новая заявка (v6.0)!\n\n"
            f"От: {name} (ID: {user.id})\n"
            f"Телефон: {phone}\n"
            f"Проблемы: {problems_text}\n\n"
            f"Описание:\n{description}"
        )

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        logger.info("v6.0 | Уведомление УСПЕШНО отправлено администратору.")
    except Exception as e:
        logger.error(
            f"v6.0 | КРИТИЧЕСКАЯ ОШИБКА при отправке уведомления администратору: {e}")


def main() -> None:
    """Основная функция для запуска бота."""
    if not TOKEN:
        logger.critical(
            "ОШИБКА ЗАПУСКА: Переменная YOUR_BOT_TOKEN не найдена!")
        return

    if not MY_PUBLIC_URL:
        logger.critical(
            "ОШИБКА ЗАПУСКА: Переменная MY_RAILWAY_PUBLIC_URL не найдена! Убедитесь, что она добавлена в 'Variables'.")
        return

    webhook_full_url = f"https://{MY_PUBLIC_URL}/{TOKEN}"
    logger.info(f"Полный URL для вебхука: {webhook_full_url}")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    # Настройка веб-приложения
    asyncio.get_event_loop().run_until_complete(setup_web_app(application))

    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Бот (v6.0) будет запущен в режиме webhook на порту {port}")

    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_full_url
    )


if __name__ == "__main__":
    main()
