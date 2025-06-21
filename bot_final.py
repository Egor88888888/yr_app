import asyncio
import json
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
# Render предоставляет URL нашего сервиса в этой переменной
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ОБРАБОТЧИКИ (без изменений) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}!\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = {}
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"Получены данные от пользователя {user.first_name} ({user.id}): {data}")
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON от Web App")
        await update.message.reply_text("Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте снова.")
        return

    try:
        await update.message.reply_text(
            text="✅ *Спасибо, ваша заявка принята!* \n\nНаш юрист скоро свяжется с вами.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Не удалось отправить подтверждение пользователю: {e}")

    if not ADMIN_CHAT_ID:
        logger.warning("Переменная окружения ADMIN_CHAT_ID не установлена. Уведомление не будет отправлено.")
        return

    try:
        def escape_markdown(text: str) -> str:
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return "".join(f"\\{char}" if char in escape_chars else char for char in str(text))

        name = escape_markdown(data.get('name', 'Не указано'))
        phone = escape_markdown(data.get('phone', 'Не указан'))
        problems_text = escape_markdown(", ".join(data.get('problems', ['Не указаны'])))
        description = escape_markdown(data.get('description', 'Не заполнено'))
        user_mention = user.mention_markdown_v2()

        admin_message = (
            f"🔔 *Новая заявка с Mini App*\\!\n\n"
            f"👤 *Отправитель:*\n"
            f"Имя: *{name}*\n"
            f"Телефон: `{phone}`\n"
            f"Пользователь TG: {user_mention}\n\n"
            f"📋 *Проблемы клиента:*\n`{problems_text}`\n\n"
            f"📝 *Описание:*\n"
            f"{description}"
        )
        
        logger.info(f"Попытка отправить уведомление администратору {ADMIN_CHAT_ID}...")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode='MarkdownV2'
        )
        logger.info(f"Уведомление УСПЕШНО отправлено администратору.")

    except TelegramError as e:
        logger.error(f"Telegram API Error: Не удалось отправить уведомление администратору. Ошибка: {e.message}")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {type(e).__name__} - {e}")


def main() -> None:
    """Основная функция для запуска бота через вебхук."""
    if not TOKEN:
        logger.critical("Переменная окружения YOUR_BOT_TOKEN не найдена!")
        return
        
    # Создаем приложение
    # Указываем путь, на который Telegram будет отправлять обновления
    # Это более надежно, чем передавать токен в URL
    application = Application.builder().token(TOKEN).arbitrary_callback_data(True).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Запускаем приложение в режиме вебхука
    # Эта встроенная функция сама установит вебхук и запустит веб-сервер
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Бот будет запущен в режиме webhook на порту {port}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN, # Путь, который будет частью нашего URL
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}" # Полный URL для регистрации в Telegram
    )


if __name__ == "__main__":
    main()

