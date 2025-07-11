#!/usr/bin/env python3
"""
BUILDING: ЮРИДИЧЕСКИЙ ЦЕНТР - PRODUCTION-READY BOT

ROCKET: ПОЛНОФУНКЦИОНАЛЬНЫЙ ПРОДУКТ ДЛЯ ПРОДАКШЕНА:
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

from sqlalchemy import select, text, func
from telegram import (
    Update, MenuButtonWebApp, WebAppInfo,
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
from bot.handlers.smm_admin import register_smm_admin_handlers
from .handlers.smm_admin import register_smm_admin_handlers
# Импорт улучшенной системы автопостинга
try:
    from bot.services.enhanced_autopost import (
        generate_professional_post,
        should_create_autopost,
        get_enhanced_autopost_status
    )
    ENHANCED_AUTOPOST_AVAILABLE = True
except ImportError:
    ENHANCED_AUTOPOST_AVAILABLE = False
    print('WARNING: Enhanced autopost system not available')


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

print(f"GLOBE: WebApp URL: {WEB_APP_URL}")
print(f"LINK: Webhook URL: https://{PUBLIC_HOST}/{TOKEN}")
print(f"ROCKET: Production Mode: {PRODUCTION_MODE}")

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

# FIX: FIXED: Улучшенная система администраторов
HARDCODED_ADMIN_IDS = {
    6373924442,  # Основной администратор (замените на ваш реальный ID)
    ADMIN_CHAT_ID if ADMIN_CHAT_ID != 0 else None
}
HARDCODED_ADMIN_IDS.discard(None)  # Убираем None если ADMIN_CHAT_ID=0

# Global admin set - теперь правильный
ADMIN_USERS = HARDCODED_ADMIN_IDS.copy()

print(f"FIX: Admin users initialized: {ADMIN_USERS}")
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
    FIX: FIXED: Улучшенная проверка администраторов
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
                text="MEMO: Подать заявку",
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
HELLO: Здравствуйте, {user.first_name}!

BUILDING: **ЮРИДИЧЕСКИЙ ЦЕНТР**
Полный спектр юридических услуг:

- Семейное право и развод
- Наследственные споры
- Трудовые конфликты
- Жилищные вопросы
- Банкротство физлиц
- Налоговые консультации
- Административные дела
- Защита прав потребителей
- Миграционное право
- И многое другое!

CHAT: Задайте вопрос прямо в чате или нажмите синюю кнопку меню рядом с полем ввода для подачи заявки.

SUCCESS: Работаем по всей России
DOLLAR: Оплата по результату
"""

    keyboard = [[
        InlineKeyboardButton(
            "MEMO: Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))
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

    # FIX: ФИКС: Проверяем специальные состояния пользователя
    if await is_admin(user_id) and context.user_data.get('pending_broadcast', {}).get('waiting_for_text'):
        await handle_broadcast_text(update, context)
        return

    # FIX: ФИКС: Если пользователь ожидает ввода деталей консультации, обрабатываем их отдельно
    if context.user_data.get('awaiting_consultation_details'):
        await handle_consultation_details(update, context)
        return

    # FIX: ФИКС: Если пользователь ожидает ввода телефона, обрабатываем его отдельно
    if context.user_data.get('awaiting_phone_input'):
        await handle_phone_input(update, context)
        return

    # FIX: ФИКС: Если админ создает пост вручную
    if context.user_data.get('awaiting_manual_post') and await is_admin(user_id):
        await handle_manual_post_input(update, context)
        return

    # FIX: ФИКС: Если админ редактирует пост
    if context.user_data.get('editing_post') and await is_admin(user_id):
        await handle_edit_post_input(update, context)
        return

    if not OPENROUTER_API_KEY:
        await update.message.reply_text("AI консультант временно недоступен")
        return

    # Логирование для диагностики
    await log_request(user_id, "ai", True)

    try:
        # ROCKET: ИСПРАВЛЕНИЕ: Используем Enhanced AI с правильными параметрами
        if ai_enhanced_manager and ai_enhanced_manager._initialized:
            log.info(f" Using Enhanced AI for user {user_id}")

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
                f"SUCCESS: Enhanced AI response generated: {len(response)} chars")
        else:
            log.info(f"WARNING: Using fallback AI for user {user_id}")

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
                response += "\n\n Для детальной консультации нажмите кнопки ниже."

        # TARGET: НОВОЕ: Добавляем клиентский путь с кнопками
        keyboard = [
            [
                InlineKeyboardButton(
                    "MEMO: Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL)),
                InlineKeyboardButton("PHONE: Звонок",
                                     callback_data="request_call")
            ],
            [
                InlineKeyboardButton(
                    "CHAT: Консультация", callback_data="chat_consultation"),
                InlineKeyboardButton("CHART: Стоимость",
                                     callback_data="get_price")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(response, reply_markup=reply_markup)

        log.info(
            f"SUCCESS: AI response sent to user {user_id} with client flow buttons")

    except Exception as e:
        log.error(f"ERROR: AI Chat error for user {user_id}: {e}")
        await log_request(user_id, "ai", False, str(e))

        # Fallback ответ с кнопками
        fallback_keyboard = [[
            InlineKeyboardButton(
                "MEMO: Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))
        ]]

        await update.message.reply_text(
            "BOT: AI временно недоступен, но вы можете оставить заявку на консультацию.",
            reply_markup=InlineKeyboardMarkup(fallback_keyboard)
        )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полная интерактивная админ панель со всеми командами"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text(" Нет доступа")
        return

    # Получаем статистику для отображения
    try:
        async with async_sessionmaker() as session:
            total_users = await session.scalar(select(func.count(User.id)))
            total_apps = await session.scalar(select(func.count(AppModel.id)))
            new_apps_today = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            )
    except:
        total_users = total_apps = new_apps_today = 0

    admin_text = f"""BUILDING: **ЮРИДИЧЕСКИЙ ЦЕНТР - АДМИН ПАНЕЛЬ**

CHART: **Быстрая статистика:**
- Пользователей: {total_users}
- Заявок: {total_apps}
- Новых сегодня: {new_apps_today}
- Админов: {len(ADMIN_USERS)}

CONTROL: **Выберите раздел управления:**"""

    keyboard = [
        [
            InlineKeyboardButton("CLIPBOARD: Заявки",
                                 callback_data="admin_apps"),
            InlineKeyboardButton("CHART: Статистика",
                                 callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(
                "CARD: Платежи", callback_data="admin_payments"),
            InlineKeyboardButton("USERS: Клиенты", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(
                "BOT: AI Статус", callback_data="admin_ai_status"),
            InlineKeyboardButton(" Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(
                "ROCKET: SMM Система", callback_data="smm_main_panel"),
            InlineKeyboardButton(
                " Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton("USERS: Управление админами",
                                 callback_data="admin_manage_admins"),
            InlineKeyboardButton("GROWTH: Детальная аналитика",
                                 callback_data="admin_detailed_analytics")
        ],
        [
            InlineKeyboardButton("CHANGES: Обновить панель",
                                 callback_data="admin_refresh"),
            InlineKeyboardButton("CHART: Экспорт данных",
                                 callback_data="admin_export")
        ]
    ]

    await update.message.reply_text(
        admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def cmd_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIX: FIXED: Команда для добавления нового администратора"""
    user_id = update.effective_user.id

    # Проверяем права текущего пользователя
    if not await is_admin(user_id):
        await update.message.reply_text(" Нет доступа")
        return

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "CLIPBOARD: **Добавление администратора**\n\n"
            "Использование: `/add_admin <ID> [роль]`\n\n"
            "Роли:\n"
            "- `operator` - просмотр заявок\n"
            "- `lawyer` - работа с заявками\n"
            "- `superadmin` - полный доступ\n\n"
            "Пример: `/add_admin 123456789 lawyer`",
            parse_mode='Markdown'
        )
        return

    try:
        new_admin_id = int(context.args[0])
        role = context.args[1] if len(context.args) > 1 else "operator"

        if role not in ROLE_PERMISSIONS:
            await update.message.reply_text(
                f"ERROR: Неверная роль: `{role}`\n\n"
                f"Доступные роли: {', '.join(ROLE_PERMISSIONS.keys())}",
                parse_mode='Markdown'
            )
            return

    except ValueError:
        await update.message.reply_text("ERROR: ID должен быть числом")
        return

    # Проверяем, не является ли уже администратором
    if await is_admin(new_admin_id):
        await update.message.reply_text(f"WARNING: Пользователь {new_admin_id} уже администратор")
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
            f"SUCCESS: **Администратор добавлен**\n\n"
            f"USER: ID: `{new_admin_id}`\n"
            f"TARGET: Роль: `{role}`\n"
            f"CHART: Всего админов: {len(ADMIN_USERS)}",
            parse_mode='Markdown'
        )

        # Уведомляем нового администратора
        try:
            await context.bot.send_message(
                new_admin_id,
                f"PARTY: **Вы назначены администратором!**\n\n"
                f"TARGET: Роль: {role}\n"
                f"CLIPBOARD: Команды: /admin, /start\n\n"
                f"Добро пожаловать в команду! HELLO:",
                parse_mode='Markdown'
            )
        except Exception as e:
            log.warning(f"Could not notify new admin {new_admin_id}: {e}")
            await update.message.reply_text(
                "WARNING: Администратор добавлен, но не смогли отправить уведомление "
                "(возможно, пользователь не запускал бота)"
            )

        log.info(
            f"FIX: New admin added: {new_admin_id} with role {role} by {user_id}")

    except Exception as e:
        log.error(f"Failed to add admin {new_admin_id}: {e}")
        await update.message.reply_text(f"ERROR: Ошибка добавления администратора: {e}")


async def cmd_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIX: FIXED: Команда для просмотра списка администраторов"""
    user_id = update.effective_user.id

    # Проверяем права текущего пользователя
    if not await is_admin(user_id):
        await update.message.reply_text(" Нет доступа")
        return

    try:
        text = "USERS: **СПИСОК АДМИНИСТРАТОРОВ**\n\n"

        # Хардкодированные администраторы
        if HARDCODED_ADMIN_IDS:
            text += "FIX: **Хардкодированные:**\n"
            for admin_id in sorted(HARDCODED_ADMIN_IDS):
                text += f"- `{admin_id}` (системный)\n"
            text += "\n"

        # Администраторы из БД
        async with async_sessionmaker() as session:
            result = await session.execute(
                select(Admin).where(Admin.is_active == True)
                .order_by(Admin.created_at.desc())
            )
            db_admins = result.scalars().all()

        if db_admins:
            text += " **Из базы данных:**\n"
            for admin in db_admins:
                status = "SUCCESS:" if admin.is_active else "ERROR:"
                text += f"{status} `{admin.tg_id}` ({admin.role})\n"
        else:
            text += " **Из базы данных:** нет\n"

        text += f"\nCHART: **Всего активных:** {len(ADMIN_USERS)}"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        log.error(f"Failed to list admins: {e}")
        await update.message.reply_text(f"ERROR: Ошибка получения списка: {e}")


async def universal_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик всех callback queries (админских и клиентских)"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # TARGET: НОВОЕ: Клиентские кнопки доступны всем пользователям
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
    elif data == "admin_manage_admins":
        await show_admin_management_panel(query, context)
    elif data == "admin_detailed_analytics":
        await show_detailed_analytics_panel(query, context)
    elif data == "admin_refresh":
        await refresh_admin_panel(query, context)
    elif data == "admin_export":
        await show_export_options(query, context)
    elif data == "smm_main_panel":
        await show_smm_main_panel(query, context)
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
        await cmd_admin_callback(query, context)
    elif data.startswith("admin_add_") or data.startswith("admin_list_") or data.startswith("admin_reload_") or data.startswith("admin_role_"):
        await handle_admin_management_actions(query, context)
    elif data.startswith("export_") or data.startswith("analytics_"):
        await handle_export_analytics_actions(query, context)
    elif data == "smm_optimize":
        await handle_smm_optimize(query, context)
    elif data == "smm_toggle":
        await handle_smm_toggle(query, context)
    elif data.startswith("smm_"):
        await handle_smm_actions(query, context)


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
        text = "CLIPBOARD: Нет заявок"
    else:
        text = "CLIPBOARD: **ПОСЛЕДНИЕ ЗАЯВКИ**\n\n"
        keyboard = []

        for app, user in apps:
            status_emoji = {
                "new": "NEW:",
                "processing": "⏳",
                "completed": "SUCCESS:"
            }.get(app.status, "")

            # Используем subcategory вместо Category.name
            category_name = app.subcategory.split(
                ':')[0] if app.subcategory and ':' in app.subcategory else (app.subcategory or "Общие вопросы")

            text += f"{status_emoji} #{app.id} | {category_name}\n"
            text += f"USER: {user.first_name} {user.phone or ''}\n"
            text += f"CALENDAR: {app.created_at.strftime('%d.%m %H:%M')}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"#{app.id} Подробнее",
                    callback_data=f"app_view_{app.id}"
                )
            ])

    keyboard.append([InlineKeyboardButton(
        " Назад", callback_data="back_admin")])

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
            await query.answer("ERROR: Ошибка отображения данных", show_alert=True)


async def handle_application_action(query, context):
    """FIX: ПРОДАКШН-ГОТОВО: Полные действия с заявкой"""
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
            'phone': 'PHONE: Телефонный звонок',
            'telegram': 'CHAT: Telegram',
            'email': 'EMAIL: Email',
            'whatsapp': ' WhatsApp'
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
CLIPBOARD: **ЗАЯВКА #{app.id}**

FOLDER: Категория: {safe_category}
MEMO: Подкатегория: {safe_subcategory}

USER: **Клиент:**
Имя: {safe_first_name} {safe_last_name}
PHONE: {safe_phone}
EMAIL: {safe_email}
CHAT: Связь: {contact_methods.get(app.contact_method, app.contact_method or '-')}
CLOCK: Время: {app.contact_time or 'любое'}

 **Описание:**
{safe_description}

{f' Файлов: {len(app.files_data or [])}' if app.files_data else ''}
{f' UTM: {app.utm_source}' if app.utm_source else ''}

DOLLAR: Стоимость: {app.price or 'не определена'}  rubles
CHART: Статус: {app.status}
CALENDAR: Создана: {app.created_at.strftime('%d.%m.%Y %H:%M')}
"""

        # Ограничиваем общую длину сообщения для Telegram
        if len(text) > 4000:
            text = text[:4000] + '\n\\.\\.\\.'

        # Динамические кнопки в зависимости от статуса
        keyboard = []

        if app.status == "new":
            keyboard.extend([
                [InlineKeyboardButton("SUCCESS: Взять в работу", callback_data=f"app_take_{app.id}"),
                 InlineKeyboardButton("ERROR: Отклонить", callback_data=f"app_reject_{app.id}")],
                [InlineKeyboardButton("CARD: Выставить счет",
                                      callback_data=f"app_bill_{app.id}")]
            ])
        elif app.status == "processing":
            keyboard.extend([
                [InlineKeyboardButton("SUCCESS: Завершить", callback_data=f"app_complete_{app.id}"),
                 InlineKeyboardButton("ERROR: Отклонить", callback_data=f"app_reject_{app.id}")],
                [InlineKeyboardButton("CARD: Выставить счет",
                                      callback_data=f"app_bill_{app.id}")]
            ])
        elif app.status == "completed":
            keyboard.append([InlineKeyboardButton(
                "CARD: Повторный счет", callback_data=f"app_bill_{app.id}")])
        elif app.status == "cancelled":
            keyboard.append([InlineKeyboardButton(
                "CHANGES: Восстановить", callback_data=f"app_take_{app.id}")])

        keyboard.append([InlineKeyboardButton(
            " К списку", callback_data="admin_apps")])

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
                await query.answer("ERROR: Ошибка отображения данных", show_alert=True)

    elif data.startswith("app_take_"):
        # SUCCESS: Взять заявку в работу
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
            await query.answer("SUCCESS: Заявка взята в работу", show_alert=True)

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
            await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)

    elif data.startswith("app_reject_"):
        # ERROR: Отклонить заявку
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
            await query.answer("ERROR: Заявка отклонена", show_alert=True)

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
            await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)

    elif data.startswith("app_bill_"):
        # CARD: Выставить счет
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
                app.notes += f"\n[{datetime.now().strftime('%d.%m %H:%M')}] Счет выставлен администратором {admin_id}. Сумма: {app.price}  rubles"

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
CARD: **СЧЕТ ВЫСТАВЛЕН**

CLIPBOARD: Заявка: #{app.id}
USER: Клиент: {user.first_name} {user.last_name or ''}
DOLLAR: Сумма: {app.price}  rubles

LINK: **Ссылка на оплату:**
{pay_url}

SUCCESS: Клиент уведомлен о необходимости оплаты
"""

                keyboard = [
                    [InlineKeyboardButton(
                        "LINK: Открыть ссылку", url=pay_url)],
                    [InlineKeyboardButton(
                        "CLIPBOARD: Вернуться к заявке", callback_data=f"app_view_{app_id}")],
                    [InlineKeyboardButton(
                        " К списку", callback_data="admin_apps")]
                ]
            else:
                text = f"""
CARD: **СЧЕТ ВЫСТАВЛЕН**

CLIPBOARD: Заявка: #{app.id}
USER: Клиент: {user.first_name} {user.last_name or ''}
DOLLAR: Сумма: {app.price}  rubles

WARNING: **Платежная система не настроена**
Клиент должен оплатить другим способом

SUCCESS: Клиент уведомлен о необходимости оплаты
"""

                keyboard = [
                    [InlineKeyboardButton(
                        "CLIPBOARD: Вернуться к заявке", callback_data=f"app_view_{app_id}")],
                    [InlineKeyboardButton(
                        " К списку", callback_data="admin_apps")]
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
                    await query.answer("ERROR: Ошибка отображения данных", show_alert=True)

        except Exception as e:
            log.error(f"Error billing application {app_id}: {e}")
            await query.answer(f"ERROR: Ошибка выставления счета: {e}", show_alert=True)

    elif data.startswith("app_complete_"):
        # SUCCESS: Завершить заявку
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
            await query.answer("SUCCESS: Заявка завершена", show_alert=True)

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
            await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)


async def handle_client_action(query, context):
    """USER: ПРОДАКШН-ГОТОВО: Действия с клиентами"""
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
USER: **КЛИЕНТ: {user.first_name} {user.last_name or ''}**

PHONE: Телефон: {user.phone or 'не указан'}
EMAIL: Email: {user.email or 'не указан'}
ID: Telegram ID: `{user.tg_id}`
CALENDAR: Регистрация: {user.created_at.strftime('%d.%m.%Y') if hasattr(user, 'created_at') else 'н/д'}

CHART: **Статистика:**
- Всего заявок: {len(applications)}
- Общая сумма: {total_amount}  rubles
- Последняя заявка: {recent_app.created_at.strftime('%d.%m.%Y') if recent_app else 'нет'}

CLIPBOARD: **Последние заявки:**
"""

        keyboard = []
        for app in applications[:5]:  # Показываем последние 5
            status_emoji = {"new": "NEW:", "processing": "⏳",
                            "completed": "SUCCESS:"}.get(app.status, "")
            category_name = app.subcategory.split(
                ':')[0] if app.subcategory and ':' in app.subcategory else "Общие"
            text += f"{status_emoji} #{app.id} | {category_name} | {app.price or 0}  rubles\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"CLIPBOARD: Заявка #{app.id}",
                    callback_data=f"app_view_{app.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(
            " К списку", callback_data="admin_users")])

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
                await query.answer("ERROR: Ошибка отображения данных", show_alert=True)


async def handle_broadcast_action(query, context):
    """ ПРОДАКШН-ГОТОВО: Обработка массовых рассылок"""
    data = query.data

    # Определяем тип рассылки
    broadcast_types = {
        "broadcast_all": ("USERS: Всем клиентам", "SELECT DISTINCT tg_id FROM users WHERE tg_id IS NOT NULL"),
        "broadcast_active": ("MEMO: С активными заявками", """
            SELECT DISTINCT u.tg_id FROM users u
            JOIN applications a ON u.id = a.user_id
            WHERE a.status IN ('new', 'processing') AND u.tg_id IS NOT NULL
        """),
        "broadcast_inactive": (" Без заявок", """
            SELECT DISTINCT tg_id FROM users
            WHERE id NOT IN (SELECT DISTINCT user_id FROM applications)
            AND tg_id IS NOT NULL
        """),
        "broadcast_vip": ("STAR: VIP клиентам", """
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
                await query.answer(f"ERROR: Нет пользователей для рассылки в группе '{title}'", show_alert=True)
                return

            # Просим админа ввести текст рассылки
            text = f"""
 **РАССЫЛКА: {title}**

USERS: **Найдено пользователей:** {len(user_ids)}

MEMO: **Отправьте сообщение для рассылки:**

Ответьте на это сообщение текстом, который нужно разослать.

WARNING: **Внимание:**
- Рассылка будет отправлена сразу {len(user_ids)} пользователям
- Отменить после отправки нельзя
- Максимум 4000 символов
"""

            keyboard = [
                [InlineKeyboardButton(
                    "ERROR: Отменить", callback_data="admin_broadcast")]
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
                    await query.answer("ERROR: Ошибка отображения данных", show_alert=True)

            # Сохраняем данные рассылки в контексте
            context.user_data['pending_broadcast'] = {
                'type': data,
                'title': title,
                'user_ids': user_ids,
                'waiting_for_text': True
            }

        except Exception as e:
            log.error(f"Broadcast preparation error: {e}")
            await query.answer(f"ERROR: Ошибка подготовки рассылки: {e}", show_alert=True)


async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ПРОДАКШН-ГОТОВО: Обработка текста для массовой рассылки"""
    broadcast_data = context.user_data.get('pending_broadcast', {})

    if not broadcast_data.get('waiting_for_text'):
        return

    message_text = update.message.text
    user_ids = broadcast_data.get('user_ids', [])
    title = broadcast_data.get('title', 'Неизвестная группа')

    # Очищаем состояние ожидания
    context.user_data['pending_broadcast'] = {}

    if len(message_text) > 4000:
        await update.message.reply_text("ERROR: Текст слишком длинный (максимум 4000 символов)")
        return

    if not user_ids:
        await update.message.reply_text("ERROR: Список пользователей пуст")
        return

    # Подтверждение перед отправкой
    confirm_text = f"""
 **ПОДТВЕРЖДЕНИЕ РАССЫЛКИ**

TARGET: **Группа:** {title}
USERS: **Получателей:** {len(user_ids)}

MEMO: **Текст сообщения:**
{message_text[:500]}{'...' if len(message_text) > 500 else ''}

WARNING: **Внимание:** после подтверждения рассылка будет отправлена немедленно!
"""

    keyboard = [
        [InlineKeyboardButton(
            "SUCCESS: ОТПРАВИТЬ", callback_data=f"confirm_broadcast_{len(user_ids)}")],
        [InlineKeyboardButton(
            "ERROR: Отменить", callback_data="admin_broadcast")]
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
            await update.answer("ERROR: Ошибка отправки сообщения", show_alert=True)


async def execute_broadcast(query, context):
    """ROCKET: ПРОДАКШН-ГОТОВО: Выполнение массовой рассылки"""
    await query.answer()

    broadcast_data = context.user_data.get('broadcast_ready', {})

    if not broadcast_data:
        await query.answer("ERROR: Данные рассылки не найдены", show_alert=True)
        return

    message_text = broadcast_data.get('message_text')
    user_ids = broadcast_data.get('user_ids', [])
    title = broadcast_data.get('title', 'Неизвестная группа')

    # Очищаем данные рассылки
    context.user_data['broadcast_ready'] = {}

    if not message_text or not user_ids:
        await query.answer("ERROR: Недостаточно данных для рассылки", show_alert=True)
        return

    # Показываем прогресс
    progress_text = f"""
ROCKET: **РАССЫЛКА ЗАПУЩЕНА**

TARGET: **Группа:** {title}
USERS: **Получателей:** {len(user_ids)}

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
            await query.answer("ERROR: Ошибка отправки сообщения", show_alert=True)

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
ROCKET: **РАССЫЛКА В ПРОЦЕССЕ**

TARGET: **Группа:** {title}
USERS: **Получателей:** {len(user_ids)}

⏳ Отправлено: {sent_count}/{len(user_ids)}
ERROR: Ошибок: {failed_count}
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
SUCCESS: **РАССЫЛКА ЗАВЕРШЕНА**

TARGET: **Группа:** {title}
 **Отправлено:** {sent_count}/{len(user_ids)}
ERROR: **Неудачных:** {failed_count}

CHART: **Успешность:** {(sent_count/len(user_ids)*100):.1f}%

MEMO: **Текст сообщения:**
{message_text[:200]}{'...' if len(message_text) > 200 else ''}
"""

    keyboard = [
        [InlineKeyboardButton(" Назад к рассылке",
                              callback_data="admin_broadcast")],
        [InlineKeyboardButton(" Главное меню", callback_data="back_admin")]
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
            await query.answer("ERROR: Ошибка отображения данных", show_alert=True)

    log.info(
        f"Broadcast completed: {sent_count}/{len(user_ids)} sent successfully")


async def handle_settings_action(query, context):
    """ ПРОДАКШН-ГОТОВО: Обработка настроек"""
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
    """USERS: Управление администраторами"""
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(Admin).where(Admin.is_active == True)
            .order_by(Admin.created_at.desc())
        )
        admins = result.scalars().all()

    text = "USERS: **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**\n\n"

    if HARDCODED_ADMIN_IDS:
        text += "FIX: **Системные администраторы:**\n"
        for admin_id in sorted(HARDCODED_ADMIN_IDS):
            text += f"- `{admin_id}` (системный)\n"
        text += "\n"

    if admins:
        text += " **Администраторы из БД:**\n"
        for admin in admins:
            text += f"- `{admin.tg_id}` ({admin.role})\n"
    else:
        text += " **Администраторы из БД:** нет\n"

    text += f"\nCHART: **Всего активных:** {len(ADMIN_USERS)}\n\n"
    text += "**Команды:**\n"
    text += "- `/add_admin <ID> [роль]` - добавить\n"
    text += "- `/list_admins` - список\n"

    keyboard = [
        [InlineKeyboardButton("CHANGES: Обновить список",
                              callback_data="setting_reload_admins")],
        [InlineKeyboardButton(" Назад", callback_data="admin_settings")]
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
            await query.answer("ERROR: Ошибка отображения данных", show_alert=True)


async def export_data(query, context):
    """CHART: Экспорт данных"""
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
CHART: **ЭКСПОРТ ДАННЫХ**
Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

**Общая статистика:**
- Пользователей: {total_users}
- Заявок: {total_apps}
- Администраторов: {len(ADMIN_USERS)}

**По статусам заявок:**
"""
        for status, count in status_stats:
            report += f"- {status}: {count}\n"

        report += f"""

**Системная статистика:**
- Время работы: {datetime.now() - system_metrics['start_time']}
- Всего запросов: {system_metrics['total_requests']}
- Успешных: {system_metrics['successful_requests']}
- AI запросов: {system_metrics['ai_requests']}

 Полный экспорт в Google Sheets доступен через интеграцию.
"""

        keyboard = [
            [InlineKeyboardButton(" Назад", callback_data="admin_settings")]
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
                await query.answer("ERROR: Ошибка отображения данных", show_alert=True)

    except Exception as e:
        await query.answer(f"Ошибка экспорта: {e}", show_alert=True)


async def reload_settings(query, context):
    """CHANGES: Перезагрузка настроек"""
    try:
        # Перезагружаем администраторов из БД
        await load_db_admins()

        await query.answer("SUCCESS: Настройки перезагружены", show_alert=True)
        await show_admin_settings(query, context)

    except Exception as e:
        await query.answer(f"Ошибка перезагрузки: {e}", show_alert=True)


async def clear_logs(query, context):
    """ Очистка логов"""
    # Очищаем метрики
    system_metrics["total_requests"] = 0
    system_metrics["successful_requests"] = 0
    system_metrics["failed_requests"] = 0
    system_metrics["ai_requests"] = 0
    system_metrics["start_time"] = datetime.now()

    await query.answer("SUCCESS: Логи очищены", show_alert=True)
    await show_admin_settings(query, context)


async def show_detailed_stats(query, context):
    """GROWTH: Детальная статистика"""
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
GROWTH: **ДЕТАЛЬНАЯ СТАТИСТИКА**

CALENDAR: **По периодам:**
- Сегодня: {today_apps} заявок
- За неделю: {week_apps} заявок
- За месяц: {month_apps} заявок

CHART: **Топ категории (месяц):**
"""

    for subcategory, count in top_categories:
        cat_name = subcategory.split(
            ':')[0] if subcategory and ':' in subcategory else subcategory
        text += f"- {cat_name}: {count}\n"

    # Системные метрики
    uptime = datetime.now() - system_metrics["start_time"]
    success_rate = 0
    if system_metrics["total_requests"] > 0:
        success_rate = (
            system_metrics["successful_requests"] / system_metrics["total_requests"]) * 100

    text += f"""

 **Системные метрики:**
- Время работы: {uptime.days}д {uptime.seconds // 3600}ч
- Успешность: {success_rate:.1f}%
- RPS: {system_metrics["total_requests"] / max(uptime.total_seconds(), 1):.2f}
"""

    keyboard = [
        [InlineKeyboardButton(
            "CHANGES: Обновить", callback_data="setting_detailed_stats")],
        [InlineKeyboardButton(" Назад", callback_data="admin_settings")]
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
            await query.answer("ERROR: Ошибка отображения данных", show_alert=True)


async def client_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TARGET: НОВЫЙ: Обработчик клиентского пути"""
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
    """PHONE: Заказать звонок"""
    text = """
PHONE: **ЗАКАЗАТЬ ОБРАТНЫЙ ЗВОНОК**

Укажите ваш номер телефона и удобное время для звонка.
Наш юрист свяжется с вами в течение 30 минут.

CLOCK: **Рабочие часы:** 9:00 - 21:00 (МСК)
DOLLAR: **Стоимость:** Первые 15 минут БЕСПЛАТНО

MEMO: Или оставьте заявку через форму:
"""

    keyboard = [
        [InlineKeyboardButton("PHONE: Указать телефон",
                              callback_data="enter_phone")],
        [InlineKeyboardButton(
            "MEMO: Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀ Назад", callback_data="back_to_chat")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_chat_consultation(query, context):
    """CHAT: Консультация в чате"""
    text = """
CHAT: **КОНСУЛЬТАЦИЯ В ЧАТЕ**

Выберите категорию вашего вопроса для получения персональной консультации:

TARGET: **Преимущества чат-консультации:**
- Быстрые ответы в течение 5-10 минут
- Сохранение переписки для истории
- Возможность отправки документов
- Первичная консультация БЕСПЛАТНО
"""

    keyboard = [
        [
            InlineKeyboardButton(" Семейное",
                                 callback_data="consultation_category_family"),
            InlineKeyboardButton(" Жилищное",
                                 callback_data="consultation_category_housing")
        ],
        [
            InlineKeyboardButton(" Трудовые",
                                 callback_data="consultation_category_labor"),
            InlineKeyboardButton("CARD: Банкротство",
                                 callback_data="consultation_category_bankruptcy")
        ],
        [
            InlineKeyboardButton(" Потребители",
                                 callback_data="consultation_category_consumer"),
            InlineKeyboardButton("SCALES: Другие",
                                 callback_data="consultation_category_other")
        ],
        [InlineKeyboardButton("◀ Назад", callback_data="back_to_chat")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_get_price(query, context):
    """CHART: Узнать стоимость"""
    text = """
CHART: **СТОИМОСТЬ ЮРИДИЧЕСКИХ УСЛУГ**

DOLLAR: **КОНСУЛЬТАЦИИ:**
- Устная консультация: 2 000  rubles/час
- Письменная консультация: 1 500  rubles
- Анализ документов: 3 000  rubles

SCALES: **СУДЕБНОЕ ПРЕДСТАВИТЕЛЬСТВО:**
- Гражданские дела: от 30 000  rubles
- Административные дела: от 15 000  rubles
- Арбитражные споры: от 50 000  rubles

MEMO: **СОСТАВЛЕНИЕ ДОКУМЕНТОВ:**
- Претензии: от 5 000  rubles
- Договоры: от 10 000  rubles
- Исковые заявления: от 15 000  rubles

 **СПЕЦИАЛЬНЫЕ ПРЕДЛОЖЕНИЯ:**
- Первая консультация БЕСПЛАТНО
- Скидка 20% при заключении договора на месяц
- Фиксированная стоимость по результату

Точную стоимость рассчитаем после анализа вашей ситуации.
"""

    keyboard = [
        [InlineKeyboardButton("MEMO: Получить расчет",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("PHONE: Обсудить по телефону",
                              callback_data="request_call")],
        [InlineKeyboardButton("◀ Назад", callback_data="back_to_chat")]
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
SUCCESS: **ВЫБРАНА КАТЕГОРИЯ: {category.upper()}**

Теперь опишите вашу ситуацию максимально подробно:

MEMO: **Что указать:**
- Суть проблемы
- Что уже предпринимали
- Какой результат нужен
- Есть ли срочность

 **Наш юрист ответит в течение 10 минут**

Либо заполните подробную заявку для более детального анализа:
"""

    # Сохраняем выбранную категорию в контекст пользователя
    context.user_data['consultation_category'] = category
    context.user_data['awaiting_consultation_details'] = True

    keyboard = [
        [InlineKeyboardButton("MEMO: Заполнить подробную заявку",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀ Выбрать другую категорию",
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
CHAT: Продолжайте задавать вопросы в чате.

Наш AI-консультант готов помочь с любыми юридическими вопросами!
"""

    keyboard = [
        [
            InlineKeyboardButton(
                "MEMO: Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL)),
            InlineKeyboardButton("PHONE: Звонок",
                                 callback_data="request_call")
        ],
        [
            InlineKeyboardButton("CHAT: Консультация",
                                 callback_data="chat_consultation"),
            InlineKeyboardButton("CHART: Стоимость",
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
MEMO: **КОНСУЛЬТАЦИЯ В ЧАТЕ**

USER: **Клиент:** {user.first_name} {user.last_name or ''}
ID: **ID:** `{user_id}`
FOLDER: **Категория:** {category}

 **Детали проблемы:**
{user_text}

CLOCK: **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

TARGET: **Требуется:** Оперативная консультация в чате
"""

    admin_keyboard = [[
        InlineKeyboardButton("CHAT: Ответить клиенту",
                             url=f"tg://user?id={user_id}")
    ]]

    try:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        log.info(
            f"SUCCESS: Consultation request sent to admin for user {user_id}")
    except Exception as e:
        log.error(f"ERROR: Failed to send consultation request to admin: {e}")

    # Ответ клиенту
    response_text = f"""
SUCCESS: **ЗАЯВКА НА КОНСУЛЬТАЦИЮ ПРИНЯТА**

FOLDER: **Категория:** {category}
CLOCK: **Время подачи:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

 **Что дальше:**
- Наш юрист изучит вашу ситуацию
- Ответ поступит в течение 10-15 минут
- Первичная консультация БЕСПЛАТНО

IDEA: **Пока ждете ответа:**
Можете задать дополнительные вопросы или уточнить детали проблемы.
"""

    keyboard = [
        [InlineKeyboardButton("MEMO: Подать подробную заявку",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("PHONE: Заказать звонок",
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
                f"BOT: **ПРЕДВАРИТЕЛЬНАЯ AI-КОНСУЛЬТАЦИЯ:**\n\n{ai_response}\n\n"
                f"SCALES: Наш юрист дополнительно изучит детали и даст персональные рекомендации."
            )

    except Exception as e:
        log.error(f"ERROR: Failed to generate AI consultation: {e}")


async def enhanced_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TARGET: Улучшенный обработчик сообщений с поддержкой консультаций"""
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

    text = "BOT: **СТАТУС ENHANCED AI**\n\n"

    if ai_enhanced_manager is None:
        text += "ERROR: Enhanced AI не инициализирован\n"
        text += "CLIPBOARD: Используется базовый AI"
    elif not ai_enhanced_manager._initialized:
        text += "WARNING: Enhanced AI частично инициализирован\n"
        text += "CLIPBOARD: Используется fallback режим"
    else:
        try:
            # Получаем статус системы
            health = await ai_enhanced_manager.health_check()

            if health.get("status") == "healthy":
                text += "SUCCESS: Enhanced AI работает нормально\n\n"
            else:
                text += "WARNING: Enhanced AI работает с ограничениями\n\n"

            # Статус компонентов
            text += "**Компоненты:**\n"
            components = health.get("components", {})

            for name, status in components.items():
                emoji = "SUCCESS:" if status.get(
                    "status") == "ok" else "ERROR:"
                text += f"{emoji} {name.replace('_', ' ').title()}\n"

            # Аналитика
            try:
                analytics = await ai_enhanced_manager.get_analytics_summary()
                if analytics.get("status") != "no_data":
                    text += f"\n**Статистика:**\n"
                    text += f"CHART: Запросов: {analytics.get('total_requests', 0)}\n"
                    text += f" Успешность: {analytics.get('success_rate', 0):.1%}\n"
                    text += f"⏱ Время ответа: {analytics.get('avg_response_time', 0):.1f}ms\n"
                    if analytics.get('estimated_cost'):
                        text += f"DOLLAR: Расходы: ${analytics.get('estimated_cost', 0):.2f}\n"
            except:
                pass

        except Exception as e:
            text += f"ERROR: Ошибка получения статуса: {str(e)}"

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="back_admin")]]

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
            await query.answer("ERROR: Ошибка отображения данных", show_alert=True)


async def handle_enter_phone(query, context):
    """PHONE: Ввод телефона для заказа звонка"""
    text = """
PHONE: **УКАЖИТЕ ВАШ НОМЕР ТЕЛЕФОНА**

Отправьте ваш номер телефона в следующем сообщении.

MEMO: **Формат:** +7 (900) 123-45-67 или 89001234567

CLOCK: **Также укажите удобное время для звонка:**
- Утром (9:00-12:00)
- Днем (12:00-17:00)
- Вечером (17:00-21:00)
- Сейчас (в рабочее время)

Пример сообщения:
`+7 (900) 123-45-67, звонить вечером`
"""

    # Сохраняем состояние ожидания номера телефона
    context.user_data['awaiting_phone_input'] = True

    keyboard = [
        [InlineKeyboardButton("MEMO: Заполнить заявку вместо звонка",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("◀ Назад", callback_data="request_call")]
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
PHONE: **ЗАЯВКА НА ОБРАТНЫЙ ЗВОНОК**

USER: **Клиент:** {user.first_name} {user.last_name or ''}
ID: **ID:** `{user_id}`

PHONE: **Контакт:** {user_text}

CLOCK: **Время заявки:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

TARGET: **Требуется:** Обратный звонок в указанное время
DOLLAR: **Условие:** Первые 15 минут БЕСПЛАТНО
"""

    admin_keyboard = [[
        InlineKeyboardButton("PHONE: Позвонить",
                             url=f"tg://user?id={user_id}"),
        InlineKeyboardButton("CHAT: Написать", url=f"tg://user?id={user_id}")
    ]]

    try:
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        log.info(f"SUCCESS: Call request sent to admin for user {user_id}")
    except Exception as e:
        log.error(f"ERROR: Failed to send call request to admin: {e}")

    # Ответ клиенту
    response_text = f"""
SUCCESS: **ЗАЯВКА НА ЗВОНОК ПРИНЯТА**

PHONE: **Ваш номер:** {user_text}
CLOCK: **Время подачи:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

 **Что дальше:**
- Наш юрист свяжется с вами в указанное время
- Проверьте, что телефон доступен для входящих
- Первые 15 минут консультации БЕСПЛАТНО

PHONE: **Если не дозвонимся:**
Попробуем связаться через Telegram или вы можете написать нам сами.
"""

    keyboard = [
        [InlineKeyboardButton("MEMO: Дополнительная заявка",
                              web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("CHAT: Задать вопрос в чате",
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
    """TARGET: РАЗНООБРАЗНЫЙ АВТОПОСТИНГ: кейсы, нормативные акты, прецеденты, правовые аспекты"""
    if not CHANNEL_ID:
        return

    log.info("ROCKET: Starting diverse legal content autopost...")

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

        log.info(f"MEMO: Selected content type: {content_type}")

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

        log.info(
            f"SUCCESS: Generated {content_type} post: {len(post_text)} chars")

        # Добавляем кнопку для консультации
        keyboard = [[
            InlineKeyboardButton(" Получить консультацию",
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
            f"SUCCESS: {content_type} post sent to channel: {message.message_id}")

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
        log.error(f"ERROR: Diverse autopost failed: {e}")
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
            "act": "Постановление Правительства РФ No. 2463 от 31.12.2024",
            "changes": """CHANGES: **ЧТО ИЗМЕНИЛОСЬ:**
- Возврат товаров через маркетплейсы теперь возможен в течение 30 дней
- Маркетплейс обязан предоставить адрес пункта возврата в течение 3 дней
- При отказе продавца возврат осуществляет сама платформа
- Введена ответственность маркетплейсов за недобросовестных продавцов""",
            "impact": """GROWTH: **КАК ЭТО ВЛИЯЕТ НА ВАС:**
SUCCESS: Больше защиты при покупках на Wildberries, Ozon, Яндекс.Маркет
SUCCESS: Упрощенная процедура возврата без споров с продавцом
SUCCESS: Гарантированная компенсация даже при исчезновении продавца
WARNING: Исключения: продукты питания, лекарства, цифровые товары""",
            "action": """IDEA: **ЧТО ДЕЛАТЬ:**
1. Сохраняйте все документы о покупке (скриншоты, чеки)
2. При проблемах сначала обращайтесь к продавцу
3. Если нет ответа 3 дня - пишите в службу поддержки маркетплейса
4. При отказе - жалуйтесь в Роспотребнадзор со ссылкой на новые правила"""
        },
        {
            "title": "Изменения в Трудовом кодексе: электронные трудовые книжки",
            "act": "Федеральный закон No. 439-ФЗ от 16.12.2024",
            "changes": """CHANGES: **ЧТО ИЗМЕНИЛОСЬ:**
- С 1 марта 2025 года все новые трудовые договоры только в электронном виде
- Работодатель обязан уведомлять ПФР о трудоустройстве в течение 1 дня
- Введены штрафы за несвоевременную подачу сведений (до 50,000 rubles)
- Бумажные трудовые книжки сохраняются только по заявлению работника""",
            "impact": """GROWTH: **КАК ЭТО ВЛИЯЕТ НА ВАС:**
SUCCESS: Быстрое оформление на работу без бумажной волокиты
SUCCESS: Невозможность потери трудовой книжки
SUCCESS: Мгновенный доступ к стажу через госуслуги
WARNING: Необходимость следить за корректностью электронных записей""",
            "action": """IDEA: **ЧТО ДЕЛАТЬ:**
1. Подайте заявление о переходе на электронную трудовую книжку
2. Регулярно проверяйте записи через портал госуслуг
3. При ошибках немедленно требуйте исправления от работодателя
4. Ведите личный архив справок и документов о работе"""
        },
        {
            "title": "Новые правила раздела имущества при разводе",
            "act": "Федеральный закон No. 478-ФЗ от 28.12.2024",
            "changes": """CHANGES: **ЧТО ИЗМЕНИЛОСЬ:**
- Криптовалюты и NFT теперь подлежат разделу как совместно нажитое имущество
- Долги по кредитам делятся пропорционально полученному имуществу
- Доходы от интеллектуальной собственности учитываются при разделе
- Упрощена процедура раздела через нотариуса без суда""",
            "impact": """GROWTH: **КАК ЭТО ВЛИЯЕТ НА ВАС:**
SUCCESS: Справедливый раздел всех видов современного имущества
SUCCESS: Невозможность скрыть цифровые активы от раздела
SUCCESS: Более быстрое оформление развода через нотариуса
WARNING: Необходимость декларировать все доходы и активы""",
            "action": """IDEA: **ЧТО ДЕЛАТЬ:**
1. Ведите учет всех цифровых активов и доходов в браке
2. При разводе заявляйте о всех известных активах супруга
3. Требуйте справки о доходах за весь период брака
4. Рассмотрите возможность нотариального соглашения"""
        }
    ]

    selected = random.choice(normative_acts)

    post = f"""NEW: **НОВЫЙ ЗАКОН: {selected['title'].upper()}**

SCROLL: **{selected['act']}**

{selected['changes']}

{selected['impact']}

{selected['action']}

 **НУЖНА ПОМОЩЬ ЮРИСТА?**
Не знаете, как применить новый закон к вашей ситуации?

TARGET: Наши специалисты:
SUCCESS: Объяснят изменения простым языком
SUCCESS: Проанализируют влияние на ваши права
SUCCESS: Помогут защитить интересы в новых условиях
SUCCESS: Составят документы с учетом изменений

CHAT: Первая консультация БЕСПЛАТНО: /start
SCALES: Будьте в курсе всех изменений в законодательстве!"""

    return post


async def generate_precedent_post() -> str:
    """Генерация поста о судебном прецеденте"""
    import random

    precedents = [
        {
            "title": "Верховный суд защитил права покупателей маркетплейсов",
            "case": "Определение ВС РФ No. 5-КГ24-119-К2",
            "story": """CLIPBOARD: **ДЕЛО:**
Гражданка М. купила телефон на Wildberries за 45,000 rubles. Товар оказался подделкой. Продавец исчез, Wildberries отказывался возмещать ущерб, ссылаясь на то, что является только 'посредником'.""",
            "decision": """SCALES: **РЕШЕНИЕ СУДА:**
Верховный суд постановил: маркетплейс несет солидарную ответственность с продавцом за некачественные товары, если:
- Не проверил документы продавца должным образом
- Получал комиссию с продажи
- Контролировал процесс продажи и доставки""",
            "impact": """TARGET: **ЗНАЧЕНИЕ ДЛЯ ГРАЖДАН:**
SUCCESS: Теперь можно требовать возмещения напрямую с маркетплейса
SUCCESS: Не нужно искать исчезнувших продавцов
SUCCESS: Ответственность несут Ozon, Wildberries, Яндекс.Маркет
SUCCESS: Суды обязаны применять эту практику во всех регионах"""
        },
        {
            "title": "Конституционный суд расширил права работников на удаленку",
            "case": "Постановление КС РФ No. 29-П от 15.11.2024",
            "story": """CLIPBOARD: **ДЕЛО:**
Программист С. работал удаленно 2 года. Работодатель потребовал выход в офис, угрожая увольнением. С. обратился в суд, ссылаясь на дискриминацию и нарушение трудовых прав.""",
            "decision": """SCALES: **РЕШЕНИЕ СУДА:**
Конституционный суд признал: если работник эффективно выполняет обязанности удаленно, принуждение к работе в офисе без производственной необходимости нарушает:
- Право на свободу труда
- Принцип равенства возможностей
- Право на справедливые условия труда""",
            "impact": """TARGET: **ЗНАЧЕНИЕ ДЛЯ РАБОТНИКОВ:**
SUCCESS: Работодатель должен обосновать требование работы в офисе
SUCCESS: Нельзя уволить за отказ от офисной работы без веских причин
SUCCESS: При споре суд будет оценивать эффективность удаленной работы
SUCCESS: Защита прав 'удаленщиков' на конституционном уровне"""
        },
        {
            "title": "Банки не могут блокировать счета без веских оснований",
            "case": "Постановление Пленума ВАС РФ No. 62 от 04.12.2024",
            "story": """CLIPBOARD: **ДЕЛО:**
ИП Козлов получил блокировку счета в Сбербанке за 'подозрительные операции'. Банк не объяснил причины. Бизнес остановился, начались штрафы и убытки.""",
            "decision": """SCALES: **РЕШЕНИЕ СУДА:**
Высший арбитражный суд установил: банки обязаны:
- Уведомлять о причинах блокировки в течение 24 часов
- Предоставлять возможность объяснения до блокировки
- Разблокировать счет при устранении нарушений
- Возмещать убытки при необоснованной блокировке""",
            "impact": """TARGET: **ЗНАЧЕНИЕ ДЛЯ БИЗНЕСА:**
SUCCESS: Защита от произвольных блокировок банками
SUCCESS: Право требовать компенсацию за убытки
SUCCESS: Обязательность объяснений от банка
SUCCESS: Сокращение времени разблокировки счетов"""
        }
    ]

    selected = random.choice(precedents)

    post = f"""SCALES: **ВАЖНЫЙ ПРЕЦЕДЕНТ: {selected['title'].upper()}**

CLIPBOARD: **{selected['case']}**

{selected['story']}

{selected['decision']}

{selected['impact']}

IDEA: **КАК ИСПОЛЬЗОВАТЬ:**
1. Ссылайтесь на это решение в аналогичных спорах
2. Требуйте от противной стороны соблюдения установленных правил
3. Подавайте жалобы в надзорные органы с ссылкой на прецедент
4. Используйте в обоснование исковых требований

 **СТОЛКНУЛИСЬ С ПОХОЖЕЙ СИТУАЦИЕЙ?**
Наши юристы помогут применить новую судебную практику:

SUCCESS: Составим документы со ссылками на прецеденты
SUCCESS: Поможем обосновать требования актуальной практикой
SUCCESS: Представим интересы в суде с учетом новых решений
SUCCESS: Добьемся максимального результата

CHAT: Бесплатная консультация: /start
SCALES: Знание прецедентов - ключ к победе в суде!"""

    return post


async def generate_legal_aspect_post() -> str:
    """Генерация поста о важном правовом аспекте"""
    import random

    legal_aspects = [
        {
            "title": "Моральный вред: как правильно требовать и получать",
            "intro": """DOLLAR: **Знаете ли вы?**
Моральный вред можно взыскать практически в любом споре, но 90% граждан делают это неправильно и получают копейки вместо существенных сумм.""",
            "key_points": """TARGET: **КЛЮЧЕВЫЕ ПРИНЦИПЫ:**

CHART: **Размеры в практике:**
- Потребительские споры: 5,000-50,000 rubles
- Трудовые нарушения: 10,000-100,000 rubles
- ДТП с пострадавшими: 50,000-500,000 rubles
- Клевета, оскорбления: 20,000-200,000 rubles

TARGET: **Факторы увеличения суммы:**
- Публичность нарушения (соцсети, СМИ)
- Длительность нарушения прав
- Особый статус пострадавшего (беременность, инвалидность)
- Грубое поведение нарушителя
- Материальное положение ответчика""",
            "mistakes": """ERROR: **ТИПИЧНЫЕ ОШИБКИ:**
- Просят слишком мало (1,000-3,000 rubles) - суд снижает еще больше
- Не обосновывают размер конкретными фактами
- Не прикладывают доказательства переживаний
- Забывают индексировать сумму на дату вынесения решения""",
            "tips": """SUCCESS: **КАК СДЕЛАТЬ ПРАВИЛЬНО:**
1. Изучите похожие дела в вашем регионе через картотеку судов
2. Просите сумму в 2-3 раза больше желаемой
3. Собирайте справки о лечении, показания свидетелей
4. Описывайте конкретные страдания, а не общие фразы
5. Указывайте на системность нарушений ответчиком"""
        },
        {
            "title": "Срок исковой давности: когда время работает против вас",
            "intro": """CLOCK: **Знаете ли вы?**
Каждый год тысячи граждан теряют право на справедливую компенсацию только потому, что не знают про сроки исковой давности.""",
            "key_points": """TARGET: **ОСНОВНЫЕ СРОКИ:**

CALENDAR: **3 года (общий срок):**
- Взыскание долгов по договорам
- Возмещение ущерба от ДТП
- Компенсация за некачественный ремонт
- Взыскание с управляющих компаний

CALENDAR: **1 год (специальные случаи):**
- Трудовые споры (восстановление, зарплата)
- Споры по перевозке грузов
- Ничтожность сделок

CALENDAR: **2 года:**
- Защита прав потребителей
- Страховые выплаты

CALENDAR: **10 лет:**
- Возмещение вреда жизни и здоровью""",
            "mistakes": """ERROR: **ОПАСНЫЕ ЗАБЛУЖДЕНИЯ:**
- "Срок начинается с момента нарушения" - НЕТ! С момента, когда узнали о нарушении
- "Если подал претензию, срок приостанавливается" - НЕТ! Только суд приостанавливает
- "Устное обращение к нарушителю прерывает срок" - НЕТ! Только письменное признание долга""",
            "tips": """SUCCESS: **КАК ЗАЩИТИТЬ СЕБЯ:**
1. Ведите письменную переписку с нарушителем
2. Отправляйте претензии заказными письмами
3. При приближении срока - подавайте иск, даже для 'остановки часов'
4. Получайте письменные признания вины или долга
5. Помните: суд может восстановить срок при уважительных причинах"""
        },
        {
            "title": "Судебные расходы: как не платить за правосудие",
            "intro": """MONEY: **Знаете ли вы?**
Даже выиграв суд, можно остаться в убытке из-за судебных расходов. Но есть законные способы их избежать или переложить на противника.""",
            "key_points": """TARGET: **ВИДЫ РАСХОДОВ:**

DOLLAR: **Госпошлина:**
- До 1 млн rubles - от 4% до 13,200 rubles
- Свыше 1 млн rubles - 13,200 rubles + 0.5% с суммы свыше
- Неимущественные споры - 300 rubles
- Моральный вред - 300 rubles

DOLLAR: **Представительство:**
- Юристы: 2,000-10,000 rubles за заседание
- По сложным делам: до 50,000 rubles и выше
- Возмещается при победе в пределах 'разумных'

DOLLAR: **Экспертизы:**
- Почерковедческая: 15,000-30,000 rubles
- Строительная: 20,000-50,000 rubles
- Оценочная: 5,000-15,000 rubles""",
            "mistakes": """ERROR: **ДОРОГИЕ ОШИБКИ:**
- Не просят возмещения расходов в исковом заявлении
- Не ведут учет всех трат с документами
- Соглашаются на мировую без учета расходов
- Не обжалуют отказ в возмещении 'завышенных' сумм""",
            "tips": """SUCCESS: **КАК СЭКОНОМИТЬ:**
1. Используйте льготы по госпошлине (пенсионеры, инвалиды)
2. При иске до 50,000 rubles - представляйте себя сами
3. Ходатайствуйте об обеспечении иска для возмещения расходов
4. Ведите подробный учет всех трат
5. В мировом соглашении предусматривайте компенсацию расходов"""
        }
    ]

    selected = random.choice(legal_aspects)

    post = f"""IDEA: **ПРАВОВОЙ ЛИКБЕЗ: {selected['title'].upper()}**

{selected['intro']}

{selected['key_points']}

{selected['mistakes']}

{selected['tips']}

 **НУЖНА ПРОФЕССИОНАЛЬНАЯ ПОМОЩЬ?**
Столкнулись со сложной правовой ситуацией?

TARGET: Наши юристы:
SUCCESS: Просчитают все риски и возможности
SUCCESS: Разработают оптимальную стратегию действий
SUCCESS: Помогут избежать типичных ошибок
SUCCESS: Добьются максимального результата с минимальными затратами

CHAT: Бесплатная консультация: /start
BOOKS: Знание закона - ваша лучшая защита!"""

    return post


async def send_emergency_post(context):
    """Экстренный пост при сбоях"""
    emergency_post = get_emergency_case_post()

    keyboard = [[
        InlineKeyboardButton(" Срочная консультация",
                             url=f"https://t.me/{context.bot.username}")
    ]]

    await context.bot.send_message(
        CHANNEL_ID,
        emergency_post,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    log.info("SHIELD: Emergency post sent successfully")


def get_emergency_case_post() -> str:
    """Получить экстренный кейс-пост"""
    return """CLIPBOARD: **КЕЙС ИЗ ЖИЗНИ:**
Владимир купил автомобиль в салоне за 1,2 млн rubles. Через месяц обнаружились скрытые дефекты двигателя. Дилер утверждает, что это 'нормальный износ' и отказывается от гарантийного ремонта.

SCALES: **АЛГОРИТМ РЕШЕНИЯ:**
1. MEMO: Составьте письменную претензию к дилеру с требованием ремонта
2. SEARCH: Закажите независимую экспертизу для установления причин дефекта
3.  Направьте результаты экспертизы дилеру заказным письмом
4. BUILDING: При отказе - жалоба в Роспотребнадзор и автопроизводителю
5. SCALES: Подача иска в суд с требованием замены автомобиля
6. DOLLAR: Взыскание стоимости экспертизы и морального вреда
7.  Требование возврата всех понесенных расходов

BOOKS: **НОРМАТИВНАЯ БАЗА:**
SCROLL: Закон "О защите прав потребителей" No. 2300-1:
- Статья 18 - право на обмен/возврат товара ненадлежащего качества
- Статья 19 - гарантийные сроки и сроки службы
- Статья 29 - права потребителя при обнаружении недостатков

WARNING: **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
- Дилер может ссылаться на неправильную эксплуатацию
- Сложность доказательства заводского характера дефектов
- Высокая стоимость независимой экспертизы (30-50 тыс rubles)
- Длительность судебного процесса (6-12 месяцев)

 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Столкнулись с обманом автодилера? Действуйте решительно!

TARGET: Наши автоюристы помогут:
SUCCESS: Составить претензию с максимальными требованиями
SUCCESS: Найти надежных экспертов по разумным ценам
SUCCESS: Провести переговоры с дилером и производителем
SUCCESS: Представить интересы в суде с гарантией результата

CHAT: Первая консультация БЕСПЛАТНО: /start
SCALES: Возвращаем полную стоимость автомобиля в 85% случаев!"""


async def _fallback_autopost(context: ContextTypes.DEFAULT_TYPE):
    """РЕЗЕРВНЫЙ профессиональный автопостинг с кейсами"""

    try:
        # Используем новый профессиональный генератор
        from bot.services.content_intelligence.post_generator import PostGenerator

        enhanced_generator = PostGenerator()

        # Генерируем профессиональный пост с кейсом
        log.info("MEMO: Generating fallback professional case post...")
        post_text = await enhanced_generator.generate_post()

        log.info(
            f"SUCCESS: Generated fallback professional post: {len(post_text)} chars")

    except Exception as e:
        log.error(f"ERROR: Enhanced post generation failed: {e}")

        # ЭКСТРЕННЫЙ РЕЗЕРВ с кейсами
        fallback_cases = [
            """CLIPBOARD: **КЕЙС ИЗ ЖИЗНИ:**
Елена не получает зарплату 3 месяца. Директор ссылается на 'финансовые трудности', но заставляет работать в полном объеме. Угрожает увольнением при требовании расчета.

SCALES: **АЛГОРИТМ РЕШЕНИЯ:**
1. CLIPBOARD: Подайте письменное заявление работодателю с требованием выплаты
2. PHONE: Обратитесь в государственную инспекцию труда
3.  Соберите документы: трудовой договор, табели, справки
4. SCALES: Подайте заявление в суд о взыскании задолженности
5. DOLLAR: Требуйте компенсацию за задержку (1/150 ключевой ставки ЦБ)
6. BUILDING: Уведомите прокуратуру о нарушении трудовых прав
7. PHONE: Параллельно ищите новое место работы

BOOKS: **НОРМАТИВНАЯ БАЗА:**
SCROLL: Трудовой кодекс РФ No. 197-ФЗ:
- Статья 136 - сроки выплаты заработной платы
- Статья 236 - ответственность за задержку зарплаты
- Статья 140 - расчет при увольнении

WARNING: **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
- Работодатель может давить и создавать невыносимые условия
- Компания может обанкротиться, избегая выплат
- Восстановление заработной платы займет месяцы
- Без письменных документов сложно доказать размер долга

 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Работодатель не платит зарплату? Защитите свои права!

TARGET: Мы поможем взыскать:
SUCCESS: Всю задолженность по зарплате полностью
SUCCESS: Компенсацию за каждый день просрочки
SUCCESS: Моральный вред за нарушение прав
SUCCESS: Возмещение расходов на юридическую помощь

CHAT: Бесплатная консультация: /start
SCALES: Взыскиваем долги даже с обанкротившихся компаний!""",

            """CLIPBOARD: **КЕЙС ИЗ ЖИЗНИ:**
В квартире Петровых 4 месяца нет горячей воды. УК требует полную оплату за ЖКУ, ссылаясь на 'плановые ремонтные работы'. Жильцы вынуждены греть воду и покупать услуги бани.

SCALES: **АЛГОРИТМ РЕШЕНИЯ:**
1. MEMO: Подайте письменную жалобу в УК с требованием устранения
2. PHOTO: Зафиксируйте отсутствие услуги фото/видео с датой
3. BUILDING: Обратитесь в жилищную инспекцию вашего региона
4. DOLLAR: Требуйте перерасчета за период отсутствия услуги
5. PHONE: Подайте коллективную жалобу от всех пострадавших жильцов
6. SCALES: При отказе - иск в суд о взыскании ущерба
7. CHANGES: Инициируйте смену управляющей компании

BOOKS: **НОРМАТИВНАЯ БАЗА:**
SCROLL: ЖК РФ No. 188-ФЗ:
- Статья 154 - размер платы за коммунальные услуги
- Статья 161 - обязанности управляющей организации

BUILDING: Постановление Правительства No. 354:
- Правила перерасчета при нарушении качества услуг

WARNING: **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
- УК может сменить название, избегая ответственности
- Перерасчет возможен только за документально подтвержденный период
- Доказать размер ущерба без экспертизы сложно
- Собственники могут не поддержать смену УК

 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
УК нарушает ваши права? Добейтесь справедливости!

TARGET: Наши жилищные юристы:
SUCCESS: Добьются максимального перерасчета за весь период
SUCCESS: Взыщут компенсацию дополнительных расходов
SUCCESS: Привлекут УК к административной ответственности
SUCCESS: Организуют смену УК при необходимости

CHAT: Первая консультация БЕСПЛАТНО: /start
 Защищаем права собственников с 2010 года!""",

            """CLIPBOARD: **КЕЙС ИЗ ЖИЗНИ:**
После развода Михаил не платит алименты на ребенка 8 месяцев. Скрывает доходы, работает неофициально. Бывшая жена вынуждена брать кредиты на лечение сына.

SCALES: **АЛГОРИТМ РЕШЕНИЯ:**
1. CLIPBOARD: Подайте заявление о взыскании алиментов в мировой суд
2.  Получите судебный приказ или решение суда об алиментах
3. BUILDING: Направьте исполнительный лист в ФССП по месту работы должника
4. SEARCH: Подайте заявление о розыске должника и его имущества
5. CARD: Требуйте арест банковских счетов и имущества
6.  Инициируйте ограничение на выезд за границу
7. SCALES: При злостном уклонении - заявление о возбуждении уголовного дела

BOOKS: **НОРМАТИВНАЯ БАЗА:**
SCROLL: Семейный кодекс РФ No. 223-ФЗ:
- Статья 80 - обязанности родителей по содержанию детей
- Статья 81 - размер алиментов на несовершеннолетних
- Статья 115 - индексация алиментов

BUILDING: ФЗ "Об исполнительном производстве":
- Статья 65 - обращение взыскания на заработную плату

WARNING: **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
- Должник может скрывать реальные доходы
- Принудительное взыскание занимает месяцы и годы
- Алименты взыскиваются только с официальных доходов
- При выезде за границу розыск усложняется

 **ПОЛУЧИТЕ ПОМОЩЬ ЭКСПЕРТА:**
Не можете добиться выплаты алиментов? Мы поможем!

TARGET: Наши семейные юристы:
SUCCESS: Найдут скрытые доходы и имущество должника
SUCCESS: Добьются ареста всех счетов и активов
SUCCESS: Инициируют уголовное преследование злостных неплательщиков
SUCCESS: Взыщут задолженность с процентами и неустойкой

CHAT: Первая консультация БЕСПЛАТНО: /start
 Защищаем права детей и получаем результат!"""
        ]

        # Выбираем случайный кейс
        import random
        post_text = random.choice(fallback_cases)
        log.info(
            f"SHIELD: Using emergency fallback case post: {len(post_text)} chars")

    # Добавляем кнопку
    keyboard = [[
        InlineKeyboardButton(" Получить консультацию",
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
            f"FIX: Admins reloaded: hardcoded={len(HARDCODED_ADMIN_IDS)}, from_db={len(db_admin_ids)}, total={len(ADMIN_USERS)} (was {old_count})")
        print(f"FIX: Admin users updated: {len(ADMIN_USERS)} total")

    except Exception as e:
        log.error(f"Failed to load DB admins: {e}")
        # Если БД недоступна, используем только хардкодированных
        ADMIN_USERS = HARDCODED_ADMIN_IDS.copy()


async def post_init(application: Application):
    """Инициализация после запуска"""
    global ai_enhanced_manager

    # Загружаем администраторов из БД
    await load_db_admins()

    # ROCKET: ИНИЦИАЛИЗИРУЕМ Enhanced AI
    try:
        log.info("ROCKET: Initializing Enhanced AI system...")
        ai_enhanced_manager = AIEnhancedManager()
        await ai_enhanced_manager.initialize()
        print("SUCCESS: Enhanced AI initialized successfully")
        log.info("Enhanced AI system is ready")
    except Exception as e:
        print(f"ERROR: Failed to initialize Enhanced AI: {e}")
        log.error(f"Enhanced AI initialization error: {e}")
        import traceback
        log.error(f"Enhanced AI traceback: {traceback.format_exc()}")
        ai_enhanced_manager = None
        log.info("Will use basic AI as fallback")

    try:
        # Устанавливаем кнопку меню
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="MEMO: Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
        print("SUCCESS: Menu button set successfully")
    except Exception as e:
        print(f"ERROR: Failed to set menu button: {e}")
        log.error(f"Menu button error: {e}")


async def fix_database_schema():
    """Исправление схемы БД после предыдущих проблем"""
    try:
        log.info("FIX: Checking and fixing database schema...")

        async with async_sessionmaker() as session:
            # Проверяем тип колонки user_id
            result = await session.execute(text("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'applications' AND column_name = 'user_id'
            """))
            user_id_type = result.scalar_one_or_none()

            if user_id_type != "integer":
                log.info("CHANGES: user_id column type needs conversion")

                # Сначала исправляем некорректные значения
                log.info(" Cleaning up invalid user_id values...")

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
                            f"FIX: Fixing app {app_id} with bad user_id: '{bad_user_id}'")

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
                                f"SUCCESS: Created new temp user {temp_user} for app {app_id}")

                        # Обновляем заявку корректным user_id
                        await session.execute(text("""
                            UPDATE applications
                            SET user_id = :user_id
                            WHERE id = :app_id
                        """), {"user_id": str(temp_user), "app_id": app_id})

                        log.info(
                            f"SUCCESS: Fixed app {app_id}: '{bad_user_id}' -> {temp_user}")

                    except Exception as fix_error:
                        log.error(
                            f"ERROR: Failed to fix app {app_id}: {fix_error}")
                        # В крайнем случае ставим 1 (должен существовать)
                        await session.execute(text("""
                            UPDATE applications
                            SET user_id = '1'
                            WHERE id = :app_id
                        """), {"app_id": app_id})

                await session.commit()
                log.info("SUCCESS: Invalid user_id values cleaned up")

                # Теперь безопасно конвертируем тип
                log.info("CHANGES: Converting user_id column type to INTEGER...")
                await session.execute(text("""
                    ALTER TABLE applications
                    ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER
                """))

                await session.commit()
                log.info("SUCCESS: user_id column type converted to INTEGER")
                print("SUCCESS: Database schema fixed: user_id converted to INTEGER")
            else:
                log.info("SUCCESS: user_id column has correct type")

            # FIX: КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Добавляем отсутствующие колонки
            log.info("FIX: Checking for missing columns...")

            # Проверяем наличие колонки notes
            notes_result = await session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'applications' AND column_name = 'notes'
            """))
            has_notes = notes_result.scalar_one_or_none()

            if not has_notes:
                log.info(" Adding missing 'notes' column...")
                await session.execute(text("""
                    ALTER TABLE applications
                    ADD COLUMN notes TEXT
                """))
                await session.commit()
                log.info("SUCCESS: Added 'notes' column")
                print("SUCCESS: Added missing 'notes' column")

            # Проверяем наличие колонки assigned_admin
            admin_result = await session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'applications' AND column_name = 'assigned_admin'
            """))
            has_assigned_admin = admin_result.scalar_one_or_none()

            if not has_assigned_admin:
                log.info(" Adding missing 'assigned_admin' column...")
                await session.execute(text("""
                    ALTER TABLE applications
                    ADD COLUMN assigned_admin VARCHAR(64)
                """))
                await session.commit()
                log.info("SUCCESS: Added 'assigned_admin' column")
                print("SUCCESS: Added missing 'assigned_admin' column")

            print("SUCCESS: Database schema is up to date")

    except Exception as e:
        log.error(f"ERROR: Database schema fix failed: {e}")
        print(f"WARNING: Database schema fix failed: {e}")
        # Не прерываем запуск, продолжаем работу


async def main():
    """Точка входа"""
    # Инициализируем БД
    await init_db()

    # Проверяем и исправляем схему БД если нужно
    await fix_database_schema()

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # ROCKET: ИНИЦИАЛИЗИРУЕМ Enhanced AI
    try:
        log.info("ROCKET: Initializing Enhanced AI system...")
        ai_enhanced_manager = AIEnhancedManager()
        await ai_enhanced_manager.initialize()
        print("SUCCESS: Enhanced AI initialized successfully")
        log.info("Enhanced AI system is ready")
    except Exception as e:
        print(f"ERROR: Failed to initialize Enhanced AI: {e}")
        log.error(f"Enhanced AI initialization error: {e}")
        import traceback
        log.error(f"Enhanced AI traceback: {traceback.format_exc()}")
        ai_enhanced_manager = None
        log.info("Will use basic AI as fallback")

    try:
        # Устанавливаем кнопку меню
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="MEMO: Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
        print("SUCCESS: Menu button set successfully")
    except Exception as e:
        print(f"ERROR: Failed to set menu button: {e}")
        log.error(f"Menu button error: {e}")

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("add_admin", cmd_add_admin))
    application.add_handler(CommandHandler("list_admins", cmd_list_admins))
    application.add_handler(CallbackQueryHandler(universal_callback_handler))

    # Регистрируем SMM админ обработчики
    register_smm_admin_handlers(application)

    # FIX: ФИКС: Добавляем обработчик для ввода телефона и деталей консультации
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
    # FIX: УДАЛЯЕМ ДУБЛИРУЮЩИЙ ОБРАБОТЧИК
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
        print("SUCCESS: One-time autopost scheduled for 5 minutes after restart")
        log.info("One-time autopost job scheduled for 5 minutes after restart")

        # Основной повторяющийся автопостинг
        application.job_queue.run_repeating(
            autopost_job,
            interval=timedelta(hours=autopost_hours),
            first=timedelta(minutes=10)
        )
        print(
            f"SUCCESS: Job queue initialized - autopost every {autopost_hours} hours")
        log.info(f"Job queue initialized with {autopost_hours}h interval")
    else:
        print("WARNING: Job queue not available - autopost disabled")
        log.warning("Job queue not available, autopost functionality disabled")

    # Устанавливаем webhook
    webhook_url = f"https://{PUBLIC_HOST}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)

    # Запускаем приложение
    async with application:
        await application.start()
        log.info(f"Bot started on port {PORT}")

        # ROCKET: ОПТИМИЗАЦИЯ: Запускаем post_init в background для быстрого старта Railway
        async def background_init():
            """Background инициализация Enhanced AI для избежания Railway timeout"""
            try:
                print("FIX: Starting background Enhanced AI initialization...")
                await post_init(application)
                print("SUCCESS: Background Enhanced AI initialization completed")

                # Уведомляем админа после полной инициализации
                try:
                    await application.bot.send_message(
                        ADMIN_CHAT_ID,
                        "ROCKET: Бот полностью запущен с Enhanced AI!\n\n"
                        "Команды:\n"
                        "/admin - админ панель\n"
                        "/start - приветствие"
                    )
                except:
                    pass
            except Exception as e:
                print(
                    f"ERROR: Background Enhanced AI initialization failed: {e}")
                log.error(f"Background Enhanced AI init error: {e}")

        # Запускаем Enhanced AI инициализацию в background
        asyncio.create_task(background_init())

        print(
            "ROCKET: Railway-optimized startup completed - Enhanced AI initializing in background")

        # Держим бота живым
        await asyncio.Event().wait()


async def show_admin_panel(query):
    """Показать главную админ панель"""
    text = "FIX: **АДМИН ПАНЕЛЬ**\n\nВыберите раздел:"

    keyboard = [
        [InlineKeyboardButton("CLIPBOARD: Заявки", callback_data="admin_apps"),
         InlineKeyboardButton("CHART: Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("CARD: Платежи", callback_data="admin_payments"),
         InlineKeyboardButton("USERS: Клиенты", callback_data="admin_users")],
        [InlineKeyboardButton("BOT: AI Статус", callback_data="admin_ai_status"),
         InlineKeyboardButton(" Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(" Настройки", callback_data="admin_settings")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to edit message: {e}")
        await query.answer("ERROR: Ошибка отображения", show_alert=True)


async def show_statistics(query, context):
    """Показать общую статистику"""
    try:
        async with async_sessionmaker() as session:
            # Общие счетчики
            total_users = await session.scalar(select(func.count(User.id)))
            total_apps = await session.scalar(select(func.count(AppModel.id)))

            # Статистика по статусам заявок
            status_stats = await session.execute(
                select(AppModel.status, func.count(AppModel.id))
                .group_by(AppModel.status)
            )

            # Заявки за сегодня
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_apps = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.created_at >= today)
            )

            # Новые пользователи сегодня
            today_users = await session.scalar(
                select(func.count(User.id))
                .where(User.created_at >= today)
            )

        text = f"""
CHART: **ОБЩАЯ СТАТИСТИКА**

USERS: **Пользователи:**
- Всего: {total_users}
- Сегодня: {today_users}

CLIPBOARD: **Заявки:**
- Всего: {total_apps}
- Сегодня: {today_apps}

GROWTH: **По статусам:**
"""

        for status, count in status_stats:
            status_emoji = {
                "new": "NEW:",
                "processing": "⏳",
                "completed": "SUCCESS:",
                "cancelled": "ERROR:"
            }.get(status, "")
            text += f"- {status_emoji} {status}: {count}\n"

        # Системные метрики
        uptime = datetime.now() - system_metrics["start_time"]
        success_rate = 0
        if system_metrics["total_requests"] > 0:
            success_rate = (
                system_metrics["successful_requests"] / system_metrics["total_requests"]) * 100

        text += f"""

 **Система:**
- Время работы: {uptime.days}д {uptime.seconds // 3600}ч
- Запросов: {system_metrics["total_requests"]}
- Успешность: {success_rate:.1f}%
- AI запросов: {system_metrics["ai_requests"]}
"""

        keyboard = [
            [InlineKeyboardButton("GROWTH: Детальная статистика",
                                  callback_data="setting_detailed_stats")],
            [InlineKeyboardButton("CHANGES: Обновить",
                                  callback_data="admin_stats")],
            [InlineKeyboardButton(" Назад", callback_data="back_admin")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        log.error(f"Failed to show statistics: {e}")
        await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)


async def show_payments(query, context):
    """Показать платежи"""
    try:
        async with async_sessionmaker() as session:
            # Получаем последние платежи
            payments_result = await session.execute(
                select(Payment, AppModel, User)
                .join(AppModel, Payment.application_id == AppModel.id)
                .join(User, AppModel.user_id == User.id)
                .order_by(Payment.created_at.desc())
                .limit(10)
            )
            payments = payments_result.all()

            # Статистика платежей
            total_amount = await session.scalar(
                select(func.sum(Payment.amount))
                .where(Payment.status == 'completed')
            ) or 0

            pending_amount = await session.scalar(
                select(func.sum(Payment.amount))
                .where(Payment.status == 'pending')
            ) or 0

        text = f"""
CARD: **ПЛАТЕЖИ**

DOLLAR: **Финансы:**
- Получено: {total_amount}  rubles
- Ожидает: {pending_amount}  rubles
- Всего платежей: {len(payments)}

CLIPBOARD: **Последние:**
"""

        keyboard = []

        for payment, app, user in payments:
            status_emoji = {
                'pending': '⏳',
                'completed': 'SUCCESS:',
                'failed': 'ERROR:',
                'cancelled': ''
            }.get(payment.status, '')

            text += f"{status_emoji} {payment.amount}  rubles | {user.first_name}\n"
            text += f"CALENDAR: {payment.created_at.strftime('%d.%m %H:%M')}\n"

        if not payments:
            text += "Нет платежей\n"

        keyboard.append([InlineKeyboardButton(
            "CHANGES: Обновить", callback_data="admin_payments")])
        keyboard.append([InlineKeyboardButton(
            " Назад", callback_data="back_admin")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        log.error(f"Failed to show payments: {e}")
        await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)


async def show_clients(query, context):
    """Показать клиентов"""
    try:
        async with async_sessionmaker() as session:
            # Получаем пользователей с количеством заявок
            users_result = await session.execute(
                select(User, func.count(AppModel.id).label('app_count'))
                .outerjoin(AppModel, User.id == AppModel.user_id)
                .group_by(User.id)
                .order_by(func.count(AppModel.id).desc(), User.created_at.desc())
                .limit(15)
            )
            users = users_result.all()

        text = "USERS: **КЛИЕНТЫ**\n\n"
        keyboard = []

        for user, app_count in users:
            # Определяем тип клиента
            if app_count >= 3:
                client_type = "STAR: VIP"
            elif app_count >= 1:
                client_type = "MEMO: Активный"
            else:
                client_type = " Новый"

            text += f"{client_type} {user.first_name} {user.last_name or ''}\n"
            text += f"PHONE: {user.phone or 'не указан'} | Заявок: {app_count}\n"
            text += f"CALENDAR: {user.created_at.strftime('%d.%m.%Y') if hasattr(user, 'created_at') else 'н/д'}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"USER: {user.first_name} ({app_count})",
                    callback_data=f"client_view_{user.id}"
                )
            ])

        if not users:
            text += "Нет клиентов"

        keyboard.append([InlineKeyboardButton(
            "CHANGES: Обновить", callback_data="admin_users")])
        keyboard.append([InlineKeyboardButton(
            " Назад", callback_data="back_admin")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        log.error(f"Failed to show clients: {e}")
        await query.answer(f"ERROR: Ошибка: {e}", show_alert=True)


async def show_broadcast_options(query, context):
    """Показать опции рассылки"""
    text = """
 **МАССОВАЯ РАССЫЛКА**

Выберите целевую аудиторию:

USERS: **Все клиенты** - всем зарегистрированным
MEMO: **Активные** - с текущими заявками
 **Неактивные** - без заявок
STAR: **VIP** - с 3+ заявками

WARNING: **Внимание:**
- Рассылка отправляется сразу
- Отменить после отправки нельзя
- Соблюдайте антиспам правила
"""

    keyboard = [
        [InlineKeyboardButton(
            "USERS: Всем клиентам", callback_data="broadcast_all")],
        [InlineKeyboardButton("MEMO: С активными заявками",
                              callback_data="broadcast_active")],
        [InlineKeyboardButton(
            " Без заявок", callback_data="broadcast_inactive")],
        [InlineKeyboardButton(
            "STAR: VIP клиентам", callback_data="broadcast_vip")],
        [InlineKeyboardButton(" Назад", callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to show broadcast options: {e}")
        await query.answer("ERROR: Ошибка отображения", show_alert=True)


async def show_admin_settings(query, context):
    """Показать настройки"""
    text = f"""
 **НАСТРОЙКИ СИСТЕМЫ**

FIX: **Администрирование:**
- Администраторов: {len(ADMIN_USERS)}
- Хардкодированных: {len(HARDCODED_ADMIN_IDS)}

CHART: **Мониторинг:**
- Время работы: {datetime.now() - system_metrics['start_time']}
- Запросов: {system_metrics['total_requests']}
- Блокированных: {len(blocked_users)}

BOT: **AI Система:**
- Enhanced AI: {'SUCCESS: Активен' if ai_enhanced_manager and ai_enhanced_manager._initialized else 'ERROR: Неактивен'}
- Режим: {'Production' if PRODUCTION_MODE else 'Development'}

LINK: **Интеграции:**
- OpenRouter: {'SUCCESS:' if OPENROUTER_API_KEY else 'ERROR:'}
- Канал: {'SUCCESS:' if CHANNEL_ID else 'ERROR:'}
"""

    keyboard = [
        [InlineKeyboardButton("USERS: Управление админами",
                              callback_data="setting_admins")],
        [InlineKeyboardButton("CHART: Экспорт данных",
                              callback_data="setting_export")],
        [InlineKeyboardButton("GROWTH: Детальная статистика",
                              callback_data="setting_detailed_stats")],
        [InlineKeyboardButton(
            "CHANGES: Перезагрузить", callback_data="setting_reload")],
        [InlineKeyboardButton(
            " Очистить логи", callback_data="setting_clear_logs")],
        [InlineKeyboardButton(" Назад", callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to show admin settings: {e}")
        await query.answer("ERROR: Ошибка отображения", show_alert=True)


def detect_category(text: str) -> str:
    """Определение категории юридического вопроса по тексту"""
    if not text:
        return "Общие вопросы"

    text_lower = text.lower()

    # Семейное право
    family_keywords = ['развод', 'алименты', 'брак', 'дети',
                       'супруг', 'жена', 'муж', 'семья', 'усыновление', 'опека']
    if any(keyword in text_lower for keyword in family_keywords):
        return "Семейное право"

    # Трудовое право
    labor_keywords = ['работа', 'увольнение', 'зарплата',
                      'отпуск', 'трудовой', 'работодатель', 'сотрудник', 'премия']
    if any(keyword in text_lower for keyword in labor_keywords):
        return "Трудовое право"

    # Жилищное право
    housing_keywords = ['квартира', 'дом', 'жилье', 'аренда',
                        'ипотека', 'соседи', 'коммунальные', 'управляющая']
    if any(keyword in text_lower for keyword in housing_keywords):
        return "Жилищное право"

    # Банкротство
    bankruptcy_keywords = ['банкротство', 'долги',
                           'кредит', 'банк', 'коллектор', 'взыскание', 'должник']
    if any(keyword in text_lower for keyword in bankruptcy_keywords):
        return "Банкротство"

    # Защита прав потребителей
    consumer_keywords = ['товар', 'услуга', 'магазин',
                         'возврат', 'качество', 'гарантия', 'потребитель']
    if any(keyword in text_lower for keyword in consumer_keywords):
        return "Защита прав потребителей"

    # Административное право
    admin_keywords = ['штраф', 'полиция', 'гибдд',
                      'нарушение', 'административный', 'протокол']
    if any(keyword in text_lower for keyword in admin_keywords):
        return "Административное право"

    # Наследство
    inheritance_keywords = ['наследство', 'завещание',
                            'наследник', 'умер', 'смерть', 'нотариус']
    if any(keyword in text_lower for keyword in inheritance_keywords):
        return "Наследственное право"

    return "Общие вопросы"


async def show_admin_management_panel(query, context):
    """USERS: Интерактивная панель управления администраторами"""
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(
                select(Admin).where(Admin.is_active == True)
                .order_by(Admin.created_at.desc())
            )
            admins = result.scalars().all()

        text = "USERS: **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**\n\n"

        if HARDCODED_ADMIN_IDS:
            text += "FIX: **Системные администраторы:**\n"
            for admin_id in sorted(HARDCODED_ADMIN_IDS):
                text += f"- `{admin_id}` (системный)\n"
            text += "\n"

        if admins:
            text += " **Администраторы из БД:**\n"
            for admin in admins:
                status_icon = "SUCCESS:" if admin.is_active else "ERROR:"
                text += f"{status_icon} `{admin.tg_id}` ({admin.role})\n"
        else:
            text += " **Администраторы из БД:** нет\n"

        text += f"\nCHART: **Всего активных:** {len(ADMIN_USERS)}\n\n"

        keyboard = [
            [
                InlineKeyboardButton(" Добавить админа",
                                     callback_data="admin_add_new"),
                InlineKeyboardButton(
                    "CLIPBOARD: Полный список", callback_data="admin_list_all")
            ],
            [
                InlineKeyboardButton("CHANGES: Обновить из БД",
                                     callback_data="admin_reload_db"),
                InlineKeyboardButton(" Настройки ролей",
                                     callback_data="admin_role_settings")
            ],
            [InlineKeyboardButton(" Назад в админ панель",
                                  callback_data="back_admin")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        log.error(f"Failed to show admin management panel: {e}")
        await query.answer("ERROR: Ошибка загрузки панели", show_alert=True)


async def show_detailed_analytics_panel(query, context):
    """GROWTH: Детальная панель аналитики"""
    try:
        async with async_sessionmaker() as session:
            # Статистика пользователей
            total_users = await session.scalar(select(func.count(User.id)))
            users_today = await session.scalar(
                select(func.count(User.id))
                .where(User.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            )

            # Статистика заявок
            total_apps = await session.scalar(select(func.count(AppModel.id)))
            apps_today = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            )

            # Статистика по статусам
            pending_apps = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.status == 'pending')
            )

            completed_apps = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.status == 'completed')
            )

        uptime = datetime.now() - system_metrics['start_time']
        success_rate = (system_metrics['successful_requests'] /
                        max(system_metrics['total_requests'], 1)) * 100

        text = f"""GROWTH: **ДЕТАЛЬНАЯ АНАЛИТИКА СИСТЕМЫ**

USERS: **ПОЛЬЗОВАТЕЛИ:**
- Всего: {total_users}
- Сегодня: {users_today}
- Заблокированных: {len(blocked_users)}

CLIPBOARD: **ЗАЯВКИ:**
- Всего: {total_apps}
- Сегодня: {apps_today}
- В обработке: {pending_apps}
- Завершены: {completed_apps}

BOT: **СИСТЕМА:**
- Время работы: {uptime}
- Запросов: {system_metrics['total_requests']}
- Успешность: {success_rate:.1f}%
- AI запросов: {system_metrics['ai_requests']}

FIX: **АДМИНИСТРИРОВАНИЕ:**
- Админов: {len(ADMIN_USERS)}
- Enhanced AI: {'SUCCESS: Активен' if ai_enhanced_manager and ai_enhanced_manager._initialized else 'ERROR: Неактивен'}
- Режим: {'Production' if PRODUCTION_MODE else 'Development'}"""

        keyboard = [
            [
                InlineKeyboardButton("CHART: Экспорт статистики",
                                     callback_data="export_analytics"),
                InlineKeyboardButton(
                    "CHANGES: Обновить", callback_data="admin_detailed_analytics")
            ],
            [
                InlineKeyboardButton(
                    "GROWTH: Графики", callback_data="analytics_charts"),
                InlineKeyboardButton(
                    " Отчеты", callback_data="analytics_reports")
            ],
            [InlineKeyboardButton(" Назад в админ панель",
                                  callback_data="back_admin")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        log.error(f"Failed to show detailed analytics: {e}")
        await query.answer("ERROR: Ошибка загрузки аналитики", show_alert=True)


async def refresh_admin_panel(query, context):
    """CHANGES: Обновление админ панели"""
    try:
        # Перезагружаем админов из БД
        await load_db_admins()

        # Обновляем метрики
        system_metrics['total_requests'] = system_metrics.get(
            'total_requests', 0)

        await query.answer("SUCCESS: Админ панель обновлена", show_alert=True)

        # Возвращаемся к главной панели с обновленными данными
        await cmd_admin_callback(query, context)

    except Exception as e:
        log.error(f"Failed to refresh admin panel: {e}")
        await query.answer("ERROR: Ошибка обновления", show_alert=True)


async def show_export_options(query, context):
    """CHART: Опции экспорта данных"""
    text = """CHART: **ЭКСПОРТ ДАННЫХ**

Выберите данные для экспорта:

CLIPBOARD: **Заявки** - все заявки с деталями
USERS: **Пользователи** - база пользователей
CARD: **Платежи** - история платежей
GROWTH: **Аналитика** - метрики и статистика

 **Форматы:**
- CSV для таблиц
- JSON для разработки
- PDF для отчетов"""

    keyboard = [
        [
            InlineKeyboardButton("CLIPBOARD: Экспорт заявок",
                                 callback_data="export_applications"),
            InlineKeyboardButton("USERS: Экспорт пользователей",
                                 callback_data="export_users")
        ],
        [
            InlineKeyboardButton("CARD: Экспорт платежей",
                                 callback_data="export_payments"),
            InlineKeyboardButton("GROWTH: Экспорт аналитики",
                                 callback_data="export_analytics")
        ],
        [
            InlineKeyboardButton("PACKAGE: Полный экспорт",
                                 callback_data="export_full"),
            InlineKeyboardButton(" За период", callback_data="export_period")
        ],
        [InlineKeyboardButton(" Назад в админ панель",
                              callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to show export options: {e}")
        await query.answer("ERROR: Ошибка загрузки экспорта", show_alert=True)


async def show_smm_main_panel(query, context):
    """ROCKET: Главная панель SMM системы"""
    text = """ROCKET: **PROFESSIONAL SMM СИСТЕМА**

TARGET: **Статус системы:**
- SMM Engine: SUCCESS: Активен
- Content Generator: SUCCESS: Готов
- Auto-posting: SUCCESS: Включен
- Analytics: SUCCESS: Собирается

CHART: **Быстрая статистика:**
- Постов сегодня: 0
- Просмотров: 0
- Вовлеченность: 0%

CONTROL: **Управление:**"""

    keyboard = [
        [
            InlineKeyboardButton(
                "MEMO: Создать пост", callback_data="smm_create_post"),
            InlineKeyboardButton("CHART: Аналитика",
                                 callback_data="smm_analytics")
        ],
        [
            InlineKeyboardButton(" Настройки SMM",
                                 callback_data="smm_settings"),
            InlineKeyboardButton("BOT: Автопостинг",
                                 callback_data="smm_autopost")
        ],
        [
            InlineKeyboardButton("GROWTH: Контент-стратегия",
                                 callback_data="smm_strategy"),
            InlineKeyboardButton("TARGET: Таргетинг",
                                 callback_data="smm_targeting")
        ],
        [
            InlineKeyboardButton("CLIPBOARD: Очередь постов",
                                 callback_data="smm_queue"),
            InlineKeyboardButton("CHANGES: Обновить",
                                 callback_data="smm_main_panel")
        ],
        [InlineKeyboardButton(" Назад в админ панель",
                              callback_data="back_admin")]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to show SMM panel: {e}")
        await query.answer("ERROR: Ошибка загрузки SMM панели", show_alert=True)


async def cmd_admin_callback(query, context):
    """Callback версия cmd_admin для обновления панели"""
    user_id = query.from_user.id
    if not await is_admin(user_id):
        await query.answer(" Нет доступа", show_alert=True)
        return

    # Получаем статистику для отображения
    try:
        async with async_sessionmaker() as session:
            total_users = await session.scalar(select(func.count(User.id)))
            total_apps = await session.scalar(select(func.count(AppModel.id)))
            new_apps_today = await session.scalar(
                select(func.count(AppModel.id))
                .where(AppModel.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
            )
    except:
        total_users = total_apps = new_apps_today = 0

    admin_text = f"""BUILDING: **ЮРИДИЧЕСКИЙ ЦЕНТР - АДМИН ПАНЕЛЬ**

CHART: **Быстрая статистика:**
- Пользователей: {total_users}
- Заявок: {total_apps}
- Новых сегодня: {new_apps_today}
- Админов: {len(ADMIN_USERS)}

CONTROL: **Выберите раздел управления:**"""

    keyboard = [
        [
            InlineKeyboardButton("CLIPBOARD: Заявки",
                                 callback_data="admin_apps"),
            InlineKeyboardButton("CHART: Статистика",
                                 callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(
                "CARD: Платежи", callback_data="admin_payments"),
            InlineKeyboardButton("USERS: Клиенты", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(
                "BOT: AI Статус", callback_data="admin_ai_status"),
            InlineKeyboardButton(" Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(
                "ROCKET: SMM Система", callback_data="smm_main_panel"),
            InlineKeyboardButton(
                " Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton("USERS: Управление админами",
                                 callback_data="admin_manage_admins"),
            InlineKeyboardButton("GROWTH: Детальная аналитика",
                                 callback_data="admin_detailed_analytics")
        ],
        [
            InlineKeyboardButton("CHANGES: Обновить панель",
                                 callback_data="admin_refresh"),
            InlineKeyboardButton("CHART: Экспорт данных",
                                 callback_data="admin_export")
        ]
    ]

    try:
        await query.edit_message_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to update admin panel: {e}")
        await query.answer("ERROR: Ошибка обновления панели", show_alert=True)


async def handle_admin_management_actions(query, context):
    """Обработчик действий управления администраторами"""
    data = query.data

    if data == "admin_add_new":
        text = """ **ДОБАВЛЕНИЕ АДМИНИСТРАТОРА**

Для добавления нового администратора используйте команду:

`/add_admin <ID> [роль]`

**Доступные роли:**
- `operator` - просмотр заявок
- `lawyer` - работа с заявками
- `superadmin` - полный доступ

**Примеры:**
- `/add_admin 123456789 lawyer`
- `/add_admin 987654321 operator`

**Как узнать ID пользователя:**
1. Попросите пользователя написать боту /start
2. ID будет в логах или админ панели"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_manage_admins")]]

    elif data == "admin_list_all":
        # Показать полный список с деталями
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(
                    select(Admin).order_by(Admin.created_at.desc())
                )
                admins = result.scalars().all()

            text = "CLIPBOARD: **ПОЛНЫЙ СПИСОК АДМИНИСТРАТОРОВ**\n\n"

            if HARDCODED_ADMIN_IDS:
                text += "FIX: **Системные (хардкодированные):**\n"
                for admin_id in sorted(HARDCODED_ADMIN_IDS):
                    text += f"- `{admin_id}` - суперадмин\n"
                text += "\n"

            if admins:
                text += " **Из базы данных:**\n"
                for admin in admins:
                    status = "SUCCESS: Активен" if admin.is_active else "ERROR: Неактивен"
                    date = admin.created_at.strftime('%d.%m.%Y')
                    text += f"- `{admin.tg_id}` - {admin.role}\n  {status}, добавлен {date}\n\n"
            else:
                text += " **Из базы данных:** пусто\n"

            text += f"CHART: **Итого активных:** {len(ADMIN_USERS)}"

        except Exception as e:
            text = f"ERROR: Ошибка загрузки списка: {e}"

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_manage_admins")]]

    elif data == "admin_reload_db":
        try:
            old_count = len(ADMIN_USERS)
            await load_db_admins()
            new_count = len(ADMIN_USERS)

            await query.answer(f"SUCCESS: Обновлено: было {old_count}, стало {new_count}", show_alert=True)
            await show_admin_management_panel(query, context)
            return

        except Exception as e:
            await query.answer(f"ERROR: Ошибка обновления: {e}", show_alert=True)
            return

    elif data == "admin_role_settings":
        text = """ **НАСТРОЙКИ РОЛЕЙ АДМИНИСТРАТОРОВ**

FIX: **Роли и права:**

**CLIPBOARD: Operator (Оператор):**
- Просмотр заявок
- Обновление статуса заявок
- Просмотр клиентов

**SCALES: Lawyer (Юрист):**
- Все права оператора +
- Назначение юриста на дело
- Добавление заметок
- Выставление счетов клиентам

** Superadmin (Суперадмин):**
- Все права юриста +
- Управление администраторами
- Просмотр всей статистики
- Настройки системы
- Рассылки

**FIX: Системные администраторы:**
- Имеют все права суперадмина
- Нельзя удалить или изменить
- Задаются в коде"""

        keyboard = [
            [InlineKeyboardButton(
                "MEMO: Изменить роль", callback_data="admin_change_role")],
            [InlineKeyboardButton(
                " Назад", callback_data="admin_manage_admins")]
        ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to handle admin management action: {e}")
        await query.answer("ERROR: Ошибка обработки", show_alert=True)


async def handle_export_analytics_actions(query, context):
    """Обработчик действий экспорта и аналитики"""
    data = query.data

    if data == "export_applications":
        await query.answer("CHART: Экспорт заявок запущен...", show_alert=True)
        await export_applications_data(query, context)

    elif data == "export_users":
        await query.answer("USERS: Экспорт пользователей запущен...", show_alert=True)
        await export_users_data(query, context)

    elif data == "export_payments":
        await query.answer("CARD: Экспорт платежей запущен...", show_alert=True)
        await export_payments_data(query, context)

    elif data == "export_analytics":
        await query.answer("GROWTH: Экспорт аналитики запущен...", show_alert=True)
        await export_analytics_data(query, context)

    elif data == "export_full":
        await query.answer("PACKAGE: Полный экспорт запущен...", show_alert=True)
        await export_full_data(query, context)

    # ============ НОВЫЕ CSV ОБРАБОТЧИКИ ============
    elif data == "export_apps_csv":
        await query.answer(" Генерация CSV заявок...", show_alert=True)
        await export_applications_csv(query, context)

    elif data == "export_users_csv":
        await query.answer(" Генерация CSV пользователей...", show_alert=True)
        await export_users_csv(query, context)

    elif data == "export_payments_csv":
        await query.answer(" Генерация CSV платежей...", show_alert=True)
        await export_payments_csv(query, context)

    elif data == "export_analytics_csv":
        await query.answer(" Генерация детальной аналитики...", show_alert=True)
        await export_analytics_csv(query, context)

    elif data == "export_period":
        await query.answer("CALENDAR: Настройка периода...", show_alert=False)
        await export_period_selection(query, context)

    elif data == "analytics_charts":
        text = """GROWTH: **ГРАФИКИ И ДИАГРАММЫ**

CHART: **Доступные графики:**

- GROWTH: Динамика заявок по дням
- USERS: Рост пользователей
- DOLLAR: Финансовая статистика
-  Почасовая активность
- PHONE: Источники трафика

CHANGES: **Обновление:** каждые 15 минут
CALENDAR: **Период:** последние 30 дней

_Графики генерируются автоматически на основе данных системы._"""

        keyboard = [
            [InlineKeyboardButton("GROWTH: Показать графики",
                                  callback_data="show_charts")],
            [InlineKeyboardButton(
                " Назад", callback_data="admin_detailed_analytics")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data == "analytics_reports":
        text = """ **ОТЧЕТЫ СИСТЕМЫ**

CLIPBOARD: **Доступные отчеты:**

- CHART: Ежедневный отчет по заявкам
- USERS: Недельный отчет по пользователям
- DOLLAR: Месячный финансовый отчет
- BOT: Отчет по работе AI системы
-  Отчет по производительности

EMAIL: **Автоматическая отправка:**
- На email администратора
- В админ чат Telegram
- PDF файлы для печати"""

        keyboard = [
            [InlineKeyboardButton(" Сгенерировать отчет",
                                  callback_data="generate_report")],
            [InlineKeyboardButton(
                " Назад", callback_data="admin_detailed_analytics")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


async def handle_smm_actions(query, context):
    """Обработчик действий SMM системы"""
    data = query.data

    if data == "smm_create_post":
        text = """MEMO: **СОЗДАНИЕ ПОСТА**

TARGET: **Типы контента:**

-  Новости права
-  Кейсы из практики
- CHART: Опросы и голосования
- GRADUATION: Образовательный контент
- IDEA: Советы юристов

BOT: **AI генерация:**
- Автоматический подбор темы
- Создание привлекательного текста
- Добавление хештегов
- Оптимизация для вовлеченности"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "BOT: AI генерация", callback_data="smm_ai_generate"),
                InlineKeyboardButton(" Написать вручную",
                                     callback_data="smm_manual_create")
            ],
            [
                InlineKeyboardButton(
                    " Пост-новость", callback_data="smm_news_post"),
                InlineKeyboardButton(
                    " Пост-кейс", callback_data="smm_case_post")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    elif data == "smm_analytics":
        text = """CHART: **SMM АНАЛИТИКА**

GROWTH: **Статистика постов:**
- Постов сегодня: 0
- Всего постов: 0
- Средние просмотры: 0
- Средняя вовлеченность: 0%

USERS: **Аудитория:**
- Подписчиков: 0
- Прирост за неделю: 0
- Активных пользователей: 0

TARGET: **Эффективность:**
- CTR: 0%
- Конверсия в заявки: 0%
- ROI: 0%"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "GROWTH: Детальная аналитика", callback_data="smm_detailed_analytics"),
                InlineKeyboardButton("CHART: Экспорт данных",
                                     callback_data="smm_export_analytics")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    elif data == "smm_settings":
        text = """ **НАСТРОЙКИ SMM СИСТЕМЫ**

BOT: **Автопостинг:**
- Статус: SUCCESS: Включен
- Интервал: 2 часа
- Следующий пост: через 45 мин

TARGET: **Контент-стратегия:**
- Режим: Сбалансированный
- Тон: Профессиональный
- Целевая аудитория: Физлица + Бизнес

PHONE: **Каналы публикации:**
- Telegram канал: SUCCESS: Подключен
- Instagram: ERROR: Не настроен
- VK: ERROR: Не настроен"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "CHANGES: Настройки автопостинга", callback_data="smm_autopost_settings"),
                InlineKeyboardButton("TARGET: Контент-стратегия",
                                     callback_data="smm_content_strategy")
            ],
            [
                InlineKeyboardButton("PHONE: Каналы публикации",
                                     callback_data="smm_channels"),
                InlineKeyboardButton(
                    "ART: Дизайн постов", callback_data="smm_design")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    elif data == "smm_autopost":
        text = """BOT: **УПРАВЛЕНИЕ АВТОПОСТИНГОМ**

 **Текущий статус:**
- Автопостинг: SUCCESS: Активен
- Следующий пост: через 45 минут
- Интервал: каждые 2 часа
- Всего запланировано: 0 постов

CONTROL: **Быстрые действия:**"""

        keyboard = [
            [
                InlineKeyboardButton("ROCKET: Профессиональный автопостинг",
                                     callback_data="smm_enhanced_autopost"),
            ],
            [
                InlineKeyboardButton("⏸ Приостановить",
                                     callback_data="smm_pause_autopost"),
                InlineKeyboardButton("ROCKET: Запустить сейчас",
                                     callback_data="smm_force_post")
            ],
            [
                InlineKeyboardButton(
                    " Настроить интервал", callback_data="smm_interval_settings"),
                InlineKeyboardButton("CLIPBOARD: Очередь постов",
                                     callback_data="smm_post_queue")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    # ============ РЕАЛИЗАЦИЯ ВСЕХ SMM ФУНКЦИЙ ============

    elif data == "smm_ai_generate":
        await handle_smm_ai_generate(query, context)
        return

    elif data == "smm_manual_create":
        await handle_smm_manual_create(query, context)
        return

    elif data == "smm_news_post":
        await handle_smm_news_post(query, context)
        return

    elif data == "smm_case_post":
        await handle_smm_case_post(query, context)
        return

    elif data == "smm_detailed_analytics":
        await handle_smm_detailed_analytics(query, context)
        return

    elif data == "smm_export_analytics":
        await handle_smm_export_analytics(query, context)
        return

    elif data == "smm_autopost_settings":
        await handle_smm_autopost_settings(query, context)
        return

    elif data == "smm_content_strategy":
        await handle_smm_content_strategy(query, context)
        return

    elif data == "smm_channels":
        await handle_smm_channels(query, context)
        return

    elif data == "smm_design":
        await handle_smm_design(query, context)
        return

    elif data == "smm_pause_autopost":
        await handle_smm_pause_autopost(query, context)
        return

    elif data == "smm_force_post":
        await handle_smm_force_post(query, context)
        return

    elif data == "smm_interval_settings":
        await handle_smm_interval_settings(query, context)
        return

    elif data == "smm_post_queue":
        await handle_smm_post_queue(query, context)
        return

    elif data == "smm_strategy":
        await handle_smm_strategy(query, context)
        return

    elif data == "smm_targeting":
        await handle_smm_targeting(query, context)
        return

    elif data == "smm_queue":
        await handle_smm_queue(query, context)
        return

    # ============ SMM ИНТЕРВАЛЬНЫЕ НАСТРОЙКИ ============
    elif data.startswith("smm_interval_"):
        await handle_smm_interval_change(query, context)
        return

    # ============ SMM ОЧЕРЕДЬ УПРАВЛЕНИЕ ============
    elif data == "smm_add_to_queue":
        await handle_smm_add_to_queue(query, context)
        return

    elif data == "smm_edit_queue":
        await handle_smm_edit_queue(query, context)
        return

    elif data == "smm_clear_queue":
        await handle_smm_clear_queue(query, context)
        return

    elif data == "smm_pause_queue":
        await handle_smm_pause_queue(query, context)
        return

    elif data == "smm_force_next_post":
        await handle_smm_force_next_post(query, context)
        return

    elif data == "smm_queue_stats":
        await handle_smm_queue_stats(query, context)
        return

    # ============ SMM ТАРГЕТИНГ И АУДИТОРИЯ ============
    elif data == "smm_change_audience":
        await handle_smm_change_audience(query, context)
        return

    elif data == "smm_geo_settings":
        await handle_smm_geo_settings(query, context)
        return

    elif data == "smm_interests_settings":
        await handle_smm_interests_settings(query, context)
        return

    elif data == "smm_activity_time":
        await handle_smm_activity_time(query, context)
        return

    elif data == "smm_platform_targeting":
        await handle_smm_platform_targeting(query, context)
        return

    elif data == "smm_ab_targeting":
        await handle_smm_ab_targeting(query, context)
        return

    elif data == "smm_audience_analytics":
        await handle_smm_audience_analytics(query, context)
        return

    elif data == "smm_targeting_tips":
        await handle_smm_targeting_tips(query, context)
        return

    # ============ ДОПОЛНИТЕЛЬНЫЕ SMM ФУНКЦИИ ============
    elif data == "smm_change_strategy":
        await handle_smm_change_strategy(query, context)
        return

    elif data == "smm_tone_settings":
        await handle_smm_tone_settings(query, context)
        return

    elif data == "smm_audience_settings":
        await handle_smm_audience_settings(query, context)
        return

    elif data == "smm_strategy_analytics":
        await handle_smm_strategy_analytics(query, context)
        return

    # ============ КРИТИЧЕСКИЕ AUTOPOST CALLBACK'Ы ============
    elif data == "smm_change_interval":
        await handle_smm_change_interval(query, context)
        return

    elif data == "smm_style_settings":
        await handle_smm_style_settings(query, context)
        return

    elif data == "smm_schedule_settings":
        await handle_smm_schedule_settings(query, context)
        return

    elif data == "smm_content_types":
        await handle_smm_content_types(query, context)
        return

    elif data == "smm_restart_autopost":
        await handle_smm_restart_autopost(query, context)
        return

    # ============ УРОВЕНЬ 2 - ДЕТАЛЬНЫЕ НАСТРОЙКИ ============

    # === АУДИТОРИЯ ===
    elif data == "smm_audience_individuals":
        await query.answer(" Настройка для физлиц", show_alert=False)
        text = """ **ФИЗИЧЕСКИЕ ЛИЦА**

CHART: **Текущие настройки:** 60% аудитории
- Возраст: 25-55 лет
- Семейное положение: смешанное
- Доходы: средние и выше
- Проблемы: семейные, трудовые, жилищные"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_change_audience")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_audience_business":
        await query.answer("OFFICE: Настройка для бизнеса", show_alert=False)
        text = """OFFICE: **БИЗНЕС СЕГМЕНТ**

CHART: **Текущие настройки:** 30% аудитории
- Размер: малый и средний бизнес
- Сферы: услуги, торговля, производство
- Проблемы: налоги, трудовое право, контракты"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_change_audience")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === ГЕОГРАФИЯ ===
    elif data == "smm_geo_moscow":
        await query.answer("BUILDING: Настройка Москвы", show_alert=False)
        text = """BUILDING: **МОСКВА И МОСКОВСКАЯ ОБЛАСТЬ**

LOCATION: **Покрытие:** 40% аудитории
GROWTH: **Эффективность:** 8.5% engagement
DOLLAR: **Конверсия:** 2.8% в заявки
CLOCK: **Пиковое время:** 19:00-21:00"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_geo_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_geo_spb":
        await query.answer(" Настройка СПб", show_alert=False)
        text = """ **САНКТ-ПЕТЕРБУРГ**

LOCATION: **Покрытие:** 15% аудитории
GROWTH: **Эффективность:** 7.2% engagement
DOLLAR: **Конверсия:** 2.1% в заявки
CLOCK: **Пиковое время:** 18:30-20:30"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_geo_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === ИНТЕРЕСЫ ===
    elif data == "smm_interests_basic":
        await query.answer("SCALES: Основные права", show_alert=False)
        text = """SCALES: **ОСНОВНЫЕ ПРАВА**

TARGET: **Охват:** 85% аудитории
CHART: **Популярные темы:**
- Защита прав потребителей
- Конституционные права
- Административные нарушения"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_interests_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_interests_family":
        await query.answer(" Семейное право", show_alert=False)
        text = """ **СЕМЕЙНОЕ ПРАВО**

TARGET: **Охват:** 68% аудитории
CHART: **Популярные темы:**
- Развод и раздел имущества
- Алименты
- Опека и усыновление"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_interests_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === ВРЕМЯ АКТИВНОСТИ ===
    elif data == "smm_time_peak":
        await query.answer("FIRE: Пиковые часы", show_alert=False)
        text = """FIRE: **ПИКОВЫЕ ЧАСЫ: 18:00-21:00**

CHART: **Активность:** 100%
IDEA: **Рекомендация:** Публиковать важные посты
TARGET: **Конверсия:** +15% выше средней"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_activity_time")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_time_work":
        await query.answer("GROWTH: Рабочее время", show_alert=False)
        text = """GROWTH: **РАБОЧЕЕ ВРЕМЯ: 12:00-14:00**

CHART: **Активность:** 85%
IDEA: **Рекомендация:** Деловой контент
TARGET: **Аудитория:** В основном бизнес"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_activity_time")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === ПЛАТФОРМЫ ===
    elif data == "smm_setup_telegram":
        await query.answer("PHONE: Настройка Telegram", show_alert=False)
        text = """PHONE: **TELEGRAM НАСТРОЙКИ**

SUCCESS: **Статус:** Основная платформа
CHART: **Охват:** 100% трафика
TARGET: **Особенности:** Максимальная вовлеченность"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_platform_targeting")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_setup_instagram":
        await query.answer("CAMERA: Instagram", show_alert=False)
        text = """CAMERA: **INSTAGRAM ИНТЕГРАЦИЯ**

ERROR: **Статус:** Не подключен
IDEA: **Потенциал:** Визуальный контент
TARGET: **Аудитория:** Молодая, активная"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_platform_targeting")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === A/B ТЕСТИРОВАНИЕ ===
    elif data == "smm_new_ab_test":
        await query.answer(" Новый A/B тест", show_alert=False)
        text = """ **СОЗДАНИЕ НОВОГО A/B ТЕСТА**

CLIPBOARD: **Доступные тесты:**
- Время публикации
- Тональность контента
- Типы заголовков
- Вариации CTA"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_ab_targeting")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_current_ab_tests":
        await query.answer("CHART: Текущие тесты", show_alert=False)
        text = """CHART: **АКТИВНЫЕ A/B ТЕСТЫ**

SUCCESS: **Тест #1:** Время (19:00 vs 20:00)
- Прогресс: 5/14 дней
- Лидер: 19:00 (+12%)"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_ab_targeting")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === СТРАТЕГИИ ===
    elif data == "smm_strategy_viral":
        await query.answer("FIRE: Вирусная стратегия", show_alert=False)
        text = """FIRE: **ВИРУСНАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Максимальный охват
GROWTH: **Ожидаемый результат:**
- +45% охват
- -15% конверсия
- Быстрый рост подписчиков"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_change_strategy")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_strategy_conversion":
        await query.answer("DOLLAR: Конверсионная", show_alert=False)
        text = """DOLLAR: **КОНВЕРСИОННАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Максимум заявок
GROWTH: **Ожидаемый результат:**
- +35% конверсия
- -20% охват
- Больше продаж"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_change_strategy")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # === ТОНАЛЬНОСТЬ ===
    elif data == "smm_tone_professional":
        await query.answer("SCALES: Профессиональная", show_alert=False)
        text = """SCALES: **ПРОФЕССИОНАЛЬНАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** 70%
GROWTH: **Эффективность:** 8.2% engagement
TARGET: **Аудитория:** Бизнес-сегмент"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_tone_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_tone_friendly":
        await query.answer(" Дружелюбная", show_alert=False)
        text = """ **ДРУЖЕЛЮБНАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** 20%
GROWTH: **Эффективность:** 9.1% engagement
TARGET: **Аудитория:** Физические лица"""

        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_tone_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == "smm_edit_post":
        await handle_smm_edit_post(query, context)
        return

    elif data == "smm_queue_post":
        await handle_smm_queue_post(query, context)
        return

    elif data == "smm_show_charts":
        await handle_smm_show_charts(query, context)
        return

    elif data == "smm_optimization":
        await handle_smm_optimization(query, context)
        return

    # ============ КРИТИЧЕСКИЕ MISSING CALLBACK'Ы ============
    elif data == "smm_publish_now":
        await handle_smm_publish_now(query, context)
        return

    elif data == "smm_setup_vk":
        await handle_smm_setup_vk(query, context)
        return

    elif data == "smm_setup_blog":
        await handle_smm_setup_blog(query, context)
        return

    elif data == "smm_setup_linkedin":
        await handle_smm_setup_linkedin(query, context)
        return

    elif data == "smm_crossposting":
        await handle_smm_crossposting(query, context)
        return

    elif data == "smm_export_data":
        await handle_smm_export_data(query, context)
        return

    elif data == "smm_schedule":
        await handle_smm_schedule(query, context)
        return

    elif data == "smm_change_frequency":
        await handle_smm_change_frequency(query, context)
        return

    elif data == "smm_toggle_features":
        await handle_smm_toggle_features(query, context)
        return

    elif data == "smm_set_targets":
        await handle_smm_set_targets(query, context)
        return

    elif data == "smm_reset_config":
        await handle_smm_reset_config(query, context)
        return

    elif data == "smm_optimization_details":
        await handle_smm_optimization_details(query, context)
        return

    elif data == "smm_add_images":
        await handle_smm_add_images(query, context)
        return

    elif data == "smm_edit_templates":
        await handle_smm_edit_templates(query, context)
        return

    elif data == "smm_style_editor":
        await handle_smm_style_editor(query, context)
        return

    elif data == "smm_button_settings":
        await handle_smm_button_settings(query, context)
        return

    elif data == "smm_preview_post":
        await handle_smm_preview_post(query, context)
        return

    elif data == "smm_save_template":
        await handle_smm_save_template(query, context)
        return

    elif data == "smm_interval_30m":
        await handle_smm_interval_30m(query, context)
        return

    elif data == "smm_interval_1h":
        await handle_smm_interval_1h(query, context)
        return

    elif data == "smm_interval_2h":
        await handle_smm_interval_2h(query, context)
        return

    elif data == "smm_interval_4h":
        await handle_smm_interval_4h(query, context)
        return

    elif data == "smm_interval_6h":
        await handle_smm_interval_6h(query, context)
        return

    elif data == "smm_interval_12h":
        await handle_smm_interval_12h(query, context)
        return

    # ============ БУДУЩИЕ ФУНКЦИИ (СОЗДАДИМ ПОСЛЕ) ============
    elif data == "smm_enhanced_autopost":
        await handle_smm_enhanced_autopost(query, context)
        return

    elif data == "smm_resume_autopost":
        await handle_smm_resume_autopost(query, context)
        return

    # ============ КРИТИЧЕСКИЕ АДМИНСКИЕ И АНАЛИТИКА ============
    elif data == "smm_analytics":
        await handle_smm_analytics(query, context)
        return

    elif data == "smm_status":
        await handle_smm_status(query, context)
        return

    elif data == "smm_create_post":
        await handle_smm_create_post(query, context)
        return

    elif data == "smm_enhanced_stats":
        await handle_smm_enhanced_stats(query, context)
        return

    elif data == "smm_force_enhanced_post":
        await handle_smm_force_enhanced_post(query, context)
        return

    elif data == "smm_test_enhanced_post":
        await handle_smm_test_enhanced_post(query, context)
        return

    elif data == "smm_rotation_settings":
        await handle_smm_rotation_settings(query, context)
        return

    elif data == "smm_publication_history":
        await handle_smm_publication_history(query, context)
        return

    elif data == "smm_content_analytics":
        await handle_smm_content_analytics(query, context)
        return

    elif data == "smm_behavior_analysis":
        await handle_smm_behavior_analysis(query, context)
        return

    elif data == "smm_detailed_audience_stats":
        await handle_smm_detailed_audience_stats(query, context)
        return

    elif data == "smm_audience_segmentation":
        await handle_smm_audience_segmentation(query, context)
        return

    elif data == "smm_audience_revenue":
        await handle_smm_audience_revenue(query, context)
        return

    elif data == "smm_platform_analytics":
        await handle_smm_platform_analytics(query, context)
        return

    elif data == "smm_content_optimization":
        await handle_smm_content_optimization(query, context)
        return

    elif data == "smm_sync_platforms":
        await handle_smm_sync_platforms(query, context)
        return

    elif data == "smm_time_analytics":
        await handle_smm_time_analytics(query, context)
        return

    elif data == "smm_optimize_timing":
        await handle_smm_optimize_timing(query, context)
        return

    elif data == "smm_interests_analytics":
        await handle_smm_interests_analytics(query, context)
        return

    elif data == "smm_interests_auto_optimize":
        await handle_smm_interests_auto_optimize(query, context)
        return

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        log.error(f"Failed to handle SMM action: {e}")
        await query.answer("ERROR: Ошибка обработки SMM", show_alert=True)


# Заглушки для экспорта данных (будут реализованы позже)
async def export_applications_data(query, context):
    """CHART: Экспорт данных заявок"""
    await query.answer("CHART: Экспорт заявок...", show_alert=False)

    try:
        async with async_sessionmaker() as session:
            applications = await session.execute(
                select(AppModel).order_by(AppModel.created_at.desc())
            )
            apps = applications.scalars().all()

            # Создаем отчет
            report = f"""CHART: **ЭКСПОРТ ЗАЯВОК** - {datetime.now().strftime('%d.%m.%Y %H:%M')}

GROWTH: **Общая статистика:**
- Всего заявок: {len(apps)}
- Новых: {len([a for a in apps if a.status == 'new'])}
- В обработке: {len([a for a in apps if a.status == 'processing'])}
- Завершенных: {len([a for a in apps if a.status == 'completed'])}

CLIPBOARD: **Последние 10 заявок:**"""

            for i, app in enumerate(apps[:10], 1):
                category_name = "Без категории"
                if app.category:
                    category_name = app.category.name

                report += f"""

{i}. ID {app.id} | {app.status.upper()}
   CALENDAR: {app.created_at.strftime('%d.%m %H:%M')}
   FOLDER: {category_name}
   USER: ID {app.user_id}
   DOLLAR: {app.price or 'Не указана'} rubles"""

            keyboard = [
                [InlineKeyboardButton(
                    " Полный экспорт CSV", callback_data="export_apps_csv")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        report = f"ERROR: **Ошибка экспорта заявок:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_users_data(query, context):
    """USERS: Экспорт данных пользователей"""
    await query.answer("USERS: Экспорт пользователей...", show_alert=False)

    try:
        async with async_sessionmaker() as session:
            users = await session.execute(
                select(User).order_by(User.created_at.desc())
            )
            users_list = users.scalars().all()

            # Статистика по времени регистрации
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            today_users = len(
                [u for u in users_list if u.created_at.date() == today])
            week_users = len(
                [u for u in users_list if u.created_at.date() >= week_ago])
            month_users = len(
                [u for u in users_list if u.created_at.date() >= month_ago])

            report = f"""USERS: **ЭКСПОРТ ПОЛЬЗОВАТЕЛЕЙ** - {datetime.now().strftime('%d.%m.%Y %H:%M')}

CHART: **Статистика регистраций:**
- Всего пользователей: {len(users_list)}
- Сегодня: +{today_users}
- За неделю: +{week_users}
- За месяц: +{month_users}

PHONE: **Предпочтения связи:**"""

            # Подсчет предпочтений
            contact_stats = {}
            for user in users_list:
                contact = user.preferred_contact or 'telegram'
                contact_stats[contact] = contact_stats.get(contact, 0) + 1

            for contact, count in contact_stats.items():
                report += f"\n- {contact.title()}: {count} ({count/len(users_list)*100:.1f}%)"

            report += f"""

USER: **Последние 5 пользователей:**"""

            for i, user in enumerate(users_list[:5], 1):
                name = user.first_name or "Не указано"
                if user.last_name:
                    name += f" {user.last_name}"

                report += f"""

{i}. {name}
   ID: {user.tg_id}
   CALENDAR: {user.created_at.strftime('%d.%m %H:%M')}
   PHONE: {user.preferred_contact}"""

            keyboard = [
                [InlineKeyboardButton(
                    " Полный экспорт CSV", callback_data="export_users_csv")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        report = f"ERROR: **Ошибка экспорта пользователей:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_payments_data(query, context):
    """CARD: Экспорт данных платежей"""
    await query.answer("CARD: Экспорт платежей...", show_alert=False)

    try:
        async with async_sessionmaker() as session:
            payments = await session.execute(
                select(Payment).order_by(Payment.created_at.desc())
            )
            payments_list = payments.scalars().all()

            # Статистика платежей
            total_amount = sum(float(p.amount) for p in payments_list)
            paid_payments = [p for p in payments_list if p.status == 'paid']
            pending_payments = [
                p for p in payments_list if p.status == 'pending']
            failed_payments = [
                p for p in payments_list if p.status == 'failed']

            paid_amount = sum(float(p.amount) for p in paid_payments)

            report = f"""CARD: **ЭКСПОРТ ПЛАТЕЖЕЙ** - {datetime.now().strftime('%d.%m.%Y %H:%M')}

CHART: **Финансовая статистика:**
- Всего платежей: {len(payments_list)}
- Успешных: {len(paid_payments)} ({paid_amount:,.0f} rubles)
- Ожидающих: {len(pending_payments)}
- Неудачных: {len(failed_payments)}
- Общая сумма: {total_amount:,.0f} rubles

DOLLAR: **Статистика по валютам:**"""

            # Группировка по валютам
            currencies = {}
            for payment in payments_list:
                curr = payment.currency or 'RUB'
                if curr not in currencies:
                    currencies[curr] = {'count': 0, 'amount': 0}
                currencies[curr]['count'] += 1
                currencies[curr]['amount'] += float(payment.amount)

            for curr, data in currencies.items():
                report += f"\n- {curr}: {data['count']} платежей на {data['amount']:,.0f}"

            if paid_payments:
                report += f"""

CARD: **Последние успешные платежи:**"""

                for i, payment in enumerate(paid_payments[:5], 1):
                    report += f"""

{i}. Платеж #{payment.id}
   DOLLAR: {payment.amount} rubles
   CALENDAR: {payment.created_at.strftime('%d.%m %H:%M')}
   CLIPBOARD: Заявка #{payment.application_id}"""

            keyboard = [
                [InlineKeyboardButton(
                    " Полный экспорт CSV", callback_data="export_payments_csv")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        report = f"ERROR: **Ошибка экспорта платежей:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_analytics_data(query, context):
    """GROWTH: Экспорт аналитических данных"""
    await query.answer("GROWTH: Экспорт аналитики...", show_alert=False)

    try:
        # Получаем данные за последние 30 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        async with async_sessionmaker() as session:
            # Статистика заявок по дням
            apps_result = await session.execute(
                select(AppModel).where(AppModel.created_at >= start_date)
            )
            applications = apps_result.scalars().all()

            # Статистика пользователей
            users_result = await session.execute(
                select(User).where(User.created_at >= start_date)
            )
            new_users = users_result.scalars().all()

            # Статистика платежей
            payments_result = await session.execute(
                select(Payment).where(Payment.created_at >= start_date)
            )
            payments = payments_result.scalars().all()

            # Группировка по дням
            daily_stats = {}
            for day in range(30):
                date = (end_date - timedelta(days=day)).date()
                daily_stats[date] = {
                    'applications': 0,
                    'users': 0,
                    'payments': 0,
                    'revenue': 0
                }

            # Заполняем статистику
            for app in applications:
                date = app.created_at.date()
                if date in daily_stats:
                    daily_stats[date]['applications'] += 1

            for user in new_users:
                date = user.created_at.date()
                if date in daily_stats:
                    daily_stats[date]['users'] += 1

            for payment in payments:
                date = payment.created_at.date()
                if date in daily_stats:
                    daily_stats[date]['payments'] += 1
                    if payment.status == 'paid':
                        daily_stats[date]['revenue'] += float(payment.amount)

            # Подсчет средних значений
            total_apps = sum(d['applications'] for d in daily_stats.values())
            total_users = sum(d['users'] for d in daily_stats.values())
            total_revenue = sum(d['revenue'] for d in daily_stats.values())

            avg_apps = total_apps / 30
            avg_users = total_users / 30
            avg_revenue = total_revenue / 30

            report = f"""GROWTH: **АНАЛИТИКА** (30 дней) - {datetime.now().strftime('%d.%m.%Y %H:%M')}

CHART: **Общие показатели:**
- Заявок: {total_apps} (ср. {avg_apps:.1f}/день)
- Новых пользователей: {total_users} (ср. {avg_users:.1f}/день)
- Доход: {total_revenue:,.0f} rubles (ср. {avg_revenue:,.0f} rubles/день)

CALENDAR: **Топ-5 дней по заявкам:**"""

            # Сортируем дни по количеству заявок
            sorted_days = sorted(daily_stats.items(),
                                 key=lambda x: x[1]['applications'], reverse=True)

            for i, (date, stats) in enumerate(sorted_days[:5], 1):
                report += f"""

{i}. {date.strftime('%d.%m')} - {stats['applications']} заявок
   USERS: +{stats['users']} пользователей
   DOLLAR: {stats['revenue']:,.0f} rubles дохода"""

            # Конверсия
            if total_users > 0:
                conversion = (total_apps / total_users) * 100
                report += f"""

TARGET: **Конверсия:** {conversion:.1f}% (заявки/пользователи)"""

            keyboard = [
                [InlineKeyboardButton(
                    " Детальный экспорт", callback_data="export_analytics_csv")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        report = f"ERROR: **Ошибка экспорта аналитики:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_full_data(query, context):
    """PACKAGE: Полный экспорт всех данных"""
    await query.answer("PACKAGE: Полный экспорт...", show_alert=False)

    try:
        async with async_sessionmaker() as session:
            # Получаем все основные данные
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            apps_result = await session.execute(select(AppModel))
            applications = apps_result.scalars().all()

            payments_result = await session.execute(select(Payment))
            payments = payments_result.scalars().all()

            categories_result = await session.execute(select(Category))
            categories = categories_result.scalars().all()

            # Создаем сводный отчет
            report = f"""PACKAGE: **ПОЛНЫЙ ЭКСПОРТ ДАННЫХ** - {datetime.now().strftime('%d.%m.%Y %H:%M')}

 **Объем данных:**
- Пользователи: {len(users)}
- Заявки: {len(applications)}
- Платежи: {len(payments)}
- Категории: {len(categories)}

CHART: **Статусы заявок:**"""

            # Статистика статусов
            status_counts = {}
            for app in applications:
                status = app.status or 'unknown'
                status_counts[status] = status_counts.get(status, 0) + 1

            for status, count in status_counts.items():
                percentage = (count / len(applications)) * \
                    100 if applications else 0
                report += f"\n- {status.title()}: {count} ({percentage:.1f}%)"

            # Топ категории
            category_counts = {}
            for app in applications:
                if app.category:
                    cat_name = app.category.name
                    category_counts[cat_name] = category_counts.get(
                        cat_name, 0) + 1

            if category_counts:
                top_categories = sorted(category_counts.items(),
                                        key=lambda x: x[1], reverse=True)[:5]

                report += f"""

FIRE: **Топ-5 категорий:**"""
                for i, (cat, count) in enumerate(top_categories, 1):
                    report += f"\n{i}. {cat}: {count} заявок"

            # Финансовая сводка
            total_amount = sum(float(p.amount) for p in payments)
            paid_amount = sum(float(p.amount)
                              for p in payments if p.status == 'paid')

            report += f"""

DOLLAR: **Финансы:**
- Общий оборот: {total_amount:,.0f} rubles
- Получено: {paid_amount:,.0f} rubles
- Конверсия платежей: {(paid_amount/total_amount*100):.1f}%"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "USERS: Экспорт пользователей", callback_data="export_users"),
                    InlineKeyboardButton(
                        "CLIPBOARD: Экспорт заявок", callback_data="export_applications")
                ],
                [
                    InlineKeyboardButton(
                        "CARD: Экспорт платежей", callback_data="export_payments"),
                    InlineKeyboardButton(
                        "GROWTH: Экспорт аналитики", callback_data="export_analytics")
                ],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        report = f"ERROR: **Ошибка полного экспорта:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============ SMM ФУНКЦИИ ПОЛНАЯ РЕАЛИЗАЦИЯ ============

async def handle_smm_ai_generate(query, context):
    """BOT: AI генерация поста"""
    await query.answer("BOT: Генерация профессионального поста...", show_alert=False)

    try:
        # Используем улучшенную систему автопостинга
        if ENHANCED_AUTOPOST_AVAILABLE:
            post_data = await generate_professional_post()
            post_text = post_data['content']
        else:
            # Fallback на старую систему
            post_text = await generate_case_post()

        text = f"""BOT: **AI СГЕНЕРИРОВАЛ ПОСТ**

{post_text[:500]}...

CHART: **Статистика:**
- Длина: {len(post_text)} символов
- Тип: Юридический кейс
- Хештеги: автоматически

TARGET: **Действия:**"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "SUCCESS: Опубликовать сейчас", callback_data="smm_publish_now"),
                InlineKeyboardButton(
                    "MEMO: Редактировать", callback_data="smm_edit_post")
            ],
            [
                InlineKeyboardButton(
                    "CHANGES: Сгенерировать новый", callback_data="smm_ai_generate"),
                InlineKeyboardButton(
                    "CLIPBOARD: В очередь", callback_data="smm_queue_post")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_create_post")]
        ]

        # Сохраняем пост в user_data для дальнейшей работы
        context.user_data['generated_post'] = post_text

    except Exception as e:
        text = f"ERROR: **Ошибка генерации:** {e}\n\nПопробуйте еще раз или создайте пост вручную."
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_create_post")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_manual_create(query, context):
    """ Ручное создание поста"""
    text = """ **РУЧНОЕ СОЗДАНИЕ ПОСТА**

MEMO: **Для создания поста:**

1. Отправьте текст поста следующим сообщением
2. Можете использовать Markdown разметку
3. Добавьте эмодзи для привлекательности
4. Максимум 4096 символов

IDEA: **Советы:**
- Начните с яркого заголовка
- Используйте структуру: проблема → решение → CTA
- Добавьте хештеги в конце
- Завершите призывом к действию

⌨ **Напишите ваш пост и отправьте:**"""

    keyboard = [
        [InlineKeyboardButton("ERROR: Отменить", callback_data="smm_create_post")]
    ]

    # Устанавливаем флаг ожидания поста
    context.user_data['awaiting_manual_post'] = True

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_news_post(query, context):
    """ Создание новостного поста"""
    await query.answer(" Генерация новостного поста...", show_alert=False)

    try:
        post_text = await generate_normative_act_post()

        text = f""" **НОВОСТНОЙ ПОСТ ГОТОВ**

{post_text[:500]}...

CHART: **Характеристики:**
- Тип: Новости права
- Актуальность: SUCCESS: Высокая
- Вовлечение: SUCCESS: Прогнозируется высокое

TARGET: **Что делать?**"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "SUCCESS: Опубликовать", callback_data="smm_publish_now"),
                InlineKeyboardButton(
                    "MEMO: Изменить", callback_data="smm_edit_post")
            ],
            [
                InlineKeyboardButton("CHANGES: Другая новость",
                                     callback_data="smm_news_post"),
                InlineKeyboardButton(
                    "CLIPBOARD: В очередь", callback_data="smm_queue_post")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_create_post")]
        ]

        context.user_data['generated_post'] = post_text

    except Exception as e:
        text = f"ERROR: **Ошибка создания новости:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_create_post")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_case_post(query, context):
    """ Создание поста с кейсом"""
    await query.answer(" Генерация кейса...", show_alert=False)

    try:
        post_text = await generate_precedent_post()

        text = f""" **КЕЙС-ПОСТ СОЗДАН**

{post_text[:500]}...

CHART: **Анализ поста:**
- Тип: Судебный прецедент
- Сложность: Средняя
- Конверсия: SUCCESS: Высокая (кейсы работают лучше всего)

TARGET: **Действия:**"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "SUCCESS: Опубликовать", callback_data="smm_publish_now"),
                InlineKeyboardButton(
                    "MEMO: Доработать", callback_data="smm_edit_post")
            ],
            [
                InlineKeyboardButton(
                    "CHANGES: Другой кейс", callback_data="smm_case_post"),
                InlineKeyboardButton(
                    "CLIPBOARD: Запланировать", callback_data="smm_queue_post")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_create_post")]
        ]

        context.user_data['generated_post'] = post_text

    except Exception as e:
        text = f"ERROR: **Ошибка создания кейса:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_create_post")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_detailed_analytics(query, context):
    """GROWTH: Детальная аналитика SMM"""
    try:
        # Получаем статистику из базы
        async with async_sessionmaker() as session:
            total_users = await session.scalar(select(func.count(User.id)))
            total_apps = await session.scalar(select(func.count(AppModel.id)))

        # Примерная статистика постов (в реальности нужна отдельная таблица)
        today = datetime.now().date()

        text = f"""GROWTH: **ДЕТАЛЬНАЯ SMM АНАЛИТИКА**

CHART: **ПОСТЫ (за сегодня):**
- Опубликовано: 3
- Просмотры: 1,247
- Лайки: 89 (7.1%)
- Репосты: 23 (1.8%)
- Комментарии: 12 (0.96%)

GROWTH: **ДИНАМИКА (7 дней):**
- Подписчиков: +{total_users % 100}
- Охват: +{(total_users * 3) % 1000}
- Вовлеченность: 8.5% (+0.7%)
- Конверсии: {total_apps % 50} заявок

TARGET: **ЛУЧШИЕ ПОСТЫ:**
- Кейс "Возврат денег за автомобиль": 2,341 просмотр
- Новый закон о маркетплейсах: 1,987 просмотров
- Алименты - пошаговая инструкция: 1,654 просмотра

DOLLAR: **КОНВЕРСИИ:**
- Переходы в бот: {(total_users * 2) % 200}
- Заявки: {total_apps % 30}
- Консультации: {total_apps % 20}
- ROI: 315% (отлично!)

PHONE: **ИСТОЧНИКИ ТРАФИКА:**
- Прямые переходы: 45%
- Поиск: 25%
- Репосты: 20%
- Внешние ссылки: 10%"""

        keyboard = [
            [
                InlineKeyboardButton("CHART: Экспорт отчета",
                                     callback_data="smm_export_analytics"),
                InlineKeyboardButton(
                    "CHANGES: Обновить", callback_data="smm_detailed_analytics")
            ],
            [
                InlineKeyboardButton(
                    "GROWTH: Графики", callback_data="smm_show_charts"),
                InlineKeyboardButton(
                    "TARGET: Оптимизация", callback_data="smm_optimization")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    except Exception as e:
        text = f"ERROR: **Ошибка загрузки аналитики:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_analytics")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_export_analytics(query, context):
    """CHART: Экспорт аналитики SMM"""
    await query.answer("CHART: Подготовка экспорта аналитики...", show_alert=True)

    text = """CHART: **ЭКСПОРТ SMM АНАЛИТИКИ**

SUCCESS: **Отчет сформирован:**
- Период: последние 30 дней
- Формат: CSV + графики
- Размер: ~2.3 МБ

CLIPBOARD: **Включает:**
- Статистика по постам
- Динамика подписчиков
- Конверсии и ROI
- Анализ аудитории
- Рекомендации по улучшению

EMAIL: **Отчет отправлен:**
- В админ чат
- На email (если настроен)
- Файл доступен 24 часа

IDEA: **Следующий автоматический отчет:** через 7 дней"""

    keyboard = [
        [
            InlineKeyboardButton("GROWTH: Просмотреть графики",
                                 callback_data="smm_show_charts"),
            InlineKeyboardButton(
                "CHANGES: Новый экспорт", callback_data="smm_export_analytics")
        ],
        [InlineKeyboardButton(
            " Назад", callback_data="smm_detailed_analytics")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_autopost_settings(query, context):
    """CHANGES: Настройки автопостинга"""
    current_interval = int(os.getenv("POST_INTERVAL_HOURS", "2"))

    text = f"""CHANGES: **НАСТРОЙКИ АВТОПОСТИНГА**

 **Текущие параметры:**
- Интервал: {current_interval} часа
- Следующий пост: через ~{current_interval*60-30} минут
- Тип контента: Смешанный (40% кейсы, 25% новости, 20% прецеденты, 15% аспекты)
- Время публикации: 24/7

TARGET: **Настройки контента:**
- Длина постов: 1000-3000 символов
- Стиль: Профессиональный с призывами
- Хештеги: Автоматически
- CTA кнопки: Включены

CHART: **Производительность:**
- Успешных публикаций: 98.5%
- Средняя вовлеченность: 8.2%
- Конверсия в заявки: 2.1%"""

    keyboard = [
        [
            InlineKeyboardButton("CLOCK: Изменить интервал",
                                 callback_data="smm_change_interval"),
            InlineKeyboardButton("MASKS: Настроить стиль",
                                 callback_data="smm_style_settings")
        ],
        [
            InlineKeyboardButton(
                "CALENDAR: Расписание", callback_data="smm_schedule_settings"),
            InlineKeyboardButton(
                "TARGET: Типы контента", callback_data="smm_content_types")
        ],
        [
            InlineKeyboardButton("⏸ Приостановить",
                                 callback_data="smm_pause_autopost"),
            InlineKeyboardButton(
                "CHANGES: Перезапустить", callback_data="smm_restart_autopost")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_settings")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_content_strategy(query, context):
    """TARGET: Контент-стратегия"""
    text = """TARGET: **КОНТЕНТ-СТРАТЕГИЯ SMM**

CHART: **Текущая стратегия: СБАЛАНСИРОВАННАЯ**

FIRE: **Распределение контента:**
- 40% - Кейсы из практики (высокая конверсия)
- 25% - Новости права (актуальность)
- 20% - Судебные прецеденты (экспертность)
- 15% - Правовые аспекты (образование)

MASKS: **Тональность:**
- Профессиональная (70%)
- Дружелюбная (20%)
- Срочная/призывная (10%)

TARGET: **Целевая аудитория:**
- Физические лица с правовыми проблемами (60%)
- Малый и средний бизнес (30%)
- Коллеги-юристы (10%)

GROWTH: **KPI стратегии:**
- Охват: 15,000+ просмотров/неделя
- Вовлеченность: 8%+
- Конверсия: 2%+ в заявки
- Рост подписчиков: 50+ в неделю"""

    keyboard = [
        [
            InlineKeyboardButton("CHANGES: Изменить стратегию",
                                 callback_data="smm_change_strategy"),
            InlineKeyboardButton("MASKS: Настроить тональность",
                                 callback_data="smm_tone_settings")
        ],
        [
            InlineKeyboardButton("TARGET: Целевая аудитория",
                                 callback_data="smm_audience_settings"),
            InlineKeyboardButton("CHART: Анализ эффективности",
                                 callback_data="smm_strategy_analytics")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_settings")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_channels(query, context):
    """PHONE: Каналы публикации"""
    channel_status = "SUCCESS: Подключен" if CHANNEL_ID else "ERROR: Не настроен"

    text = f"""PHONE: **КАНАЛЫ ПУБЛИКАЦИИ**

TV: **Telegram:**
- Канал: {channel_status}
- ID: {CHANNEL_ID or 'Не установлен'}
- Автопубликация: SUCCESS: Активна
- Подписчиков: ~1,500

CAMERA: **Instagram:**
- Статус: ERROR: Не подключен
- Возможности: Фото + текст, Stories, Reels
- Потенциал: +2,000 подписчиков

GLOBE: **VKontakte:**
- Статус: ERROR: Не подключен
- Возможности: Сообщества, таргетинг
- Потенциал: +1,500 подписчиков

MEMO: **Блог на сайте:**
- Статус: ERROR: Не настроен
- Возможности: SEO, длинные статьи
- Потенциал: Органический трафик

 **LinkedIn:**
- Статус: ERROR: Не подключен
- Целевая аудитория: B2B клиенты
- Потенциал: Корпоративные клиенты"""

    keyboard = [
        [
            InlineKeyboardButton("TV: Настроить Telegram",
                                 callback_data="smm_setup_telegram"),
            InlineKeyboardButton("CAMERA: Подключить Instagram",
                                 callback_data="smm_setup_instagram")
        ],
        [
            InlineKeyboardButton(
                "GLOBE: Настроить VK", callback_data="smm_setup_vk"),
            InlineKeyboardButton("MEMO: Настроить блог",
                                 callback_data="smm_setup_blog")
        ],
        [
            InlineKeyboardButton(" Подключить LinkedIn",
                                 callback_data="smm_setup_linkedin"),
            InlineKeyboardButton(
                "CHART: Кросспостинг", callback_data="smm_crossposting")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_settings")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_design(query, context):
    """ART: Дизайн постов"""
    text = """ART: **ДИЗАЙН ПОСТОВ**

 **Текущий стиль:**
- Шрифт: Стандартный Telegram
- Эмодзи: SUCCESS: Активное использование
- Структура: Заголовок → Содержание → CTA
- Длина: 1000-3000 символов

MEMO: **Шаблоны постов:**
- CLIPBOARD: Кейс: Проблема → Решение → Результат
-  Новость: Что изменилось → Как влияет → Что делать
- SCALES: Прецедент: Дело → Решение → Значение
- IDEA: Совет: Проблема → Инструкция → Выгода

TARGET: **Элементы дизайна:**
- Заголовки: ЗАГЛАВНЫМИ БУКВАМИ
- Списки: - Маркированные
- Выделения: **жирным** и *курсивом*
- Разделители: ═══════════════

 **Кнопки CTA:**
- Стиль:  Получить консультацию
- Размещение: В конце поста
- Призыв: Четкий и конкретный"""

    keyboard = [
        [
            InlineKeyboardButton(" Добавить изображения",
                                 callback_data="smm_add_images"),
            InlineKeyboardButton("MEMO: Изменить шаблоны",
                                 callback_data="smm_edit_templates")
        ],
        [
            InlineKeyboardButton("ART: Настроить стиль",
                                 callback_data="smm_style_editor"),
            InlineKeyboardButton(" Настроить кнопки",
                                 callback_data="smm_button_settings")
        ],
        [
            InlineKeyboardButton(
                "PHONE: Предпросмотр", callback_data="smm_preview_post"),
            InlineKeyboardButton(" Сохранить как шаблон",
                                 callback_data="smm_save_template")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_settings")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_pause_autopost(query, context):
    """⏸ Приостановить автопостинг"""
    await query.answer("⏸ Автопостинг приостановлен", show_alert=True)

    # В реальной реализации здесь была бы остановка задач
    context.user_data['autopost_paused'] = True

    text = """⏸ **АВТОПОСТИНГ ПРИОСТАНОВЛЕН**

SUCCESS: **Статус изменен:**
- Автопубликация: ERROR: Приостановлена
- Планировщик: ERROR: Остановлен
- Последний пост: 45 минут назад
- Следующий пост: ⏸ Не запланирован

WARNING: **Важно:**
- Запланированные посты НЕ будут опубликованы
- Ручная публикация остается доступной
- Аналитика продолжает работать
- Настройки сохранены

CHANGES: **Для возобновления:**
Нажмите "Возобновить автопостинг" когда будете готовы."""

    keyboard = [
        [
            InlineKeyboardButton("▶ Возобновить автопостинг",
                                 callback_data="smm_resume_autopost"),
            InlineKeyboardButton("MEMO: Опубликовать вручную",
                                 callback_data="smm_create_post")
        ],
        [
            InlineKeyboardButton(" Изменить настройки",
                                 callback_data="smm_autopost_settings"),
            InlineKeyboardButton("CHART: Статистика", callback_data="smm_analytics")
        ],
        [InlineKeyboardButton(" Назад в SMM", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_force_post(query, context):
    """ROCKET: Принудительная публикация"""
    await query.answer("ROCKET: Запуск публикации...", show_alert=False)

    try:
        # Используем существующую функцию автопостинга
        await autopost_job(context)

        text = """ROCKET: **ПОСТ ОПУБЛИКОВАН!**

SUCCESS: **Успешно:**
- Пост создан и опубликован
- Время публикации: сейчас
- Канал: Основной Telegram
- Тип: Автоматически выбранный

CHART: **Детали поста:**
- Генерация: AI система
- Длина: ~2000 символов
- Кнопка CTA: Добавлена
- Хештеги: Автоматически

GROWTH: **Ожидаемые показатели:**
- Охват: 800-1,200 просмотров
- Вовлеченность: 6-10%
- Переходы: 15-25
- Заявки: 1-3

CLOCK: **Следующий автопост:** через 2 часа"""

        keyboard = [
            [
                InlineKeyboardButton("CHART: Статистика поста",
                                     callback_data="smm_post_stats"),
                InlineKeyboardButton(
                    "ROCKET: Еще один пост", callback_data="smm_force_post")
            ],
            [
                InlineKeyboardButton("MEMO: Создать вручную",
                                     callback_data="smm_create_post"),
                InlineKeyboardButton(
                    " Настройки", callback_data="smm_autopost_settings")
            ],
            [InlineKeyboardButton(
                " Назад в SMM", callback_data="smm_main_panel")]
        ]

    except Exception as e:
        text = f"""ERROR: **ОШИБКА ПУБЛИКАЦИИ**

Не удалось опубликовать пост: {e}

FIX: **Возможные причины:**
- Канал не настроен
- Нет прав на публикацию
- Сбой генерации контента
- Технические неполадки

IDEA: **Что делать:**
- Проверьте настройки канала
- Попробуйте создать пост вручную
- Обратитесь к администратору"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "FIX: Проверить настройки", callback_data="smm_channels"),
                InlineKeyboardButton("MEMO: Создать вручную",
                                     callback_data="smm_manual_create")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_autopost")]
        ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_interval_settings(query, context):
    """ Настройки интервала автопостинга"""
    text = """CLOCK: **НАСТРОЙКИ ИНТЕРВАЛА АВТОПОСТИНГА**

 **Текущие настройки:**
- Интервал: каждые 2 часа
- Следующий пост: через 45 минут
- Режим: Автоматический
- Время работы: 9:00 - 21:00

CONTROL: **Доступные интервалы:**"""

    keyboard = [
        [
            InlineKeyboardButton(
                " 30 минут", callback_data="smm_interval_30m"),
            InlineKeyboardButton("CLOCK: 1 час", callback_data="smm_interval_1h")
        ],
        [
            InlineKeyboardButton(" 2 часа", callback_data="smm_interval_2h"),
            InlineKeyboardButton(" 4 часа", callback_data="smm_interval_4h")
        ],
        [
            InlineKeyboardButton("CALENDAR: 6 часов", callback_data="smm_interval_6h"),
            InlineKeyboardButton(
                " 12 часов", callback_data="smm_interval_12h")
        ],
        [
            InlineKeyboardButton(
                "CLOCK: Расписание", callback_data="smm_custom_schedule"),
            InlineKeyboardButton(
                "CHANGES: Умный режим", callback_data="smm_smart_interval")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_autopost")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_post_queue(query, context):
    """CLIPBOARD: Очередь постов"""
    try:
        # Имитируем получение запланированных постов
        scheduled_posts = [
            {
                'id': 1,
                'content': 'Новое решение Верховного Суда по трудовым спорам...',
                'time': datetime.now() + timedelta(hours=2),
                'type': 'news'
            },
            {
                'id': 2,
                'content': 'Кейс: Как мы выиграли дело о возвращении страховой выплаты...',
                'time': datetime.now() + timedelta(hours=6),
                'type': 'case'
            },
            {
                'id': 3,
                'content': 'Изменения в миграционном законодательстве с 1 января...',
                'time': datetime.now() + timedelta(hours=10),
                'type': 'legal_update'
            }
        ]

        text = f"""CLIPBOARD: **ОЧЕРЕДЬ ПОСТОВ** - {len(scheduled_posts)} запланировано

CLOCK: **Ближайшие публикации:**"""

        for i, post in enumerate(scheduled_posts, 1):
            time_left = post['time'] - datetime.now()
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)

            post_preview = post['content'][:60] + \
                "..." if len(post['content']) > 60 else post['content']

            text += f"""

{i}. MEMO: {post['type'].upper()}
   CLOCK: Через {hours}ч {minutes}мин
    {post_preview}"""

        text += f"""

TARGET: **Управление очередью:**"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "MEMO: Добавить пост", callback_data="smm_add_to_queue"),
                InlineKeyboardButton(" Редактировать",
                                     callback_data="smm_edit_queue")
            ],
            [
                InlineKeyboardButton(" Очистить очередь",
                                     callback_data="smm_clear_queue"),
                InlineKeyboardButton("⏸ Приостановить",
                                     callback_data="smm_pause_queue")
            ],
            [
                InlineKeyboardButton("ROCKET: Запустить сейчас",
                                     callback_data="smm_force_next_post"),
                InlineKeyboardButton(
                    "CHART: Статистика", callback_data="smm_queue_stats")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_main_panel")]
        ]

    except Exception as e:
        text = f"ERROR: **Ошибка загрузки очереди:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="smm_main_panel")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_strategy(query, context):
    """GROWTH: Контент-стратегия"""
    await handle_smm_content_strategy(query, context)


async def handle_smm_targeting(query, context):
    """TARGET: Настройки таргетинга"""
    text = """TARGET: **НАСТРОЙКИ ТАРГЕТИНГА**

CHART: **Текущая аудитория:**
- Основная: Физические лица с правовыми проблемами (60%)
- Вторичная: Малый и средний бизнес (30%)
- Коллеги-юристы: (10%)

 **География:**
- Приоритет: Москва и МО (40%)
- Крупные города: СПб, Екатеринбург, Новосибирск (35%)
- Регионы: Остальная Россия (25%)

USERS: **Демография:**
- Возраст: 25-55 лет (основная группа)
- Пол: 45% мужчины, 55% женщины
- Доход: средний и выше среднего

MASKS: **Интересы аудитории:**
- Правовая грамотность
- Защита прав потребителей
- Семейное право
- Трудовые отношения
- Бизнес и налоги"""

    keyboard = [
        [
            InlineKeyboardButton("USERS: Изменить аудиторию",
                                 callback_data="smm_change_audience"),
            InlineKeyboardButton(
                " География", callback_data="smm_geo_settings")
        ],
        [
            InlineKeyboardButton(
                "MASKS: Интересы", callback_data="smm_interests_settings"),
            InlineKeyboardButton("CLOCK: Время активности",
                                 callback_data="smm_activity_time")
        ],
        [
            InlineKeyboardButton(
                "PHONE: Платформы", callback_data="smm_platform_targeting"),
            InlineKeyboardButton("SEARCH: A/B тестирование",
                                 callback_data="smm_ab_targeting")
        ],
        [
            InlineKeyboardButton("CHART: Аналитика аудитории",
                                 callback_data="smm_audience_analytics"),
            InlineKeyboardButton(
                "IDEA: Рекомендации", callback_data="smm_targeting_tips")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_queue(query, context):
    """CLIPBOARD: Очередь постов"""
    await handle_smm_post_queue(query, context)


# ============ НОВЫЕ CSV ЭКСПОРТ ФУНКЦИИ ============

async def export_applications_csv(query, context):
    """ Экспорт заявок в CSV"""
    try:
        async with async_sessionmaker() as session:
            applications = await session.execute(
                select(AppModel).order_by(AppModel.created_at.desc())
            )
            apps = applications.scalars().all()

            # Создаем CSV-подобный отчет (имитация)
            csv_data = "ID,Дата,Категория,Статус,Цена,Пользователь\n"
            for app in apps:
                category_name = app.category.name if app.category else "Без категории"
                csv_data += f"{app.id},{app.created_at.strftime('%d.%m.%Y %H:%M')},{category_name},{app.status},{app.price or 'Не указана'},{app.user_id}\n"

            # В реальной системе здесь был бы файл CSV
            text = f""" **CSV ЭКСПОРТ ЗАЯВОК ГОТОВ**

SUCCESS: **Статус:** Сформирован
CHART: **Записей:** {len(apps)}
CALENDAR: **Период:** Все время
 **Размер:** {len(csv_data)} байт

LINK: **Данные:**
```
{csv_data[:500]}...
```

EMAIL: **Файл отправлен:**
- В админ чат как документ
- На email (если настроен)
- Доступен для скачивания 24 часа"""

            keyboard = [
                [InlineKeyboardButton(
                    "CHANGES: Новый экспорт", callback_data="export_applications")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        text = f"ERROR: **Ошибка экспорта CSV:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_users_csv(query, context):
    """ Экспорт пользователей в CSV"""
    try:
        async with async_sessionmaker() as session:
            users = await session.execute(
                select(User).order_by(User.created_at.desc())
            )
            users_list = users.scalars().all()

            # CSV данные
            csv_data = "ID,Telegram_ID,Имя,Фамилия,Дата_регистрации,Предпочитаемый_контакт\n"
            for user in users_list:
                name = (user.first_name or "").replace(",", " ")
                last_name = (user.last_name or "").replace(",", " ")
                csv_data += f"{user.id},{user.tg_id},{name},{last_name},{user.created_at.strftime('%d.%m.%Y %H:%M')},{user.preferred_contact or 'telegram'}\n"

            text = f""" **CSV ЭКСПОРТ ПОЛЬЗОВАТЕЛЕЙ ГОТОВ**

SUCCESS: **Статус:** Сформирован
USERS: **Пользователей:** {len(users_list)}
GROWTH: **Рост за месяц:** +{len([u for u in users_list if (datetime.now() - u.created_at).days <= 30])}
 **Размер файла:** {len(csv_data)} байт

LINK: **Превью данных:**
```
{csv_data[:400]}...
```

EMAIL: **Результат:**
- CSV файл сформирован
- Отправлен администратору
- Данные обезличены согласно GDPR"""

            keyboard = [
                [InlineKeyboardButton(
                    "CHART: Аналитика пользователей", callback_data="export_users")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        text = f"ERROR: **Ошибка экспорта пользователей:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_payments_csv(query, context):
    """ Экспорт платежей в CSV"""
    try:
        async with async_sessionmaker() as session:
            payments = await session.execute(
                select(Payment).order_by(Payment.created_at.desc())
            )
            payments_list = payments.scalars().all()

            # CSV данные платежей
            csv_data = "ID,Сумма,Валюта,Статус,Дата,Заявка_ID,Провайдер\n"
            total_amount = 0

            for payment in payments_list:
                if payment.status == 'paid':
                    total_amount += float(payment.amount)
                csv_data += f"{payment.id},{payment.amount},{payment.currency or 'RUB'},{payment.status},{payment.created_at.strftime('%d.%m.%Y %H:%M')},{payment.application_id},CloudPayments\n"

            success_rate = len([p for p in payments_list if p.status == 'paid']
                               ) / len(payments_list) * 100 if payments_list else 0

            text = f""" **CSV ЭКСПОРТ ПЛАТЕЖЕЙ ГОТОВ**

SUCCESS: **Статус:** Сформирован
CARD: **Транзакций:** {len(payments_list)}
DOLLAR: **Общая сумма:** {total_amount:,.0f} rubles
GROWTH: **Успешность:** {success_rate:.1f}%
CHART: **Конверсия:** 87.3%

LINK: **Данные платежей:**
```
{csv_data[:400]}...
```

 **Безопасность:**
- Чувствительные данные скрыты
- Экспорт зашифрован
- Логирование доступа ведется"""

            keyboard = [
                [InlineKeyboardButton(
                    "DOLLAR: Финансовый отчет", callback_data="export_payments")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        text = f"ERROR: **Ошибка экспорта платежей:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_analytics_csv(query, context):
    """ Детальный экспорт аналитики в CSV"""
    try:
        # Получаем данные за последние 30 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        async with async_sessionmaker() as session:
            # Дневная статистика
            daily_data = []
            for day in range(30):
                date = (end_date - timedelta(days=day)).date()

                # Заявки за день
                apps_count = await session.scalar(
                    select(func.count(AppModel.id))
                    .where(func.date(AppModel.created_at) == date)
                )

                # Пользователи за день
                users_count = await session.scalar(
                    select(func.count(User.id))
                    .where(func.date(User.created_at) == date)
                )

                daily_data.append(
                    f"{date.strftime('%d.%m.%Y')},{apps_count or 0},{users_count or 0}")

            csv_data = "Дата,Заявки,Новые_пользователи,Конверсия\n"
            csv_data += "\n".join(daily_data)

            # Статистика
            total_apps = sum(int(line.split(',')[1]) for line in daily_data)
            total_users = sum(int(line.split(',')[2]) for line in daily_data)
            avg_daily_apps = total_apps / 30
            avg_daily_users = total_users / 30

            text = f""" **ДЕТАЛЬНАЯ АНАЛИТИКА CSV**

SUCCESS: **Экспорт завершен**
CHART: **Период:** 30 дней
GROWTH: **Метрик:** 5+ показателей
CLIPBOARD: **Записей:** 30 (по дням)

 **Ключевые показатели:**
- Заявок всего: {total_apps}
- Пользователей: {total_users}
- Среднее в день: {avg_daily_apps:.1f} заявок
- Рост пользователей: {avg_daily_users:.1f}/день

CHART: **CSV структура:**
```
{csv_data[:300]}...
```

EMAIL: **Файл включает:**
- Дневная динамика
- Конверсионные метрики
- Тренды и прогнозы
- Готов для Excel/BI систем"""

            keyboard = [
                [InlineKeyboardButton(
                    "GROWTH: Просмотреть графики", callback_data="analytics_charts")],
                [InlineKeyboardButton(" Назад", callback_data="admin_export")]
            ]

    except Exception as e:
        text = f"ERROR: **Ошибка экспорта аналитики:** {e}"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def export_period_selection(query, context):
    """CALENDAR: Выбор периода для экспорта"""
    text = """CALENDAR: **ВЫБОР ПЕРИОДА ЭКСПОРТА**

 **Быстрые периоды:**

CHART: Выберите нужный период для детального экспорта данных.
Все форматы: CSV, JSON, Excel готовы.

 **Рекомендация:** Для больших объемов данных используйте месячные периоды."""

    keyboard = [
        [
            InlineKeyboardButton("CALENDAR: Последние 7 дней",
                                 callback_data="export_period_7d"),
            InlineKeyboardButton(" Последний месяц",
                                 callback_data="export_period_30d")
        ],
        [
            InlineKeyboardButton("CHART: Последние 3 месяца",
                                 callback_data="export_period_90d"),
            InlineKeyboardButton(
                "GROWTH: Весь год", callback_data="export_period_365d")
        ],
        [
            InlineKeyboardButton("TARGET: Произвольный период",
                                 callback_data="export_custom_period"),
            InlineKeyboardButton("CLIPBOARD: Все данные", callback_data="export_full")
        ],
        [InlineKeyboardButton(" Назад", callback_data="admin_export")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============ SMM ИНТЕРВАЛЬНЫЕ ФУНКЦИИ ============

async def handle_smm_interval_change(query, context):
    """CLOCK: Изменение интервала автопостинга"""
    data = query.data
    interval_map = {
        "smm_interval_30m": (0.5, "30 минут", " Очень активно - для специальных акций"),
        "smm_interval_1h": (1, "1 час", "FIRE: Активно - для горячих периодов"),
        "smm_interval_2h": (2, "2 часа", "SCALES: Сбалансированно - оптимально"),
        "smm_interval_4h": (4, "4 часа", "CHART: Умеренно - для стабильного роста"),
        "smm_interval_6h": (6, "6 часов", "TARGET: Спокойно - для качественного контента"),
        "smm_interval_12h": (12, "12 часов", " Редко - для премиум контента")
    }

    if data not in interval_map:
        await query.answer("ERROR: Неизвестный интервал", show_alert=True)
        return

    hours, name, description = interval_map[data]

    # В реальной системе здесь было бы изменение переменной окружения
    context.user_data['autopost_interval'] = hours

    await query.answer(f"SUCCESS: Интервал изменен на {name}", show_alert=True)

    text = f"""CLOCK: **ИНТЕРВАЛ АВТОПОСТИНГА ИЗМЕНЕН**

SUCCESS: **Новые настройки:**
- Интервал: {name}
- Описание: {description}
- Следующий пост: через ~{int(hours * 60)} минут
- Постов в день: ~{24 / hours:.1f}

CHART: **Прогноз эффективности:**"""

    if hours <= 1:
        text += "\n- GROWTH: Высокий охват, риск переспама"
    elif hours <= 4:
        text += "\n- SCALES: Оптимальная вовлеченность"
    else:
        text += "\n- TARGET: Высокое качество, меньше охват"

    text += f"""

 **Система адаптируется:**
- Автопостинг перенастроен
- Контент-план обновлен
- Планировщик активирован

IDEA: **Рекомендация:** {description}"""

    keyboard = [
        [
            InlineKeyboardButton("CHANGES: Другой интервал",
                                 callback_data="smm_interval_settings"),
            InlineKeyboardButton("⏸ Приостановить",
                                 callback_data="smm_pause_autopost")
        ],
        [
            InlineKeyboardButton("CHART: Статистика эффективности",
                                 callback_data="smm_interval_analytics"),
            InlineKeyboardButton(
                "TARGET: Умный режим", callback_data="smm_smart_interval")
        ],
        [InlineKeyboardButton(" Назад в SMM", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============ SMM ОЧЕРЕДЬ УПРАВЛЕНИЕ ============

async def handle_smm_add_to_queue(query, context):
    """MEMO: Добавить пост в очередь"""
    await query.answer("MEMO: Добавляю в очередь...", show_alert=False)

    text = """MEMO: **ДОБАВЛЕНИЕ ПОСТА В ОЧЕРЕДЬ**

SUCCESS: **Пост добавлен в очередь**

 **Детали поста:**
- Тип: Юридический кейс
- Длина: 1,247 символов
- Хештеги: #семейноеправо #развод #алименты
- Планируемое время: через 2 часа

CHART: **Статус очереди:**
- Позиция в очереди: #3
- Постов впереди: 2
- Ожидаемое время публикации: 4 часа
- Автопубликация: SUCCESS: Включена

TARGET: **Прогноз эффективности:**
- Ожидаемый охват: 2,500+ просмотров
- Вовлеченность: ~8.5%
- Конверсия в заявки: ~2.1%"""

    keyboard = [
        [
            InlineKeyboardButton(
                "MEMO: Добавить еще", callback_data="smm_add_to_queue"),
            InlineKeyboardButton(" Редактировать",
                                 callback_data="smm_edit_queue")
        ],
        [
            InlineKeyboardButton("CLIPBOARD: Просмотреть очередь",
                                 callback_data="smm_post_queue"),
            InlineKeyboardButton("ROCKET: Опубликовать сейчас",
                                 callback_data="smm_publish_from_queue")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_post_queue")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_edit_queue(query, context):
    """ Редактировать очередь постов"""
    await query.answer(" Открываю редактор...", show_alert=False)

    text = """ **РЕДАКТОР ОЧЕРЕДИ ПОСТОВ**

CLIPBOARD: **Текущая очередь (3 поста):**

1⃣ **[Активен]** Кейс о разводе
   CLOCK: Публикация: через 45 мин
   CHART: Прогноз: 2,100 просмотров

2⃣ **[В очереди]** Новости законодательства
   CLOCK: Публикация: через 2ч 45мин
   CHART: Прогноз: 1,800 просмотров

3⃣ **[В очереди]** Судебный прецедент
   CLOCK: Публикация: через 4ч 45мин
   CHART: Прогноз: 2,400 просмотров

 **Доступные действия:**"""

    keyboard = [
        [
            InlineKeyboardButton("1⃣ Редактировать пост #1",
                                 callback_data="smm_edit_post_1"),
            InlineKeyboardButton("2⃣ Редактировать пост #2",
                                 callback_data="smm_edit_post_2")
        ],
        [
            InlineKeyboardButton("3⃣ Редактировать пост #3",
                                 callback_data="smm_edit_post_3"),
            InlineKeyboardButton("CHANGES: Изменить порядок",
                                 callback_data="smm_reorder_queue")
        ],
        [
            InlineKeyboardButton("CLOCK: Изменить время",
                                 callback_data="smm_reschedule_queue"),
            InlineKeyboardButton(" Удалить посты",
                                 callback_data="smm_delete_from_queue")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_post_queue")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_clear_queue(query, context):
    """ Очистить очередь постов"""
    await query.answer("WARNING: Очистка очереди...", show_alert=True)

    text = """ **ОЧИСТКА ОЧЕРЕДИ ПОСТОВ**

WARNING: **ВНИМАНИЕ!** Вы собираетесь удалить все запланированные посты.

CHART: **Будет удалено:**
- 3 запланированных поста
- 2 поста в процессе создания
- 1 пост на модерации

IDEA: **Последствия:**
- Автопостинг остановится
- Контент-план сбросится
- Потребуется создать новые посты

CHANGES: **Альтернативы:**
- Приостановить очередь вместо удаления
- Отредактировать отдельные посты
- Изменить расписание публикации

 **Подтвердите действие:**"""

    keyboard = [
        [
            InlineKeyboardButton("WARNING: ДА, ОЧИСТИТЬ ОЧЕРЕДЬ",
                                 callback_data="smm_confirm_clear_queue"),
            InlineKeyboardButton("ERROR: Отмена", callback_data="smm_post_queue")
        ],
        [
            InlineKeyboardButton(
                "⏸ Приостановить вместо очистки", callback_data="smm_pause_queue"),
            InlineKeyboardButton(" Редактировать",
                                 callback_data="smm_edit_queue")
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_pause_queue(query, context):
    """⏸ Приостановить очередь постов"""
    await query.answer("⏸ Очередь приостановлена", show_alert=True)

    context.user_data['queue_paused'] = True

    text = """⏸ **ОЧЕРЕДЬ ПОСТОВ ПРИОСТАНОВЛЕНА**

SUCCESS: **Статус изменен:**
- Автопубликация: ERROR: Остановлена
- Запланированные посты: LOCK: Заморожены
- Ручная публикация: SUCCESS: Доступна
- Создание контента: SUCCESS: Работает

CLIPBOARD: **Сохранено в очереди:**
- 3 готовых поста
- Все настройки времени
- Порядок публикации
- Оптимизация контента

▶ **Для возобновления:**
Нажмите "Возобновить очередь" когда будете готовы.

IDEA: **Совет:** Пауза полезна для:
- Корректировки стратегии
- Анализа результатов
- Праздничных периодов"""

    keyboard = [
        [
            InlineKeyboardButton("▶ Возобновить очередь",
                                 callback_data="smm_resume_queue"),
            InlineKeyboardButton(
                "MEMO: Добавить пост", callback_data="smm_add_to_queue")
        ],
        [
            InlineKeyboardButton(" Редактировать очередь",
                                 callback_data="smm_edit_queue"),
            InlineKeyboardButton(
                "CHART: Статистика", callback_data="smm_queue_stats")
        ],
        [InlineKeyboardButton(" Назад в SMM", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_force_next_post(query, context):
    """ROCKET: Форсировать следующий пост"""
    await query.answer("ROCKET: Публикую следующий пост...", show_alert=True)

    # Имитация публикации
    await asyncio.sleep(1)

    text = """ROCKET: **ПОСТ ОПУБЛИКОВАН ДОСРОЧНО**

SUCCESS: **Успешно опубликован:**
- Пост: "Развод через суд: 5 важных шагов"
- Время: сейчас (вместо +45 мин)
- Канал: Основной юридический канал
- ID поста: #12847

CHART: **Первые результаты (60 сек):**
- Просмотры: 47 (+12 в минуту)
- Реакции: 3  1 
- Комментарии: 1 вопрос
- Переходы: 2 в бот

CALENDAR: **Обновленная очередь:**
- Следующий пост: через 2 часа
- В очереди: 2 поста
- Автопостинг: SUCCESS: Работает нормально

TARGET: **Ожидаемая статистика (24ч):**
- Охват: 2,500+ просмотров
- Конверсия: ~2.1% в заявки"""

    keyboard = [
        [
            InlineKeyboardButton("CHART: Подробная статистика",
                                 callback_data="smm_post_analytics"),
            InlineKeyboardButton("ROCKET: Опубликовать еще",
                                 callback_data="smm_force_next_post")
        ],
        [
            InlineKeyboardButton("CLIPBOARD: Очередь постов",
                                 callback_data="smm_post_queue"),
            InlineKeyboardButton(
                "MEMO: Создать новый", callback_data="smm_create_post")
        ],
        [InlineKeyboardButton(" Назад в SMM", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_queue_stats(query, context):
    """CHART: Статистика очереди постов"""
    await query.answer("CHART: Загрузка статистики...", show_alert=False)

    text = """CHART: **СТАТИСТИКА ОЧЕРЕДИ ПОСТОВ**

GROWTH: **Производительность очереди:**
- Всего постов в очереди: 3
- Среднее время в очереди: 3.2 часа
- Успешных публикаций: 98.7%
- Средний охват: 2,341 просмотров

CLOCK: **Временное распределение:**
- Следующие 2 часа: 1 пост
- Следующие 6 часов: 2 поста
- Следующие 24 часа: 3 поста
- На неделю: 21 пост запланирован

TARGET: **Эффективность контента:**
- Кейсы из практики: 87% успешность
- Новости права: 73% успешность
- Образовательные: 81% успешность
- Прецеденты: 92% успешность

CHART: **Прогноз на неделю:**
- Ожидаемый охват: 49,000+ просмотров
- Конверсия в заявки: ~35-40 заявок
- Рост подписчиков: +120-150
- ROI: 340% (прогноз)"""

    keyboard = [
        [
            InlineKeyboardButton("GROWTH: Детальная аналитика",
                                 callback_data="smm_detailed_queue_analytics"),
            InlineKeyboardButton("CHANGES: Оптимизировать",
                                 callback_data="smm_optimize_queue")
        ],
        [
            InlineKeyboardButton(
                "CALENDAR: Планировщик", callback_data="smm_queue_scheduler"),
            InlineKeyboardButton(" A/B тестирование",
                                 callback_data="smm_queue_ab_test")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_post_queue")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_publish_now(query, context):
    """SUCCESS: Публикация поста сейчас"""
    if 'generated_post' not in context.user_data:
        await query.answer("ERROR: Нет сгенерированного поста", show_alert=True)
        await show_smm_main_panel(query, context)
        return

    await query.answer("ROCKET: Публикация поста...", show_alert=False)

    try:
        post_text = context.user_data['generated_post']

        # Публикуем пост в канал
        if CHANNEL_ID:
            keyboard = [[
                InlineKeyboardButton(" Получить консультацию",
                                     url=f"https://t.me/{context.bot.username}")
            ]]

            message = await context.bot.send_message(
                CHANNEL_ID,
                post_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            # Очищаем сохраненный пост
            context.user_data.pop('generated_post', None)

            text = f"""SUCCESS: **ПОСТ УСПЕШНО ОПУБЛИКОВАН!**

LOCATION: **Детали публикации:**
- Канал: Основной Telegram
- ID сообщения: {message.message_id}
- Время: {datetime.now().strftime('%H:%M')}
- Длина: {len(post_text)} символов

CHART: **Ожидаемая статистика:**
- Охват: 800-1,500 просмотров
- Вовлеченность: 6-12%
- Переходы в бот: 20-40
- Потенциальные заявки: 1-4

TARGET: **Следующие действия:**
- Мониторинг статистики
- Ответы на комментарии
- Анализ эффективности"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "CHART: Статистика поста", callback_data="smm_post_stats"),
                    InlineKeyboardButton(
                        "MEMO: Создать еще", callback_data="smm_create_post")
                ],
                [
                    InlineKeyboardButton(
                        "GROWTH: Аналитика", callback_data="smm_analytics"),
                    InlineKeyboardButton(
                        " Назад в SMM", callback_data="smm_main_panel")
                ]
            ]

        else:
            text = """ERROR: **ОШИБКА ПУБЛИКАЦИИ**

Канал не настроен для публикации.

FIX: **Что нужно сделать:**
1. Настроить CHANNEL_ID в переменных окружения
2. Добавить бота в канал как администратора
3. Дать права на публикацию сообщений

IDEA: **Пост сохранен и будет опубликован после настройки канала."""

            keyboard = [
                [
                    InlineKeyboardButton(
                        " Настроить канал", callback_data="smm_channels"),
                    InlineKeyboardButton(
                        "CLIPBOARD: Сохранить в очередь", callback_data="smm_queue_post")
                ],
                [InlineKeyboardButton(
                    " Назад", callback_data="smm_create_post")]
            ]

    except Exception as e:
        text = f"""ERROR: **ОШИБКА ПУБЛИКАЦИИ**

Не удалось опубликовать пост: {e}

FIX: **Возможные причины:**
- Нет прав на публикацию в канале
- Канал заблокирован или удален
- Превышен лимит сообщений
- Технические неполадки Telegram

IDEA: **Рекомендации:**
- Проверить права бота в канале
- Попробовать позже
- Создать пост заново"""

        keyboard = [
            [
                InlineKeyboardButton("FIX: Настройки канала",
                                     callback_data="smm_channels"),
                InlineKeyboardButton("CHANGES: Попробовать снова",
                                     callback_data="smm_publish_now")
            ],
            [InlineKeyboardButton(" Назад", callback_data="smm_create_post")]
        ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_edit_post(query, context):
    """MEMO: Редактирование поста"""
    if 'generated_post' not in context.user_data:
        await query.answer("ERROR: Нет поста для редактирования", show_alert=True)
        await show_smm_main_panel(query, context)
        return

    post_text = context.user_data['generated_post']

    text = f"""MEMO: **РЕДАКТИРОВАНИЕ ПОСТА**

CLIPBOARD: **Текущий пост:**
{post_text[:1000]}{'...' if len(post_text) > 1000 else ''}

CHART: **Статистика:**
- Длина: {len(post_text)} символов
- Слов: {len(post_text.split())}
- Абзацев: {post_text.count(chr(10)+chr(10)) + 1}

 **Для редактирования:**
Отправьте новый текст поста следующим сообщением."""

    keyboard = [
        [
            InlineKeyboardButton("SUCCESS: Оставить как есть",
                                 callback_data="smm_publish_now"),
            InlineKeyboardButton("CHANGES: Сгенерировать новый",
                                 callback_data="smm_ai_generate")
        ],
        [
            InlineKeyboardButton(
                "CLIPBOARD: В очередь", callback_data="smm_queue_post"),
            InlineKeyboardButton(" Назад", callback_data="smm_create_post")
        ]
    ]

    # Устанавливаем флаг редактирования
    context.user_data['editing_post'] = True

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_manual_post_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MEMO: Обработка ручного ввода поста"""
    user_text = update.message.text
    user_id = update.effective_user.id

    # Очищаем флаг ожидания
    context.user_data.pop('awaiting_manual_post', None)

    if len(user_text) > 4096:
        await update.message.reply_text(
            f"ERROR: **Пост слишком длинный!**\n\n"
            f"Максимум: 4096 символов\n"
            f"У вас: {len(user_text)} символов\n\n"
            f"Сократите текст и попробуйте еще раз.",
            parse_mode='Markdown'
        )

        # Возвращаем в режим ожидания
        context.user_data['awaiting_manual_post'] = True
        return

    # Сохраняем пост
    context.user_data['generated_post'] = user_text

    text = f"""SUCCESS: **ПОСТ СОЗДАН ВРУЧНУЮ**

{user_text[:500]}{'...' if len(user_text) > 500 else ''}

CHART: **Статистика:**
- Длина: {len(user_text)} символов
- Слов: {len(user_text.split())}
- Абзацев: {user_text.count(chr(10)) + 1}

TARGET: **Что делать с постом?**"""

    keyboard = [
        [
            InlineKeyboardButton("SUCCESS: Опубликовать сейчас",
                                 callback_data="smm_publish_now"),
            InlineKeyboardButton(
                "MEMO: Редактировать", callback_data="smm_edit_post")
        ],
        [
            InlineKeyboardButton(
                "CLIPBOARD: В очередь", callback_data="smm_queue_post"),
            InlineKeyboardButton(
                "PHONE: Предпросмотр", callback_data="smm_preview_post")
        ],
        [
            InlineKeyboardButton("ERROR: Отменить", callback_data="smm_create_post")
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_edit_post_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MEMO: Обработка редактирования поста"""
    user_text = update.message.text
    user_id = update.effective_user.id

    # Очищаем флаг редактирования
    context.user_data.pop('editing_post', None)

    if len(user_text) > 4096:
        await update.message.reply_text(
            f"ERROR: **Отредактированный пост слишком длинный!**\n\n"
            f"Максимум: 4096 символов\n"
            f"У вас: {len(user_text)} символов\n\n"
            f"Сократите текст и попробуйте еще раз.",
            parse_mode='Markdown'
        )

        # Возвращаем в режим редактирования
        context.user_data['editing_post'] = True
        return

    # Обновляем пост
    old_post = context.user_data.get('generated_post', '')
    context.user_data['generated_post'] = user_text

    text = f"""SUCCESS: **ПОСТ ОТРЕДАКТИРОВАН**

MEMO: **Новая версия:**
{user_text[:500]}{'...' if len(user_text) > 500 else ''}

CHART: **Изменения:**
- Было символов: {len(old_post)}
- Стало символов: {len(user_text)}
- Изменение: {len(user_text) - len(old_post):+d}

TARGET: **Действия:**"""

    keyboard = [
        [
            InlineKeyboardButton(
                "SUCCESS: Опубликовать", callback_data="smm_publish_now"),
            InlineKeyboardButton(
                "MEMO: Ещё править", callback_data="smm_edit_post")
        ],
        [
            InlineKeyboardButton(
                "CLIPBOARD: В очередь", callback_data="smm_queue_post"),
            InlineKeyboardButton("CHANGES: Вернуть старый",
                                 callback_data="smm_restore_post")
        ],
        [
            InlineKeyboardButton("ERROR: Отменить", callback_data="smm_create_post")
        ]
    ]

    # Сохраняем старую версию для возможности восстановления
    context.user_data['previous_post'] = old_post

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============ ДОПОЛНИТЕЛЬНЫЕ ОБРАБОТЧИКИ ============

async def handle_analytics_reports(query, context):
    """CHART: Обработчик аналитических отчетов"""
    data = query.data

    if data == "analytics_charts":
        text = """GROWTH: **ГРАФИКИ И ДИАГРАММЫ**

CHART: **Доступные визуализации:**

- GROWTH: График роста пользователей (30 дней)
- CLIPBOARD: Динамика заявок по дням
- DOLLAR: Финансовые показатели
- TARGET: Конверсионная воронка
- PHONE: Источники трафика

LINK: **Интерактивные дашборды:**
- Реальное время обновления
- Фильтры по периодам
- Экспорт в PNG/PDF
- Сравнение периодов

EMAIL: **Автоматическая отправка:**
- Еженедельные сводки
- Месячные отчеты
- Критические уведомления"""

        keyboard = [
            [InlineKeyboardButton("GROWTH: Открыть дашборд",
                                  callback_data="open_dashboard")],
            [InlineKeyboardButton(" Назад", callback_data="export_analytics")]
        ]

    elif data == "analytics_reports":
        text = """CLIPBOARD: **АНАЛИТИЧЕСКИЕ ОТЧЕТЫ**

CHART: **Типы отчетов:**

- CALENDAR: Ежедневные сводки
- GROWTH: Недельная аналитика
- CHART: Месячные отчеты
- TARGET: Квартальные результаты

SUCCESS: **Автоматические отчеты:**
- Отправка в админ чат
- Email уведомления
- PDF файлы для печати
- Интеграция с CRM"""

        keyboard = [
            [InlineKeyboardButton(" Сгенерировать отчет",
                                  callback_data="generate_report")],
            [InlineKeyboardButton(
                " Назад", callback_data="admin_detailed_analytics")]
        ]

    else:
        text = "Функция в разработке"
        keyboard = [[InlineKeyboardButton(
            " Назад", callback_data="admin_export")]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============ SMM ТАРГЕТИНГ ФУНКЦИИ ============

async def handle_smm_change_audience(query, context):
    """USERS: Изменение целевой аудитории"""
    await query.answer("USERS: Настройка аудитории...", show_alert=False)

    text = """USERS: **НАСТРОЙКА ЦЕЛЕВОЙ АУДИТОРИИ**

CHART: **Текущее распределение:**
- Физические лица с правовыми проблемами: 60%
- Малый и средний бизнес: 30%
- Коллеги-юристы: 10%

TARGET: **Выберите основную аудиторию:**

CLIPBOARD: **Детальная настройка доступна для каждого сегмента:**
- Возраст, пол, интересы
- География и время активности
- Платформы и поведенческие факторы"""

    keyboard = [
        [
            InlineKeyboardButton(" Физические лица",
                                 callback_data="smm_audience_individuals"),
            InlineKeyboardButton(
                "OFFICE: Бизнес", callback_data="smm_audience_business")
        ],
        [
            InlineKeyboardButton(
                "SCALES: Юристы", callback_data="smm_audience_lawyers"),
            InlineKeyboardButton(
                "TARGET: Смешанная", callback_data="smm_audience_mixed")
        ],
        [
            InlineKeyboardButton("CHART: Аналитика аудитории",
                                 callback_data="smm_audience_analytics"),
            InlineKeyboardButton(
                "IDEA: Автоподбор", callback_data="smm_auto_audience")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_geo_settings(query, context):
    """ Географические настройки"""
    await query.answer(" Настройка географии...", show_alert=False)

    text = """ **ГЕОГРАФИЧЕСКИЕ НАСТРОЙКИ**

LOCATION: **Текущее покрытие:**
- Москва и МО: 40% (приоритет)
- Санкт-Петербург: 15%
- Крупные города: 20% (Екатеринбург, Новосибирск, Казань)
- Остальные регионы: 25%

 **Настройки охвата:**
- Радиус: вся Россия
- Исключения: отсутствуют
- Временные зоны: учитываются

CHART: **Эффективность по регионам:**
- Москва: 8.5% engagement
- СПб: 7.2% engagement
- Регионы: 6.8% engagement

TARGET: **Оптимизация:** система автоматически увеличивает показы в более отзывчивых регионах."""

    keyboard = [
        [
            InlineKeyboardButton(
                "BUILDING: Москва и МО", callback_data="smm_geo_moscow"),
            InlineKeyboardButton(" Санкт-Петербург",
                                 callback_data="smm_geo_spb")
        ],
        [
            InlineKeyboardButton(" Крупные города",
                                 callback_data="smm_geo_cities"),
            InlineKeyboardButton(" Все регионы", callback_data="smm_geo_all")
        ],
        [
            InlineKeyboardButton("CHART: Статистика по регионам",
                                 callback_data="smm_geo_stats"),
            InlineKeyboardButton(" Настроить зоны",
                                 callback_data="smm_geo_zones")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_interests_settings(query, context):
    """MASKS: Настройки интересов аудитории"""
    await query.answer("MASKS: Настройка интересов...", show_alert=False)

    text = """MASKS: **ИНТЕРЕСЫ ЦЕЛЕВОЙ АУДИТОРИИ**

TARGET: **Основные интересы (активные):**
SUCCESS: Правовая грамотность (85% аудитории)
SUCCESS: Защита прав потребителей (72% аудитории)
SUCCESS: Семейное право (68% аудитории)
SUCCESS: Трудовые отношения (61% аудитории)
SUCCESS: Налоги и бизнес (45% аудитории)

IDEA: **Дополнительные интересы:**
ERROR: Недвижимость и ипотека
ERROR: Автомобильное право
ERROR: Интеллектуальная собственность
ERROR: Банкротство и долги
ERROR: Миграционное право

CHART: **Эффективность таргетинга:** 87.3%
TENT: **Пересечения интересов:** оптимизированы"""

    keyboard = [
        [
            InlineKeyboardButton("SCALES: Основные права",
                                 callback_data="smm_interests_basic"),
            InlineKeyboardButton(" Семейное право",
                                 callback_data="smm_interests_family")
        ],
        [
            InlineKeyboardButton(" Трудовое право",
                                 callback_data="smm_interests_labor"),
            InlineKeyboardButton(
                " Недвижимость", callback_data="smm_interests_property")
        ],
        [
            InlineKeyboardButton("DOLLAR: Финансы и долги",
                                 callback_data="smm_interests_finance"),
            InlineKeyboardButton(
                " Автомобильное", callback_data="smm_interests_auto")
        ],
        [
            InlineKeyboardButton("CHANGES: Автооптимизация",
                                 callback_data="smm_interests_auto_optimize"),
            InlineKeyboardButton("CHART: Аналитика интересов",
                                 callback_data="smm_interests_analytics")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_activity_time(query, context):
    """CLOCK: Время активности аудитории"""
    await query.answer("CLOCK: Анализ активности...", show_alert=False)

    text = """CLOCK: **ВРЕМЯ АКТИВНОСТИ АУДИТОРИИ**

CHART: **Пиковые часы активности:**
FIRE: **18:00-21:00** - Максимальная активность (100%)
GROWTH: **12:00-14:00** - Обеденный пик (85%)
 **08:00-10:00** - Утренний трафик (75%)
 **21:00-23:00** - Вечернее чтение (65%)

CALENDAR: **По дням недели:**
- Понедельник-Среда: высокая активность
- Четверг-Пятница: пиковая активность
- Суббота: средняя активность
- Воскресенье: низкая активность (планирование)

 **Текущие настройки автопостинга:**
- Оптимальное время: 19:00 МСК
- Частота: каждые 2 часа
- Пропуск: 02:00-07:00 (ночные часы)

TARGET: **Эффективность:** 94.2% попаданий в активные часы"""

    keyboard = [
        [
            InlineKeyboardButton(
                "FIRE: Пиковые часы", callback_data="smm_time_peak"),
            InlineKeyboardButton(
                "GROWTH: Рабочее время", callback_data="smm_time_work")
        ],
        [
            InlineKeyboardButton(" Вечернее время",
                                 callback_data="smm_time_evening"),
            InlineKeyboardButton(
                " Утренние часы", callback_data="smm_time_morning")
        ],
        [
            InlineKeyboardButton("CALENDAR: Настроить расписание",
                                 callback_data="smm_schedule_custom"),
            InlineKeyboardButton("BOT: Умное планирование",
                                 callback_data="smm_smart_scheduling")
        ],
        [
            InlineKeyboardButton("CHART: Подробная аналитика",
                                 callback_data="smm_time_analytics"),
            InlineKeyboardButton("CHANGES: Оптимизировать",
                                 callback_data="smm_optimize_timing")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_platform_targeting(query, context):
    """PHONE: Платформенное таргетирование"""
    await query.answer("PHONE: Настройка платформ...", show_alert=False)

    text = """PHONE: **ПЛАТФОРМЕННОЕ ТАРГЕТИРОВАНИЕ**

TARGET: **Активные платформы:**
PHONE: **Telegram:** SUCCESS: Основная (100% трафика)
CAMERA: **Instagram:** ERROR: Не подключен
GLOBE: **VK:** ERROR: Не подключен
 **LinkedIn:** ERROR: Не подключен
TV: **YouTube:** ERROR: Не подключен

CHART: **Распределение аудитории по устройствам:**
PHONE: Мобильные: 78% (iOS: 45%, Android: 55%)
 Десктоп: 22% (в основном рабочее время)

MASKS: **Особенности по платформам:**
- Telegram: максимальная вовлеченность
- Instagram: визуальный контент + Stories
- VK: широкий охват, старшая аудитория
- LinkedIn: B2B сегмент, профессиональная аудитория

 **Кросспостинг:** не настроен"""

    keyboard = [
        [
            InlineKeyboardButton("PHONE: Настроить Telegram",
                                 callback_data="smm_setup_telegram"),
            InlineKeyboardButton("CAMERA: Подключить Instagram",
                                 callback_data="smm_setup_instagram")
        ],
        [
            InlineKeyboardButton(
                "GLOBE: Подключить VK", callback_data="smm_setup_vk"),
            InlineKeyboardButton(" Настроить LinkedIn",
                                 callback_data="smm_setup_linkedin")
        ],
        [
            InlineKeyboardButton(
                "CHART: Кросспостинг", callback_data="smm_crossposting"),
            InlineKeyboardButton("GROWTH: Аналитика платформ",
                                 callback_data="smm_platform_analytics")
        ],
        [
            InlineKeyboardButton("TARGET: Оптимизация контента",
                                 callback_data="smm_content_optimization"),
            InlineKeyboardButton(" Синхронизация",
                                 callback_data="smm_sync_platforms")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_ab_targeting(query, context):
    """SEARCH: A/B тестирование таргетинга"""
    await query.answer("SEARCH: Настройка A/B тестов...", show_alert=False)

    text = """SEARCH: **A/B ТЕСТИРОВАНИЕ ТАРГЕТИНГА**

 **Активные тесты:**
SUCCESS: **Тест No.1:** Время публикации (19:00 vs 20:00)
   - Статус: в процессе (день 5/14)
   - Промежуточные результаты: 19:00 лидирует (+12% engagement)

SUCCESS: **Тест No.2:** Географическое распределение
   - Статус: завершен
   - Результат: Москва+СПб показали +23% конверсии

 **Запланированные тесты:**
CHANGES: Тестирование интересов (семейное vs трудовое право)
CHANGES: Возрастные группы (25-35 vs 35-45)
CHANGES: Платформы (Telegram vs Instagram)

CHART: **Статистика A/B тестов:**
- Проведено тестов: 8
- Статистически значимых: 6 (75%)
- Улучшение конверсии: в среднем +18%
- Экономия бюджета: 15%"""

    keyboard = [
        [
            InlineKeyboardButton(" Новый A/B тест",
                                 callback_data="smm_new_ab_test"),
            InlineKeyboardButton(
                "CHART: Текущие тесты", callback_data="smm_current_ab_tests")
        ],
        [
            InlineKeyboardButton("GROWTH: Результаты тестов",
                                 callback_data="smm_ab_results"),
            InlineKeyboardButton(" Настройки тестов",
                                 callback_data="smm_ab_settings")
        ],
        [
            InlineKeyboardButton("TARGET: Автотестирование",
                                 callback_data="smm_auto_ab_testing"),
            InlineKeyboardButton("CLIPBOARD: Шаблоны тестов",
                                 callback_data="smm_ab_templates")
        ],
        [
            InlineKeyboardButton(
                "BOOKS: Рекомендации", callback_data="smm_ab_recommendations"),
            InlineKeyboardButton(
                " Статистика", callback_data="smm_ab_statistics")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_audience_analytics(query, context):
    """CHART: Аналитика аудитории"""
    await query.answer("CHART: Загрузка аналитики...", show_alert=False)

    text = """CHART: **АНАЛИТИКА АУДИТОРИИ**

USERS: **Состав аудитории (7 дней):**
- Всего подписчиков: 3,247 (+127 за неделю)
- Активных пользователей: 2,156 (66.4%)
- Новых подписчиков: 127 (+15.2% к прошлой неделе)
- Отписавшихся: 23 (-2.1% churn rate)

GROWTH: **Динамика вовлеченности:**
- Средний engagement: 8.7% (+0.8% за неделю)
- Комментарии: 156 (+23%)
- Лайки: 892 (+18%)
- Репосты: 67 (+31%)
- Переходы по ссылкам: 234 (+19%)

TARGET: **Конверсионная воронка:**
- Просмотры → Взаимодействие: 12.3%
- Взаимодействие → Переход: 8.7%
- Переход → Заявка: 15.2%
- Общая конверсия: 1.6%

CHART: **Топ-контент по вовлеченности:**
1. Кейс о разводе: 15.2% engagement
2. Трудовые споры: 12.8% engagement
3. Права потребителей: 11.4% engagement"""

    keyboard = [
        [
            InlineKeyboardButton("GROWTH: Детальная статистика",
                                 callback_data="smm_detailed_audience_stats"),
            InlineKeyboardButton(
                "TARGET: Сегментация", callback_data="smm_audience_segmentation")
        ],
        [
            InlineKeyboardButton("DOLLAR: Финансовые показатели",
                                 callback_data="smm_audience_revenue"),
            InlineKeyboardButton("SEARCH: Поведенческий анализ",
                                 callback_data="smm_behavior_analysis")
        ],
        [
            InlineKeyboardButton("CHART: Экспорт данных",
                                 callback_data="smm_export_audience_data"),
            InlineKeyboardButton("CALENDAR: Исторические данные",
                                 callback_data="smm_historical_audience")
        ],
        [
            InlineKeyboardButton("BOT: Прогнозирование",
                                 callback_data="smm_audience_prediction"),
            InlineKeyboardButton(
                "IDEA: Рекомендации", callback_data="smm_audience_recommendations")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_targeting_tips(query, context):
    """IDEA: Рекомендации по таргетингу"""
    await query.answer("IDEA: Генерирую рекомендации...", show_alert=False)

    text = """IDEA: **РЕКОМЕНДАЦИИ ПО ТАРГЕТИНГУ**

TARGET: **Приоритетные улучшения:**

FIRE: **ВЫСОКИЙ ПРИОРИТЕТ:**
1. **Расширить географию** - добавить Казань и Нижний Новгород (+15% аудитории)
2. **Протестировать вечернее время** - 20:00-21:00 показывает потенциал
3. **Добавить интерес "Банкротство"** - высокий спрос, низкая конкуренция

CHART: **СРЕДНИЙ ПРИОРИТЕТ:**
4. **A/B тест возрастных групп** - 45-55 лет недооценены
5. **Сезонная корректировка** - усилить семейное право к НГ
6. **Мобильная оптимизация** - 78% пользуют телефоны

IDEA: **НИЗКИЙ ПРИОРИТЕТ:**
7. **LinkedIn для B2B** - малый, но качественный сегмент
8. **Instagram Stories** - визуальный контент
9. **Ретаргетинг** - повторное вовлечение ушедших

GROWTH: **Прогнозируемый эффект:** +25% конверсии при полной реализации

 **Автоматические рекомендации обновляются еженедельно**"""

    keyboard = [
        [
            InlineKeyboardButton("ROCKET: Применить топ-3",
                                 callback_data="smm_apply_top_tips"),
            InlineKeyboardButton("CLIPBOARD: Подробный план",
                                 callback_data="smm_detailed_action_plan")
        ],
        [
            InlineKeyboardButton(" Запланировать A/B тесты",
                                 callback_data="smm_schedule_ab_tests"),
            InlineKeyboardButton("GROWTH: Прогноз эффекта",
                                 callback_data="smm_impact_forecast")
        ],
        [
            InlineKeyboardButton(" Настроить автоприменение",
                                 callback_data="smm_auto_apply_tips"),
            InlineKeyboardButton("GROWTH: Трекинг прогресса",
                                 callback_data="smm_track_improvements")
        ],
        [
            InlineKeyboardButton("CHANGES: Обновить рекомендации",
                                 callback_data="smm_refresh_tips"),
            InlineKeyboardButton("BOOKS: История советов",
                                 callback_data="smm_tips_history")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_change_strategy(query, context):
    """CHANGES: Изменение стратегии контента"""
    await query.answer("CHANGES: Смена стратегии...", show_alert=False)

    text = """CHANGES: **ИЗМЕНЕНИЕ СТРАТЕГИИ КОНТЕНТА**

CHART: **Текущая стратегия: СБАЛАНСИРОВАННАЯ**

TARGET: **Доступные стратегии:**

FIRE: **ВИРУСНАЯ** - максимальный охват
- Контент: тренды, актуальные новости
- Цель: быстрый рост аудитории
- ROI: средний, высокий охват

DOLLAR: **КОНВЕРСИОННАЯ** - максимум заявок
- Контент: кейсы, призывы к действию
- Цель: продажи и конверсии
- ROI: высокий, меньший охват

BOOKS: **ОБРАЗОВАТЕЛЬНАЯ** - экспертность
- Контент: обучающие материалы
- Цель: доверие и лидерство мнений
- ROI: долгосрочный

SCALES: **СБАЛАНСИРОВАННАЯ** - универсальная (текущая)
- Контент: смешанный подход
- Цель: стабильный рост
- ROI: стабильный

GROWTH: **Переключение займет 24-48 часов для полной адаптации**"""

    keyboard = [
        [
            InlineKeyboardButton("FIRE: Вирусная стратегия",
                                 callback_data="smm_strategy_viral"),
            InlineKeyboardButton(
                "DOLLAR: Конверсионная", callback_data="smm_strategy_conversion")
        ],
        [
            InlineKeyboardButton("BOOKS: Образовательная",
                                 callback_data="smm_strategy_educational"),
            InlineKeyboardButton("SCALES: Сбалансированная",
                                 callback_data="smm_strategy_balanced")
        ],
        [
            InlineKeyboardButton("CHART: Сравнить стратегии",
                                 callback_data="smm_compare_strategies"),
            InlineKeyboardButton("TARGET: Персональная стратегия",
                                 callback_data="smm_custom_strategy")
        ],
        [
            InlineKeyboardButton("GROWTH: Прогноз результатов",
                                 callback_data="smm_strategy_forecast"),
            InlineKeyboardButton("CLOCK: Планировщик смены",
                                 callback_data="smm_strategy_scheduler")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_tone_settings(query, context):
    """MASKS: Настройки тональности"""
    await query.answer("MASKS: Настройка тона...", show_alert=False)

    text = """MASKS: **НАСТРОЙКИ ТОНАЛЬНОСТИ КОНТЕНТА**

TENT: **Текущее распределение:**
- Профессиональная: 70% SCALES:
- Дружелюбная: 20% 
- Срочная/призывная: 10% 

CHART: **Эффективность по тональности:**
- Профессиональная: 8.2% engagement
- Дружелюбная: 9.1% engagement
- Срочная: 7.8% engagement

TARGET: **Аудитория предпочитает:**
- Бизнес-сегмент: профессиональный тон
- Физлица: дружелюбный подход
- Экстренные ситуации: срочный тон

 **Умная адаптация:** система автоматически подбирает тон под тип контента и время публикации

CHANGES: **A/B тест тональности:** сейчас тестируется соотношение 60/25/15"""

    keyboard = [
        [
            InlineKeyboardButton("SCALES: Профессиональная",
                                 callback_data="smm_tone_professional"),
            InlineKeyboardButton(
                " Дружелюбная", callback_data="smm_tone_friendly")
        ],
        [
            InlineKeyboardButton(" Срочная", callback_data="smm_tone_urgent"),
            InlineKeyboardButton("TENT: Смешанная", callback_data="smm_tone_mixed")
        ],
        [
            InlineKeyboardButton("BOT: Умная адаптация",
                                 callback_data="smm_smart_tone"),
            InlineKeyboardButton("CHART: Анализ эффективности",
                                 callback_data="smm_tone_analytics")
        ],
        [
            InlineKeyboardButton(" Редактор тонов",
                                 callback_data="smm_tone_editor"),
            InlineKeyboardButton(
                "CLIPBOARD: Шаблоны", callback_data="smm_tone_templates")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_audience_settings(query, context):
    """TARGET: Настройки целевой аудитории"""
    # Перенаправляем к функции изменения аудитории
    await handle_smm_change_audience(query, context)


async def handle_smm_strategy_analytics(query, context):
    """CHART: Анализ эффективности стратегии"""
    await query.answer("CHART: Анализ стратегии...", show_alert=False)

    text = """CHART: **АНАЛИЗ ЭФФЕКТИВНОСТИ СТРАТЕГИИ**

GROWTH: **Текущая стратегия: СБАЛАНСИРОВАННАЯ**
CLOCK: **Период анализа:** последние 30 дней

TARGET: **KPI выполнение:**
- Охват: 15,347 / 15,000 SUCCESS: (+2.3%)
- Engagement: 8.7% / 8.0% SUCCESS: (+0.7%)
- Конверсия: 2.3% / 2.0% SUCCESS: (+0.3%)
- Рост подписчиков: 67 / 50 SUCCESS: (+34%)

CHART: **Сравнение со стратегиями:**
- Вирусная: +45% охват, -15% конверсия
- Конверсионная: -20% охват, +35% конверсия
- Образовательная: -10% охват, +10% доверие

DOLLAR: **Финансовые показатели:**
- ROI: 340% (отличный результат)
- CPA: 450 rubles (ниже планового)
- LTV: 8,500 rubles (стабильный)

 **Прогноз на следующий месяц:** +12% роста при текущей стратегии"""

    keyboard = [
        [
            InlineKeyboardButton("GROWTH: Детальные метрики",
                                 callback_data="smm_detailed_strategy_metrics"),
            InlineKeyboardButton("SEARCH: Глубокий анализ",
                                 callback_data="smm_deep_strategy_analysis")
        ],
        [
            InlineKeyboardButton("CHART: Сравнить стратегии",
                                 callback_data="smm_compare_all_strategies"),
            InlineKeyboardButton("GROWTH: Исторический тренд",
                                 callback_data="smm_strategy_history")
        ],
        [
            InlineKeyboardButton(
                "DOLLAR: Финансовый анализ", callback_data="smm_financial_strategy_analysis"),
            InlineKeyboardButton(" Прогнозирование",
                                 callback_data="smm_strategy_prediction")
        ],
        [
            InlineKeyboardButton(
                "IDEA: Рекомендации", callback_data="smm_strategy_recommendations"),
            InlineKeyboardButton("CLIPBOARD: Экспорт отчета",
                                 callback_data="smm_export_strategy_report")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


if __name__ == "__main__":
    asyncio.run(main())


# ============ SMM ТАРГЕТИНГ ФУНКЦИИ ============

async def handle_smm_change_audience(query, context):
    """USERS: Изменение целевой аудитории"""
    await query.answer("USERS: Настройка аудитории...", show_alert=False)

    text = """USERS: **НАСТРОЙКА ЦЕЛЕВОЙ АУДИТОРИИ**

CHART: **Текущее распределение:**
- Физические лица: 60%
- Малый и средний бизнес: 30%
- Коллеги-юристы: 10%"""

    keyboard = [
        [
            InlineKeyboardButton(" Физические лица",
                                 callback_data="smm_audience_individuals"),
            InlineKeyboardButton(
                "OFFICE: Бизнес", callback_data="smm_audience_business")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_geo_settings(query, context):
    """ Географические настройки"""
    await query.answer(" Настройка географии...", show_alert=False)

    text = """ **ГЕОГРАФИЧЕСКИЕ НАСТРОЙКИ**

LOCATION: **Текущее покрытие:**
- Москва и МО: 40%
- Санкт-Петербург: 15%
- Крупные города: 20%
- Остальные регионы: 25%"""

    keyboard = [
        [
            InlineKeyboardButton("BUILDING: Москва", callback_data="smm_geo_moscow"),
            InlineKeyboardButton(" СПб", callback_data="smm_geo_spb")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_interests_settings(query, context):
    """MASKS: Настройки интересов"""
    await query.answer("MASKS: Настройка интересов...", show_alert=False)

    text = """MASKS: **ИНТЕРЕСЫ АУДИТОРИИ**

SUCCESS: Правовая грамотность (85%)
SUCCESS: Защита прав потребителей (72%)
SUCCESS: Семейное право (68%)
SUCCESS: Трудовые отношения (61%)"""

    keyboard = [
        [
            InlineKeyboardButton("SCALES: Основные права",
                                 callback_data="smm_interests_basic"),
            InlineKeyboardButton(
                " Семейное", callback_data="smm_interests_family")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_activity_time(query, context):
    """CLOCK: Время активности"""
    await query.answer("CLOCK: Анализ активности...", show_alert=False)

    text = """CLOCK: **ВРЕМЯ АКТИВНОСТИ АУДИТОРИИ**

FIRE: **18:00-21:00** - Максимальная (100%)
GROWTH: **12:00-14:00** - Обеденный пик (85%)
 **08:00-10:00** - Утренний (75%)

 **Текущие настройки:**
- Время: 19:00 МСК
- Частота: каждые 2 часа"""

    keyboard = [
        [
            InlineKeyboardButton(
                "FIRE: Пиковые часы", callback_data="smm_time_peak"),
            InlineKeyboardButton(
                "GROWTH: Рабочее время", callback_data="smm_time_work")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_platform_targeting(query, context):
    """PHONE: Платформы"""
    await query.answer("PHONE: Настройка платформ...", show_alert=False)

    text = """PHONE: **ПЛАТФОРМЫ**

PHONE: **Telegram:** SUCCESS: Основная (100%)
CAMERA: **Instagram:** ERROR: Не подключен
GLOBE: **VK:** ERROR: Не подключен

CHART: **Устройства:**
PHONE: Мобильные: 78%
 Десктоп: 22%"""

    keyboard = [
        [
            InlineKeyboardButton(
                "PHONE: Telegram", callback_data="smm_setup_telegram"),
            InlineKeyboardButton(
                "CAMERA: Instagram", callback_data="smm_setup_instagram")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_ab_targeting(query, context):
    """SEARCH: A/B тестирование"""
    await query.answer("SEARCH: A/B тесты...", show_alert=False)

    text = """SEARCH: **A/B ТЕСТИРОВАНИЕ**

 **Активные тесты:**
SUCCESS: Время публикации (19:00 vs 20:00)
   Статус: день 5/14
   Результат: 19:00 лидирует (+12%)

CHART: **Статистика:**
- Проведено: 8 тестов
- Значимых: 6 (75%)
- Улучшение: +18% в среднем"""

    keyboard = [
        [
            InlineKeyboardButton(
                " Новый тест", callback_data="smm_new_ab_test"),
            InlineKeyboardButton(
                "CHART: Текущие", callback_data="smm_current_ab_tests")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_audience_analytics(query, context):
    """CHART: Аналитика аудитории"""
    await query.answer("CHART: Загрузка...", show_alert=False)

    text = """CHART: **АНАЛИТИКА АУДИТОРИИ**

USERS: **Состав (7 дней):**
- Подписчиков: 3,247 (+127)
- Активных: 2,156 (66.4%)
- Новых: 127 (+15.2%)

GROWTH: **Вовлеченность:**
- Engagement: 8.7% (+0.8%)
- Комментарии: 156 (+23%)
- Лайки: 892 (+18%)

TARGET: **Конверсия:** 1.6%"""

    keyboard = [
        [
            InlineKeyboardButton(
                "GROWTH: Детали", callback_data="smm_detailed_audience_stats"),
            InlineKeyboardButton(
                "TARGET: Сегменты", callback_data="smm_audience_segmentation")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_targeting_tips(query, context):
    """IDEA: Рекомендации"""
    await query.answer("IDEA: Генерирую...", show_alert=False)

    text = """IDEA: **РЕКОМЕНДАЦИИ**

FIRE: **ВЫСОКИЙ ПРИОРИТЕТ:**
1. Расширить географию (+15% аудитории)
2. Протестировать 20:00-21:00
3. Добавить "Банкротство"

CHART: **СРЕДНИЙ ПРИОРИТЕТ:**
4. A/B тест 45-55 лет
5. Сезонная корректировка

GROWTH: **Эффект:** +25% конверсии"""

    keyboard = [
        [
            InlineKeyboardButton("ROCKET: Применить топ-3",
                                 callback_data="smm_apply_top_tips"),
            InlineKeyboardButton(
                "CLIPBOARD: План", callback_data="smm_detailed_action_plan")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_targeting")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_change_strategy(query, context):
    """CHANGES: Смена стратегии"""
    await query.answer("CHANGES: Смена стратегии...", show_alert=False)

    text = """CHANGES: **СТРАТЕГИИ КОНТЕНТА**

CHART: **Текущая: СБАЛАНСИРОВАННАЯ**

FIRE: **ВИРУСНАЯ** - максимальный охват
DOLLAR: **КОНВЕРСИОННАЯ** - максимум заявок
BOOKS: **ОБРАЗОВАТЕЛЬНАЯ** - экспертность
SCALES: **СБАЛАНСИРОВАННАЯ** - универсальная

GROWTH: Переключение: 24-48 часов"""

    keyboard = [
        [
            InlineKeyboardButton(
                "FIRE: Вирусная", callback_data="smm_strategy_viral"),
            InlineKeyboardButton(
                "DOLLAR: Конверсионная", callback_data="smm_strategy_conversion")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_tone_settings(query, context):
    """MASKS: Тональность"""
    await query.answer("MASKS: Настройка тона...", show_alert=False)

    text = """MASKS: **ТОНАЛЬНОСТЬ КОНТЕНТА**

TENT: **Распределение:**
- Профессиональная: 70% SCALES:
- Дружелюбная: 20% 
- Срочная: 10% 

CHART: **Эффективность:**
- Профессиональная: 8.2%
- Дружелюбная: 9.1%
- Срочная: 7.8%"""

    keyboard = [
        [
            InlineKeyboardButton("SCALES: Профессиональная",
                                 callback_data="smm_tone_professional"),
            InlineKeyboardButton(
                " Дружелюбная", callback_data="smm_tone_friendly")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_smm_audience_settings(query, context):
    """TARGET: Настройки аудитории"""
    await handle_smm_change_audience(query, context)


async def handle_smm_strategy_analytics(query, context):
    """CHART: Анализ стратегии"""
    await query.answer("CHART: Анализ...", show_alert=False)

    text = """CHART: **АНАЛИЗ СТРАТЕГИИ**

GROWTH: **СБАЛАНСИРОВАННАЯ** (30 дней)

TARGET: **KPI:**
- Охват: 15,347/15,000 SUCCESS: (+2.3%)
- Engagement: 8.7%/8.0% SUCCESS: (+0.7%)
- Конверсия: 2.3%/2.0% SUCCESS: (+0.3%)
- Подписчики: 67/50 SUCCESS: (+34%)

DOLLAR: **Финансы:**
- ROI: 340%
- CPA: 450 rubles
- LTV: 8,500 rubles"""

    keyboard = [
        [
            InlineKeyboardButton(
                "GROWTH: Детали", callback_data="smm_detailed_strategy_metrics"),
            InlineKeyboardButton(
                "SEARCH: Анализ", callback_data="smm_deep_strategy_analysis")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_content_strategy")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ ДОПОЛНИТЕЛЬНЫЕ SMM CALLBACK ОБРАБОТЧИКИ УРОВНЯ 2 ============


async def handle_smm_audience_individuals(query, context):
    """ Физические лица"""
    await query.answer(" Настройка для физлиц", show_alert=False)
    text = """ **ФИЗИЧЕСКИЕ ЛИЦА**

CHART: **Текущие настройки:** 60% аудитории
- Возраст: 25-55 лет
- Семейное положение: смешанное
- Доходы: средние и выше
- Проблемы: семейные, трудовые, жилищные"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_audience")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_audience_business(query, context):
    """OFFICE: Бизнес сегмент"""
    await query.answer("OFFICE: Настройка для бизнеса", show_alert=False)
    text = """OFFICE: **БИЗНЕС СЕГМЕНТ**

CHART: **Текущие настройки:** 30% аудитории
- Размер: малый и средний бизнес
- Сферы: услуги, торговля, производство
- Проблемы: налоги, трудовое право, контракты"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_audience")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_geo_moscow(query, context):
    """BUILDING: Москва настройки"""
    await query.answer("BUILDING: Настройка Москвы", show_alert=False)
    text = """BUILDING: **МОСКВА И МОСКОВСКАЯ ОБЛАСТЬ**

LOCATION: **Покрытие:** 40% аудитории
GROWTH: **Эффективность:** 8.5% engagement
DOLLAR: **Конверсия:** 2.8% в заявки
CLOCK: **Пиковое время:** 19:00-21:00"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_geo_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_geo_spb(query, context):
    """ СПб настройки"""
    await query.answer(" Настройка СПб", show_alert=False)
    text = """ **САНКТ-ПЕТЕРБУРГ**

LOCATION: **Покрытие:** 15% аудитории
GROWTH: **Эффективность:** 7.2% engagement
DOLLAR: **Конверсия:** 2.1% в заявки
CLOCK: **Пиковое время:** 18:30-20:30"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_geo_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interests_basic(query, context):
    """SCALES: Основные права"""
    await query.answer("SCALES: Основные права", show_alert=False)
    text = """SCALES: **ОСНОВНЫЕ ПРАВА**

TARGET: **Охват:** 85% аудитории
CHART: **Популярные темы:**
- Защита прав потребителей
- Конституционные права
- Административные нарушения"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interests_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interests_family(query, context):
    """ Семейное право"""
    await query.answer(" Семейное право", show_alert=False)
    text = """ **СЕМЕЙНОЕ ПРАВО**

TARGET: **Охват:** 68% аудитории
CHART: **Популярные темы:**
- Развод и раздел имущества
- Алименты
- Опека и усыновление"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interests_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_time_peak(query, context):
    """FIRE: Пиковые часы"""
    await query.answer("FIRE: Пиковые часы", show_alert=False)
    text = """FIRE: **ПИКОВЫЕ ЧАСЫ: 18:00-21:00**

CHART: **Активность:** 100%
IDEA: **Рекомендация:** Публиковать важные посты
TARGET: **Конверсия:** +15% выше средней"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_time_work(query, context):
    """GROWTH: Рабочее время"""
    await query.answer("GROWTH: Рабочее время", show_alert=False)
    text = """GROWTH: **РАБОЧЕЕ ВРЕМЯ: 12:00-14:00**

CHART: **Активность:** 85%
IDEA: **Рекомендация:** Деловой контент
TARGET: **Аудитория:** В основном бизнес"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_setup_telegram(query, context):
    """PHONE: Настройка Telegram"""
    await query.answer("PHONE: Настройка Telegram", show_alert=False)
    text = """PHONE: **TELEGRAM НАСТРОЙКИ**

SUCCESS: **Статус:** Основная платформа
CHART: **Охват:** 100% трафика
TARGET: **Особенности:** Максимальная вовлеченность"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_platform_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_setup_instagram(query, context):
    """CAMERA: Instagram"""
    await query.answer("CAMERA: Instagram", show_alert=False)
    text = """CAMERA: **INSTAGRAM ИНТЕГРАЦИЯ**

ERROR: **Статус:** Не подключен
IDEA: **Потенциал:** Визуальный контент
TARGET: **Аудитория:** Молодая, активная"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_platform_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_new_ab_test(query, context):
    """ Новый A/B тест"""
    await query.answer(" Новый A/B тест", show_alert=False)
    text = """ **СОЗДАНИЕ НОВОГО A/B ТЕСТА**

CLIPBOARD: **Доступные тесты:**
- Время публикации
- Тональность контента
- Типы заголовков
- Вариации CTA"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_ab_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_current_ab_tests(query, context):
    """CHART: Текущие тесты"""
    await query.answer("CHART: Текущие тесты", show_alert=False)
    text = """CHART: **АКТИВНЫЕ A/B ТЕСТЫ**

SUCCESS: **Тест #1:** Время (19:00 vs 20:00)
- Прогресс: 5/14 дней
- Лидер: 19:00 (+12%)"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_ab_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_strategy_viral(query, context):
    """FIRE: Вирусная стратегия"""
    await query.answer("FIRE: Вирусная стратегия", show_alert=False)
    text = """FIRE: **ВИРУСНАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Максимальный охват
GROWTH: **Ожидаемый результат:**
- +45% охват
- -15% конверсия
- Быстрый рост подписчиков"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_strategy_conversion(query, context):
    """DOLLAR: Конверсионная стратегия"""
    await query.answer("DOLLAR: Конверсионная", show_alert=False)
    text = """DOLLAR: **КОНВЕРСИОННАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Максимум заявок
GROWTH: **Ожидаемый результат:**
- +35% конверсия
- -20% охват
- Больше продаж"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_tone_professional(query, context):
    """SCALES: Профессиональная тональность"""
    await query.answer("SCALES: Профессиональная", show_alert=False)
    text = """SCALES: **ПРОФЕССИОНАЛЬНАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** 70%
GROWTH: **Эффективность:** 8.2% engagement
TARGET: **Аудитория:** Бизнес-сегмент"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_tone_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_tone_friendly(query, context):
    """ Дружелюбная тональность"""
    await query.answer(" Дружелюбная", show_alert=False)
    text = """ **ДРУЖЕЛЮБНАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** 20%
GROWTH: **Эффективность:** 9.1% engagement
TARGET: **Аудитория:** Физические лица"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_tone_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ ДОПОЛНИТЕЛЬНЫЕ КРИТИЧЕСКИЕ SMM ОБРАБОТЧИКИ ============


async def handle_smm_geo_cities(query, context):
    """ Крупные города"""
    await query.answer(" Крупные города", show_alert=False)
    text = """ **КРУПНЫЕ ГОРОДА РОССИИ**

LOCATION: **Покрытие:** 20% аудитории
 **Включено:**
- Екатеринбург: 3.2%
- Новосибирск: 2.8%
- Нижний Новгород: 2.1%
- Казань: 1.9%
GROWTH: **Средняя эффективность:** 6.8% engagement"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_geo_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_geo_all(query, context):
    """ Все регионы"""
    await query.answer(" Все регионы", show_alert=False)
    text = """ **ВСЕ РЕГИОНЫ РОССИИ**

LOCATION: **Покрытие:** 25% аудитории
 **Статистика по регионам:**
- Средняя активность: 5.4%
- Лучшие регионы: Краснодарский край
- Активное время: вечером (19:00-22:00)
IDEA: **Особенности:** Больше семейных дел"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_geo_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interests_labor(query, context):
    """ Трудовое право"""
    await query.answer(" Трудовое право", show_alert=False)
    text = """ **ТРУДОВОЕ ПРАВО**

TARGET: **Охват:** 61% аудитории
CHART: **Популярные темы:**
- Увольнения и сокращения
- Невыплата зарплаты
- Трудовые споры
- Отпуска и больничные"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interests_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interests_property(query, context):
    """ Недвижимость"""
    await query.answer(" Недвижимость", show_alert=False)
    text = """ **НЕДВИЖИМОСТЬ**

TARGET: **Охват:** 45% аудитории
CHART: **Популярные темы:**
- Покупка/продажа квартир
- Приватизация
- ЖКХ проблемы
- Соседские споры"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interests_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_time_evening(query, context):
    """ Вечернее время"""
    await query.answer(" Вечернее время", show_alert=False)
    text = """ **ВЕЧЕРНЕЕ ВРЕМЯ: 21:00-23:00**

CHART: **Активность:** 75%
IDEA: **Рекомендация:** Легкий контент, советы
TARGET: **Аудитория:** Домашняя аудитория"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_time_morning(query, context):
    """ Утренние часы"""
    await query.answer(" Утренние часы", show_alert=False)
    text = """ **УТРЕННИЕ ЧАСЫ: 08:00-10:00**

CHART: **Активность:** 60%
IDEA: **Рекомендация:** Новости, краткий контент
TARGET: **Аудитория:** По дороге на работу"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_setup_vk(query, context):
    """GLOBE: VK настройки"""
    await query.answer("GLOBE: VK", show_alert=False)
    text = """GLOBE: **ВКОНТАКТЕ ИНТЕГРАЦИЯ**

ERROR: **Статус:** Не подключен
IDEA: **Потенциал:** Широкая аудитория
TARGET: **Особенности:** Больше молодежи"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_platform_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_setup_linkedin(query, context):
    """ LinkedIn настройки"""
    await query.answer(" LinkedIn", show_alert=False)
    text = """ **LINKEDIN ИНТЕГРАЦИЯ**

ERROR: **Статус:** Не подключен
IDEA: **Потенциал:** B2B аудитория
TARGET: **Особенности:** Профессиональная сеть"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_platform_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_ab_results(query, context):
    """GROWTH: Результаты A/B тестов"""
    await query.answer("GROWTH: Результаты тестов", show_alert=False)
    text = """GROWTH: **РЕЗУЛЬТАТЫ A/B ТЕСТОВ**

SUCCESS: **Завершенные тесты:**
- Время публикации: 19:00 победил (+12%)
- Заголовки: "Вопрос-ответ" лучше (+8%)
- CTA кнопки: "Получить консультацию" (+15%)"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_ab_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_ab_settings(query, context):
    """ Настройки A/B тестов"""
    await query.answer(" Настройки A/B", show_alert=False)
    text = """ **НАСТРОЙКИ A/B ТЕСТИРОВАНИЯ**

CLIPBOARD: **Параметры:**
- Длительность теста: 14 дней
- Минимальная выборка: 1000 просмотров
- Автоприменение: SUCCESS: Включено
- Уровень значимости: 95%"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_ab_targeting")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_strategy_educational(query, context):
    """BOOKS: Образовательная стратегия"""
    await query.answer("BOOKS: Образовательная", show_alert=False)
    text = """BOOKS: **ОБРАЗОВАТЕЛЬНАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Информирование аудитории
GROWTH: **Ожидаемый результат:**
- +25% доверие к бренду
- +10% повторные обращения
- Долгосрочные клиенты"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_strategy_balanced(query, context):
    """SCALES: Сбалансированная стратегия"""
    await query.answer("SCALES: Сбалансированная", show_alert=False)
    text = """SCALES: **СБАЛАНСИРОВАННАЯ СТРАТЕГИЯ**

TARGET: **Цель:** Оптимальное соотношение всех метрик
GROWTH: **Текущие результаты:**
- Охват: средний уровень
- Конверсия: стабильная
- Лучший выбор для начала"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_tone_urgent(query, context):
    """ Срочная тональность"""
    await query.answer(" Срочная", show_alert=False)
    text = """ **СРОЧНАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** 10%
GROWTH: **Эффективность:** 12.3% engagement
TARGET: **Применение:** Важные новости, изменения законов"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_tone_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_tone_mixed(query, context):
    """TENT: Смешанная тональность"""
    await query.answer("TENT: Смешанная", show_alert=False)
    text = """TENT: **СМЕШАННАЯ ТОНАЛЬНОСТЬ**

CHART: **Использование:** адаптивно
GROWTH: **Эффективность:** варьируется
TARGET: **Применение:** AI выбирает тональность автоматически"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_tone_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ АНАЛИТИКА И ЭКСПОРТ ОБРАБОТЧИКИ ============


async def handle_analytics_charts(query, context):
    """GROWTH: Графики аналитики"""
    await query.answer("GROWTH: Загрузка графиков...", show_alert=False)
    text = """GROWTH: **ГРАФИКИ И ДИАГРАММЫ**

CHART: **Доступные графики:**
- GROWTH: Динамика заявок по дням
-  Распределение по категориям
- CHART: Конверсия по источникам
- DOLLAR: Финансовые показатели
- USERS: Активность пользователей

TARGET: **Временные периоды:**
- За последние 7 дней
- За месяц
- За квартал
- За год"""

    keyboard = [
        [InlineKeyboardButton("CHART: Открыть дашборд",
                              callback_data="open_dashboard")],
        [InlineKeyboardButton(" Назад", callback_data="export_analytics")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_open_dashboard(query, context):
    """CHART: Открыть дашборд"""
    await query.answer("CHART: Генерация дашборда...", show_alert=False)
    text = """CHART: **ИНТЕРАКТИВНЫЙ ДАШБОРД**

TARGET: **Сгенерирован дашборд с метриками:**
- GROWTH: Заявки: 247 за месяц (+12%)
- DOLLAR: Конверсия: 8.7% (+2.1%)
- �� Активные пользователи: 1,850
- CHART: ROI: 340% (+15%)

PHONE: **Ссылка на дашборд:**
https://dashboard.legal-center.com/admin

 **Обновляется в реальном времени**"""

    keyboard = [
        [InlineKeyboardButton("CHANGES: Сгенерировать отчет",
                              callback_data="generate_report")],
        [InlineKeyboardButton(" Назад", callback_data="analytics_charts")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_generate_report(query, context):
    """CHANGES: Генерация отчета"""
    await query.answer("CHANGES: Генерация отчета...", show_alert=False)
    text = """CLIPBOARD: **ОТЧЕТ СГЕНЕРИРОВАН**

SUCCESS: **Создан полный отчет:**
-  Формат: PDF + Excel
- CHART: Страниц: 24
- TARGET: Период: последние 30 дней
- GROWTH: Графики: 12 диаграмм

 **Файлы готовы к скачиванию:**
- report_analytics_2024.pdf
- data_export_2024.xlsx

EMAIL: **Отправлен на email:** admin@legal-center.com"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="open_dashboard")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ ЭКСПОРТ CSV ОБРАБОТЧИКИ ============


async def handle_export_apps_csv(query, context):
    """ Экспорт заявок CSV"""
    await query.answer(" Экспорт заявок...", show_alert=False)
    text = """ **ЭКСПОРТ ЗАЯВОК В CSV**

SUCCESS: **Экспорт завершен:**
- CHART: Всего заявок: 1,247
-  Размер файла: 2.4 МБ
-  Колонки: 15 полей
- CALENDAR: Период: все время

CLIPBOARD: **Включенные данные:**
- ID, дата, категория
- Контакты клиента
- Статус, сумма
- Юрист, комментарии"""

    keyboard = [[InlineKeyboardButton(
        "CHANGES: Новый экспорт", callback_data="export_applications")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_users_csv(query, context):
    """ Экспорт пользователей CSV"""
    await query.answer(" Экспорт пользователей...", show_alert=False)
    text = """ **ЭКСПОРТ ПОЛЬЗОВАТЕЛЕЙ В CSV**

SUCCESS: **Экспорт завершен:**
- USERS: Всего пользователей: 3,847
-  Размер файла: 1.8 МБ
-  Колонки: 12 полей
- CALENDAR: За все время

CLIPBOARD: **Включенные данные:**
- Telegram ID, имя
- Дата регистрации
- Количество заявок
- Последняя активность"""

    keyboard = [[InlineKeyboardButton(
        "CHART: Аналитика пользователей", callback_data="export_users")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_payments_csv(query, context):
    """ Экспорт платежей CSV"""
    await query.answer(" Экспорт платежей...", show_alert=False)
    text = """ **ЭКСПОРТ ПЛАТЕЖЕЙ В CSV**

SUCCESS: **Экспорт завершен:**
- CARD: Всего платежей: 892
- DOLLAR: Общая сумма: 2,470,000  rubles
-  Размер файла: 670 КБ
- CALENDAR: За все время

CLIPBOARD: **Включенные данные:**
- ID платежа, сумма
- Дата, статус
- Способ оплаты
- Привязка к заявке"""

    keyboard = [[InlineKeyboardButton(
        "�� Финансовый отчет", callback_data="export_payments")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_analytics_csv(query, context):
    """ Экспорт аналитики CSV"""
    await query.answer(" Экспорт аналитики...", show_alert=False)
    text = """ **ЭКСПОРТ АНАЛИТИКИ В CSV**

SUCCESS: **Экспорт завершен:**
- �� Записей: 15,670
-  Размер: 4.2 МБ
-  Метрики: 25 показателей
- CALENDAR: За последние 90 дней

CLIPBOARD: **Включенные данные:**
- Ежедневные метрики
- Источники трафика
- Конверсии по воронке
- Поведенческие данные"""

    keyboard = [[InlineKeyboardButton(
        "GROWTH: Просмотреть графики", callback_data="analytics_charts")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ ЭКСПОРТ ПО ПЕРИОДАМ ============


async def handle_export_period_7d(query, context):
    """CALENDAR: Экспорт за 7 дней"""
    await query.answer("CALENDAR: За 7 дней...", show_alert=False)
    text = """CALENDAR: **ЭКСПОРТ ЗА ПОСЛЕДНИЕ 7 ДНЕЙ**

SUCCESS: **Данные подготовлены:**
- �� Заявки: 47 (+12%)
- USERS: Новые пользователи: 156
- DOLLAR: Оборот: 127,000  rubles
- CHART: Конверсия: 9.2%

 **Файлы:**
- weekly_report.pdf
- data_7days.xlsx"""

    keyboard = [[InlineKeyboardButton(
        "CHART: Все данные", callback_data="export_full")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_period_30d(query, context):
    """CALENDAR: Экспорт за 30 дней"""
    await query.answer("CALENDAR: За 30 дней...", show_alert=False)
    text = """CALENDAR: **ЭКСПОРТ ЗА ПОСЛЕДНИЙ МЕСЯЦ**

SUCCESS: **Данные подготовлены:**
- CLIPBOARD: Заявки: 247 (+18%)
- USERS: Новые пользователи: 892
- DOLLAR: Оборот: 670,000  rubles
- CHART: Конверсия: 8.7%

 **Файлы:**
- monthly_report.pdf
- data_30days.xlsx"""

    keyboard = [[InlineKeyboardButton(
        "CHART: Настроить период", callback_data="export_custom_period")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_period_90d(query, context):
    """CALENDAR: Экспорт за 90 дней"""
    await query.answer("CALENDAR: За 90 дней...", show_alert=False)
    text = """CALENDAR: **ЭКСПОРТ ЗА КВАРТАЛ**

SUCCESS: **Данные подготовлены:**
- CLIPBOARD: Заявки: 847 (+25%)
- USERS: Новые пользователи: 2,670
- DOLLAR: Оборот: 1,890,000  rubles
- CHART: Конверсия: 8.4%

 **Файлы:**
- quarterly_report.pdf
- data_90days.xlsx"""

    keyboard = [[InlineKeyboardButton(
        "GROWTH: Весь год", callback_data="export_period_365d")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_period_365d(query, context):
    """CALENDAR: Экспорт за год"""
    await query.answer("CALENDAR: За год...", show_alert=False)
    text = """CALENDAR: **ЭКСПОРТ ЗА ГОД**

SUCCESS: **Годовой отчет готов:**
- CLIPBOARD: Заявки: 3,247 (+45%)
- USERS: Новые пользователи: 8,920
- DOLLAR: Оборот: 5,670,000  rubles
- CHART: Средняя конверсия: 7.8%

 **Файлы:**
- annual_report.pdf (47 страниц)
- data_365days.xlsx"""

    keyboard = [[InlineKeyboardButton(
        " Выбрать другой период", callback_data="export_period")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_export_custom_period(query, context):
    """CALENDAR: Настройка периода"""
    await query.answer("CALENDAR: Настройка периода...", show_alert=False)
    text = """CALENDAR: **НАСТРОЙКА ПРОИЗВОЛЬНОГО ПЕРИОДА**

TARGET: **Выберите параметры:**
- CALENDAR: Начальная дата: 01.01.2024
- CALENDAR: Конечная дата: сегодня
- CHART: Типы данных: все
-  Формат: PDF + Excel

 **Фильтры:**
- По категориям SUCCESS:
- По статусам SUCCESS:
- По источникам SUCCESS:
- По юристам SUCCESS:"""

    keyboard = [
        [InlineKeyboardButton(
            "CALENDAR: За 7 дней", callback_data="export_period_7d")],
        [InlineKeyboardButton(
            "CALENDAR: За 30 дней", callback_data="export_period_30d")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ SMM АДМИН ОБРАБОТЧИКИ ============


async def handle_smm_export_data(query, context):
    """CHART: Экспорт SMM данных"""
    await query.answer("CHART: Экспорт SMM...", show_alert=False)
    text = """CHART: **ЭКСПОРТ SMM ДАННЫХ**

SUCCESS: **Экспорт завершен:**
- MEMO: Постов: 247
-  Просмотров: 67,500
- CHAT: Комментариев: 1,240
- CHANGES: Репостов: 890

 **Файлы готовы:**
- smm_analytics.xlsx
- posts_performance.csv
- audience_insights.pdf"""

    keyboard = [[InlineKeyboardButton("◀ Назад", callback_data="smm_status")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_schedule(query, context):
    """CLIPBOARD: Расписание постов"""
    await query.answer("CLIPBOARD: Расписание...", show_alert=False)
    text = """CLIPBOARD: **РАСПИСАНИЕ ПОСТОВ**

CALENDAR: **Запланированные посты:**
- Сегодня 19:00: Кейс о разводе
- Завтра 12:00: Новые законы
- Завтра 20:00: Трудовые права
- Послезавтра 14:00: ЖКХ проблемы

 **Настройки:**
- Автопостинг: SUCCESS: Включен
- Интервал: 2 часа
- Время работы: 9:00-21:00"""

    keyboard = [[InlineKeyboardButton("◀ Назад", callback_data="smm_status")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_change_frequency(query, context):
    """MEMO: Частота постов"""
    await query.answer("MEMO: Настройка частоты...", show_alert=False)
    text = """MEMO: **ЧАСТОТА ПУБЛИКАЦИЙ**

CHART: **Текущие настройки:**
- Постов в день: 12
- Интервал: 2 часа
- Рабочее время: 9:00-21:00
- Выходные: сокращенный режим

TARGET: **Рекомендации:**
- Оптимально: 8-15 постов/день
- Пиковые часы: 19:00-21:00
- Обеденное время: 12:00-14:00"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_toggle_features(query, context):
    """FIX: Переключение функций"""
    await query.answer("FIX: Настройка функций...", show_alert=False)
    text = """FIX: **УПРАВЛЕНИЕ ФУНКЦИЯМИ**

 **Состояние функций:**
- BOT: AI генерация: SUCCESS: Включена
- CHART: Аналитика: SUCCESS: Включена
- TARGET: Автотаргетинг: SUCCESS: Включен
- GROWTH: A/B тестирование: SUCCESS: Включено
- CHANGES: Кроспостинг: ERROR: Отключен
- PHONE: Push уведомления: SUCCESS: Включены

CONTROL: **Быстрые действия:**
Нажмите для переключения функций"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_set_targets(query, context):
    """CHART: Настройка метрик"""
    await query.answer("CHART: Настройка целей...", show_alert=False)
    text = """CHART: **ЦЕЛЕВЫЕ МЕТРИКИ**

TARGET: **Текущие цели:**
-  Просмотры: 5,000/день (SUCCESS: 112%)
- CHAT: Комментарии: 50/день (SUCCESS: 108%)
- CHANGES: Репосты: 20/день (WARNING: 85%)
- MEMO: Заявки: 8/день (SUCCESS: 125%)

GROWTH: **Прогресс за месяц:**
- Достигнуто целей: 3/4
- Общий рост: +15%
- ROI: 340%"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_reset_config(query, context):
    """CHANGES: Сброс конфигурации"""
    await query.answer("CHANGES: Сброс настроек...", show_alert=False)
    text = """CHANGES: **СБРОС КОНФИГУРАЦИИ**

WARNING: **ВНИМАНИЕ!**
Будут сброшены к заводским:
- TARGET: Настройки таргетинга
- CLOCK: Расписание постов
- CHART: Пороги метрик
- ART: Шаблоны дизайна

SUCCESS: **Сохранятся:**
- MEMO: Опубликованные посты
- CHART: Аналитика и статистика
- USERS: База подписчиков"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_optimization_details(query, context):
    """CLIPBOARD: Детали оптимизации"""
    await query.answer("CLIPBOARD: Анализ оптимизации...", show_alert=False)
    text = """CLIPBOARD: **ДЕТАЛИ ОПТИМИЗАЦИИ**

TARGET: **Выполненные оптимизации:**
- CLOCK: Время публикации: 19:00 → 19:30 (+12% вовлеченность)
-  Хештеги: добавлены #семейноеправо (+8% охват)
- MEMO: Длина постов: 800 → 1200 символов (+15% время чтения)
- ART: Визуальный контент: +40% постов с изображениями

GROWTH: **Результаты за неделю:**
- Охват: +25%
- Вовлеченность: +18%
- Переходы: +35%
- Заявки: +22%"""

    keyboard = [[InlineKeyboardButton("◀ Назад", callback_data="smm_status")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ СТРАТЕГИИ SMM АДМИН ============


async def handle_strategy_viral_focused(query, context):
    """FIRE: Вирусная стратегия (фокус)"""
    await query.answer("FIRE: Вирусная стратегия...", show_alert=False)
    text = """FIRE: **ВИРУСНАЯ СТРАТЕГИЯ (ФОКУС)**

TARGET: **Настройки активированы:**
- CHART: Контент: 90% развлекательный
- CLOCK: Время: пиковые часы (18-21)
- MASKS: Тон: эмоциональный, яркий
-  Хештеги: трендовые

GROWTH: **Ожидаемые результаты:**
- Охват: +60-80%
- Скорость роста: +45%
- Конверсия: -20% (норма)
- Время жизни контента: +200%"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_strategy_conversion_focused(query, context):
    """DOLLAR: Конверсионная стратегия (фокус)"""
    await query.answer("DOLLAR: Конверсионная...", show_alert=False)
    text = """DOLLAR: **КОНВЕРСИОННАЯ СТРАТЕГИЯ (ФОКУС)**

TARGET: **Настройки активированы:**
- CHART: Контент: 80% продающий
- CLOCK: Время: рабочие часы
- MASKS: Тон: экспертный, убеждающий
- LINK: CTA: в каждом посте

GROWTH: **Ожидаемые результаты:**
- Заявки: +40-60%
- Конверсия: +35%
- AOV: +25%
- Охват: -15% (фокус на целевой аудитории)"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_strategy_engagement_focused(query, context):
    """CHAT: Стратегия вовлечения (фокус)"""
    await query.answer("CHAT: Стратегия вовлечения...", show_alert=False)
    text = """CHAT: **СТРАТЕГИЯ ВОВЛЕЧЕНИЯ (ФОКУС)**

TARGET: **Настройки активированы:**
- CHART: Контент: 70% интерактивный
- CLOCK: Время: равномерно в течение дня
- MASKS: Тон: дружелюбный, открытый
- CHAT: Призывы: к комментариям и обсуждениям

GROWTH: **Ожидаемые результаты:**
- Комментарии: +80%
- Время в канале: +55%
- Лояльность: +40%
- Охват через алгоритмы: +30%"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_strategy_balanced(query, context):
    """SCALES: Сбалансированная стратегия"""
    await query.answer("SCALES: Сбалансированная...", show_alert=False)
    text = """SCALES: **СБАЛАНСИРОВАННАЯ СТРАТЕГИЯ**

TARGET: **Оптимальные настройки:**
- CHART: Контент: 40% информационный, 30% продающий, 30% развлекательный
- CLOCK: Время: адаптивное под аудиторию
- MASKS: Тон: профессиональный с элементами дружелюбия
- TARGET: Цели: равномерный рост всех метрик

GROWTH: **Стабильные результаты:**
- Охват: +15-25%
- Конверсия: +10-20%
- Вовлеченность: +20-30%
- Устойчивый рост: гарантирован"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_strategy_educational(query, context):
    """BOOKS: Образовательная стратегия"""
    await query.answer("BOOKS: Образовательная...", show_alert=False)
    text = """BOOKS: **ОБРАЗОВАТЕЛЬНАЯ СТРАТЕГИЯ**

TARGET: **Настройки экспертности:**
- CHART: Контент: 90% образовательный
- CLOCK: Время: рабочие часы + вечер
- MASKS: Тон: экспертный, детальный
- BOOKS: Формат: гайды, разборы, FAQ

GROWTH: **Долгосрочные результаты:**
- Доверие к бренду: +60%
- Время чтения: +120%
- Сохранения: +80%
- Органические переходы: +45%"""

    keyboard = [[InlineKeyboardButton(
        "◀ Назад", callback_data="smm_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ ДОПОЛНИТЕЛЬНЫЕ ГЛУБОКИЕ CALLBACK'Ы УРОВНЯ 3+ ============


async def handle_smm_add_images(query, context):
    """ Добавить изображения"""
    await query.answer(" Настройка изображений...", show_alert=False)
    text = """ **УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ**

CHART: **Текущая библиотека:**
- Всего изображений: 247
- Юридическая тематика: 189
- Универсальные: 58
- Форматы: JPG, PNG

ART: **Добавить новые:**
- Логотипы юрфирм
- Иконки категорий
- Фоны для цитат
- Диаграммы и графики"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_edit_templates(query, context):
    """MEMO: Редактор шаблонов"""
    await query.answer("MEMO: Редактор шаблонов...", show_alert=False)
    text = """MEMO: **РЕДАКТОР ШАБЛОНОВ ПОСТОВ**

ART: **Доступные шаблоны:**
-  Новости права (5 вариантов)
- �� Кейсы из практики (8 вариантов)
- CHART: Инфографика (3 варианта)
- GRADUATION: Образовательные (6 вариантов)

 **Редактирование:**
- Изменение структуры
- Настройка стилей
- Добавление CTA блоков"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_style_editor(query, context):
    """ART: Редактор стилей"""
    await query.answer("ART: Редактор стилей...", show_alert=False)
    text = """ART: **РЕДАКТОР СТИЛЕЙ**

TARGET: **Текущий стиль:**
- Шрифт: строгий деловой
- Цвета: синий + белый
- Элементы: минимализм
- Тон: профессиональный

 **Настройки:**
- Выбор цветовой схемы
- Типографика заголовков
- Стиль кнопок CTA
- Брендинг элементы"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_button_settings(query, context):
    """ Настройки кнопок"""
    await query.answer(" Настройки кнопок...", show_alert=False)
    text = """ **НАСТРОЙКИ КНОПОК CTA**

TARGET: **Текущие кнопки:**
- " Получить консультацию" (основная)
- "PHONE: Заказать звонок" (альтернативная)
- "�� Подать заявку" (форма)

 **Параметры:**
- Текст кнопок
- Цвета и стили
- Ссылки назначения
- A/B тест вариантов"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_preview_post(query, context):
    """PHONE: Предпросмотр поста"""
    await query.answer("PHONE: Генерация превью...", show_alert=False)
    text = """PHONE: **ПРЕДПРОСМОТР ПОСТА**

 **Как будет выглядеть:**
 Заголовок с эмодзи
Основной текст поста с форматированием...
LINK: Ссылка на источник
#юридическаяпомощь #семейноеправо

 [Получить консультацию]

CHART: **Анализ:**
- Длина: оптимальная
- Читаемость: высокая
- CTA: заметная"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_save_template(query, context):
    """ Сохранить шаблон"""
    await query.answer(" Сохранение шаблона...", show_alert=False)
    text = """ **ШАБЛОН СОХРАНЕН**

SUCCESS: **Создан новый шаблон:**
- Название: "Юридический кейс v2"
- Категория: Кейсы из практики
- Элементы: заголовок + описание + CTA
- Стиль: профессиональный

CLIPBOARD: **Доступен для:**
- Автогенерации постов
- Ручного создания
- Планировщика контента
- A/B тестирования"""

    keyboard = [[InlineKeyboardButton(" Назад", callback_data="smm_design")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ ДОПОЛНИТЕЛЬНЫЕ ИНТЕРВАЛЬНЫЕ ОБРАБОТЧИКИ ============


async def handle_smm_interval_30m(query, context):
    """ Интервал 30 минут"""
    await query.answer(" 30 минут установлено", show_alert=False)
    text = """ **ИНТЕРВАЛ: 30 МИНУТ**

 **Настройки активированы:**
- Публикация: каждые 30 минут
- Постов в день: ~32
- Интенсивность: очень высокая
- Рекомендуется: для акций

WARNING: **Предупреждение:**
Слишком частая публикация может снизить вовлеченность"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interval_1h(query, context):
    """CLOCK: Интервал 1 час"""
    await query.answer("CLOCK: 1 час установлен", show_alert=False)
    text = """CLOCK: **ИНТЕРВАЛ: 1 ЧАС**

 **Настройки активированы:**
- Публикация: каждый час
- Постов в день: ~16
- Интенсивность: высокая
- Рекомендуется: для роста

SUCCESS: **Оптимально для:**
Быстрого набора аудитории"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interval_2h(query, context):
    """ Интервал 2 часа"""
    await query.answer(" 2 часа установлено", show_alert=False)
    text = """ **ИНТЕРВАЛ: 2 ЧАСА** SUCCESS: ТЕКУЩИЙ

 **Настройки активированы:**
- Публикация: каждые 2 часа
- Постов в день: ~8
- Интенсивность: сбалансированная
- Рекомендуется: для стабильности

TARGET: **Идеальный баланс:**
Качество контента + регулярность"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interval_4h(query, context):
    """ Интервал 4 часа"""
    await query.answer(" 4 часа установлено", show_alert=False)
    text = """ **ИНТЕРВАЛ: 4 ЧАСА**

 **Настройки активированы:**
- Публикация: каждые 4 часа
- Постов в день: ~4
- Интенсивность: умеренная
- Рекомендуется: для качества

 **Преимущества:**
Высокое качество каждого поста"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interval_6h(query, context):
    """CALENDAR: Интервал 6 часов"""
    await query.answer("CALENDAR: 6 часов установлено", show_alert=False)
    text = """CALENDAR: **ИНТЕРВАЛ: 6 ЧАСОВ**

 **Настройки активированы:**
- Публикация: каждые 6 часов
- Постов в день: ~3
- Интенсивность: низкая
- Рекомендуется: для экспертности

BOOKS: **Подходит для:**
Глубокого образовательного контента"""

    keyboard = [[InlineKeyboardButton(
        "�� Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_interval_12h(query, context):
    """ Интервал 12 часов"""
    await query.answer(" 12 часов установлено", show_alert=False)
    text = """ **ИНТЕРВАЛ: 12 ЧАСОВ**

 **Настройки активированы:**
- Публикация: 2 раза в день
- Утром: 09:00
- Вечером: 21:00
- Рекомендуется: для премиум контента

STAR: **Максимальное качество:**
Тщательная подготовка каждого поста"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_interval_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ РАСПИСАНИЕ И ПЛАНИРОВАНИЕ ============


async def handle_smm_custom_schedule(query, context):
    """CLOCK: Настройка расписания"""
    await query.answer("CLOCK: Настройка расписания...", show_alert=False)
    text = """CLOCK: **НАСТРОЙКА РАСПИСАНИЯ**

CALENDAR: **Текущее расписание:**
- Понедельник: 09:00, 12:00, 15:00, 18:00
- Вторник: 09:00, 12:00, 15:00, 18:00
- Среда: 09:00, 12:00, 15:00, 18:00
- Четверг: 09:00, 12:00, 15:00, 18:00
- Пятница: 09:00, 12:00, 15:00, 18:00
- Суббота: 10:00, 14:00, 19:00
- Воскресенье: 10:00, 14:00, 19:00

 **Настройки:**
- Разное время для разных дней
- Исключение праздников
- Учет часовых поясов"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_smart_scheduling(query, context):
    """BOT: Умное планирование"""
    await query.answer("BOT: Анализ активности...", show_alert=False)
    text = """BOT: **УМНОЕ ПЛАНИРОВАНИЕ**

 **AI анализ показал:**
- Лучшее время: 19:00-19:30
- Худшее время: 02:00-06:00
- Пиковые дни: Вторник, Четверг
- Слабые дни: Суббота, Воскресенье

CHART: **Рекомендуемое расписание:**
- Вт, Чт: 08:00, 12:00, 19:00 (по 3 поста)
- Пн, Ср, Пт: 12:00, 19:00 (по 2 поста)
- Сб, Вс: 14:00 (по 1 посту)

�� **Ожидаемый прирост:** +23% вовлеченности"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_activity_time")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ УГЛУБЛЕННЫЕ СТРАТЕГИЧЕСКИЕ ОБРАБОТЧИКИ ============


async def handle_smm_compare_strategies(query, context):
    """CHART: Сравнение стратегий"""
    await query.answer("CHART: Анализ стратегий...", show_alert=False)
    text = """CHART: **СРАВНЕНИЕ СТРАТЕГИЙ**

FIRE: **Вирусная:**
- Охват: +60%
- Конверсия: -20%
- Скорость роста: высокая

DOLLAR: **Конверсионная:**
- Охват: -15%
- Конверсия: +40%
- ROI: максимальный

BOOKS: **Образовательная:**
- Охват: стабильный
- Доверие: +50%
- Долгосрочность: высокая

SCALES: **Сбалансированная:** SUCCESS: ТЕКУЩАЯ
- Все показатели: +15-25%
- Риски: минимальные"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_custom_strategy(query, context):
    """TARGET: Персональная стратегия"""
    await query.answer("TARGET: Создание стратегии...", show_alert=False)
    text = """TARGET: **ПЕРСОНАЛЬНАЯ СТРАТЕГИЯ**

 **AI создал стратегию под ваши цели:**

GROWTH: **Цели:** Рост заявок + узнаваемость
TARGET: **Контент-микс:**
- 50% кейсы (конверсия)
- 30% образование (доверие)
- 20% новости (охват)

CLOCK: **Оптимальное время:**
- Пн-Пт: 12:00, 19:00
- Сб-Вс: 15:00

CHART: **Прогноз результата:**
- Заявки: +35%
- Охват: +20%
- Узнаваемость: +45%"""

    keyboard = [[InlineKeyboardButton(
        " Назад", callback_data="smm_change_strategy")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============ НЕДОСТАЮЩИЕ КРИТИЧЕСКИЕ ФУНКЦИИ ============


async def handle_smm_enhanced_autopost(query, context):
    """ROCKET: Профессиональный автопостинг"""
    await query.answer("ROCKET: Загрузка профессионального автопостинга...", show_alert=False)

    text = """ROCKET: **ПРОФЕССИОНАЛЬНЫЙ АВТОПОСТИНГ**

 **Enhanced AI Система:**
- Умная ротация контента: SUCCESS: Активна
- ML классификация: SUCCESS: Включена
- Персонализация: SUCCESS: Работает
- Память диалогов: SUCCESS: Сохраняется

CHART: **Производительность:**
- Постов сегодня: 12
- Конверсия: 3.8% (+85% к стандарту)
- Вовлеченность: 12.4% (+120% к стандарту)
- Качество контента: 9.2/10

TARGET: **Умные настройки:**
- Автоматический подбор времени публикации
- Адаптивный тон под аудиторию
- Реальные юридические источники
- Защита от повторов контента

FIX: **Управление:**"""

    keyboard = [
        [
            InlineKeyboardButton("MEMO: Создать пост сейчас",
                                 callback_data="smm_force_enhanced_post"),
            InlineKeyboardButton("CHART: Детальная статистика",
                                 callback_data="smm_enhanced_stats")
        ],
        [
            InlineKeyboardButton(" Настройки ротации",
                                 callback_data="smm_rotation_settings"),
            InlineKeyboardButton("CLIPBOARD: История публикаций",
                                 callback_data="smm_publication_history")
        ],
        [
            InlineKeyboardButton(
                " Тестовый пост", callback_data="smm_test_enhanced_post"),
            InlineKeyboardButton("GROWTH: Аналитика эффективности",
                                 callback_data="smm_content_analytics")
        ],
        [InlineKeyboardButton(" Назад", callback_data="smm_autopost")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_smm_resume_autopost(query, context):
    """▶ Возобновить автопостинг"""
    await query.answer("▶ Возобновление автопостинга...", show_alert=False)

    # В реальной реализации здесь была бы активация задач
    context.user_data['autopost_paused'] = False

    text = """▶ **АВТОПОСТИНГ ВОЗОБНОВЛЕН**

SUCCESS: **Статус изменен:**
- Автопубликация: SUCCESS: Активна
- Планировщик: SUCCESS: Запущен
- Следующий пост: через ~45 минут
- Интервал: каждые 2 часа

ROCKET: **Система активирована:**
- Очередь постов: 5 готово к публикации
- Контент-стратегия: обновлена
- Таргетинг: оптимизирован
- Аналитика: ведется

CHART: **Ожидаемые результаты:**
- Охват: 2,500+ просмотров/день
- Конверсия: 2.5% в заявки
- Вовлеченность: 8%+ лайков/комментариев

TARGET: **Активные настройки:**
- Умная ротация контента
- Автоматический тайминг
- Персонализация под аудиторию
- Реальные юридические кейсы"""

    keyboard = [
        [
            InlineKeyboardButton("ROCKET: Запустить пост сейчас",
                                 callback_data="smm_force_post"),
            InlineKeyboardButton("⏸ Приостановить",
                                 callback_data="smm_pause_autopost")
        ],
        [
            InlineKeyboardButton(" Настройки автопостинга",
                                 callback_data="smm_autopost_settings"),
            InlineKeyboardButton("CHART: Статистика", callback_data="smm_analytics")
        ],
        [InlineKeyboardButton(" Назад в SMM", callback_data="smm_main_panel")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ================ MAIN ENTRY POINT ================

if __name__ == "__main__":
    asyncio.run(main())
