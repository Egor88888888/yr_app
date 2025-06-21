import json
import logging
import os
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
    """
    Отправляет приветственное сообщение с маркером версии.
    """
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}! (v3.0)\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из веб-приложения"""
    user = update.effective_user
    data = {}
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"ШАГ 1: Получены данные от пользователя {user.first_name} ({user.id}): {data}")
    except json.JSONDecodeError:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось декодировать JSON от Web App")
        await update.message.reply_text("Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте снова.")
        return

    try:
        await update.message.reply_text(
            text="✅ *Спасибо, ваша заявка принята!* \n\nНаш юрист скоро свяжется с вами.",
            parse_mode='Markdown'
        )
        logger.info("ШАГ 2: Подтверждение успешно отправлено пользователю.")
    except Exception as e:
        logger.error(f"ОШИБКА: Не удалось отправить подтверждение пользователю: {e}")

    if not ADMIN_CHAT_ID:
        logger.warning("ШАГ 3: Переменная ADMIN_CHAT_ID не найдена. Уведомление не будет отправлено.")
        return
    
    logger.info("ШАГ 3: Переменная ADMIN_CHAT_ID найдена. Начинаю отправку уведомления.")

    try:
        problems_text = ", ".join(data.get('problems', ['Не указаны']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не заполнено')
        user_id = user.id

        admin_message = (
            f"🔔 Новая заявка!\n\n"
            f"Отправитель: {name}\n"
            f"Телефон: {phone}\n"
            f"ID Пользователя: {user_id}\n\n"
            f"Проблемы: {problems_text}\n\n"
            f"Описание:\n{description}"
        )
        logger.info(f"ШАГ 4: Сообщение для администратора успешно сформировано. Текст: {admin_message}")
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message
        )
        logger.info(f"ШАГ 5: Уведомление УСПЕШНО отправлено администратору ({ADMIN_CHAT_ID}).")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА на ШАГЕ 5 при отправке уведомления администратору: {type(e).__name__} - {e}")


def main() -> None:
    if not TOKEN:
        logger.critical("Переменная окружения YOUR_BOT_TOKEN не найдена!")
        return
        
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Бот будет запущен в режиме webhook на порту {port}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )


if __name__ == "__main__":
    main()

