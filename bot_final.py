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
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

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
        f"Здравствуйте, {user.mention_html()}! (v4.0)\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из веб-приложения"""
    logger.info("--- v4.0: ЗАПУЩЕНА ФУНКЦИЯ WEB_APP_DATA ---")
    user = update.effective_user
    
    # --- ШАГ 1: Отправка подтверждения клиенту ---
    try:
        await update.message.reply_text("✅ Спасибо, ваша заявка принята! Скоро свяжемся с вами.")
        logger.info("v4.0 | ШАГ 1: Подтверждение успешно отправлено пользователю.")
    except Exception as e:
        logger.error(f"v4.0 | ОШИБКА на ШАГЕ 1 (ответ клиенту): {e}")
        # Если не можем ответить клиенту, нет смысла продолжать
        return

    # --- ШАГ 2: Проверка наличия ADMIN_CHAT_ID ---
    if not ADMIN_CHAT_ID:
        logger.warning("v4.0 | ШАГ 2: Переменная ADMIN_CHAT_ID не найдена. Уведомление не будет отправлено.")
        return
    logger.info(f"v4.0 | ШАГ 2: ADMIN_CHAT_ID найден ({ADMIN_CHAT_ID}).")

    # --- ШАГ 3: Обработка и формирование сообщения для админа ---
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"v4.0 | ШАГ 3: Данные успешно декодированы: {data}")

        problems_text = ", ".join(data.get('problems', ['Не указаны']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не заполнено')
        user_id = user.id

        admin_message = (
            f"🔔 Новая заявка (v4.0)!\n\n"
            f"Отправитель: {name}\n"
            f"Телефон: {phone}\n"
            f"ID Пользователя: {user_id}\n\n"
            f"Проблемы: {problems_text}\n\n"
            f"Описание:\n{description}"
        )
        logger.info("v4.0 | ШАГ 3: Сообщение для администратора успешно сформировано.")
    except Exception as e:
        logger.error(f"v4.0 | КРИТИЧЕСКАЯ ОШИБКА на ШАГЕ 3 (обработка данных): {e}")
        # Отправляем админу уведомление об ошибке, если можем
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Ошибка обработки заявки от {user.id}: {e}")
        return

    # --- ШАГ 4: Отправка финального уведомления администратору ---
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message
        )
        logger.info(f"v4.0 | ШАГ 4: Уведомление УСПЕШНО отправлено администратору.")
    except Exception as e:
        logger.error(f"v4.0 | КРИТИЧЕСКАЯ ОШИБКА на ШАГЕ 4 (отправка админу): {e}")


def main() -> None:
    """Основная функция для запуска бота."""
    if not TOKEN:
        logger.critical("Переменная окружения YOUR_BOT_TOKEN не найдена!")
        return
        
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Бот (v4.0) будет запущен в режиме webhook на порту {port}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )


if __name__ == "__main__":
    main()
