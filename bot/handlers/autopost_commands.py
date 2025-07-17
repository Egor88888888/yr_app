"""
🚀 КОМАНДЫ УПРАВЛЕНИЯ АВТОПОСТИНГОМ
Простые команды для тестирования и управления автопостингом
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

logger = logging.getLogger(__name__)


async def cmd_autopost_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки статуса автопостинга"""
    user_id = update.effective_user.id

    # Проверяем права администратора
    from bot.main import ADMIN_USERS
    if user_id not in ADMIN_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    try:
        from bot.services.simple_autopost import get_simple_autopost
        autopost = get_simple_autopost()

        if autopost:
            status = await autopost.get_status()

            text = f"""📊 **СТАТУС АВТОПОСТИНГА**

🟢 **Состояние:** {'Работает' if status['running'] else 'Остановлен'}
⏱️ **Интервал:** {status['interval_minutes']} минут
📝 **Постов сегодня:** {status['posts_today']}/{status['daily_limit']}
📅 **Последний пост:** {status['last_post_time'][:16] if status['last_post_time'] else 'Не было'}
🚀 **Deploy пост:** {status['last_deploy_post'][:16] if status['last_deploy_post'] else 'Не было'}
📺 **Канал:** {status['channel_id']}

✅ **Система работает стабильно!**"""

        else:
            text = "❌ Система автопостинга не инициализирована"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in autopost_status: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статуса: {e}")


async def cmd_autopost_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для создания тестового поста"""
    user_id = update.effective_user.id

    # Проверяем права администратора
    from bot.main import ADMIN_USERS
    if user_id not in ADMIN_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    try:
        from bot.services.simple_autopost import get_simple_autopost
        autopost = get_simple_autopost()

        if autopost:
            # Создаем тестовый пост
            result = await autopost.create_immediate_post("regular")

            if result.get('success'):
                text = f"""✅ **ТЕСТОВЫЙ ПОСТ СОЗДАН!**

📋 **ID сообщения:** {result['message_id']}
📝 **Тип:** {result.get('type', 'regular')}
⏰ **Время:** {datetime.now().strftime('%H:%M:%S')}

🎯 Пост опубликован в канале для проверки работы автопостинга."""
            else:
                text = f"❌ **ОШИБКА СОЗДАНИЯ ПОСТА:** {result.get('error')}"
        else:
            text = "❌ Система автопостинга не инициализирована"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in autopost_test: {e}")
        await update.message.reply_text(f"❌ Ошибка создания тестового поста: {e}")


async def cmd_autopost_deploy_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для создания тестового deploy поста"""
    user_id = update.effective_user.id

    # Проверяем права администратора
    from bot.main import ADMIN_USERS
    if user_id not in ADMIN_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    try:
        from bot.services.simple_autopost import get_simple_autopost
        autopost = get_simple_autopost()

        if autopost:
            # Создаем deploy пост
            result = await autopost.create_immediate_post("deploy")

            if result.get('success'):
                text = f"""✅ **DEPLOY ПОСТ СОЗДАН!**

📋 **ID сообщения:** {result['message_id']}
📝 **Тип:** Deploy Autopost
⏰ **Время:** {datetime.now().strftime('%H:%M:%S')}

🚀 Deploy пост опубликован для проверки работы системы."""
            else:
                text = f"❌ **ОШИБКА СОЗДАНИЯ DEPLOY ПОСТА:** {result.get('error')}"
        else:
            text = "❌ Система автопостинга не инициализирована"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in autopost_deploy_test: {e}")
        await update.message.reply_text(f"❌ Ошибка создания deploy поста: {e}")


def register_autopost_commands(application: Application):
    """Регистрация команд автопостинга"""
    try:
        application.add_handler(CommandHandler(
            "autopost_status", cmd_autopost_status))
        application.add_handler(CommandHandler(
            "autopost_test", cmd_autopost_test))
        application.add_handler(CommandHandler(
            "autopost_deploy_test", cmd_autopost_deploy_test))

        logger.info("✅ Autopost commands registered")

    except Exception as e:
        logger.error(f"Failed to register autopost commands: {e}")
        raise
