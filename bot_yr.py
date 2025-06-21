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
        f"Здравствуйте, {user.mention_html()}! (v3.1)\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из веб-приложения"""
    logger.info("--- ЗАПУЩЕНА ФУНКЦИЯ WEB_APP_DATA (v3.1) ---")
    user = update.effective_user
    
    # --- ШАГ 1: Попытка отправить предварительное уведомление ---
    try:
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🔔 Получена новая заявка от пользователя {user.id}. Начинаю обработку..."
            )
            logger.info("Предварительное уведомление администратору отправлено.")
        else:
            logger.warning("ADMIN_CHAT_ID не найден, предварительное уведомление пропущено.")
    except Exception as e:
        logger.error(f"ОШИБКА при отправке предварительного уведомления: {e}")

    # --- ШАГ 2: Обработка данных ---
    data = {}
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"Данные успешно декодированы: {data}")
    except json.JSONDecodeError:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось декодировать JSON от Web App")
        await update.message.reply_text("Произошла ошибка при обработке вашей заявки (код 1). Пожалуйста, попробуйте снова.")
        return

    # --- ШАГ 3: Отправка подтверждения клиенту ---
    try:
        await update.message.reply_text(
            text="✅ *Спасибо, ваша заявка принята!* \n\nНаш юрист скоро свяжется с вами.",
            parse_mode='Markdown'
        )
        logger.info("Подтверждение успешно отправлено пользователю.")
    except Exception as e:
        logger.error(f"ОШИБКА: Не удалось отправить подтверждение пользователю: {e}")

    # --- ШАГ 4: Отправка финального уведомления администратору ---
    if not ADMIN_CHAT_ID:
        return

    try:
        problems_text = ", ".join(data.get('problems', ['Не указаны']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не заполнено')

        admin_message = (
            f"✅ Детали заявки:\n\n"
            f"Отправитель: {name}\n"
            f"Телефон: {phone}\n"
            f"Проблемы: {problems_text}\n\n"
            f"Описание:\n{description}"
        )
        logger.info("Финальное сообщение для администратора успешно сформировано.")
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message
        )
        logger.info(f"Финальное уведомление УСПЕШНО отправлено администратору.")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при отправке финального уведомления администратору: {e}")


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
