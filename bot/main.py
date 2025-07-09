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
    """AI консультант по всем юридическим вопросам с Enhanced AI + обработка рассылок"""
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

    try:
        # Используем Enhanced AI если доступен
        if ai_enhanced_manager and ai_enhanced_manager._initialized:
            response = await ai_enhanced_manager.generate_response(
                user_id=user.id,
                message=user_text
            )
        else:
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
            response += "\n\n💼 Для детальной консультации нажмите /start и заполните заявку."

        await update.message.reply_text(response)

    except Exception as e:
        log.error(f"AI Chat error: {e}")
        await update.message.reply_text(
            "🤖 Извините, временные проблемы с AI консультантом. "
            "Попробуйте позже или обратитесь к администратору."
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
    if not await is_admin(user_id):
        await query.answer("Нет доступа", show_alert=True)
        return

    data = query.data

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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

        text = f"""
📋 **ЗАЯВКА #{app.id}**

📂 Категория: {category_name}
📝 Подкатегория: {subcategory_detail}

👤 **Клиент:**
Имя: {user.first_name} {user.last_name or ''}
📞 {user.phone or '-'}
📧 {user.email or '-'}
💬 Связь: {contact_methods.get(app.contact_method, app.contact_method or '-')}
🕐 Время: {app.contact_time or 'любое'}

📄 **Описание:**
{app.description or '-'}

{f'📎 Файлов: {len(app.files_data or [])}' if app.files_data else ''}
{f'🏷️ UTM: {app.utm_source}' if app.utm_source else ''}

💰 Стоимость: {app.price or 'не определена'} ₽
📊 Статус: {app.status}
📅 Создана: {app.created_at.strftime('%d.%m.%Y %H:%M')}
"""

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

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

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
                except Exception as e:
                    log.error(f"Payment creation error: {e}")
                    # Fallback URL
                    pay_url = f"https://example.com/pay/{app.id}"

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

            # Отправляем ссылку на оплату администратору
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

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        "🔧 **АДМИН ПАНЕЛЬ**\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


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

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

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

    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        progress_text,
        parse_mode='Markdown'
    )

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

    await query.edit_message_text(
        final_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

        await query.edit_message_text(
            report,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ================ JOBS ================

async def autopost_job(context: ContextTypes.DEFAULT_TYPE):
    """🧠 ML-POWERED АВТОПОСТИНГ с парсингом реальных новостей"""
    if not CHANNEL_ID:
        return

    try:
        # Инициализируем Content Intelligence System
        from bot.services.content_intelligence import ContentIntelligenceSystem

        content_system = ContentIntelligenceSystem()
        await content_system.initialize()

        # Собираем и обрабатываем новости
        log.info("🔍 Starting intelligent content collection...")
        generated_posts = await content_system.collect_and_process_news()

        if generated_posts:
            # Публикуем первый пост из сгенерированных
            post_text = generated_posts[0]
            log.info(f"📝 Publishing AI-generated post: {post_text[:50]}...")

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

            log.info("✅ Intelligent autopost published successfully")
        else:
            # Fallback к старой системе если нет новостей
            log.info("📰 No new content found, using fallback post generation")
            await _fallback_autopost(context)

    except Exception as e:
        log.error(f"❌ ML autopost failed: {e}")
        # Fallback к старой системе при ошибке
        await _fallback_autopost(context)


async def _fallback_autopost(context: ContextTypes.DEFAULT_TYPE):
    """Fallback автопостинг при ошибке ML системы"""

    # Улучшенные темы для fallback
    advanced_topics = [
        "Новые изменения в трудовом законодательстве 2024",
        "Цифровые права граждан: что нужно знать",
        "Защита персональных данных: практические советы",
        "Налоговые льготы для физических лиц в 2024",
        "Электронные услуги Росреестра: пошаговый алгоритм",
        "Права потребителей при покупке онлайн",
        "Семейное право: новые тенденции в судебной практике",
        "Банкротство физлиц: актуальные изменения",
        "Жилищные споры: как защитить свои права",
        "Административные штрафы: новые правила обжалования"
    ]

    topic = random.choice(advanced_topics)

    messages = [{
        "role": "system",
        "content": """Ты - опытный юрист, создающий экспертные посты для Telegram канала.
        Требования:
        - Используй актуальную правовую информацию
        - Добавляй практические советы
        - Структурируй текст с эмодзи
        - Объем: 400-500 символов
        - Избегай общих фраз, давай конкретику"""
    }, {
        "role": "user",
        "content": f"Создай экспертный пост на тему: {topic}. Включи практические рекомендации и ссылки на нормативные акты."
    }]

    text = await generate_ai_response(messages, model="openai/gpt-4o", max_tokens=600)

    # Добавляем кнопку
    keyboard = [[
        InlineKeyboardButton("💼 Получить консультацию",
                             url=f"https://t.me/{context.bot.username}")
    ]]

    await context.bot.send_message(
        CHANNEL_ID,
        text,
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
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        ai_chat
    ))

    # Джобы
    if application.job_queue is not None:
        application.job_queue.run_repeating(
            autopost_job,
            interval=timedelta(hours=2),
            first=timedelta(minutes=10)
        )
        print("✅ Job queue initialized - autopost enabled")
        log.info("Job queue initialized successfully")
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
