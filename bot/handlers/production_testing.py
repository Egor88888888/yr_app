#!/usr/bin/env python3
"""
МИНИМАЛЬНОЕ ТЕСТИРОВАНИЕ
Заменяет раздутый production_testing.py (540 строк → ~50 строк)
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config.settings import is_admin
from bot.core.metrics import get_system_stats

logger = logging.getLogger(__name__)

async def cmd_test_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Базовый тест системы"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    try:
        stats = get_system_stats()
        await update.message.reply_text(
            f"✅ Система работает\n"
            f"📊 Запросов: {stats.get('total_requests', 0)}\n"
            f"⏱️ Время работы: {stats.get('uptime_human', 'N/A')}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка тестирования: {e}")

def register_production_testing_handlers(app: Application):
    """Регистрация минимального тестирования"""
    app.add_handler(CommandHandler("test", cmd_test_system))
    
    logger.info("✅ Minimal testing handlers registered")