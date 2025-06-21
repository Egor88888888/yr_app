#!/usr/bin/env python3
"""
РАБОЧАЯ версия бота с GitHub Pages
"""
import json
import logging
import os
import asyncio
from telegram import Update, WebAppInfo, MenuButton, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_web_app(application: Application) -> None:
    """Настройка веб-приложения с GitHub Pages"""
    try:
        # ИСПОЛЬЗУЕМ GITHUB PAGES ПРАВИЛЬНО
        web_app_url = "https://egor88888888.github.io/yr_app/"
        web_app = WebAppInfo(url=web_app_url)
        menu_button = MenuButtonWebApp(
            text="📝 Оставить заявку", web_app=web_app)

        await application.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Веб-приложение настроено: {web_app_url}")
    except Exception as e:
        logger.error(f"❌ Ошибка настройки веб-приложения: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Стартовое сообщение"""
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}! 🏛️\n\n"
        "Я ваш юридический помощник по страховым вопросам.\n"
        "Нажмите кнопку меню для подачи заявки."
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка заявки"""
    logger.info("🎯 ПОЛУЧЕНА ЗАЯВКА ОТ ВЕБА!")
    user = update.effective_user

    if not update.effective_message or not update.effective_message.web_app_data:
        logger.error("❌ Нет данных веб-приложения!")
        return

    logger.info(f"📄 Данные: {update.effective_message.web_app_data.data}")

    try:
        await update.message.reply_text("✅ Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.")
        logger.info("✅ Ответ клиенту отправлен")
    except Exception as e:
        logger.error(f"❌ Ошибка ответа клиенту: {e}")
        return

    if not ADMIN_CHAT_ID:
        logger.warning("⚠️ ADMIN_CHAT_ID не настроен!")
        return

    try:
        data = json.loads(update.effective_message.web_app_data.data)
        problems = ", ".join(data.get('problems', ['Не указано']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не указано')

        admin_message = f"""🔔 НОВАЯ ЗАЯВКА!

👤 Клиент: {name} (ID: {user.id})
📞 Телефон: {phone}
⚠️ Проблемы: {problems}

📝 Описание ситуации:
{description}

⏰ Время: {update.effective_message.date}"""

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        logger.info("✅ Заявка отправлена администратору!")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки администратору: {e}")
        import traceback
        traceback.print_exc()


async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для отладки всех сообщений"""
    logger.info(
        f"📨 Получено сообщение от пользователя {update.effective_user.id}")
    logger.info(f"📨 Тип сообщения: {type(update.message)}")
    logger.info(f"📨 Содержимое: {update.message}")

    if update.message and hasattr(update.message, 'web_app_data'):
        logger.info(
            f"🌐 Атрибут web_app_data существует: {update.message.web_app_data}")
        if update.message.web_app_data:
            logger.info(
                f"🌐 WEB APP DATA найдена: {update.message.web_app_data.data}")
        else:
            logger.info("🌐 web_app_data None")
    else:
        logger.info("🌐 web_app_data атрибут отсутствует")


def main():
    """Запуск бота"""
    if not TOKEN:
        logger.critical("❌ YOUR_BOT_TOKEN не найден в переменных окружения!")
        return

    if ADMIN_CHAT_ID:
        logger.info(f"✅ ADMIN_CHAT_ID настроен: {ADMIN_CHAT_ID}")
    else:
        logger.warning(
            "⚠️ ADMIN_CHAT_ID не настроен! Заявки не будут приходить.")

    application = Application.builder().token(TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, debug_all_messages))

    # Настройка веб-приложения
    try:
        asyncio.get_event_loop().run_until_complete(setup_web_app(application))
    except Exception as e:
        logger.error(f"❌ Ошибка настройки веб-приложения: {e}")

    logger.info("🚀 Запуск ИСПРАВЛЕННОГО бота...")

    # Используем webhook для Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        MY_PUBLIC_URL = os.environ.get("MY_RAILWAY_PUBLIC_URL")
        if MY_PUBLIC_URL:
            webhook_url = f"https://{MY_PUBLIC_URL}/{TOKEN}"
            port = int(os.environ.get('PORT', 8080))
            logger.info(f"🌐 Webhook: {webhook_url}")
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=TOKEN,
                webhook_url=webhook_url
            )
        else:
            logger.error("❌ MY_RAILWAY_PUBLIC_URL не найден!")
    else:
        # Локальный запуск
        logger.info("🏠 Локальный режим polling")
        application.run_polling()


if __name__ == "__main__":
    main()
