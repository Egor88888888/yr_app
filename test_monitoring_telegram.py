"""
🔍 SIMPLE MONITORING TEST VIA TELEGRAM
Простая команда для тестирования системы мониторинга
"""

import asyncio
import logging
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from bot.handlers.production_testing import production_test_command, production_test_callback_handler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def simple_monitoring_test():
    """Простой тест системы мониторинга через Telegram"""

    print("🔍 Starting Simple Monitoring Test via Telegram")
    print("=" * 50)

    # Проверяем переменные окружения
    bot_token = os.getenv('BOT_TOKEN')
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')

    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return

    if not admin_chat_id:
        print("❌ ADMIN_CHAT_ID not found in environment")
        return

    print(f"✅ Environment configured")
    print(f"   - Admin Chat ID: {admin_chat_id}")

    try:
        # Создание приложения
        application = Application.builder().token(bot_token).build()

        # Регистрация хэндлеров
        application.add_handler(CommandHandler(
            "test", production_test_command))
        application.add_handler(CallbackQueryHandler(
            production_test_callback_handler,
            pattern="^test_"
        ))

        print("✅ Telegram bot configured")
        print("✅ Production testing handlers registered")

        # Отправка уведомления о готовности
        bot = Bot(token=bot_token)

        startup_message = """🚀 **PRODUCTION TESTING BOT READY**

✅ Система тестирования запущена
✅ Команды готовы к использованию

🧪 **Доступные команды:**
/test - Запуск продакшн тестирования

🔍 **Доступные тесты:**
• Quick Check - быстрая проверка
• Full Test - полное тестирование
• Monitoring Test - тест системы мониторинга
• Performance Test - тест производительности

⚡ Используйте /test для начала тестирования"""

        await bot.send_message(
            chat_id=admin_chat_id,
            text=startup_message,
            parse_mode="Markdown"
        )

        print("✅ Startup notification sent")
        print("🚀 Bot is running... Use /test command in Telegram")
        print("🛑 Press Ctrl+C to stop")

        # Запуск бота
        await application.run_polling(drop_pending_updates=True)

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_monitoring_test())
