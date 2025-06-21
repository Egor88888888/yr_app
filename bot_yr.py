import asyncio
import json
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
# Получаем токен бота и ID администратора из переменных окружения для безопасности.
TOKEN = os.environ.get("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# Включаем логирование, чтобы видеть информацию о работе бота в консоли.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Эта функция вызывается, когда пользователь отправляет команду /start.
    Она отправляет приветственное сообщение.
    """
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}!\n\n"
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг и оставить заявку, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Эта функция обрабатывает данные, полученные от Mini App.
    Она отправляет ответ пользователю и уведомление администратору.
    """
    user = update.effective_user
    data = {}
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"Получены данные от пользователя {user.first_name} ({user.id}): {data}")
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON от Web App")
        await update.message.reply_text("Произошла ошибка при обработке вашей заявки. Пожалуйста, попробуйте снова.")
        return

    # --- 1. Отправляем подтверждение пользователю ---
    await update.message.reply_text(
        text="✅ *Спасибо, ваша заявка принята!* \n\nНаш юрист скоро свяжется с вами.",
        parse_mode='Markdown'
    )
    
    # --- 2. Отправляем уведомление администратору (@dEgor88) ---
    if not ADMIN_CHAT_ID:
        logger.warning("Переменная окружения ADMIN_CHAT_ID не установлена. Уведомление не будет отправлено.")
        return

    try:
        # Формируем красивое и подробное сообщение для администратора.
        problems_text = ", ".join(data.get('problems', ['Не указаны']))
        
        admin_message = (
            f"🔔 *Новая заявка с Mini App!*\n\n"
            f"👤 *Отправитель:*\n"
            f"Имя: *{data.get('name', 'Не указано')}*\n"
            f"Телефон: `{data.get('phone', 'Не указан')}`\n"
            f"Пользователь TG: {user.mention_markdown_v2()}\n\n"
            f"📋 *Проблемы клиента:*\n`{problems_text}`\n\n"
            f"📝 *Описание:*\n"
            f"{data.get('description', 'Не заполнено')}"
        )

        # Отправляем сообщение администратору.
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode='MarkdownV2'
        )
        logger.info(f"Уведомление успешно отправлено администратору {ADMIN_CHAT_ID}")

    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")


async def main() -> None:
    """Основная функция для запуска бота."""
    if not TOKEN:
        logger.critical("Переменная окружения YOUR_BOT_TOKEN не найдена! Бот не может быть запущен.")
        return
        
    application = Application.builder().token(TOKEN).build()

    # ВАЖНО: Принудительно очищаем очередь обновлений и отключаем любые "зависшие" подключения
    logger.info("Force-clearing pending updates and any lingering webhook...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    print("Бот запущен в режиме polling и готов принимать заявки...")
    # Запускаем бота
    await application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    # Используем asyncio.run() для запуска асинхронной функции main
    asyncio.run(main())
