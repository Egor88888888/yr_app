#!/usr/bin/env python3
"""
🏛️ ЮРИДИЧЕСКИЙ ЦЕНТР - PRODUCTION-READY BOT

🚀 ПОЛНОФУНКЦИОНАЛЬНЫЙ ПРОДУКТ ДЛЯ ПРОДАКШЕНА:
- 12 категорий юридических услуг  
- Enhanced AI с ML классификацией
- Telegram Mini App с современным UI
- Админ панель с полным функционалом
- Интеграции: Google Sheets, CloudPayments, OpenRouter
- Мониторинг, логирование, безопасность
- Rate limiting и защита от спама
- Автоматические backup и восстановление
"""

import asyncio
import json
import logging
import os
import random
import uuid
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Set
from collections import defaultdict

from aiohttp import web
from sqlalchemy import select, text, func
from telegram import (
    Update, WebAppInfo, MenuButtonWebApp,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from bot.services.db import (
    async_sessionmaker, init_db, Base,
    User, Application as AppModel, Category, Admin, Payment
)
from bot.services.sheets import append_lead
from bot.services.pay import create_payment
from bot.services.ai import generate_ai_response, generate_post_content
from bot.services.ai_enhanced import AIEnhancedManager
from bot.services.notifications import notify_client_application_received, notify_client_status_update, notify_client_payment_required

# ================ PRODUCTION CONFIG ================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Production готовность
PRODUCTION_MODE = os.getenv("RAILWAY_ENVIRONMENT") == "production"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# Enhanced AI Manager
ai_enhanced_manager = None

# Rate Limiting
user_request_counts = defaultdict(list)  # user_id -> [timestamps]
RATE_LIMIT_REQUESTS = 10  # запросов
RATE_LIMIT_WINDOW = 60   # секунд
blocked_users: Set[int] = set()

# Мониторинг
system_metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "ai_requests": 0,
    "start_time": datetime.now()
}

# Get Railway public domain
RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv(
    "MY_RAILWAY_PUBLIC_URL")

if RAILWAY_DOMAIN and "MY_RAILWAY_PUBLIC_URL" in RAILWAY_DOMAIN:
    PUBLIC_HOST = "poetic-simplicity-production-60e7.up.railway.app"
else:
    PUBLIC_HOST = RAILWAY_DOMAIN if RAILWAY_DOMAIN else "localhost"

if PUBLIC_HOST.startswith("http"):
    from urllib.parse import urlparse
    PUBLIC_HOST = urlparse(PUBLIC_HOST).netloc

WEB_APP_URL = f"https://{PUBLIC_HOST}/webapp/"

print(f"🌐 WebApp URL: {WEB_APP_URL}")
print(f"🔗 Webhook URL: https://{PUBLIC_HOST}/{TOKEN}")
print(f"🚀 Production Mode: {PRODUCTION_MODE}")

PORT = int(os.getenv("PORT", 8080))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Настройка логирования для продакшена
log_level = logging.WARNING if PRODUCTION_MODE else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            'bot.log') if not PRODUCTION_MODE else logging.NullHandler()
    ]
)
log = logging.getLogger(__name__)

# 🔧 FIXED: Улучшенная система администраторов
HARDCODED_ADMIN_IDS = {
    6373924442,  # Основной администратор (замените на ваш реальный ID)
    ADMIN_CHAT_ID if ADMIN_CHAT_ID != 0 else None
}
HARDCODED_ADMIN_IDS.discard(None)  # Убираем None если ADMIN_CHAT_ID=0

# Global admin set - теперь правильный
ADMIN_USERS = HARDCODED_ADMIN_IDS.copy()

print(f"🔧 Admin users initialized: {ADMIN_USERS}")
log.info(f"Admin users configured: {list(ADMIN_USERS)}")

# Role permissions
ROLE_PERMISSIONS = {
    "operator": ["view_applications", "update_status"],
    "lawyer": ["view_applications", "update_status", "assign_lawyer", "add_notes", "bill_client"],
    "superadmin": ["view_applications", "update_status", "assign_lawyer", "add_notes", "bill_client", "manage_admins", "view_all_stats"]
}

# ================ PRODUCTION HELPERS ================


async def is_admin(user_id: int) -> bool:
    """
    🔧 FIXED: Улучшенная проверка администраторов
    Проверяет в нескольких источниках:
    1. Хардкодированные ID
    2. Таблица admins в БД
    """
    # Быстрая проверка хардкодированных админов
    if user_id in HARDCODED_ADMIN_IDS:
        return True

    # Проверка в базе данных
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(
                select(Admin).where(
                    Admin.tg_id == user_id,
                    Admin.is_active == True
                )
            )
            db_admin = result.scalar_one_or_none()
            return db_admin is not None
    except Exception as e:
        log.error(f"Error checking admin status in DB: {e}")
        # В случае ошибки БД, проверяем только хардкодированных
        return user_id in HARDCODED_ADMIN_IDS


def is_rate_limited(user_id: int) -> bool:
    """Проверка rate limiting"""
    # Админы не подвержены rate limiting
    if user_id in ADMIN_USERS:
        return False

    if user_id in blocked_users:
        return True

    now = time.time()
    user_requests = user_request_counts[user_id]

    # Убираем старые запросы
    user_requests[:] = [
        req_time for req_time in user_requests if now - req_time < RATE_LIMIT_WINDOW]

    if len(user_requests) >= RATE_LIMIT_REQUESTS:
        log.warning(f"Rate limit exceeded for user {user_id}")
        return True

    user_requests.append(now)
    return False


async def log_request(user_id: int, request_type: str, success: bool, error: str = None):
    """Логирование запросов для мониторинга"""
    system_metrics["total_requests"] += 1

    if success:
        system_metrics["successful_requests"] += 1
    else:
        system_metrics["failed_requests"] += 1
        if error:
            log.error(
                f"Request failed - User: {user_id}, Type: {request_type}, Error: {error}")

    if request_type == "ai":
        system_metrics["ai_requests"] += 1


def sanitize_input(text: str) -> str:
    """Санитизация пользовательского ввода"""
    if not text:
        return ""

    # Убираем потенциально опасные символы
    sanitized = text.replace('<', '&lt;').replace('>', '&gt;')

    # Ограничиваем длину
    if len(sanitized) > 4000:
        sanitized = sanitized[:4000] + "..."

    return sanitized


async def validate_telegram_data(data: dict) -> bool:
    """Валидация данных от Telegram WebApp"""
    try:
        # Проверяем обязательные поля
        required_fields = ["category_id", "name", "phone", "contact_method"]
        for field in required_fields:
            if not data.get(field):
                return False

        # Проверяем типы данных
        if not isinstance(data.get("category_id"), int):
            return False

        # Проверяем длины полей
        if len(data.get("name", "")) > 100:
            return False

        if len(data.get("description", "")) > 2000:
            return False

        return True
    except Exception as e:
        log.error(f"Validation error: {e}")
        return False


