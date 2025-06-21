import asyncio
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
TOKEN = os.environ.get("YOUR_BOT_TOKEN")

# --- КОНФИГУРАЦИЯ ---
# Вставьте сюда API-токен вашего бота, полученный от @BotFather.
# ВАЖНО: В реальном проекте храните токен в безопасности, например, в переменных окружения.


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
        "Я ваш личный юридический помощник. Чтобы посмотреть каталог услуг, "
        "нажмите на кнопку 'Меню' слева от поля ввода текста.",
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Эта функция обрабатывает данные, полученные от Mini App.
    """
    # Данные приходят в формате JSON, но как строка. Преобразуем их в объект Python.
    data = json.loads(update.effective_message.web_app_data.data)
    user = update.effective_user
    
    logger.info(f"Получены данные от пользователя {user.first_name} ({user.id}): {data}")
    
    # Формируем красивое иформативное ответное сообщение.
    # Используем Markdown для форматирования текста (жирный, курсив и т.д.).
    reply_text = "✅ *Ваш заказ принят!*\n\n"
    reply_text += "Спасибо! Мы получили вашу заявку и скоро свяжемся с вами для уточнения деталей.\n\n"
    reply_text += "*Детали заказа:*\n"
    
    # В цикле перебираем все заказанные услуги из полученных данных.
    for service in data.get('services', []):
        # Форматируем цену, чтобы она выглядела красиво (например, 10 000 ₽).
        price_str = f"{service.get('price', 0):,} ₽".replace(',', ' ')
        reply_text += f"• {service.get('name', 'Неизвестная услуга')}: *{price_str}*\n"
    
    # Добавляем общую стоимость в конец сообщения.
    total_price_str = f"{data.get('totalPrice', 0):,} ₽".replace(',', ' ')
    reply_text += f"\n*Итого к оплате: {total_price_str}*"
    
    # Отправляем итоговое сообщение пользователю.
    await update.message.reply_text(
        text=reply_text,
        parse_mode='Markdown'
    )

def main() -> None:
    """Основная функция для запуска бота."""
    
    # Создаем объект Application и передаем ему токен бота.
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики: один для команды /start, другой для данных от Mini App.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Запускаем бота. Он будет постоянно опрашивать Telegram на наличие новых сообщений.
    # Этот режим (polling) - самый простой для тестирования и небольших проектов.
    print("Бот запущен и готов принимать заказы...")
    application.run_polling()


if __name__ == "__main__":
    main()
