import json
import logging
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ОБРАБОТЧИК ---
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Радикально упрощенный обработчик для финальной диагностики.
    """
    logger.info("--- !!! v5.0 DEBUG HANDLER EXECUTED !!! ---")
    
    if not ADMIN_CHAT_ID:
        logger.error("v5.0 | ADMIN_CHAT_ID is NOT SET. Cannot send notification.")
        return

    try:
        # Просто пересылаем сырые данные администратору
        data_str = update.effective_message.web_app_data.data
        logger.info(f"v5.0 | Received data string: {data_str}")
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"v5.0 DEBUG: Заявка пришла!\n\nДАННЫЕ:\n{data_str}"
        )
        logger.info("v5.0 | DEBUG notification sent to admin.")
        
        # Отвечаем пользователю для подтверждения
        await update.message.reply_text("v5.0: Сервер получил ваши данные.")

    except Exception as e:
        logger.error(f"v5.0 | An error occurred inside web_app_data: {e}", exc_info=True)
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"v5.0 DEBUG: Ошибка в обработчике!\n\n{e}"
            )

def main() -> None:
    """Основная функция для запуска бота."""
    logger.info("--- LAUNCHING BOT v5.0 ---")
    if not TOKEN:
        logger.critical("YOUR_BOT_TOKEN not found!")
        return
        
    application = Application.builder().token(TOKEN).build()
    
    # Оставляем только один, самый важный обработчик
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"v5.0 | Bot will run on port {port}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
