#!/usr/bin/env python3
"""
🚀 PROFESSIONAL SMM DEPLOYMENT SCRIPT
Deploys enhanced Telegram bot with Professional SMM System
"""

from bot.services.db import init_db
from bot.services.ai_enhanced import AIEnhancedManager
from bot.services.smm_integration import initialize_smm_integration, start_smm_system
from telegram.ext import Application
import os
import sys
from pathlib import Path
from datetime import datetime
import logging
import asyncio

# Загружаем переменные окружения ПЕРВЫМ ДЕЛОМ
from dotenv import load_dotenv
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('professional_smm_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def initialize_professional_smm_bot():
    """Инициализация бота с Professional SMM System"""

    try:
        logger.info("🚀 Starting Professional SMM Bot initialization...")

        # 1. Создаем основное приложение
        logger.info("📱 Creating Telegram application...")
        token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN or BOT_TOKEN not set")

        application = Application.builder().token(token).build()

        # 2. Инициализируем базу данных
        logger.info("💾 Initializing database...")
        await init_db()

        # 3. Инициализируем AI Manager
        logger.info("🧠 Initializing Enhanced AI Manager...")
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        # 4. Инициализируем SMM интеграцию
        logger.info("📊 Initializing Professional SMM System...")
        smm_integration = await initialize_smm_integration(
            bot=application.bot,
            ai_manager=ai_manager
        )

        # 5. Запускаем SMM систему в фоне
        logger.info("🎯 Starting SMM automation...")
        smm_task = asyncio.create_task(start_smm_system())

        # 6. Добавляем обработчик завершения
        async def post_init(application: Application) -> None:
            """Пост-инициализация"""
            logger.info("✅ Professional SMM Bot fully initialized!")

            # Генерируем стартовый отчет
            try:
                status = await smm_integration.get_smm_analytics_report(days_back=1)
                logger.info(
                    f"📈 SMM System Status: {status.get('system_status', {})}")
            except Exception as e:
                logger.warning(f"Could not generate initial SMM report: {e}")

        async def post_shutdown(application: Application) -> None:
            """Завершение работы"""
            logger.info("🛑 Shutting down Professional SMM Bot...")

            try:
                # Останавливаем SMM систему
                await smm_integration.stop_smm_system()
                logger.info("📊 SMM System stopped")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

        # Устанавливаем обработчики
        application.post_init = post_init
        application.post_shutdown = post_shutdown

        return application, smm_task

    except Exception as e:
        logger.error(f"❌ Failed to initialize Professional SMM Bot: {e}")
        raise


async def main():
    """Главная функция запуска"""

    try:
        # Проверяем переменные окружения
        required_env_vars = ['TELEGRAM_BOT_TOKEN', 'BOT_TOKEN']
        if not any(os.getenv(var) for var in required_env_vars):
            logger.error("❌ Missing TELEGRAM_BOT_TOKEN or BOT_TOKEN")
            return

        # Инициализируем бота
        application, smm_task = await initialize_professional_smm_bot()

        logger.info("🎉 Professional SMM Bot is starting...")
        logger.info(f"🕐 Start time: {datetime.now().isoformat()}")

        # Запускаем бота и SMM систему параллельно
        try:
            await asyncio.gather(
                application.run_polling(drop_pending_updates=True),
                smm_task,
                return_exceptions=True
            )
        except KeyboardInterrupt:
            logger.info("👋 Received shutdown signal")
        except Exception as e:
            logger.error(f"❌ Runtime error: {e}")
        finally:
            # Корректное завершение
            if application.running:
                await application.stop()

            # Отменяем SMM задачу
            if not smm_task.done():
                smm_task.cancel()
                try:
                    await smm_task
                except asyncio.CancelledError:
                    logger.info("🛑 SMM task cancelled")

        logger.info("✅ Professional SMM Bot stopped gracefully")

    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Interrupted by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
