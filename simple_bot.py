#!/usr/bin/env python3
"""
Упрощенная версия бота со встроенным HTML
"""
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

# Встроенный HTML для веб-приложения
WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Страховая справедливость</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
        button { background-color: #007aff; color: white; padding: 15px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; margin-top: 20px; }
        .service-card { border: 2px solid #ccc; padding: 15px; margin: 10px 0; border-radius: 8px; cursor: pointer; }
        .service-card.selected { border-color: #007aff; background-color: #f0f8ff; }
    </style>
</head>
<body>
    <h1>Страховая справедливость</h1>
    <p>Выберите вашу проблему:</p>
    
    <div class="service-card" onclick="toggleService('denial')">
        <h3>🛡️ Отказ в выплате</h3>
        <p>Страховая отказывает в выплате</p>
    </div>
    
    <div class="service-card" onclick="toggleService('underpayment')">
        <h3>📉 Занижение выплаты</h3>
        <p>Выплата меньше реального ущерба</p>
    </div>
    
    <div class="service-card" onclick="toggleService('delay')">
        <h3>⏳ Затягивание сроков</h3>
        <p>Страховая нарушает сроки выплат</p>
    </div>
    
    <div class="form-group">
        <label for="name">Ваше имя:</label>
        <input type="text" id="name" placeholder="Иван Иванов">
    </div>
    
    <div class="form-group">
        <label for="phone">Телефон:</label>
        <input type="tel" id="phone" placeholder="+7 (999) 123-45-67">
    </div>
    
    <div class="form-group">
        <label for="description">Описание проблемы:</label>
        <textarea id="description" rows="4" placeholder="Опишите вашу ситуацию..."></textarea>
    </div>
    
    <button onclick="sendData()">Отправить заявку</button>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        
        let selectedServices = [];
        
        function toggleService(serviceId) {
            const card = event.target.closest('.service-card');
            if (selectedServices.includes(serviceId)) {
                selectedServices = selectedServices.filter(s => s !== serviceId);
                card.classList.remove('selected');
            } else {
                selectedServices.push(serviceId);
                card.classList.add('selected');
            }
        }
        
        function sendData() {
            const name = document.getElementById('name').value;
            const phone = document.getElementById('phone').value;
            const description = document.getElementById('description').value;
            
            if (!name || !phone || selectedServices.length === 0) {
                alert('Пожалуйста, заполните все поля и выберите проблему');
                return;
            }
            
            const data = {
                problems: selectedServices,
                name: name,
                phone: phone,
                description: description
            };
            
            tg.sendData(JSON.stringify(data));
        }
    </script>
</body>
</html>"""

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_web_app(application: Application) -> None:
    """Настройка веб-приложения с кнопкой меню"""
    try:
        # Используем data URL для встроенного HTML
        web_app_url = f"data:text/html;charset=utf-8,{WEBAPP_HTML}"
        web_app = WebAppInfo(
            url="https://telegram.org/demo/webapps")  # Fallback
        menu_button = MenuButtonWebApp(
            text="📝 Оставить заявку", web_app=web_app)

        await application.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Веб-приложение настроено")
    except Exception as e:
        logger.error(f"❌ Ошибка настройки веб-приложения: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Стартовое сообщение"""
    user = update.effective_user
    await update.message.reply_html(
        f"Здравствуйте, {user.mention_html()}! (ПРОСТАЯ ВЕРСИЯ)\n\n"
        "Я ваш юридический помощник. Нажмите кнопку меню для подачи заявки."
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка заявки"""
    logger.info("🎯 ПОЛУЧЕНА ЗАЯВКА!")
    user = update.effective_user

    try:
        await update.message.reply_text("✅ Заявка получена! Свяжемся с вами.")
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

👤 От: {name} (ID: {user.id})
📞 Телефон: {phone}
⚠️ Проблемы: {problems}

📝 Описание:
{description}"""

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        logger.info("✅ Заявка отправлена администратору!")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки администратору: {e}")


def main():
    """Запуск бота"""
    if not TOKEN:
        logger.critical("❌ YOUR_BOT_TOKEN не найден!")
        return

    if ADMIN_CHAT_ID:
        logger.info(f"✅ ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
    else:
        logger.warning("⚠️ ADMIN_CHAT_ID не настроен!")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    # Настройка веб-приложения
    asyncio.get_event_loop().run_until_complete(setup_web_app(application))

    logger.info("🚀 Запуск простого бота...")
    application.run_polling()


if __name__ == "__main__":
    main()
