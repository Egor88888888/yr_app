#!/usr/bin/env python3
"""
МИНИМАЛЬНАЯ SMM АДМИНКА - только базовые функции
Заменяет раздутый smm_admin.py (1,802 строки → ~50 строк)
"""

from telegram.ext import Application
from bot.handlers.admin.simple_admin import register_simple_admin_handlers

def register_smm_admin_handlers(app: Application):
    """Регистрация упрощенных SMM админ хендлеров"""
    # Используем новую упрощенную админку
    register_simple_admin_handlers(app)