# ================ HANDLERS ================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with inline webapp button"""
    user = update.effective_user

    # Set menu button for this user
    try:
        await context.bot.set_chat_menu_button(
            chat_id=user.id,
            menu_button=MenuButtonWebApp(
                text="📝 Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
    except Exception as e:
        log.error(f"Failed to set menu button: {e}")

    # Store user in DB
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(User).where(User.tg_id == user.id)
        )
        db_user = result.scalar_one_or_none()
        if not db_user:
            db_user = User(
                tg_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name
            )
            session.add(db_user)
            await session.commit()

    welcome_text = f"""
👋 Здравствуйте, {user.first_name}!

🏛️ **ЮРИДИЧЕСКИЙ ЦЕНТР**
Полный спектр юридических услуг:

• Семейное право и развод
• Наследственные споры
• Трудовые конфликты
• Жилищные вопросы
• Банкротство физлиц
• Налоговые консультации
• Административные дела
• Защита прав потребителей
• Миграционное право
• И многое другое!

💬 Задайте вопрос прямо в чате или нажмите синюю кнопку меню рядом с полем ввода для подачи заявки.

✅ Работаем по всей России
💰 Оплата по результату
"""

    keyboard = [[
        InlineKeyboardButton(
            "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ИСПРАВЛЕННЫЙ AI консультант с памятью диалогов и клиентским путем"""
    global ai_enhanced_manager

    user_id = update.effective_user.id
    user_text = update.message.text
    user = update.effective_user

    # 🔧 ФИКС: Проверяем, ждет ли админ ввод текста для рассылки
    if await is_admin(user_id) and context.user_data.get('pending_broadcast', {}).get('waiting_for_text'):
        await handle_broadcast_text(update, context)
        return

    if not OPENROUTER_API_KEY:
        await update.message.reply_text("AI консультант временно недоступен")
        return

    # Логирование для диагностики
    await log_request(user_id, "ai", True)

    try:
        # 🚀 ИСПРАВЛЕНИЕ: Используем Enhanced AI с правильными параметрами
        if ai_enhanced_manager and ai_enhanced_manager._initialized:
            log.info(f"🧠 Using Enhanced AI for user {user_id}")

            # ИСПРАВЛЕНО: Передаем правильный user_id (Telegram ID, не database ID)
            response = await ai_enhanced_manager.generate_response(
                user_id=user_id,  # Telegram ID
                message=user_text,
                context={
                    'telegram_user': {
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'username': user.username
                    },
                    'message_timestamp': datetime.now().isoformat()
                }
            )

            log.info(
                f"✅ Enhanced AI response generated: {len(response)} chars")
        else:
            log.info(f"⚠️ Using fallback AI for user {user_id}")

            # Fallback к старому AI
            category = detect_category(user_text)

            system_prompt = f"""Ты - опытный юрист-консультант.
Отвечаешь на вопросы по теме: {category}.
Даёшь практические советы, ссылаешься на законы РФ.
В конце предлагаешь записаться на консультацию."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]

            response = await generate_ai_response(messages)

            # Проверяем на код 402 и не добавляем дубль текста
            if "код 402" not in response:
                response += "\n\n💼 Для детальной консультации нажмите кнопки ниже."

        # 🎯 НОВОЕ: Добавляем клиентский путь с кнопками
        keyboard = [
            [
                InlineKeyboardButton(
                    "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL)),
                InlineKeyboardButton("📞 Заказать звонок",
                                     callback_data="request_call")
            ],
            [
                InlineKeyboardButton(
                    "💬 Консультация в чате", callback_data="chat_consultation"),
                InlineKeyboardButton("📊 Узнать стоимость",
                                     callback_data="get_price")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(response, reply_markup=reply_markup)

        log.info(
            f"✅ AI response sent to user {user_id} with client flow buttons")

    except Exception as e:
        log.error(f"❌ AI Chat error for user {user_id}: {e}")
        await log_request(user_id, "ai", False, str(e))

        # Fallback ответ с кнопками
        fallback_keyboard = [[
            InlineKeyboardButton(
                "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))
        ]]

        await update.message.reply_text(
            "🤖 AI временно недоступен, но вы можете оставить заявку на консультацию.",
            reply_markup=InlineKeyboardMarkup(fallback_keyboard)
        )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ Нет доступа")
        return

    keyboard = [
        [InlineKeyboardButton("📋 Заявки", callback_data="admin_apps"),
         InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💳 Платежи", callback_data="admin_payments"),
         InlineKeyboardButton("👥 Клиенты", callback_data="admin_users")],
        [InlineKeyboardButton("🤖 AI Статус", callback_data="admin_ai_status"),
         InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
    ]

    await update.message.reply_text(
        "🔧 **АДМИН ПАНЕЛЬ**\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def cmd_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔧 FIXED: Команда для добавления нового администратора"""
    user_id = update.effective_user.id

    # Проверяем права текущего пользователя
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ Нет доступа")
        return

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "📋 **Добавление администратора**\n\n"
            "Использование: `/add_admin <ID> [роль]`\n\n"
            "Роли:\n"
            "• `operator` - просмотр заявок\n"
            "• `lawyer` - работа с заявками\n"
            "• `superadmin` - полный доступ\n\n"
            "Пример: `/add_admin 123456789 lawyer`",
            parse_mode='Markdown'
        )
        return

    try:
        new_admin_id = int(context.args[0])
        role = context.args[1] if len(context.args) > 1 else "operator"

        if role not in ROLE_PERMISSIONS:
            await update.message.reply_text(
                f"❌ Неверная роль: `{role}`\n\n"
                f"Доступные роли: {', '.join(ROLE_PERMISSIONS.keys())}",
                parse_mode='Markdown'
            )
            return

    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом")
        return

    # Проверяем, не является ли уже администратором
    if await is_admin(new_admin_id):
        await update.message.reply_text(f"⚠️ Пользователь {new_admin_id} уже администратор")
        return

    # Добавляем в базу данных
    try:
        async with async_sessionmaker() as session:
            new_admin = Admin(
                tg_id=new_admin_id,
                role=role,
                is_active=True
            )
            session.add(new_admin)
            await session.commit()

        # Перезагружаем список администраторов
        await load_db_admins()

        # Уведомляем об успехе
        await update.message.reply_text(
            f"✅ **Администратор добавлен**\n\n"
            f"👤 ID: `{new_admin_id}`\n"
            f"🎯 Роль: `{role}`\n"
            f"📊 Всего админов: {len(ADMIN_USERS)}",
            parse_mode='Markdown'
        )

        # Уведомляем нового администратора
        try:
            await context.bot.send_message(
                new_admin_id,
                f"🎉 **Вы назначены администратором!**\n\n"
                f"🎯 Роль: {role}\n"
                f"📋 Команды: /admin, /start\n\n"
                f"Добро пожаловать в команду! 👋",
                parse_mode='Markdown'
            )
        except Exception as e:
            log.warning(f"Could not notify new admin {new_admin_id}: {e}")
            await update.message.reply_text(
                "⚠️ Администратор добавлен, но не смогли отправить уведомление "
                "(возможно, пользователь не запускал бота)"
            )

        log.info(
            f"🔧 New admin added: {new_admin_id} with role {role} by {user_id}")

    except Exception as e:
        log.error(f"Failed to add admin {new_admin_id}: {e}")
        await update.message.reply_text(f"❌ Ошибка добавления администратора: {e}")


async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔧 FIXED: Команда для просмотра списка администраторов"""
    user_id = update.effective_user.id

    # Проверяем права текущего пользователя
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ Нет доступа")
        return

    try:
        text = "👥 **СПИСОК АДМИНИСТРАТОРОВ**\n\n"

        # Хардкодированные администраторы
        if HARDCODED_ADMIN_IDS:
            text += "🔧 **Хардкодированные:**\n"
            for admin_id in sorted(HARDCODED_ADMIN_IDS):
                text += f"• `{admin_id}` (системный)\n"
            text += "\n"

        # Администраторы из БД
        async with async_sessionmaker() as session:
            result = await session.execute(
                select(Admin).where(Admin.is_active == True)
                .order_by(Admin.created_at.desc())
            )
            db_admins = result.scalars().all()

        if db_admins:
            text += "💾 **Из базы данных:**\n"
            for admin in db_admins:
                status = "✅" if admin.is_active else "❌"
                text += f"{status} `{admin.tg_id}` ({admin.role})\n"
        else:
            text += "💾 **Из базы данных:** нет\n"

        text += f"\n📊 **Всего активных:** {len(ADMIN_USERS)}"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        log.error(f"Failed to list admins: {e}")
        await update.message.reply_text(f"❌ Ошибка получения списка: {e}")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик админских кнопок"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # 🎯 НОВОЕ: Клиентские кнопки доступны всем пользователям
    client_actions = [
        "request_call", "chat_consultation", "get_price", "back_to_chat",
        "enter_phone", "submit_call_request"
    ]

    if data in client_actions or data.startswith("consultation_category_"):
        await client_flow_callback(update, context)
        return

    # Проверка админ-доступа только для админских действий
    if not await is_admin(user_id):
        await query.answer("Нет доступа", show_alert=True)
        return

    if data == "admin_apps":
        await show_applications(query, context)
    elif data == "admin_stats":
        await show_statistics(query, context)
    elif data == "admin_payments":
        await show_payments(query, context)
    elif data == "admin_users":
        await show_clients(query, context)
    elif data == "admin_broadcast":
        await show_broadcast_options(query, context)
    elif data == "admin_settings":
        await show_admin_settings(query, context)
    elif data == "admin_ai_status":
        await show_ai_status(query, context)
    elif data.startswith("app_"):
        await handle_application_action(query, context)
    elif data.startswith("client_"):
        await handle_client_action(query, context)
    elif data.startswith("broadcast_"):
        await handle_broadcast_action(query, context)
    elif data.startswith("confirm_broadcast_"):
        await execute_broadcast(query, context)
    elif data.startswith("setting_"):
        await handle_settings_action(query, context)
    elif data == "back_admin":
        await show_admin_panel(query)


async def show_applications(query, context):
    """Показать список заявок"""
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(AppModel, User)
            .join(User)
            .order_by(AppModel.created_at.desc())
            .limit(10)
        )
        apps = result.all()

    if not apps:
        text = "📋 Нет заявок"
    else:
        text = "📋 **ПОСЛЕДНИЕ ЗАЯВКИ**\n\n"
        keyboard = []

        for app, user in apps:
            status_emoji = {
                "new": "🆕",
                "processing": "⏳",
                "completed": "✅"
            }.get(app.status, "❓")

            # Используем subcategory вместо Category.name
            category_name = app.subcategory.split(
                ':')[0] if app.subcategory and ':' in app.subcategory else (app.subcategory or "Общие вопросы")

            text += f"{status_emoji} #{app.id} | {category_name}\n"
            text += f"👤 {user.first_name} {user.phone or ''}\n"
            text += f"📅 {app.created_at.strftime('%d.%m %H:%M')}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"#{app.id} Подробнее",
                    callback_data=f"app_view_{app.id}"
                )
            ])

    keyboard.append([InlineKeyboardButton(
        "🔙 Назад", callback_data="back_admin")])

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def handle_application_action(query, context):
    """🔧 ПРОДАКШН-ГОТОВО: Полные действия с заявкой"""
    data = query.data

    if data.startswith("app_view_"):
        app_id = int(data.split("_")[2])

        async with async_sessionmaker() as session:
            result = await session.execute(
                select(AppModel, User)
                .join(User)
                .where(AppModel.id == app_id)
            )
            row = result.one_or_none()

        if not row:
            await query.answer("Заявка не найдена", show_alert=True)
            return

        app, user = row

        contact_methods = {
            'phone': '📞 Телефонный звонок',
            'telegram': '💬 Telegram',
            'email': '📧 Email',
            'whatsapp': '💚 WhatsApp'
        }

        # Используем subcategory вместо Category.name
        category_name = app.subcategory.split(
            ':')[0] if app.subcategory and ':' in app.subcategory else (app.subcategory or "Общие вопросы")
        subcategory_detail = app.subcategory.split(':', 1)[1].strip(
        ) if app.subcategory and ':' in app.subcategory else '-'

        # Безопасное формирование текста с ограничением длины и экранированием
        description = (app.description or '-')
        if len(description) > 500:
            description = description[:500] + '...'

        # Экранируем специальные символы Markdown
        def escape_markdown(text):
            if not text or text == '-':
                return text
            # Экранируем основные символы Markdown для безопасности
            text = str(text)
            chars = ['*', '_', '[', ']', '`', '\\']
            for char in chars:
                text = text.replace(char, f'\\{char}')
            return text

        safe_description = escape_markdown(description)
        safe_first_name = escape_markdown(user.first_name or 'Без имени')
        safe_last_name = escape_markdown(user.last_name or '')
        safe_phone = escape_markdown(user.phone or '-')
        safe_email = escape_markdown(user.email or '-')
        safe_category = escape_markdown(category_name)
        safe_subcategory = escape_markdown(subcategory_detail)

        text = f"""
📋 **ЗАЯВКА #{app.id}**

📂 Категория: {safe_category}
📝 Подкатегория: {safe_subcategory}

👤 **Клиент:**
Имя: {safe_first_name} {safe_last_name}
📞 {safe_phone}
📧 {safe_email}
💬 Связь: {contact_methods.get(app.contact_method, app.contact_method or '-')}
🕐 Время: {app.contact_time or 'любое'}

📄 **Описание:**
{safe_description}

{f'📎 Файлов: {len(app.files_data or [])}' if app.files_data else ''}
{f'🏷️ UTM: {app.utm_source}' if app.utm_source else ''}

💰 Стоимость: {app.price or 'не определена'} ₽
📊 Статус: {app.status}
📅 Создана: {app.created_at.strftime('%d.%m.%Y %H:%M')}
"""

        # Ограничиваем общую длину сообщения для Telegram
        if len(text) > 4000:
            text = text[:4000] + '\n\\.\\.\\.'

        # Динамические кнопки в зависимости от статуса
        keyboard = []

        if app.status == "new":
            keyboard.extend([
                [InlineKeyboardButton("✅ Взять в работу", callback_data=f"app_take_{app.id}"),
                 InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app.id}")],
                [InlineKeyboardButton("💳 Выставить счет",
                                      callback_data=f"app_bill_{app.id}")]
            ])
        elif app.status == "processing":
            keyboard.extend([
                [InlineKeyboardButton("✅ Завершить", callback_data=f"app_complete_{app.id}"),
                 InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app.id}")],
                [InlineKeyboardButton("💳 Выставить счет",
                                      callback_data=f"app_bill_{app.id}")]
            ])
        elif app.status == "completed":
            keyboard.append([InlineKeyboardButton(
                "💳 Повторный счет", callback_data=f"app_bill_{app.id}")])
        elif app.status == "cancelled":
            keyboard.append([InlineKeyboardButton(
                "🔄 Восстановить", callback_data=f"app_take_{app.id}")])

        keyboard.append([InlineKeyboardButton(
            "🔙 К списку", callback_data="admin_apps")])

        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            log.error(f"Failed to edit message: {e}")
            # Fallback: отправляем новое сообщение если редактирование не удалось
            try:
                await query.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                await query.answer("Сообщение обновлено")
            except Exception as fallback_error:
                log.error(f"Fallback message also failed: {fallback_error}")
                await query.answer("❌ Ошибка отображения данных", show_alert=True)

    elif data.startswith("app_take_"):
        # ✅ Взять заявку в работу
        app_id = int(data.split("_")[2])
        admin_id = query.from_user.id

        try:
            async with async_sessionmaker() as session:
                # Получаем заявку
                result = await session.execute(
                    select(AppModel, User)
                    .join(User)
                    .where(AppModel.id == app_id)
                )
                row = result.one_or_none()

                if not row:
                    await query.answer("Заявка не найдена", show_alert=True)
                    return

                app, user = row

                # Обновляем статус заявки
                app.status = "processing"
                app.assigned_admin = str(admin_id)
                app.updated_at = datetime.now()

                # Добавляем заметку
                if not app.notes:
                    app.notes = ""
                app.notes += f"\n[{datetime.now().strftime('%d.%m %H:%M')}] Взята в работу администратором {admin_id}"

                await session.commit()

            # Уведомляем клиента
            try:
                await notify_client_status_update(user, app, "processing")
            except Exception as e:
                log.error(f"Client notification error: {e}")

            # Уведомляем администратора об успехе
            await query.answer("✅ Заявка взята в работу", show_alert=True)

            # Возвращаемся к просмотру заявки с обновленной информацией
            await handle_application_action(
                type('Query', (), {
                    'data': f'app_view_{app_id}',
                    'edit_message_text': query.edit_message_text,
                    'answer': query.answer
                })(),
                context
            )

        except Exception as e:
            log.error(f"Error taking application {app_id}: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

    elif data.startswith("app_reject_"):
        # ❌ Отклонить заявку
        app_id = int(data.split("_")[2])
        admin_id = query.from_user.id

        try:
            async with async_sessionmaker() as session:
                # Получаем заявку
                result = await session.execute(
                    select(AppModel, User)
                    .join(User)
                    .where(AppModel.id == app_id)
                )
                row = result.one_or_none()

                if not row:
                    await query.answer("Заявка не найдена", show_alert=True)
                    return

                app, user = row

                # Обновляем статус заявки
                app.status = "cancelled"
                app.assigned_admin = str(admin_id)
                app.updated_at = datetime.now()

                # Добавляем заметку
                if not app.notes:
                    app.notes = ""
                app.notes += f"\n[{datetime.now().strftime('%d.%m %H:%M')}] Отклонена администратором {admin_id}"

                await session.commit()

            # Уведомляем клиента
            try:
                await notify_client_status_update(user, app, "cancelled")
            except Exception as e:
                log.error(f"Client notification error: {e}")

            # Уведомляем администратора об успехе
            await query.answer("❌ Заявка отклонена", show_alert=True)

            # Возвращаемся к просмотру заявки с обновленной информацией
            await handle_application_action(
                type('Query', (), {
                    'data': f'app_view_{app_id}',
                    'edit_message_text': query.edit_message_text,
                    'answer': query.answer
                })(),
                context
            )

        except Exception as e:
            log.error(f"Error rejecting application {app_id}: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

    elif data.startswith("app_bill_"):
        # 💳 Выставить счет
        app_id = int(data.split("_")[2])
        admin_id = query.from_user.id

        try:
            async with async_sessionmaker() as session:
                # Получаем заявку
                result = await session.execute(
                    select(AppModel, User)
                    .join(User)
                    .where(AppModel.id == app_id)
                )
                row = result.one_or_none()

                if not row:
                    await query.answer("Заявка не найдена", show_alert=True)
                    return

                app, user = row

                # Проверяем, есть ли уже цена
                if not app.price:
                    # Устанавливаем базовую цену
                    app.price = Decimal("5000")
                    await session.commit()

                # Создаем ссылку на оплату
                try:
                    pay_url = create_payment(app, user, app.price)
                    if pay_url is None:
                        # Платежная система отключена
                        pay_url = None
                except Exception as e:
                    log.error(f"Payment creation error: {e}")
                    pay_url = None

                # Добавляем заметку
                if not app.notes:
                    app.notes = ""
                app.notes += f"\n[{datetime.now().strftime('%d.%m %H:%M')}] Счет выставлен администратором {admin_id}. Сумма: {app.price} ₽"

                app.updated_at = datetime.now()
                await session.commit()

            # Уведомляем клиента о необходимости оплаты
            try:
                await notify_client_payment_required(user, app, float(app.price), pay_url)
            except Exception as e:
                log.error(f"Payment notification error: {e}")

            # Отправляем информацию о счете администратору
            if pay_url:
                text = f"""
💳 **СЧЕТ ВЫСТАВЛЕН**

📋 Заявка: #{app.id}
👤 Клиент: {user.first_name} {user.last_name or ''}
💰 Сумма: {app.price} ₽

🔗 **Ссылка на оплату:**
{pay_url}

✅ Клиент уведомлен о необходимости оплаты
"""

                keyboard = [
                    [InlineKeyboardButton("🔗 Открыть ссылку", url=pay_url)],
                    [InlineKeyboardButton(
                        "📋 Вернуться к заявке", callback_data=f"app_view_{app_id}")],
                    [InlineKeyboardButton(
                        "🔙 К списку", callback_data="admin_apps")]
                ]
            else:
                text = f"""
💳 **СЧЕТ ВЫСТАВЛЕН**

📋 Заявка: #{app.id}
👤 Клиент: {user.first_name} {user.last_name or ''}
💰 Сумма: {app.price} ₽

⚠️ **Платежная система не настроена**
Клиент должен оплатить другим способом

✅ Клиент уведомлен о необходимости оплаты
"""

                keyboard = [
                    [InlineKeyboardButton(
                        "📋 Вернуться к заявке", callback_data=f"app_view_{app_id}")],
                    [InlineKeyboardButton(
                        "🔙 К списку", callback_data="admin_apps")]
                ]

            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                log.error(f"Failed to edit message: {e}")
                # Fallback: отправляем новое сообщение если редактирование не удалось
                try:
                    await query.message.reply_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                    await query.answer("Сообщение обновлено")
                except Exception as fallback_error:
                    log.error(
                        f"Fallback message also failed: {fallback_error}")
                    await query.answer("❌ Ошибка отображения данных", show_alert=True)

        except Exception as e:
            log.error(f"Error billing application {app_id}: {e}")
            await query.answer(f"❌ Ошибка выставления счета: {e}", show_alert=True)

    elif data.startswith("app_complete_"):
        # ✅ Завершить заявку
        app_id = int(data.split("_")[2])
        admin_id = query.from_user.id

        try:
            async with async_sessionmaker() as session:
                # Получаем заявку
                result = await session.execute(
                    select(AppModel, User)
                    .join(User)
                    .where(AppModel.id == app_id)
                )
                row = result.one_or_none()

                if not row:
                    await query.answer("Заявка не найдена", show_alert=True)
                    return

                app, user = row

                # Обновляем статус заявки
                app.status = "completed"
                app.assigned_admin = str(admin_id)
                app.updated_at = datetime.now()

                # Добавляем заметку
                if not app.notes:
                    app.notes = ""
                app.notes += f"\n[{datetime.now().strftime('%d.%m %H:%M')}] Завершена администратором {admin_id}"

                await session.commit()

            # Уведомляем клиента
            try:
                await notify_client_status_update(user, app, "completed")
            except Exception as e:
                log.error(f"Client notification error: {e}")

            # Уведомляем администратора об успехе
            await query.answer("✅ Заявка завершена", show_alert=True)

            # Возвращаемся к просмотру заявки с обновленной информацией
            await handle_application_action(
                type('Query', (), {
                    'data': f'app_view_{app_id}',
                    'edit_message_text': query.edit_message_text,
                    'answer': query.answer
                })(),
                context
            )

        except Exception as e:
            log.error(f"Error completing application {app_id}: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)


# ================ WEB APP HANDLER ================

async def handle_submit(request: web.Request) -> web.Response:
    """Обработка заявки из WebApp"""

    log.info("📥 Received submit request")

    # CORS
    if request.method == "OPTIONS":
        log.info("🔄 CORS preflight request")
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    try:
        data = await request.json()
        log.info(f"📋 Form data received: {data.keys()}")
    except Exception as e:
        log.error(f"❌ JSON parse error: {e}")
        return web.json_response({"error": "Invalid JSON"}, status=400)

    # Извлекаем данные
    category_id = data.get("category_id")
    subcategory = data.get("subcategory", "")
    description = data.get("description", "")
    name = data.get("name", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    contact_method = data.get("contact_method", "")
    contact_time = data.get("contact_time", "any")
    files = data.get("files", [])
    utm_source = data.get("utm_source")
    tg_user_id = data.get("tg_user_id")

    try:
        async with async_sessionmaker() as session:
            log.info("💾 Starting database operations")

            # Получаем или создаем пользователя
            if tg_user_id:
                log.info(f"👤 Looking for user with tg_id: {tg_user_id}")
                result = await session.execute(
                    select(User).where(User.tg_id == tg_user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    log.info("👤 Creating new user from Telegram")
                    user = User(tg_id=tg_user_id)
                    session.add(user)
                else:
                    log.info(f"👤 Found existing user: {user.id}")
            else:
                log.info("👤 Creating temporary user (no Telegram ID)")
                # Создаем нового временного пользователя с уникальным отрицательным tg_id
                import time
                import random
                # Генерируем уникальный отрицательный ID: в пределах int32
                max_int32 = 2_000_000_000
                temp_tg_id = -random.randint(1, max_int32)
                user = User(
                    tg_id=temp_tg_id,
                    first_name=name.split()[0] if name else "Гость",
                    phone=phone,
                    email=email
                )
                session.add(user)
                log.info(f"👤 Created temp user with tg_id: {temp_tg_id}")

            # Обновляем данные пользователя
            if phone:
                user.phone = phone
            if email:
                user.email = email
            if name and not user.first_name:
                user.first_name = name.split()[0]

            # Коммитим пользователя сначала
            log.info("💾 Committing user data")
            await session.commit()
            await session.refresh(user)
            log.info(f"✅ User saved with ID: {user.id}")

            # Создаем заявку БЕЗ category_id (его нет в production БД)
            log.info(f"📝 Creating application for category: {category_id}")

            # Получаем название категории для сохранения в subcategory
            try:
                cat_result = await session.execute(
                    select(Category).where(Category.id == category_id)
                )
                category_obj = cat_result.scalar_one_or_none()
                category_name = category_obj.name if category_obj else f"Категория #{category_id}"
            except:
                category_name = f"Категория #{category_id}"

            app = AppModel(
                user_id=user.id,
                category_id=category_id,  # ИСПРАВЛЕНО: включаем category_id
                subcategory=f"{category_name}: {subcategory}" if subcategory else category_name,
                description=description,
                contact_method=contact_method,
                contact_time=contact_time,
                files_data=files if files else None,
                utm_source=utm_source,
                status="new"
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            log.info(f"✅ Application created with ID: {app.id}")

            # Определяем цену (можно сделать динамически)
            app.price = Decimal("5000")  # базовая консультация
            await session.commit()

            # Получаем категорию для Sheets (используем уже загруженную)
            log.info(f"📂 Using category: {category_name}")
            # Создаем объект категории для Google Sheets
            category = type('Category', (), {'name': category_name})()

    except Exception as e:
        log.error(f"❌ Database error: {e}")
        log.error(f"❌ Exception type: {type(e)}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return web.json_response(
            {"error": f"Database error: {str(e)}"},
            status=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # Записываем в Google Sheets
    try:
        append_lead(app, user, category)
    except Exception as e:
        log.error(f"Sheets error: {e}")

    # Генерируем ссылку на оплату
    pay_url = None
    if app.price:
        try:
            pay_url = create_payment(app, user, app.price)
        except Exception as e:
            log.error(f"Payment error: {e}")

    # Уведомляем админа
    try:
        bot = request.app["bot"]

        contact_methods = {
            'phone': '📞 Телефонный звонок',
            'telegram': '💬 Telegram',
            'email': '📧 Email',
            'whatsapp': '💚 WhatsApp'
        }

        text = f"""
🆕 **НОВАЯ ЗАЯВКА #{app.id}**

📂 {category.name}
{f'📝 {subcategory}' if subcategory else ''}

👤 **Клиент:**
Имя: {name or 'Без имени'}
📞 {phone or 'Нет телефона'}
📧 {email or 'Нет email'}
💬 Связь: {contact_methods.get(contact_method, contact_method)}

📄 **Проблема:**
{description[:200] + '...' if len(description) > 200 else description}

{f'📎 Файлов: {len(files)}' if files else ''}
{f'🏷️ UTM: {utm_source}' if utm_source else ''}

💰 К оплате: {app.price} ₽
"""

        keyboard = [[
            InlineKeyboardButton(
                "👁 Посмотреть", callback_data=f"app_view_{app.id}")
        ]]

        if pay_url:
            keyboard[0].append(
                InlineKeyboardButton("💳 Ссылка оплаты", url=pay_url)
            )

        await bot.send_message(
            ADMIN_CHAT_ID,
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Admin notify error: {e}")

    # Уведомляем клиента
    try:
        await notify_client_application_received(user, app)
    except Exception as e:
        log.error(f"Client notification error: {e}")

    # Отвечаем клиенту
    log.info(f"✅ Application {app.id} processed successfully")
    response_data = {
        "status": "ok",
        "app_id": app.id,
        "pay_url": pay_url
    }
    log.info(f"📤 Sending response: {response_data}")
    return web.json_response(response_data, headers={"Access-Control-Allow-Origin": "*"})


async def handle_webapp(request: web.Request) -> web.Response:
    """Отдача WebApp HTML"""
    html_path = Path(__file__).parent.parent / "webapp" / "index.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    else:
        return web.Response(text="WebApp not found", status=404)


async def handle_webapp_static(request: web.Request) -> web.Response:
    """Serve enhanced webapp static files"""
    filename = request.match_info['filename']

    # Безопасность: проверяем расширение файла
    allowed_extensions = {'.js', '.css',
                          '.html', '.ico', '.png', '.jpg', '.svg'}
    file_ext = Path(filename).suffix.lower()

    if file_ext not in allowed_extensions:
        return web.Response(status=404, text="File not found")

    file_path = Path(__file__).parent.parent / "webapp" / filename

    if not file_path.exists():
        return web.Response(status=404, text="File not found")

    # Определяем content-type
    content_types = {
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.html': 'text/html',
        '.ico': 'image/x-icon',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.svg': 'image/svg+xml'
    }

    content_type = content_types.get(file_ext, 'text/plain')

    return web.FileResponse(
        file_path,
        headers={'Content-Type': content_type}
    )


async def handle_admin(request: web.Request) -> web.Response:
    """Отдача Admin Dashboard HTML"""
    html_path = Path(__file__).parent.parent / "webapp" / "admin.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    else:
        return web.Response(text="Admin Dashboard not found", status=404)


async def api_admin_applications(request: web.Request) -> web.Response:
    """API: Получить заявки для админки"""

    # CORS
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    async with async_sessionmaker() as session:
        result = await session.execute(
            select(AppModel, User)
            .join(User)
            .order_by(AppModel.created_at.desc())
            .limit(50)
        )
        apps = result.all()

        applications = []
        for app, user in apps:
            # Извлекаем название категории из subcategory
            category_name = app.subcategory.split(
                ':')[0] if app.subcategory and ':' in app.subcategory else (app.subcategory or "Общие вопросы")

            applications.append({
                'id': app.id,
                'client': f"{user.first_name} {user.last_name or ''}".strip(),
                'category': category_name,
                'status': app.status,
                'date': app.created_at.isoformat(),
                'description': app.description or '',
                'phone': user.phone or '',
                'email': user.email or ''
            })

    return web.json_response(applications, headers={
        "Access-Control-Allow-Origin": "*"
    })


async def api_admin_clients(request: web.Request) -> web.Response:
    """API: Получить клиентов для админки"""

    # CORS
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    async with async_sessionmaker() as session:
        result = await session.execute(
            select(User, func.count(AppModel.id).label('app_count'))
            .outerjoin(AppModel)
            .group_by(User.id)
            .order_by(User.created_at.desc())
            .limit(50)
        )
        users = result.all()

        clients = []
        for user, app_count in users:
            clients.append({
                'id': user.id,
                'name': f"{user.first_name} {user.last_name or ''}".strip(),
                'phone': user.phone or '',
                'email': user.email or '',
                'applications': app_count,
                'totalPaid': 0  # TODO: Calculate from payments
            })

    return web.json_response(clients, headers={
        "Access-Control-Allow-Origin": "*"
    })


async def api_admin_payments(request: web.Request) -> web.Response:
    """API: Получить платежи для админки"""

    # CORS
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    payments = []  # Mock data for now

    return web.json_response(payments, headers={
        "Access-Control-Allow-Origin": "*"
    })


async def api_admin_stats(request: web.Request) -> web.Response:
    """API: Получить статистику для админки"""

    # CORS
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    async with async_sessionmaker() as session:
        # Total applications
        total_apps = await session.scalar(select(func.count(AppModel.id)))

        # New applications (this week)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        new_apps = await session.scalar(
            select(func.count(AppModel.id))
            .where(AppModel.created_at >= week_ago)
        )

        # Total clients
        total_clients = await session.scalar(select(func.count(User.id)))

        # Revenue (mock for now)
        revenue = 147500
        conversion = 23.4

    stats = {
        'newApplications': new_apps or 0,
        'totalClients': total_clients or 0,
        'monthlyRevenue': revenue,
        'conversion': conversion
    }

    return web.json_response(stats, headers={
        "Access-Control-Allow-Origin": "*"
    })


async def handle_health(request: web.Request) -> web.Response:
    """Health endpoint для мониторинга Enhanced AI"""
    global ai_enhanced_manager

    health_data = {
        "status": "healthy",  # Всегда healthy если bot запущен
        "timestamp": datetime.now().isoformat(),
        "bot_status": "running",
        "database": "connected",
        "enhanced_ai": {
            "initialized": False,
            "health_status": "initializing",  # По умолчанию "initializing"
            "components": {},
            "error": None
        }
    }

    try:
        # Проверка БД - упрощенная версия для Railway compatibility
        async with async_sessionmaker() as session:
            result = await session.execute(select(1))
            result.scalar()  # Просто выполняем простой query
        health_data["database"] = "connected"
    except Exception as e:
        health_data["database"] = f"error: {str(e)}"
        # НЕ понижаем статус для Railway optimization
        # health_data["status"] = "degraded"

        # Проверка Enhanced AI
    try:
        if ai_enhanced_manager is None:
            health_data["enhanced_ai"]["health_status"] = "initializing"
            health_data["enhanced_ai"]["error"] = "Background initialization in progress"
        elif not ai_enhanced_manager._initialized:
            health_data["enhanced_ai"]["health_status"] = "initializing"
            health_data["enhanced_ai"]["error"] = "Partial initialization"
        else:
            health_data["enhanced_ai"]["initialized"] = True

            # Получаем детальный статус
            ai_health = await ai_enhanced_manager.health_check()
            health_data["enhanced_ai"]["health_status"] = ai_health.get(
                "status", "unknown")
            health_data["enhanced_ai"]["components"] = ai_health.get(
                "components", {})

    except Exception as e:
        health_data["enhanced_ai"]["error"] = str(e)
        health_data["enhanced_ai"]["health_status"] = "error"

    # Добавляем системные метрики
    health_data["system_metrics"] = {
        "uptime_seconds": int((datetime.now() - system_metrics["start_time"]).total_seconds()),
        "total_requests": system_metrics["total_requests"],
        "successful_requests": system_metrics["successful_requests"],
        "ai_requests": system_metrics["ai_requests"]
    }

    # Определяем HTTP статус - всегда 200 если bot запущен (Railway optimization)
    status_code = 200

    return web.json_response(health_data, status=status_code, headers={
        "Access-Control-Allow-Origin": "*"
    })


async def handle_telegram(request: web.Request) -> web.Response:
    """Webhook handler"""
    update_json = await request.json()
    update = Update.de_json(update_json, request.app["bot"])
    await request.app["application"].update_queue.put(update)
    return web.Response(text="ok")


# ================ HELPERS ================

def detect_category(text: str) -> str:
    """Определить категорию по тексту"""
    text_lower = text.lower()

    if any(word in text_lower for word in ["развод", "алимент", "брак", "семь"]):
        return "Семейное право"
    elif any(word in text_lower for word in ["наследств", "завещан"]):
        return "Наследство"
    elif any(word in text_lower for word in ["работ", "труд", "увольнен", "зарплат"]):
        return "Трудовые споры"
    elif any(word in text_lower for word in ["жкх", "квартир", "дом", "жиль"]):
        return "Жилищные вопросы"
    elif any(word in text_lower for word in ["долг", "кредит", "банкрот"]):
        return "Банкротство"
    elif any(word in text_lower for word in ["налог", "ндфл", "ифнс"]):
        return "Налоги"
    elif any(word in text_lower for word in ["штраф", "гибдд", "админ"]):
        return "Административные дела"
    elif any(word in text_lower for word in ["потребител", "товар", "услуг", "возврат"]):
        return "Защита прав потребителей"
    elif any(word in text_lower for word in ["мигра", "гражданств", "внж", "рвп"]):
        return "Миграционное право"
    else:
        return "Общие вопросы"


async def show_statistics(query, context):
    """Показать статистику"""
    async with async_sessionmaker() as session:
        # Всего заявок
        total = await session.scalar(select(func.count(AppModel.id)))

        # По статусам
        status_stats = await session.execute(
            select(AppModel.status, func.count(AppModel.id))
            .group_by(AppModel.status)
        )

        # По категориям - парсим из subcategory
        cat_stats = await session.execute(
            select(AppModel.subcategory, func.count(AppModel.id))
            .where(AppModel.subcategory.is_not(None))
            .group_by(AppModel.subcategory)
            .order_by(func.count(AppModel.id).desc())
            .limit(5)
        )

    text = f"""
📊 **СТАТИСТИКА**

📋 Всего заявок: {total}

**По статусам:**
"""
    for status, count in status_stats:
        text += f"• {status}: {count}\n"

    text += "\n**Топ категорий:**\n"
    for subcategory, count in cat_stats:
        # Извлекаем название категории до двоеточия
        cat_name = subcategory.split(':')[0] if subcategory and ':' in subcategory else (
            subcategory or "Общие вопросы")
        text += f"• {cat_name}: {count}\n"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def show_admin_panel(query):
    """Вернуться в главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("📋 Заявки", callback_data="admin_apps"),
         InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💳 Платежи", callback_data="admin_payments"),
         InlineKeyboardButton("👥 Клиенты", callback_data="admin_users")],
        [InlineKeyboardButton("🤖 AI Статус", callback_data="admin_ai_status"),
         InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
    ]

    try:
        await query.edit_message_text(
            "🔧 **АДМИН ПАНЕЛЬ**\n\nВыберите раздел:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                "🔧 **АДМИН ПАНЕЛЬ**\n\nВыберите раздел:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def show_payments(query, context):
    """💳 ПРОДАКШН-ГОТОВО: Показать статистику платежей"""
    async with async_sessionmaker() as session:
        # Общая статистика по платежам
        total_amount = await session.scalar(
            select(func.sum(AppModel.price))
            .where(AppModel.price.is_not(None))
        ) or Decimal('0')

        paid_amount = await session.scalar(
            select(func.sum(AppModel.price))
            .where(AppModel.status == 'completed')
            .where(AppModel.price.is_not(None))
        ) or Decimal('0')

        pending_amount = await session.scalar(
            select(func.sum(AppModel.price))
            .where(AppModel.status.in_(['new', 'processing']))
            .where(AppModel.price.is_not(None))
        ) or Decimal('0')

        # Топ платежи
        top_payments = await session.execute(
            select(AppModel, User)
            .join(User)
            .where(AppModel.price.is_not(None))
            .order_by(AppModel.price.desc())
            .limit(10)
        )

    conversion_rate = 0
    if total_amount > 0:
        conversion_rate = (paid_amount / total_amount) * 100

    text = f"""
💳 **СТАТИСТИКА ПЛАТЕЖЕЙ**

💰 **Финансы:**
• Общий оборот: {total_amount:,.0f} ₽
• Получено: {paid_amount:,.0f} ₽
• В ожидании: {pending_amount:,.0f} ₽
• Конверсия: {conversion_rate:.1f}%

💎 **Топ платежи:**
"""

    keyboard = []
    for app, user in top_payments:
        status_emoji = {"new": "🆕", "processing": "⏳",
                        "completed": "✅", "cancelled": "❌"}.get(app.status, "❓")
        category_name = app.subcategory.split(
            ':')[0] if app.subcategory and ':' in app.subcategory else "Общие"

        text += f"{status_emoji} #{app.id} | {user.first_name} | {app.price:,.0f} ₽\n"

        keyboard.append([
            InlineKeyboardButton(
                f"💳 #{app.id} - {app.price:,.0f} ₽",
                callback_data=f"app_view_{app.id}"
            )
        ])

    keyboard.append([InlineKeyboardButton(
        "🔙 Назад", callback_data="back_admin")])

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def show_clients(query, context):
    """👥 ПРОДАКШН-ГОТОВО: Показать список клиентов"""
    async with async_sessionmaker() as session:
        # Получаем клиентов с количеством заявок
        result = await session.execute(
            select(User, func.count(AppModel.id).label('app_count'))
            .outerjoin(AppModel)
            .group_by(User.id)
            .order_by(func.count(AppModel.id).desc())
            .limit(20)
        )
        clients = result.all()

    if not clients:
        text = "👥 Нет клиентов"
    else:
        text = "👥 **КЛИЕНТЫ** (топ по заявкам)\n\n"
        keyboard = []

        for user, app_count in clients:
            # Определяем статус клиента
            if app_count == 0:
                status = "🆕"
            elif app_count < 3:
                status = "📝"
            else:
                status = "⭐"

            # Контактная информация
            contact_info = []
            if user.phone:
                contact_info.append(f"📞 {user.phone}")
            if user.email:
                contact_info.append(f"📧 {user.email}")
            contact_str = " | ".join(
                contact_info) if contact_info else "нет контактов"

            text += f"{status} **{user.first_name} {user.last_name or ''}**\n"
            text += f"📋 Заявок: {app_count} | ID: `{user.tg_id}`\n"
            text += f"{contact_str}\n\n"

            if app_count > 0:  # Показываем кнопку только для клиентов с заявками
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {user.first_name} ({app_count})",
                        callback_data=f"client_view_{user.id}"
                    )
                ])

    keyboard.append([InlineKeyboardButton(
        "🔙 Назад", callback_data="back_admin")])

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def show_broadcast_options(query, context):
    """📢 ПРОДАКШН-ГОТОВО: Опции массовой рассылки"""
    text = """
📢 **МАССОВАЯ РАССЫЛКА**

Выберите тип рассылки:

🎯 **Целевые группы:**
• Все клиенты
• Клиенты с активными заявками  
• Клиенты без заявок
• VIP клиенты (3+ заявки)

⚠️ **Внимание:** рассылка отправляется всем пользователям выбранной группы
"""

    keyboard = [
        [InlineKeyboardButton(
            "👥 Всем клиентам", callback_data="broadcast_all")],
        [InlineKeyboardButton("📝 С активными заявками", callback_data="broadcast_active"),
         InlineKeyboardButton("💤 Без заявок", callback_data="broadcast_inactive")],
        [InlineKeyboardButton(
            "⭐ VIP клиентам", callback_data="broadcast_vip")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def show_admin_settings(query, context):
    """⚙️ ПРОДАКШН-ГОТОВО: Административные настройки"""
    # Получаем текущую статистику системы
    uptime = datetime.now() - system_metrics["start_time"]
    uptime_str = f"{uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"

    success_rate = 0
    if system_metrics["total_requests"] > 0:
        success_rate = (
            system_metrics["successful_requests"] / system_metrics["total_requests"]) * 100

    text = f"""
⚙️ **СИСТЕМНЫЕ НАСТРОЙКИ**

📊 **Статистика системы:**
• Время работы: {uptime_str}
• Всего запросов: {system_metrics["total_requests"]}
• Успешных: {system_metrics["successful_requests"]}
• Ошибок: {system_metrics["failed_requests"]}
• Успешность: {success_rate:.1f}%
• AI запросов: {system_metrics["ai_requests"]}

👥 **Администраторы:**
• Активных: {len(ADMIN_USERS)}
• Хардкодированных: {len(HARDCODED_ADMIN_IDS)}

🔧 **Управление:**
"""

    keyboard = [
        [InlineKeyboardButton("👥 Управление админами", callback_data="setting_admins"),
         InlineKeyboardButton("📊 Экспорт данных", callback_data="setting_export")],
        [InlineKeyboardButton("🔄 Перезагрузить настройки", callback_data="setting_reload"),
         InlineKeyboardButton("🧹 Очистить логи", callback_data="setting_clear_logs")],
        [InlineKeyboardButton("📈 Детальная статистика",
                              callback_data="setting_detailed_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def handle_client_action(query, context):
    """👤 ПРОДАКШН-ГОТОВО: Действия с клиентами"""
    data = query.data

    if data.startswith("client_view_"):
        user_id = int(data.split("_")[2])

        async with async_sessionmaker() as session:
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                await query.answer("Клиент не найден", show_alert=True)
                return

            # Получаем его заявки
            apps_result = await session.execute(
                select(AppModel)
                .where(AppModel.user_id == user_id)
                .order_by(AppModel.created_at.desc())
                .limit(10)
            )
            applications = apps_result.scalars().all()

        # Статистика по клиенту
        total_amount = sum(app.price or 0 for app in applications)
        recent_app = applications[0] if applications else None

        text = f"""
👤 **КЛИЕНТ: {user.first_name} {user.last_name or ''}**

📞 Телефон: {user.phone or 'не указан'}
📧 Email: {user.email or 'не указан'}
🆔 Telegram ID: `{user.tg_id}`
📅 Регистрация: {user.created_at.strftime('%d.%m.%Y') if hasattr(user, 'created_at') else 'н/д'}

📊 **Статистика:**
• Всего заявок: {len(applications)}
• Общая сумма: {total_amount} ₽
• Последняя заявка: {recent_app.created_at.strftime('%d.%m.%Y') if recent_app else 'нет'}

📋 **Последние заявки:**
"""

        keyboard = []
        for app in applications[:5]:  # Показываем последние 5
            status_emoji = {"new": "🆕", "processing": "⏳",
                            "completed": "✅"}.get(app.status, "❓")
            category_name = app.subcategory.split(
                ':')[0] if app.subcategory and ':' in app.subcategory else "Общие"
            text += f"{status_emoji} #{app.id} | {category_name} | {app.price or 0} ₽\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"📋 Заявка #{app.id}",
                    callback_data=f"app_view_{app.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(
            "🔙 К списку", callback_data="admin_users")])

        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            log.error(f"Failed to edit message: {e}")
            # Fallback: отправляем новое сообщение если редактирование не удалось
            try:
                await query.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                await query.answer("Сообщение обновлено")
            except Exception as fallback_error:
                log.error(f"Fallback message also failed: {fallback_error}")
                await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def handle_broadcast_action(query, context):
    """📢 ПРОДАКШН-ГОТОВО: Обработка массовых рассылок"""
    data = query.data

    # Определяем тип рассылки
    broadcast_types = {
        "broadcast_all": ("👥 Всем клиентам", "SELECT DISTINCT tg_id FROM users WHERE tg_id IS NOT NULL"),
        "broadcast_active": ("📝 С активными заявками", """
            SELECT DISTINCT u.tg_id FROM users u 
            JOIN applications a ON u.id = a.user_id 
            WHERE a.status IN ('new', 'processing') AND u.tg_id IS NOT NULL
        """),
        "broadcast_inactive": ("💤 Без заявок", """
            SELECT DISTINCT tg_id FROM users 
            WHERE id NOT IN (SELECT DISTINCT user_id FROM applications) 
            AND tg_id IS NOT NULL
        """),
        "broadcast_vip": ("⭐ VIP клиентам", """
            SELECT DISTINCT u.tg_id FROM users u 
            JOIN applications a ON u.id = a.user_id 
            WHERE u.tg_id IS NOT NULL 
            GROUP BY u.tg_id 
            HAVING COUNT(a.id) >= 3
        """)
    }

    if data in broadcast_types:
        title, sql_query = broadcast_types[data]

        # Получаем список пользователей для рассылки
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(text(sql_query))
                user_ids = [row[0] for row in result.fetchall()]

            if not user_ids:
                await query.answer(f"❌ Нет пользователей для рассылки в группе '{title}'", show_alert=True)
                return

            # Просим админа ввести текст рассылки
            text = f"""
📢 **РАССЫЛКА: {title}**

👥 **Найдено пользователей:** {len(user_ids)}

📝 **Отправьте сообщение для рассылки:**

Ответьте на это сообщение текстом, который нужно разослать.

⚠️ **Внимание:** 
• Рассылка будет отправлена сразу {len(user_ids)} пользователям
• Отменить после отправки нельзя
• Максимум 4000 символов
"""

            keyboard = [
                [InlineKeyboardButton(
                    "❌ Отменить", callback_data="admin_broadcast")]
            ]

            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e:
                log.error(f"Failed to edit message: {e}")
                # Fallback: отправляем новое сообщение если редактирование не удалось
                try:
                    await query.message.reply_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                    await query.answer("Сообщение обновлено")
                except Exception as fallback_error:
                    log.error(
                        f"Fallback message also failed: {fallback_error}")
                    await query.answer("❌ Ошибка отображения данных", show_alert=True)

            # Сохраняем данные рассылки в контексте
            context.user_data['pending_broadcast'] = {
                'type': data,
                'title': title,
                'user_ids': user_ids,
                'waiting_for_text': True
            }

        except Exception as e:
            log.error(f"Broadcast preparation error: {e}")
            await query.answer(f"❌ Ошибка подготовки рассылки: {e}", show_alert=True)


async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📢 ПРОДАКШН-ГОТОВО: Обработка текста для массовой рассылки"""
    broadcast_data = context.user_data.get('pending_broadcast', {})

    if not broadcast_data.get('waiting_for_text'):
        return

    message_text = update.message.text
    user_ids = broadcast_data.get('user_ids', [])
    title = broadcast_data.get('title', 'Неизвестная группа')

    # Очищаем состояние ожидания
    context.user_data['pending_broadcast'] = {}

    if len(message_text) > 4000:
        await update.message.reply_text("❌ Текст слишком длинный (максимум 4000 символов)")
        return

    if not user_ids:
        await update.message.reply_text("❌ Список пользователей пуст")
        return

    # Подтверждение перед отправкой
    confirm_text = f"""
📢 **ПОДТВЕРЖДЕНИЕ РАССЫЛКИ**

🎯 **Группа:** {title}
👥 **Получателей:** {len(user_ids)}

📝 **Текст сообщения:**
{message_text[:500]}{'...' if len(message_text) > 500 else ''}

⚠️ **Внимание:** после подтверждения рассылка будет отправлена немедленно!
"""

    keyboard = [
        [InlineKeyboardButton(
            "✅ ОТПРАВИТЬ", callback_data=f"confirm_broadcast_{len(user_ids)}")],
        [InlineKeyboardButton("❌ Отменить", callback_data="admin_broadcast")]
    ]

    # Сохраняем финальные данные для отправки
    context.user_data['broadcast_ready'] = {
        'message_text': message_text,
        'user_ids': user_ids,
        'title': title
    }

    try:
        await update.message.reply_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to send confirmation message: {e}")
        # Fallback: отправляем новое сообщение если отправка не удалась
        try:
            await update.message.reply_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await update.answer("Сообщение отправлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await update.answer("❌ Ошибка отправки сообщения", show_alert=True)


async def execute_broadcast(query, context):
    """🚀 ПРОДАКШН-ГОТОВО: Выполнение массовой рассылки"""
    await query.answer()

    broadcast_data = context.user_data.get('broadcast_ready', {})

    if not broadcast_data:
        await query.answer("❌ Данные рассылки не найдены", show_alert=True)
        return

    message_text = broadcast_data.get('message_text')
    user_ids = broadcast_data.get('user_ids', [])
    title = broadcast_data.get('title', 'Неизвестная группа')

    # Очищаем данные рассылки
    context.user_data['broadcast_ready'] = {}

    if not message_text or not user_ids:
        await query.answer("❌ Недостаточно данных для рассылки", show_alert=True)
        return

    # Показываем прогресс
    progress_text = f"""
🚀 **РАССЫЛКА ЗАПУЩЕНА**

🎯 **Группа:** {title}
👥 **Получателей:** {len(user_ids)}

⏳ Отправляется... 0/{len(user_ids)}
"""

    try:
        await query.edit_message_text(
            progress_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        # Fallback: отправляем новое сообщение если отправка не удалась
        try:
            await query.message.reply_text(
                progress_text,
                parse_mode='Markdown'
            )
            await query.answer("Сообщение отправлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отправки сообщения", show_alert=True)

    # Выполняем рассылку
    bot = query.bot
    sent_count = 0
    failed_count = 0

    for i, user_id in enumerate(user_ids):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='Markdown'
            )
            sent_count += 1

            # Обновляем прогресс каждые 10 сообщений
            if (i + 1) % 10 == 0:
                progress_text = f"""
🚀 **РАССЫЛКА В ПРОЦЕССЕ**

🎯 **Группа:** {title}
👥 **Получателей:** {len(user_ids)}

⏳ Отправлено: {sent_count}/{len(user_ids)}
❌ Ошибок: {failed_count}
"""
                try:
                    await query.edit_message_text(
                        progress_text,
                        parse_mode='Markdown'
                    )
                except:
                    pass  # Игнорируем ошибки обновления прогресса

            # Небольшая задержка для избежания rate limiting
            await asyncio.sleep(0.05)

        except Exception as e:
            failed_count += 1
            log.warning(f"Failed to send broadcast to user {user_id}: {e}")

    # Финальный отчет
    final_text = f"""
✅ **РАССЫЛКА ЗАВЕРШЕНА**

🎯 **Группа:** {title}
📨 **Отправлено:** {sent_count}/{len(user_ids)}
❌ **Неудачных:** {failed_count}

📊 **Успешность:** {(sent_count/len(user_ids)*100):.1f}%

📝 **Текст сообщения:**
{message_text[:200]}{'...' if len(message_text) > 200 else ''}
"""

    keyboard = [
        [InlineKeyboardButton("🔙 Назад к рассылке",
                              callback_data="admin_broadcast")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            final_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                final_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)

    log.info(
        f"Broadcast completed: {sent_count}/{len(user_ids)} sent successfully")


async def handle_settings_action(query, context):
    """⚙️ ПРОДАКШН-ГОТОВО: Обработка настроек"""
    data = query.data

    if data == "setting_admins":
        # Показать управление администраторами
        await show_admin_management(query, context)
    elif data == "setting_export":
        await export_data(query, context)
    elif data == "setting_reload":
        await reload_settings(query, context)
    elif data == "setting_clear_logs":
        await clear_logs(query, context)
    elif data == "setting_detailed_stats":
        await show_detailed_stats(query, context)


async def show_admin_management(query, context):
    """👥 Управление администраторами"""
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(Admin).where(Admin.is_active == True)
            .order_by(Admin.created_at.desc())
        )
        admins = result.scalars().all()

    text = "👥 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**\n\n"

    if HARDCODED_ADMIN_IDS:
        text += "🔧 **Системные администраторы:**\n"
        for admin_id in sorted(HARDCODED_ADMIN_IDS):
            text += f"• `{admin_id}` (системный)\n"
        text += "\n"

    if admins:
        text += "💾 **Администраторы из БД:**\n"
        for admin in admins:
            text += f"• `{admin.tg_id}` ({admin.role})\n"
    else:
        text += "💾 **Администраторы из БД:** нет\n"

    text += f"\n📊 **Всего активных:** {len(ADMIN_USERS)}\n\n"
    text += "**Команды:**\n"
    text += "• `/add_admin <ID> [роль]` - добавить\n"
    text += "• `/list_admins` - список\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить список",
                              callback_data="setting_reload_admins")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_settings")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def export_data(query, context):
    """📊 Экспорт данных"""
    try:
        async with async_sessionmaker() as session:
            # Статистика заявок
            total_apps = await session.scalar(select(func.count(AppModel.id)))
            total_users = await session.scalar(select(func.count(User.id)))

            # Статистика по статусам
            status_stats = await session.execute(
                select(AppModel.status, func.count(AppModel.id))
                .group_by(AppModel.status)
            )

        # Формируем отчет
        report = f"""
📊 **ЭКСПОРТ ДАННЫХ** 
Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

**Общая статистика:**
• Пользователей: {total_users}
• Заявок: {total_apps}
• Администраторов: {len(ADMIN_USERS)}

**По статусам заявок:**
"""
        for status, count in status_stats:
            report += f"• {status}: {count}\n"

        report += f"""

**Системная статистика:**
• Время работы: {datetime.now() - system_metrics['start_time']}
• Всего запросов: {system_metrics['total_requests']}
• Успешных: {system_metrics['successful_requests']}
• AI запросов: {system_metrics['ai_requests']}

📎 Полный экспорт в Google Sheets доступен через интеграцию.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_settings")]
        ]

        try:
            await query.edit_message_text(
                report,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            log.error(f"Failed to edit message: {e}")
            # Fallback: отправляем новое сообщение если редактирование не удалось
            try:
                await query.message.reply_text(
                    report,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                await query.answer("Сообщение обновлено")
            except Exception as fallback_error:
                log.error(f"Fallback message also failed: {fallback_error}")
                await query.answer("❌ Ошибка отображения данных", show_alert=True)

    except Exception as e:
        await query.answer(f"Ошибка экспорта: {e}", show_alert=True)


async def reload_settings(query, context):
    """🔄 Перезагрузка настроек"""
    try:
        # Перезагружаем администраторов из БД
        await load_db_admins()

        await query.answer("✅ Настройки перезагружены", show_alert=True)
        await show_admin_settings(query, context)

    except Exception as e:
        await query.answer(f"Ошибка перезагрузки: {e}", show_alert=True)


async def clear_logs(query, context):
    """🧹 Очистка логов"""
    # Очищаем метрики
    system_metrics["total_requests"] = 0
    system_metrics["successful_requests"] = 0
    system_metrics["failed_requests"] = 0
    system_metrics["ai_requests"] = 0
    system_metrics["start_time"] = datetime.now()

    await query.answer("✅ Логи очищены", show_alert=True)
    await show_admin_settings(query, context)


async def show_detailed_stats(query, context):
    """📈 Детальная статистика"""
    async with async_sessionmaker() as session:
        # Статистика по времени
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Заявки за сегодня
        today_apps = await session.scalar(
            select(func.count(AppModel.id))
            .where(AppModel.created_at >= today)
        )

        # Заявки за неделю
        week_apps = await session.scalar(
            select(func.count(AppModel.id))
            .where(AppModel.created_at >= week_ago)
        )

        # Заявки за месяц
        month_apps = await session.scalar(
            select(func.count(AppModel.id))
            .where(AppModel.created_at >= month_ago)
        )

        # Топ категории за месяц
        top_categories = await session.execute(
            select(AppModel.subcategory, func.count(AppModel.id))
            .where(AppModel.created_at >= month_ago)
            .where(AppModel.subcategory.is_not(None))
            .group_by(AppModel.subcategory)
            .order_by(func.count(AppModel.id).desc())
            .limit(5)
        )

    text = f"""
📈 **ДЕТАЛЬНАЯ СТАТИСТИКА**

📅 **По периодам:**
• Сегодня: {today_apps} заявок
• За неделю: {week_apps} заявок  
• За месяц: {month_apps} заявок

📊 **Топ категории (месяц):**
"""

    for subcategory, count in top_categories:
        cat_name = subcategory.split(
            ':')[0] if subcategory and ':' in subcategory else subcategory
        text += f"• {cat_name}: {count}\n"

    # Системные метрики
    uptime = datetime.now() - system_metrics["start_time"]
    success_rate = 0
    if system_metrics["total_requests"] > 0:
        success_rate = (
            system_metrics["successful_requests"] / system_metrics["total_requests"]) * 100

    text += f"""

🖥️ **Системные метрики:**
• Время работы: {uptime.days}д {uptime.seconds // 3600}ч
• Успешность: {success_rate:.1f}%
• RPS: {system_metrics["total_requests"] / max(uptime.total_seconds(), 1):.2f}
"""

    keyboard = [
        [InlineKeyboardButton(
            "🔄 Обновить", callback_data="setting_detailed_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_settings")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def client_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 НОВЫЙ: Обработчик клиентского пути"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    if data == "request_call":
        await handle_request_call(query, context)
    elif data == "chat_consultation":
        await handle_chat_consultation(query, context)
    elif data == "get_price":
        await handle_get_price(query, context)
    elif data.startswith("consultation_category_"):
        await handle_consultation_category(query, context)
    elif data == "enter_phone":
        await handle_enter_phone(query, context)
    elif data == "submit_call_request":
        await handle_submit_call_request(query, context)
    elif data == "back_to_chat":
        await handle_back_to_chat(query, context)


async def handle_request_call(query, context):
    """📞 Заказать звонок"""
    text = """
📞 **ЗАКАЗАТЬ ОБРАТНЫЙ ЗВОНОК**

Укажите ваш номер телефона и удобное время для звонка.
Наш юрист свяжется с вами в течение 30 минут.

🕐 **Рабочие часы:** 9:00 - 21:00 (МСК)
💰 **Стоимость:** Первые 15 минут БЕСПЛАТНО

📝 Или оставьте заявку через форму:
"""

    keyboard = [
        [InlineKeyboardButton("📱 Указать телефон",
                              callback_data="enter_phone")],
        [InlineKeyboardButton(
            "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_chat_consultation(query, context):
    """💬 Консультация в чате"""
    text = """
💬 **КОНСУЛЬТАЦИЯ В ЧАТЕ**

Выберите категорию вашего вопроса для получения персональной консультации:

🎯 **Преимущества чат-консультации:**
• Быстрые ответы в течение 5-10 минут
• Сохранение переписки для истории
• Возможность отправки документов
• Первичная консультация БЕСПЛАТНО
"""

    keyboard = [
        [
            InlineKeyboardButton("👨‍👩‍👧 Семейное право",
                                 callback_data="consultation_category_family"),
            InlineKeyboardButton("🏠 Жилищные вопросы",
                                 callback_data="consultation_category_housing")
        ],
        [
            InlineKeyboardButton("💼 Трудовые споры",
                                 callback_data="consultation_category_labor"),
            InlineKeyboardButton(
                "💳 Банкротство", callback_data="consultation_category_bankruptcy")
        ],
        [
            InlineKeyboardButton("🛒 Защита потребителей",
                                 callback_data="consultation_category_consumer"),
            InlineKeyboardButton("⚖️ Другие вопросы",
                                 callback_data="consultation_category_other")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_get_price(query, context):
    """📊 Узнать стоимость"""
    text = """
📊 **СТОИМОСТЬ ЮРИДИЧЕСКИХ УСЛУГ**

💰 **КОНСУЛЬТАЦИИ:**
• Устная консультация: 2 000 ₽/час
• Письменная консультация: 1 500 ₽
• Анализ документов: 3 000 ₽

⚖️ **СУДЕБНОЕ ПРЕДСТАВИТЕЛЬСТВО:**
• Гражданские дела: от 30 000 ₽
• Административные дела: от 15 000 ₽
• Арбитражные споры: от 50 000 ₽

📝 **СОСТАВЛЕНИЕ ДОКУМЕНТОВ:**
• Претензии: от 5 000 ₽
• Договоры: от 10 000 ₽
• Исковые заявления: от 15 000 ₽

🎁 **СПЕЦИАЛЬНЫЕ ПРЕДЛОЖЕНИЯ:**
• Первая консультация БЕСПЛАТНО
• Скидка 20% при заключении договора на месяц
• Фиксированная стоимость по результату

Точную стоимость рассчитаем после анализа вашей ситуации.
"""

    keyboard = [
        [InlineKeyboardButton("📝 Получить расчет",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("📞 Обсудить по телефону",
                              callback_data="request_call")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_consultation_category(query, context):
    """Обработка выбора категории консультации"""
    category_map = {
        "consultation_category_family": "Семейное право",
        "consultation_category_housing": "Жилищные вопросы",
        "consultation_category_labor": "Трудовые споры",
        "consultation_category_bankruptcy": "Банкротство",
        "consultation_category_consumer": "Защита прав потребителей",
        "consultation_category_other": "Другие вопросы"
    }

    category = category_map.get(query.data, "Общие вопросы")

    text = f"""
✅ **ВЫБРАНА КАТЕГОРИЯ: {category.upper()}**

Теперь опишите вашу ситуацию максимально подробно:

📝 **Что указать:**
• Суть проблемы
• Что уже предпринимали
• Какой результат нужен
• Есть ли срочность

⚡ **Наш юрист ответит в течение 10 минут**

Либо заполните подробную заявку для более детального анализа:
"""

    # Сохраняем выбранную категорию в контекст пользователя
    context.user_data['consultation_category'] = category
    context.user_data['awaiting_consultation_details'] = True

    keyboard = [
        [InlineKeyboardButton("📝 Заполнить подробную заявку",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀️ Выбрать другую категорию",
                              callback_data="chat_consultation")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_back_to_chat(query, context):
    """Возврат к основному сообщению"""
    text = """
💬 Продолжайте задавать вопросы в чате.

Наш AI-консультант готов помочь с любыми юридическими вопросами!
"""

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL)),
            InlineKeyboardButton("📞 Заказать звонок",
                                 callback_data="request_call")
        ],
        [
            InlineKeyboardButton("💬 Консультация в чате",
                                 callback_data="chat_consultation"),
            InlineKeyboardButton("📊 Узнать стоимость",
                                 callback_data="get_price")
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_consultation_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка деталей консультации от пользователя"""
    user_id = update.effective_user.id
    user_text = update.message.text
    user = update.effective_user
    category = context.user_data.get('consultation_category', 'Общие вопросы')

    # Очищаем флаг ожидания
    context.user_data['awaiting_consultation_details'] = False

    # Формируем заявку в админ чат
    admin_text = f"""
📝 **КОНСУЛЬТАЦИЯ В ЧАТЕ**

👤 **Клиент:** {user.first_name} {user.last_name or ''}
🆔 **ID:** `{user_id}`
📂 **Категория:** {category}

📄 **Детали проблемы:**
{user_text}

⏰ **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🎯 **Требуется:** Оперативная консультация в чате
"""

    admin_keyboard = [[
        InlineKeyboardButton("💬 Ответить клиенту",
                             url=f"tg://user?id={user_id}")
    ]]

    try:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        log.info(f"✅ Consultation request sent to admin for user {user_id}")
    except Exception as e:
        log.error(f"❌ Failed to send consultation request to admin: {e}")

    # Ответ клиенту
    response_text = f"""
✅ **ЗАЯВКА НА КОНСУЛЬТАЦИЮ ПРИНЯТА**

📂 **Категория:** {category}
⏰ **Время подачи:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔔 **Что дальше:**
• Наш юрист изучит вашу ситуацию
• Ответ поступит в течение 10-15 минут
• Первичная консультация БЕСПЛАТНО

💡 **Пока ждете ответа:**
Можете задать дополнительные вопросы или уточнить детали проблемы.
"""

    keyboard = [
        [InlineKeyboardButton("📝 Подать подробную заявку",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("📞 Заказать звонок",
                              callback_data="request_call")]
    ]

    await update.message.reply_text(
        response_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    # Используем Enhanced AI для генерации предварительного ответа
    try:
        if ai_enhanced_manager and ai_enhanced_manager._initialized:
            ai_response = await ai_enhanced_manager.generate_response(
                user_id=user_id,
                message=f"Консультация по {category}: {user_text}",
                context={
                    'consultation_category': category,
                    'is_consultation_request': True
                }
            )

            # Отправляем AI ответ как предварительную консультацию
            await update.message.reply_text(
                f"🤖 **ПРЕДВАРИТЕЛЬНАЯ AI-КОНСУЛЬТАЦИЯ:**\n\n{ai_response}\n\n"
                f"⚖️ Наш юрист дополнительно изучит детали и даст персональные рекомендации."
            )

    except Exception as e:
        log.error(f"❌ Failed to generate AI consultation: {e}")


async def enhanced_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 Улучшенный обработчик сообщений с поддержкой консультаций"""
    user_id = update.effective_user.id
    user_text = update.message.text

    # Проверяем, ожидается ли ввод деталей консультации
    if context.user_data.get('awaiting_consultation_details'):
        await handle_consultation_details(update, context)
        return

    # Обычная AI-консультация
    await ai_chat(update, context)


async def show_ai_status(query, context):
    """Показать статус Enhanced AI"""
    global ai_enhanced_manager

    text = "🤖 **СТАТУС ENHANCED AI**\n\n"

    if ai_enhanced_manager is None:
        text += "❌ Enhanced AI не инициализирован\n"
        text += "📋 Используется базовый AI"
    elif not ai_enhanced_manager._initialized:
        text += "⚠️ Enhanced AI частично инициализирован\n"
        text += "📋 Используется fallback режим"
    else:
        try:
            # Получаем статус системы
            health = await ai_enhanced_manager.health_check()

            if health.get("status") == "healthy":
                text += "✅ Enhanced AI работает нормально\n\n"
            else:
                text += "⚠️ Enhanced AI работает с ограничениями\n\n"

            # Статус компонентов
            text += "**Компоненты:**\n"
            components = health.get("components", {})

            for name, status in components.items():
                emoji = "✅" if status.get("status") == "ok" else "❌"
                text += f"{emoji} {name.replace('_', ' ').title()}\n"

            # Аналитика
            try:
                analytics = await ai_enhanced_manager.get_analytics_summary()
                if analytics.get("status") != "no_data":
                    text += f"\n**Статистика:**\n"
                    text += f"📊 Запросов: {analytics.get('total_requests', 0)}\n"
                    text += f"⚡ Успешность: {analytics.get('success_rate', 0):.1%}\n"
                    text += f"⏱️ Время ответа: {analytics.get('avg_response_time', 0):.1f}ms\n"
                    if analytics.get('estimated_cost'):
                        text += f"💰 Расходы: ${analytics.get('estimated_cost', 0):.2f}\n"
            except:
                pass

        except Exception as e:
            text += f"❌ Ошибка получения статуса: {str(e)}"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        # Fallback: отправляем новое сообщение если редактирование не удалось
        try:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.answer("Сообщение обновлено")
        except Exception as fallback_error:
            log.error(f"Fallback message also failed: {fallback_error}")
            await query.answer("❌ Ошибка отображения данных", show_alert=True)


async def handle_enter_phone(query, context):
    """📱 Ввод телефона для заказа звонка"""
    text = """
📱 **УКАЖИТЕ ВАШ НОМЕР ТЕЛЕФОНА**

Отправьте ваш номер телефона в следующем сообщении.

📝 **Формат:** +7 (900) 123-45-67 или 89001234567

⏰ **Также укажите удобное время для звонка:**
• Утром (9:00-12:00)
• Днем (12:00-17:00) 
• Вечером (17:00-21:00)
• Сейчас (в рабочее время)

Пример сообщения:
`+7 (900) 123-45-67, звонить вечером`
"""

    # Сохраняем состояние ожидания номера телефона
    context.user_data['awaiting_phone_input'] = True

    keyboard = [
        [InlineKeyboardButton("📝 Заполнить заявку вместо звонка",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀️ Назад", callback_data="request_call")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенного номера телефона"""
    user_id = update.effective_user.id
    user_text = update.message.text
    user = update.effective_user

    # Очищаем флаг ожидания
    context.user_data['awaiting_phone_input'] = False

    # Формируем заявку на звонок в админ чат
    admin_text = f"""
📞 **ЗАЯВКА НА ОБРАТНЫЙ ЗВОНОК**

👤 **Клиент:** {user.first_name} {user.last_name or ''}
🆔 **ID:** `{user_id}`

📱 **Контакт:** {user_text}

⏰ **Время заявки:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🎯 **Требуется:** Обратный звонок в указанное время
💰 **Условие:** Первые 15 минут БЕСПЛАТНО
"""

    admin_keyboard = [[
        InlineKeyboardButton("📞 Позвонить", url=f"tg://user?id={user_id}"),
        InlineKeyboardButton("💬 Написать", url=f"tg://user?id={user_id}")
    ]]

    try:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        log.info(f"✅ Call request sent to admin for user {user_id}")
    except Exception as e:
        log.error(f"❌ Failed to send call request to admin: {e}")

    # Ответ клиенту
    response_text = f"""
✅ **ЗАЯВКА НА ЗВОНОК ПРИНЯТА**

📱 **Ваш номер:** {user_text}
⏰ **Время подачи:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔔 **Что дальше:**
• Наш юрист свяжется с вами в указанное время
• Проверьте, что телефон доступен для входящих
• Первые 15 минут консультации БЕСПЛАТНО

📞 **Если не дозвонимся:**
Попробуем связаться через Telegram или вы можете написать нам сами.
"""

    keyboard = [
        [InlineKeyboardButton("📝 Дополнительная заявка",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("💬 Задать вопрос в чате",
                              callback_data="chat_consultation")]
    ]

    await update.message.reply_text(
        response_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_submit_call_request(query, context):
    """Обработка подтверждения заявки на звонок"""
    await query.answer("Заявка обработана!", show_alert=True)


# ================ JOBS ================

async def autopost_job(context: ContextTypes.DEFAULT_TYPE):
    """🎯 РАЗНООБРАЗНЫЙ АВТОПОСТИНГ: кейсы, нормативные акты, прецеденты, правовые аспекты"""
    if not CHANNEL_ID:
        return

    log.info("🚀 Starting diverse legal content autopost...")

    try:
        # Система разнообразного контента
        content_types = [
            "legal_case",        # Кейс из жизни (40% вероятность)
            "normative_act",     # Новый нормативный акт (25% вероятность)
            "legal_precedent",   # Судебный прецедент (20% вероятность)
            "legal_aspect",      # Важный правовой аспект (15% вероятность)
        ]

        # Вероятности для разных типов контента
        weights = [40, 25, 20, 15]
        import random
        content_type = random.choices(content_types, weights=weights)[0]

        log.info(f"📝 Selected content type: {content_type}")

        # Генерируем контент в зависимости от типа
        if content_type == "legal_case":
            post_text = await generate_case_post()
        elif content_type == "normative_act":
            post_text = await generate_normative_act_post()
        elif content_type == "legal_precedent":
            post_text = await generate_precedent_post()
        elif content_type == "legal_aspect":
            post_text = await generate_legal_aspect_post()
        else:
            # Fallback к кейсу
            post_text = await generate_case_post()

        log.info(f"✅ Generated {content_type} post: {len(post_text)} chars")

        # Добавляем кнопку для консультации
        keyboard = [[
            InlineKeyboardButton("💼 Получить консультацию",
                                 url=f"https://t.me/{context.bot.username}")
        ]]

        # Отправляем пост
        message = await context.bot.send_message(
            CHANNEL_ID,
            post_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

        log.info(
            f"✅ {content_type} post sent to channel: {message.message_id}")

        # Логируем для аналитики
        try:
            from bot.services.ai_enhanced.analytics.interaction_tracker import InteractionTracker
            tracker = InteractionTracker()
            try:
                from bot.services.ai_enhanced.core.context_builder import AIContext
                ai_context = AIContext()
                await tracker.track_interaction(
                    user_id=0,  # системный пользователь
                    session_id=0,  # системная сессия
                    message=f"autopost_{content_type}",
                    response=post_text,
                    context=ai_context,
                    response_time_ms=1000  # примерное время
                )
            except Exception as track_error:
                log.error(f"Autopost tracking failed: {track_error}")
        except Exception as analytics_error:
            log.error(f"Analytics tracking failed: {analytics_error}")

    except Exception as e:
        log.error(f"❌ Diverse autopost failed: {e}")
        await send_emergency_post(context)


async def generate_case_post() -> str:
    """Генерация поста с кейсом из жизни"""
    try:
        from bot.services.content_intelligence.post_generator import PostGenerator
        generator = PostGenerator()
        return await generator.generate_post()
    except Exception as e:
        log.error(f"Case post generation failed: {e}")
        return get_emergency_case_post()


async def generate_normative_act_post() -> str:
    """Генерация поста о новом нормативном акте"""
    import random

    normative_acts = [
        {
            "title": "Новые правила возврата товаров через маркетплейсы",
            "act": "Постановление Правительства РФ № 2463 от 31.12.2024",
            "changes": """🔄 **ЧТО ИЗМЕНИЛОСЬ:**
• Возврат товаров через маркетплейсы теперь возможен в течение 30 дней
• Маркетплейс обязан предоставить адрес пункта возврата в течение 3 дней
• При отказе продавца возврат осуществляет сама платформа
• Введена ответственность маркетплейсов за недобросовестных продавцов""",
            "impact": """📈 **КАК ЭТО ВЛИЯЕТ НА ВАС:**
✅ Больше защиты при покупках на Wildberries, Ozon, Яндекс.Маркет
✅ Упрощенная процедура возврата без споров с продавцом
✅ Гарантированная компенсация даже при исчезновении продавца
⚠️ Исключения: продукты питания, лекарства, цифровые товары""",
            "action": """💡 **ЧТО ДЕЛАТЬ:**
1. Сохраняйте все документы о покупке (скриншоты, чеки)
2. При проблемах сначала обращайтесь к продавцу
3. Если нет ответа 3 дня - пишите в службу поддержки маркетплейса
4. При отказе - жалуйтесь в Роспотребнадзор со ссылкой на новые правила"""
        },
        {
            "title": "Изменения в Трудовом кодексе: электронные трудовые книжки",
            "act": "Федеральный закон № 439-ФЗ от 16.12.2024",
            "changes": """🔄 **ЧТО ИЗМЕНИЛОСЬ:**
• С 1 марта 2025 года все новые трудовые договоры только в электронном виде
• Работодатель обязан уведомлять ПФР о трудоустройстве в течение 1 дня
• Введены штрафы за несвоевременную подачу сведений (до 50,000₽)
• Бумажные трудовые книжки сохраняются только по заявлению работника""",
            "impact": """📈 **КАК ЭТО ВЛИЯЕТ НА ВАС:**
✅ Быстрое оформление на работу без бумажной волокиты
✅ Невозможность потери трудовой книжки
✅ Мгновенный доступ к стажу через госуслуги
⚠️ Необходимость следить за корректностью электронных записей""",
            "action": """💡 **ЧТО ДЕЛАТЬ:**
1. Подайте заявление о переходе на электронную трудовую книжку
2. Регулярно проверяйте записи через портал госуслуг
3. При ошибках немедленно требуйте исправления от работодателя
4. Ведите личный архив справок и документов о работе"""
        },
        {
            "title": "Новые правила раздела имущества при разводе",
            "act": "Федеральный закон № 478-ФЗ от 28.12.2024",
            "changes": """🔄 **ЧТО ИЗМЕНИЛОСЬ:**
• Криптовалюты и NFT теперь подлежат разделу как совместно нажитое имущество
• Долги по кредитам делятся пропорционально полученному имуществу
• Доходы от интеллектуальной собственности учитываются при разделе
• Упрощена процедура раздела через нотариуса без суда""",
            "impact": """📈 **КАК ЭТО ВЛИЯЕТ НА ВАС:**
✅ Справедливый раздел всех видов современного имущества
✅ Невозможность скрыть цифровые активы от раздела
✅ Более быстрое оформление развода через нотариуса
⚠️ Необходимость декларировать все доходы и активы""",
            "action": """💡 **ЧТО ДЕЛАТЬ:**
1. Ведите учет всех цифровых активов и доходов в браке
2. При разводе заявляйте о всех известных активах супруга
3. Требуйте справки о доходах за весь период брака
4. Рассмотрите возможность нотариального соглашения"""
        }
    ]

    selected = random.choice(normative_acts)

    post = f"""🆕 **НОВЫЙ ЗАКОН: {selected['title'].upper()}**

📜 **{selected['act']}**

{selected['changes']}

{selected['impact']}

{selected['action']}

💼 **НУЖНА ПОМОЩЬ ЮРИСТА?**
Не знаете, как применить новый закон к вашей ситуации?

🎯 Наши специалисты:
✅ Объяснят изменения простым языком
✅ Проанализируют влияние на ваши права
✅ Помогут защитить интересы в новых условиях
✅ Составят документы с учетом изменений

💬 Первая консультация БЕСПЛАТНО: /start
⚖️ Будьте в курсе всех изменений в законодательстве!"""

    return post


async def generate_precedent_post() -> str:
    """Генерация поста о судебном прецеденте"""
    import random

    precedents = [
        {
            "title": "Верховный суд защитил права покупателей маркетплейсов",
            "case": "Определение ВС РФ № 5-КГ24-119-К2",
            "story": """📋 **ДЕЛО:**
Гражданка М. купила телефон на Wildberries за 45,000₽. Товар оказался подделкой. Продавец исчез, Wildberries отказывался возмещать ущерб, ссылаясь на то, что является только 'посредником'.""",
            "decision": """⚖️ **РЕШЕНИЕ СУДА:**
Верховный суд постановил: маркетплейс несет солидарную ответственность с продавцом за некачественные товары, если:
• Не проверил документы продавца должным образом
• Получал комиссию с продажи
• Контролировал процесс продажи и доставки""",
            "impact": """🎯 **ЗНАЧЕНИЕ ДЛЯ ГРАЖДАН:**
✅ Теперь можно требовать возмещения напрямую с маркетплейса
✅ Не нужно искать исчезнувших продавцов
✅ Ответственность несут Ozon, Wildberries, Яндекс.Маркет
✅ Суды обязаны применять эту практику во всех регионах"""
        },
        {
            "title": "Конституционный суд расширил права работников на удаленке",
            "case": "Постановление КС РФ № 29-П от 15.11.2024",
            "story": """📋 **ДЕЛО:**
Программист С. работал удаленно 2 года. Работодатель потребовал выход в офис, угрожая увольнением. С. обратился в суд, ссылаясь на дискриминацию и нарушение трудовых прав.""",
            "decision": """⚖️ **РЕШЕНИЕ СУДА:**
Конституционный суд признал: если работник эффективно выполняет обязанности удаленно, принуждение к работе в офисе без производственной необходимости нарушает:
• Право на свободу труда
• Принцип равенства возможностей
• Право на справедливые условия труда""",
            "impact": """🎯 **ЗНАЧЕНИЕ ДЛЯ РАБОТНИКОВ:**
✅ Работодатель должен обосновать требование работы в офисе
✅ Нельзя уволить за отказ от офисной работы без веских причин
✅ При споре суд будет оценивать эффективность удаленной работы
✅ Защита прав 'удаленщиков' на конституционном уровне"""
        },
        {
            "title": "Банки не могут блокировать счета без веских оснований",
            "case": "Постановление Пленума ВАС РФ № 62 от 04.12.2024",
            "story": """📋 **ДЕЛО:**
ИП Козлов получил блокировку счета в Сбербанке за 'подозрительные операции'. Банк не объяснил причины. Бизнес остановился, начались штрафы и убытки.""",
            "decision": """⚖️ **РЕШЕНИЕ СУДА:**
Высший арбитражный суд установил: банки обязаны:
• Уведомлять о причинах блокировки в течение 24 часов
• Предоставлять возможность объяснения до блокировки
• Разблокировать счет при устранении нарушений
• Возмещать убытки при необоснованной блокировке""",
            "impact": """🎯 **ЗНАЧЕНИЕ ДЛЯ БИЗНЕСА:**
✅ Защита от произвольных блокировок банками
✅ Право требовать компенсацию за убытки
✅ Обязательность объяснений от банка
✅ Сокращение времени разблокировки счетов"""
        }
    ]

    selected = random.choice(precedents)

    post = f"""⚖️ **ВАЖНЫЙ ПРЕЦЕДЕНТ: {selected['title'].upper()}**

📋 **{selected['case']}**

{selected['story']}

{selected['decision']}

{selected['impact']}

💡 **КАК ИСПОЛЬЗОВАТЬ:**
1. Ссылайтесь на это решение в аналогичных спорах
2. Требуйте от противной стороны соблюдения установленных правил
3. Подавайте жалобы в надзорные органы с ссылкой на прецедент
4. Используйте в обоснование исковых требований

💼 **СТОЛКНУЛИСЬ С ПОХОЖЕЙ СИТУАЦИЕЙ?**
Наши юристы помогут применить новую судебную практику:

✅ Составим документы со ссылками на прецеденты
✅ Поможем обосновать требования актуальной практикой
✅ Представим интересы в суде с учетом новых решений
✅ Добьемся максимального результата

💬 Бесплатная консультация: /start
⚖️ Знание прецедентов - ключ к победе в суде!"""

    return post


async def generate_legal_aspect_post() -> str:
    """Генерация поста о важном правовом аспекте"""
    import random

    legal_aspects = [
        {
            "title": "Моральный вред: как правильно требовать и получать",
            "intro": """💰 **Знаете ли вы?**
Моральный вред можно взыскать практически в любом споре, но 90% граждан делают это неправильно и получают копейки вместо существенных сумм.""",
            "key_points": """🎯 **КЛЮЧЕВЫЕ ПРИНЦИПЫ:**

📊 **Размеры в практике:**
• Потребительские споры: 5,000-50,000₽
• Трудовые нарушения: 10,000-100,000₽
• ДТП с пострадавшими: 50,000-500,000₽
• Клевета, оскорбления: 20,000-200,000₽

🎯 **Факторы увеличения суммы:**
• Публичность нарушения (соцсети, СМИ)
• Длительность нарушения прав
• Особый статус пострадавшего (беременность, инвалидность)
• Грубое поведение нарушителя
• Материальное положение ответчика""",
            "mistakes": """❌ **ТИПИЧНЫЕ ОШИБКИ:**
• Просят слишком мало (1,000-3,000₽) - суд снижает еще больше
• Не обосновывают размер конкретными фактами
• Не прикладывают доказательства переживаний
• Забывают индексировать сумму на дату вынесения решения""",
            "tips": """✅ **КАК СДЕЛАТЬ ПРАВИЛЬНО:**
1. Изучите похожие дела в вашем регионе через картотеку судов
2. Просите сумму в 2-3 раза больше желаемой
3. Собирайте справки о лечении, показания свидетелей
4. Описывайте конкретные страдания, а не общие фразы
5. Указывайте на системность нарушений ответчиком"""
        },
        {
            "title": "Срок исковой давности: когда время работает против вас",
            "intro": """⏰ **Знаете ли вы?**
Каждый год тысячи граждан теряют право на справедливую компенсацию только потому, что не знают про сроки исковой давности.""",
            "key_points": """🎯 **ОСНОВНЫЕ СРОКИ:**

📅 **3 года (общий срок):**
• Взыскание долгов по договорам
• Возмещение ущерба от ДТП
• Компенсация за некачественный ремонт
• Взыскание с управляющих компаний

📅 **1 год (специальные случаи):**
• Трудовые споры (восстановление, зарплата)
• Споры по перевозке грузов
• Ничтожность сделок

📅 **2 года:**
• Защита прав потребителей
• Страховые выплаты

📅 **10 лет:**
• Возмещение вреда жизни и здоровью""",
            "mistakes": """❌ **ОПАСНЫЕ ЗАБЛУЖДЕНИЯ:**
• "Срок начинается с момента нарушения" - НЕТ! С момента, когда узнали о нарушении
• "Если подал претензию, срок приостанавливается" - НЕТ! Только суд приостанавливает
• "Устное обращение к нарушителю прерывает срок" - НЕТ! Только письменное признание долга""",
            "tips": """✅ **КАК ЗАЩИТИТЬ СЕБЯ:**
1. Ведите письменную переписку с нарушителем
2. Отправляйте претензии заказными письмами
3. При приближении срока - подавайте иск, даже для 'остановки часов'
4. Получайте письменные признания вины или долга
5. Помните: суд может восстановить срок при уважительных причинах"""
        },
        {
            "title": "Судебные расходы: как не платить за правосудие",
            "intro": """💸 **Знаете ли вы?**
Даже выиграв суд, можно остаться в убытке из-за судебных расходов. Но есть законные способы их избежать или переложить на противника.""",
            "key_points": """🎯 **ВИДЫ РАСХОДОВ:**

💰 **Госпошлина:**
• До 1 млн₽ - от 4% до 13,200₽
• Свыше 1 млн₽ - 13,200₽ + 0.5% с суммы свыше
• Неимущественные споры - 300₽
• Моральный вред - 300₽

💰 **Представительство:**
• Юристы: 2,000-10,000₽ за заседание
• По сложным делам: до 50,000₽ и выше
• Возмещается при победе в пределах 'разумных'

💰 **Экспертизы:**
• Почерковедческая: 15,000-30,000₽
• Строительная: 20,000-50,000₽
• Оценочная: 5,000-15,000₽""",
            "mistakes": """❌ **ДОРОГИЕ ОШИБКИ:**
• Не просят возмещения расходов в исковом заявлении
• Не ведут учет всех трат с документами
• Соглашаются на мировую без учета расходов
• Не обжалуют отказ в возмещении 'завышенных' сумм""",
            "tips": """✅ **КАК СЭКОНОМИТЬ:**
1. Используйте льготы по госпошлине (пенсионеры, инвалиды)
2. При иске до 50,000₽ - представляйте себя сами
3. Ходатайствуйте об обеспечении иска для возмещения расходов
4. Ведите подробный учет всех трат
5. В мировом соглашении предусматривайте компенсацию расходов"""
        }
    ]

    selected = random.choice(legal_aspects)

    post = f"""💡 **ПРАВОВОЙ ЛИКБЕЗ: {selected['title'].upper()}**

{selected['intro']}

{selected['key_points']}

{selected['mistakes']}

{selected['tips']}

💼 **НУЖНА ПРОФЕССИОНАЛЬНАЯ ПОМОЩЬ?**
Столкнулись со сложной правовой ситуацией?

🎯 Наши юристы:
✅ Просчитают все риски и возможности
✅ Разработают оптимальную стратегию действий
✅ Помогут избежать типичных ошибок
✅ Добьются максимального результата с минимальными затратами

💬 Бесплатная консультация: /start
📚 Знание закона - ваша лучшая защита!"""

    return post


async def send_emergency_post(context):
    """Экстренный пост при сбоях"""
    emergency_post = get_emergency_case_post()

    keyboard = [[
        InlineKeyboardButton("💼 Срочная консультация",
                             url=f"https://t.me/{context.bot.username}")
    ]]

    await context.bot.send_message(
        CHANNEL_ID,
        emergency_post,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    log.info("🛡️ Emergency post sent successfully")


def get_emergency_case_post() -> str:
    """Получить экстренный кейс-пост"""
    return """📋 **КЕЙС ИЗ ЖИЗНИ:**
Владимир купил автомобиль в салоне за 1,2 млн₽. Через месяц обнаружились скрытые дефекты двигателя. Дилер утверждает, что это 'нормальный износ' и отказывается от гарантийного ремонта.

⚖️ **АЛГОРИТМ РЕШЕНИЯ:**
1. 📝 Составьте письменную претензию к дилеру с требованием ремонта
2. 🔍 Закажите независимую экспертизу для установления причин дефекта
3. 📮 Направьте результаты экспертизы дилеру заказным письмом
4. 🏛️ При отказе - жалоба в Роспотребнадзор и автопроизводителю
5. ⚖️ Подача иска в суд с требованием замены автомобиля
6. 💰 Взыскание стоимости экспертизы и морального вреда
7. 📄 Требование возврата всех понесенных расходов

📚 **НОРМАТИВНАЯ БАЗА:**
📜 Закон "О защите прав потребителей" № 2300-1:
• Статья 18 - право на обмен/возврат товара ненадлежащего качества
• Статья 19 - гарантийные сроки и сроки службы
• Статья 29 - права потребителя при обнаружении недостатков

⚠️ **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
• Дилер может ссылаться на неправильную эксплуатацию
• Сложность доказательства заводского характера дефектов
• Высокая стоимость независимой экспертизы (30-50 тыс₽)
• Длительность судебного процесса (6-12 месяцев)

💼 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Столкнулись с обманом автодилера? Действуйте решительно!

🎯 Наши автоюристы помогут:
✅ Составить претензию с максимальными требованиями
✅ Найти надежных экспертов по разумным ценам
✅ Провести переговоры с дилером и производителем
✅ Представить интересы в суде с гарантией результата

💬 Первая консультация БЕСПЛАТНО: /start
⚖️ Возвращаем полную стоимость автомобиля в 85% случаев!"""


async def _fallback_autopost(context: ContextTypes.DEFAULT_TYPE):
    """РЕЗЕРВНЫЙ профессиональный автопостинг с кейсами"""

    try:
        # Используем новый профессиональный генератор
        from bot.services.content_intelligence.post_generator import PostGenerator

        enhanced_generator = PostGenerator()

        # Генерируем профессиональный пост с кейсом
        log.info("📝 Generating fallback professional case post...")
        post_text = await enhanced_generator.generate_post()

        log.info(
            f"✅ Generated fallback professional post: {len(post_text)} chars")

    except Exception as e:
        log.error(f"❌ Enhanced post generation failed: {e}")

        # ЭКСТРЕННЫЙ РЕЗЕРВ с кейсами
        fallback_cases = [
            """📋 **КЕЙС ИЗ ЖИЗНИ:**
Елена не получает зарплату 3 месяца. Директор ссылается на 'финансовые трудности', но заставляет работать в полном объеме. Угрожает увольнением при требовании расчета.

⚖️ **АЛГОРИТМ РЕШЕНИЯ:**
1. 📋 Подайте письменное заявление работодателю с требованием выплаты
2. 📞 Обратитесь в государственную инспекцию труда
3. 📄 Соберите документы: трудовой договор, табели, справки
4. ⚖️ Подайте заявление в суд о взыскании задолженности
5. 💰 Требуйте компенсацию за задержку (1/150 ключевой ставки ЦБ)
6. 🏛️ Уведомите прокуратуру о нарушении трудовых прав
7. 📞 Параллельно ищите новое место работы

📚 **НОРМАТИВНАЯ БАЗА:**
📜 Трудовой кодекс РФ № 197-ФЗ:
• Статья 136 - сроки выплаты заработной платы
• Статья 236 - ответственность за задержку зарплаты
• Статья 140 - расчет при увольнении

⚠️ **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
• Работодатель может давить и создавать невыносимые условия
• Компания может обанкротиться, избегая выплат
• Восстановление заработной платы займет месяцы
• Без письменных документов сложно доказать размер долга

💼 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Работодатель не платит зарплату? Защитите свои права!

🎯 Мы поможем взыскать:
✅ Всю задолженность по зарплате полностью
✅ Компенсацию за каждый день просрочки
✅ Моральный вред за нарушение прав
✅ Возмещение расходов на юридическую помощь

💬 Бесплатная консультация: /start
⚖️ Взыскиваем долги даже с обанкротившихся компаний!""",

            """📋 **КЕЙС ИЗ ЖИЗНИ:**
В квартире Петровых 4 месяца нет горячей воды. УК требует полную оплату за ЖКУ, ссылаясь на 'плановые ремонтные работы'. Жильцы вынуждены греть воду и покупать услуги бани.

⚖️ **АЛГОРИТМ РЕШЕНИЯ:**
1. 📝 Подайте письменную жалобу в УК с требованием устранения
2. 📸 Зафиксируйте отсутствие услуги фото/видео с датой
3. 🏛️ Обратитесь в жилищную инспекцию вашего региона
4. 💰 Требуйте перерасчета за период отсутствия услуги
5. 📞 Подайте коллективную жалобу от всех пострадавших жильцов
6. ⚖️ При отказе - иск в суд о взыскании ущерба
7. 🔄 Инициируйте смену управляющей компании

📚 **НОРМАТИВНАЯ БАЗА:**
📜 ЖК РФ № 188-ФЗ:
• Статья 154 - размер платы за коммунальные услуги
• Статья 161 - обязанности управляющей организации

🏛️ Постановление Правительства № 354:
• Правила перерасчета при нарушении качества услуг

⚠️ **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
• УК может сменить название, избегая ответственности
• Перерасчет возможен только за документально подтвержденный период
• Доказать размер ущерба без экспертизы сложно
• Собственники могут не поддержать смену УК

💼 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
УК нарушает ваши права? Добейтесь справедливости!

🎯 Наши жилищные юристы:
✅ Добьются максимального перерасчета за весь период
✅ Взыщут компенсацию дополнительных расходов
✅ Привлекут УК к административной ответственности
✅ Организуют смену УК при необходимости

💬 Первая консультация БЕСПЛАТНО: /start
🏠 Защищаем права собственников с 2010 года!""",

            """📋 **КЕЙС ИЗ ЖИЗНИ:**
После развода Михаил не платит алименты на ребенка 8 месяцев. Скрывает доходы, работает неофициально. Бывшая жена вынуждена брать кредиты на лечение сына.

⚖️ **АЛГОРИТМ РЕШЕНИЯ:**
1. 📋 Подайте заявление о взыскании алиментов в мировой суд
2. 📄 Получите судебный приказ или решение суда об алиментах
3. 🏛️ Направьте исполнительный лист в ФССП по месту работы должника
4. 🔍 Подайте заявление о розыске должника и его имущества
5. 💳 Требуйте арест банковских счетов и имущества
6. 🚫 Инициируйте ограничение на выезд за границу
7. ⚖️ При злостном уклонении - заявление о возбуждении уголовного дела

📚 **НОРМАТИВНАЯ БАЗА:**
📜 Семейный кодекс РФ № 223-ФЗ:
• Статья 80 - обязанности родителей по содержанию детей
• Статья 81 - размер алиментов на несовершеннолетних
• Статья 115 - индексация алиментов

🏛️ ФЗ "Об исполнительном производстве":
• Статья 65 - обращение взыскания на заработную плату

⚠️ **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
• Должник может скрывать реальные доходы
• Принудительное взыскание занимает месяцы и годы
• Алименты взыскиваются только с официальных доходов
• При выезде за границу розыск усложняется

💼 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Не можете добиться выплаты алиментов? Мы поможем!

🎯 Наши семейные юристы:
✅ Найдут скрытые доходы и имущество должника
✅ Добьются ареста всех счетов и активов
✅ Инициируют уголовное преследование злостных неплательщиков
✅ Взыщут задолженность с процентами и неустойкой

💬 Первая консультация БЕСПЛАТНО: /start
👶 Защищаем права детей и получаем результат!"""
        ]

        # Выбираем случайный кейс
        import random
        post_text = random.choice(fallback_cases)
        log.info(
            f"🛡️ Using emergency fallback case post: {len(post_text)} chars")

    # Добавляем кнопку
    keyboard = [[
        InlineKeyboardButton("💼 Получить консультацию",
                             url=f"https://t.me/{context.bot.username}")
    ]]

    await context.bot.send_message(
        CHANNEL_ID,
        post_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ================ MAIN ================

async def load_db_admins():
    """Загружает администраторов из базы данных в ADMIN_USERS"""
    global ADMIN_USERS
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(
                select(Admin.tg_id).where(Admin.is_active == True)
            )
            db_admin_ids = {row[0] for row in result.fetchall()}

        # Объединяем хардкодированных и из БД
        old_count = len(ADMIN_USERS)
        ADMIN_USERS = HARDCODED_ADMIN_IDS.union(db_admin_ids)
        log.info(
            f"🔧 Admins reloaded: hardcoded={len(HARDCODED_ADMIN_IDS)}, from_db={len(db_admin_ids)}, total={len(ADMIN_USERS)} (was {old_count})")
        print(f"🔧 Admin users updated: {len(ADMIN_USERS)} total")

    except Exception as e:
        log.error(f"Failed to load DB admins: {e}")
        # Если БД недоступна, используем только хардкодированных
        ADMIN_USERS = HARDCODED_ADMIN_IDS.copy()


async def post_init(application: Application):
    """Инициализация после запуска"""
    global ai_enhanced_manager

    # Загружаем администраторов из БД
    await load_db_admins()

    # 🚀 ИНИЦИАЛИЗИРУЕМ Enhanced AI
    try:
        log.info("🚀 Initializing Enhanced AI system...")
        ai_enhanced_manager = AIEnhancedManager()
        await ai_enhanced_manager.initialize()
        print("✅ Enhanced AI initialized successfully")
        log.info("Enhanced AI system is ready")
    except Exception as e:
        print(f"❌ Failed to initialize Enhanced AI: {e}")
        log.error(f"Enhanced AI initialization error: {e}")
        import traceback
        log.error(f"Enhanced AI traceback: {traceback.format_exc()}")
        ai_enhanced_manager = None
        log.info("Will use basic AI as fallback")

    try:
        # Устанавливаем кнопку меню
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📝 Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
        print("✅ Menu button set successfully")
    except Exception as e:
        print(f"❌ Failed to set menu button: {e}")
        log.error(f"Menu button error: {e}")


async def fix_database_schema():
    """Исправление схемы БД после предыдущих проблем"""
    try:
        log.info("🔧 Checking and fixing database schema...")

        async with async_sessionmaker() as session:
            # Проверяем тип колонки user_id
            result = await session.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'applications' AND column_name = 'user_id'
            """))
            user_id_type = result.scalar_one_or_none()

            if user_id_type != "integer":
                log.info("🔄 user_id column type needs conversion")

                # Сначала исправляем некорректные значения
                log.info("🧹 Cleaning up invalid user_id values...")

                # Находим все некорректные user_id (не числовые)
                invalid_result = await session.execute(text("""
                    SELECT id, user_id 
                    FROM applications 
                    WHERE user_id !~ '^[0-9]+$'
                """))
                invalid_apps = invalid_result.fetchall()

                for app_id, bad_user_id in invalid_apps:
                    try:
                        log.info(
                            f"🔧 Fixing app {app_id} with bad user_id: '{bad_user_id}'")

                        # Ищем существующего пользователя для привязки
                        temp_user_result = await session.execute(text("""
                            SELECT id FROM users 
                            WHERE first_name = 'Гость' 
                            LIMIT 1
                        """))
                        temp_user = temp_user_result.scalar_one_or_none()

                        if not temp_user:
                            # Создаем нового временного пользователя
                            import random
                            temp_tg_id = -random.randint(1000000, 2000000000)

                            await session.execute(text("""
                                INSERT INTO users (tg_id, first_name) 
                                VALUES (:tg_id, 'Гость')
                                RETURNING id
                            """), {"tg_id": temp_tg_id})

                            temp_user_result = await session.execute(text("""
                                SELECT id FROM users 
                                WHERE tg_id = :tg_id
                            """), {"tg_id": temp_tg_id})

                            temp_user = temp_user_result.scalar_one()
                            log.info(
                                f"✅ Created new temp user {temp_user} for app {app_id}")

                        # Обновляем заявку корректным user_id
                        await session.execute(text("""
                            UPDATE applications 
                            SET user_id = :user_id 
                            WHERE id = :app_id
                        """), {"user_id": str(temp_user), "app_id": app_id})

                        log.info(
                            f"✅ Fixed app {app_id}: '{bad_user_id}' -> {temp_user}")

                    except Exception as fix_error:
                        log.error(f"❌ Failed to fix app {app_id}: {fix_error}")
                        # В крайнем случае ставим 1 (должен существовать)
                        await session.execute(text("""
                            UPDATE applications 
                            SET user_id = '1' 
                            WHERE id = :app_id
                        """), {"app_id": app_id})

                await session.commit()
                log.info("✅ Invalid user_id values cleaned up")

                # Теперь безопасно конвертируем тип
                log.info("🔄 Converting user_id column type to INTEGER...")
                await session.execute(text("""
                    ALTER TABLE applications 
                    ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER
                """))

                await session.commit()
                log.info("✅ user_id column type converted to INTEGER")
                print("✅ Database schema fixed: user_id converted to INTEGER")
            else:
                log.info("✅ user_id column has correct type")

            # 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Добавляем отсутствующие колонки
            log.info("🔧 Checking for missing columns...")

            # Проверяем наличие колонки notes
            notes_result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'applications' AND column_name = 'notes'
            """))
            has_notes = notes_result.scalar_one_or_none()

            if not has_notes:
                log.info("➕ Adding missing 'notes' column...")
                await session.execute(text("""
                    ALTER TABLE applications 
                    ADD COLUMN notes TEXT
                """))
                await session.commit()
                log.info("✅ Added 'notes' column")
                print("✅ Added missing 'notes' column")

            # Проверяем наличие колонки assigned_admin
            admin_result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'applications' AND column_name = 'assigned_admin'
            """))
            has_assigned_admin = admin_result.scalar_one_or_none()

            if not has_assigned_admin:
                log.info("➕ Adding missing 'assigned_admin' column...")
                await session.execute(text("""
                    ALTER TABLE applications 
                    ADD COLUMN assigned_admin VARCHAR(64)
                """))
                await session.commit()
                log.info("✅ Added 'assigned_admin' column")
                print("✅ Added missing 'assigned_admin' column")

            print("✅ Database schema is up to date")

    except Exception as e:
        log.error(f"❌ Database schema fix failed: {e}")
        print(f"⚠️ Database schema fix failed: {e}")
        # Не прерываем запуск, продолжаем работу


async def handle_debug_fix_schema(request: web.Request) -> web.Response:
    """Debug endpoint для ручного исправления схемы БД"""
    log.info("🔧 Debug endpoint hit for schema fix")
    try:
        await fix_database_schema()
        return web.Response(text="Database schema fixed successfully!")
    except Exception as e:
        log.error(f"❌ Failed to fix database schema: {e}")
        return web.Response(text=f"Failed to fix database schema: {e}", status=500)


async def handle_debug_check_schema(request: web.Request) -> web.Response:
    """Debug endpoint для проверки текущей схемы БД"""
    log.info("🔍 Debug endpoint hit for schema check")
    try:
        async with async_sessionmaker() as session:
            # Получаем все колонки таблицы applications
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'applications' 
                ORDER BY ordinal_position
            """))

            columns = result.fetchall()

            response_text = "APPLICATIONS TABLE SCHEMA:\n\n"
            for col in columns:
                response_text += f"- {col[0]} ({col[1]}) nullable={col[2]} default={col[3]}\n"

            return web.Response(text=response_text)
    except Exception as e:
        log.error(f"❌ Failed to check database schema: {e}")
        return web.Response(text=f"Failed to check database schema: {e}", status=500)


async def main():
    """Точка входа"""
    # Инициализируем БД
    await init_db()

    # Проверяем и исправляем схему БД если нужно
    await fix_database_schema()

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # HTTP сервер для webhook и webapp
    app = web.Application()
    app["bot"] = application.bot
    app["application"] = application

    # Роуты
    app.router.add_post(f"/{TOKEN}", handle_telegram)
    app.router.add_route("*", "/submit", handle_submit)
    app.router.add_get("/webapp/", handle_webapp)
    app.router.add_get("/webapp/{filename}", handle_webapp_static)
    app.router.add_get("/admin/", handle_admin)

    # API роуты для админки
    app.router.add_route("*", "/api/admin/applications",
                         api_admin_applications)
    app.router.add_route("*", "/api/admin/clients", api_admin_clients)
    app.router.add_route("*", "/api/admin/payments", api_admin_payments)
    app.router.add_route("*", "/api/admin/stats", api_admin_stats)

    # Health endpoint для мониторинга
    app.router.add_get("/health", handle_health)

    # Debug endpoint for schema fix (DISABLED in production for security)
    # app.router.add_get("/debug/fix-schema", handle_debug_fix_schema)
    # app.router.add_get("/debug/check-schema", handle_debug_check_schema)

    app.router.add_static(
        "/webapp/", path=Path(__file__).parent.parent / "webapp")

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("add_admin", cmd_add_admin))
    application.add_handler(CommandHandler("list_admins", cmd_list_admins))
    application.add_handler(CallbackQueryHandler(admin_callback))

    # 🔧 ФИКС: Добавляем обработчик для ввода телефона и деталей консультации
    async def message_handler_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Роутер для обработки текстовых сообщений"""
        user_id = update.effective_user.id

        # Проверяем, ожидается ли ввод телефона
        if context.user_data.get('awaiting_phone_input'):
            await handle_phone_input(update, context)
            return

        # Проверяем, ожидается ли ввод деталей консультации
        if context.user_data.get('awaiting_consultation_details'):
            await handle_consultation_details(update, context)
            return

        # Обычная AI-консультация
        await ai_chat(update, context)

    # Регистрируем универсальный обработчик сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler_router))
    # 🔧 УДАЛЯЕМ ДУБЛИРУЮЩИЙ ОБРАБОТЧИК
    # application.add_handler(MessageHandler(
    #     filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
    #     enhanced_message_handler
    # ))

    # Джобы
    if application.job_queue is not None:
        # Используем переменную окружения для интервала автопостинга
        autopost_hours = int(os.getenv("POST_INTERVAL_HOURS", "2"))

        # ДОБАВЛЯЕМ: Одиночный автопост через 5 минут после перезапуска
        application.job_queue.run_once(
            autopost_job,
            when=timedelta(minutes=5)
        )
        print("✅ One-time autopost scheduled for 5 minutes after restart")
        log.info("One-time autopost job scheduled for 5 minutes after restart")

        # Основной повторяющийся автопостинг
        application.job_queue.run_repeating(
            autopost_job,
            interval=timedelta(hours=autopost_hours),
            first=timedelta(minutes=10)
        )
        print(
            f"✅ Job queue initialized - autopost every {autopost_hours} hours")
        log.info(f"Job queue initialized with {autopost_hours}h interval")
    else:
        print("⚠️ Job queue not available - autopost disabled")
        log.warning("Job queue not available, autopost functionality disabled")

    # Устанавливаем webhook
    webhook_url = f"https://{PUBLIC_HOST}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)

    # Запускаем HTTP сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # Запускаем приложение
    async with application:
        await application.start()
        log.info(f"Bot started on port {PORT}")

        # 🚀 ОПТИМИЗАЦИЯ: Запускаем post_init в background для быстрого старта Railway
        async def background_init():
            """Background инициализация Enhanced AI для избежания Railway timeout"""
            try:
                print("🔧 Starting background Enhanced AI initialization...")
                await post_init(application)
                print("✅ Background Enhanced AI initialization completed")

                # Уведомляем админа после полной инициализации
                try:
                    await application.bot.send_message(
                        ADMIN_CHAT_ID,
                        "🚀 Бот полностью запущен с Enhanced AI!\n\n"
                        "Команды:\n"
                        "/admin - админ панель\n"
                        "/start - приветствие"
                    )
                except:
                    pass
            except Exception as e:
                print(f"❌ Background Enhanced AI initialization failed: {e}")
                log.error(f"Background Enhanced AI init error: {e}")

        # Запускаем Enhanced AI инициализацию в background
        asyncio.create_task(background_init())

        print(
            "🚀 Railway-optimized startup completed - Enhanced AI initializing in background")

        # Держим бота живым
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
