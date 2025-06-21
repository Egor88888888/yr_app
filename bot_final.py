#!/usr/bin/env python3
"""
РАБОЧАЯ версия бота с GitHub Pages
"""
import json
import logging
import os
import asyncio
from telegram import Update, WebAppInfo, MenuButton, MenuButtonWebApp, KeyboardButton, ReplyKeyboardMarkup
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

    greeting_text = (
        f"Здравствуйте, {user.mention_html()}! 🏛️\n\n"
        "Я ваш юридический помощник по страховым вопросам.\n"
        "Нажмите кнопку \"📝 Подать заявку\", чтобы открыть форму."
    )

    # Кнопка-клавиатура с WebApp — ИМЕННО она позволяет использовать tg.sendData.
    web_app_url = "https://egor88888888.github.io/yr_app/"
    kb = [
        [
            KeyboardButton(
                text="📝 Подать заявку",
                web_app=WebAppInfo(url=web_app_url),
            )
        ]
    ]

    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)

    await update.message.reply_html(greeting_text, reply_markup=reply_markup)


# /form — на случай, если пользователь потерял клавиатуру
async def form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляем сообщение с кнопкой WebApp ещё раз."""
    web_app_url = "https://egor88888888.github.io/yr_app/"
    kb = [[KeyboardButton(text="📝 Подать заявку",
                          web_app=WebAppInfo(url=web_app_url))]]
    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть форму:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка заявки"""
    logger.info("🎯🎯🎯 WEB_APP_DATA HANDLER ВЫЗВАН!")
    logger.info(f"🔍 Update объект: {update}")
    logger.info(f"🔍 Update.effective_message: {update.effective_message}")
    logger.info(f"🔍 Update.effective_user: {update.effective_user}")

    user = update.effective_user
    logger.info(f"👤 Пользователь: {user.id} - {user.full_name}")

    if not update.effective_message:
        logger.error("❌ КРИТИЧНО: update.effective_message отсутствует!")
        return

    if not update.effective_message.web_app_data:
        logger.error(
            "❌ КРИТИЧНО: update.effective_message.web_app_data отсутствует!")
        logger.error(f"❌ Но сообщение есть: {update.effective_message}")
        return

    logger.info(f"📄 RAW web_app_data: {update.effective_message.web_app_data}")
    logger.info(
        f"📄 WEB APP ДАННЫЕ: {update.effective_message.web_app_data.data}")
    logger.info(
        f"📄 Длина данных: {len(update.effective_message.web_app_data.data)}")

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
        logger.info("🔄 Парсим JSON данные...")
        data = json.loads(update.effective_message.web_app_data.data)
        logger.info(f"📊 Распарсенные данные: {data}")

        problems = ", ".join(data.get('problems', ['Не указано']))
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        description = data.get('description', 'Не указано')

        logger.info(
            f"📋 Подготовленные данные: problems={problems}, name={name}, phone={phone}")

        admin_message = f"""🔔 НОВАЯ ЗАЯВКА!

👤 Клиент: {name} (ID: {user.id})
📞 Телефон: {phone}
⚠️ Проблемы: {problems}

📝 Описание ситуации:
{description}

⏰ Время: {update.effective_message.date}"""

        logger.info(f"📨 Отправляем сообщение админу в чат: {ADMIN_CHAT_ID}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        logger.info("✅✅✅ ЗАЯВКА УСПЕШНО ОТПРАВЛЕНА АДМИНИСТРАТОРУ!")
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА отправки администратору: {e}")
        import traceback
        logger.error(f"❌ Stack trace: {traceback.format_exc()}")
        traceback.print_exc()


async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для отладки всех сообщений"""
    logger.info("=" * 50)
    logger.info(
        f"📨 ПОЛУЧЕНО СООБЩЕНИЕ от пользователя {update.effective_user.id}")
    logger.info(f"📨 Тип update: {type(update)}")
    logger.info(f"📨 Тип сообщения: {type(update.message)}")
    logger.info(f"📨 Полное содержимое update.message: {update.message}")

    if update.message:
        logger.info(f"📨 Message ID: {update.message.message_id}")
        logger.info(f"📨 Text: {getattr(update.message, 'text', 'NO TEXT')}")
        logger.info(
            f"📨 Caption: {getattr(update.message, 'caption', 'NO CAPTION')}")

        if hasattr(update.message, 'web_app_data'):
            logger.info(
                f"🌐 web_app_data атрибут СУЩЕСТВУЕТ: {update.message.web_app_data}")
            if update.message.web_app_data:
                logger.info(
                    f"🌐🌐🌐 WEB APP DATA НАЙДЕНА: {update.message.web_app_data.data}")
                logger.info(
                    f"🌐 Длина данных: {len(update.message.web_app_data.data) if update.message.web_app_data.data else 0}")
            else:
                logger.info("🌐 web_app_data существует но None")
        else:
            logger.info("🌐 web_app_data атрибут НЕ СУЩЕСТВУЕТ")

        # Попытка прямого доступа к web_app_data
        try:
            direct_access = update.message.web_app_data
            logger.info(f"🔍 Прямой доступ к web_app_data: {direct_access}")
        except AttributeError as e:
            logger.info(f"🔍 Ошибка прямого доступа: {e}")
    else:
        logger.info("📨 update.message отсутствует!")

    logger.info("=" * 50)


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
    application.add_handler(CommandHandler("form", form))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, debug_all_messages))

    # Настройка веб-приложения и одновременное создание ГЛОБАЛЬНОГО event-loop,
    # который затем будет использован `application.run_webhook`.
    # 1. Создаём новый цикл
    # 2. Делаем его текущим (set_event_loop)
    # 3. Выполняем coroutine настройки веб-аппа
    # 4. НЕ закрываем цикл, чтобы он остался доступен run_webhook.
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_web_app(application))
        # ВАЖНО: не закрываем loop, иначе run_webhook потеряет текущий цикл.
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
