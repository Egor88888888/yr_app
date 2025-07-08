#!/usr/bin/env python3
"""
Юридический Супер-сервис бот
Полный спектр юридических услуг с онлайн оплатой

Features:
- Web App для заявок (12 категорий услуг)
- Интеграция с Google Sheets для CRM
- Онлайн оплата через CloudPayments
- AI консультант на базе OpenRouter
- Админ панель с управлением заявками
- Автопостинг контента в канал
"""

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

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

# ================ CONFIG ================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Enhanced AI Manager
ai_enhanced_manager = None
# Get Railway public domain
RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv(
    "MY_RAILWAY_PUBLIC_URL")

# Use known Railway domain if env var contains placeholder
if RAILWAY_DOMAIN and "MY_RAILWAY_PUBLIC_URL" in RAILWAY_DOMAIN:
    # Your actual Railway domain
    PUBLIC_HOST = "poetic-simplicity-production-60e7.up.railway.app"
else:
    PUBLIC_HOST = RAILWAY_DOMAIN if RAILWAY_DOMAIN else "localhost"

# If Railway domain contains full URL, extract domain
if PUBLIC_HOST.startswith("http"):
    from urllib.parse import urlparse
    PUBLIC_HOST = urlparse(PUBLIC_HOST).netloc

WEB_APP_URL = f"https://{PUBLIC_HOST}/webapp/"

print(f"🌐 WebApp URL: {WEB_APP_URL}")
print(f"🔗 Webhook URL: https://{PUBLIC_HOST}/{TOKEN}")
PORT = int(os.getenv("PORT", 8080))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Global admin set
ADMIN_USERS = {ADMIN_CHAT_ID}

# Role permissions
ROLE_PERMISSIONS = {
    "operator": ["view_applications", "update_status"],
    "lawyer": ["view_applications", "update_status", "assign_lawyer", "add_notes", "bill_client"],
    "superadmin": ["view_applications", "update_status", "assign_lawyer", "add_notes", "bill_client", "manage_admins", "view_all_stats"]
}


async def check_admin_permission(user_id: int, permission: str) -> bool:
    """Check if user has specific permission"""
    if user_id == ADMIN_CHAT_ID:  # Superadmin by default
        return True

    async with async_sessionmaker() as session:
        result = await session.execute(
            select(Admin).where(
                Admin.tg_id == user_id,
                Admin.is_active == True
            )
        )
        admin = result.scalar_one_or_none()
        if not admin:
            return False

        return permission in ROLE_PERMISSIONS.get(admin.role, [])


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
    """AI консультант по всем юридическим вопросам с Enhanced AI"""
    global ai_enhanced_manager

    if not OPENROUTER_API_KEY:
        await update.message.reply_text("AI консультант временно недоступен")
        return

    user_text = update.message.text
    user = update.effective_user

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
    if user_id not in ADMIN_USERS:
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


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик админских кнопок"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_USERS:
        await query.answer("Нет доступа", show_alert=True)
        return

    data = query.data

    if data == "admin_apps":
        await show_applications(query, context)
    elif data == "admin_stats":
        await show_statistics(query, context)
    elif data == "admin_payments":
        await show_payments(query, context)
    elif data == "admin_ai_status":
        await show_ai_status(query, context)
    elif data.startswith("app_"):
        await handle_application_action(query, context)
    elif data == "back_admin":
        await show_admin_panel(query)


async def show_applications(query, context):
    """Показать список заявок"""
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(AppModel, User, Category)
            .join(User)
            .join(Category)
            .order_by(AppModel.created_at.desc())
            .limit(10)
        )
        apps = result.all()

    if not apps:
        text = "📋 Нет заявок"
    else:
        text = "📋 **ПОСЛЕДНИЕ ЗАЯВКИ**\n\n"
        keyboard = []

        for app, user, cat in apps:
            status_emoji = {
                "new": "🆕",
                "processing": "⏳",
                "completed": "✅"
            }.get(app.status, "❓")

            text += f"{status_emoji} #{app.id} | {cat.name}\n"
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
    """Действия с заявкой"""
    data = query.data

    if data.startswith("app_view_"):
        app_id = int(data.split("_")[2])

        async with async_sessionmaker() as session:
            result = await session.execute(
                select(AppModel, User, Category)
                .join(User)
                .join(Category)
                .where(AppModel.id == app_id)
            )
            row = result.one_or_none()

        if not row:
            await query.answer("Заявка не найдена", show_alert=True)
            return

        app, user, cat = row

        contact_methods = {
            'phone': '📞 Телефонный звонок',
            'telegram': '💬 Telegram',
            'email': '📧 Email',
            'whatsapp': '💚 WhatsApp'
        }

        text = f"""
📋 **ЗАЯВКА #{app.id}**

📂 Категория: {cat.name}
📝 Подкатегория: {app.subcategory or '-'}

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

        keyboard = [
            [InlineKeyboardButton("✅ Взять в работу", callback_data=f"app_take_{app.id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app.id}")],
            [InlineKeyboardButton("💳 Выставить счет",
                                  callback_data=f"app_bill_{app.id}")],
            [InlineKeyboardButton("🔙 К списку", callback_data="admin_apps")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


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
                # Создаем временного пользователя
                user = User(
                    tg_id=0,  # временный
                    first_name=name.split()[0] if name else "Гость",
                    phone=phone,
                    email=email
                )
                session.add(user)

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

            # Создаем заявку
            log.info(f"📝 Creating application for category_id: {category_id}")
            app = AppModel(
                user_id=user.id,
                category_id=category_id,
                subcategory=subcategory,
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

            # Получаем категорию для Sheets
            log.info(f"📂 Getting category {category_id}")
            cat_result = await session.execute(
                select(Category).where(Category.id == category_id)
            )
            category = cat_result.scalar_one()
            log.info(f"📂 Found category: {category.name}")

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
            select(AppModel, User, Category)
            .join(User)
            .join(Category)
            .order_by(AppModel.created_at.desc())
            .limit(50)
        )
        apps = result.all()

        applications = []
        for app, user, cat in apps:
            applications.append({
                'id': app.id,
                'client': f"{user.first_name} {user.last_name or ''}".strip(),
                'category': cat.name,
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

        # По категориям
        cat_stats = await session.execute(
            select(Category.name, func.count(AppModel.id))
            .join(AppModel)
            .group_by(Category.name)
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
    for cat_name, count in cat_stats:
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
    """Показать платежи"""
    async with async_sessionmaker() as session:
        result = await session.execute(
            select(Payment, AppModel, User)
            .join(AppModel)
            .join(User)
            .order_by(Payment.created_at.desc())
            .limit(10)
        )
        payments = result.all()

    if not payments:
        text = "💳 Нет платежей"
    else:
        text = "💳 **ПОСЛЕДНИЕ ПЛАТЕЖИ**\n\n"

        for pay, app, user in payments:
            status_emoji = {
                "pending": "⏳",
                "paid": "✅",
                "failed": "❌"
            }.get(pay.status, "❓")

            text += f"{status_emoji} #{pay.id} | {pay.amount} ₽\n"
            text += f"Заявка #{app.id} | {user.first_name}\n"
            text += f"📅 {pay.created_at.strftime('%d.%m %H:%M')}\n\n"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]

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
    """Автопостинг в канал"""
    if not CHANNEL_ID:
        return

    # Генерируем пост через AI
    topics = [
        "Как правильно оформить развод",
        "Раздел имущества при разводе",
        "Взыскание алиментов: пошаговая инструкция",
        "Что делать если не платят зарплату",
        "Защита прав при увольнении",
        "Как вступить в наследство",
        "Споры с соседями: правовые аспекты",
        "Банкротство физлиц: плюсы и минусы",
        "Как обжаловать штраф ГИБДД",
        "Защита прав потребителей: возврат товара"
    ]

    topic = random.choice(topics)

    messages = [{
        "role": "system",
        "content": "Ты юрист, пишешь полезные посты для Telegram. Используй эмодзи, делай текст структурированным."
    }, {
        "role": "user",
        "content": f"Напиши пост на тему: {topic}. Объем 300-400 символов."
    }]

    text = await generate_ai_response(messages)

    # Добавляем кнопку
    keyboard = [[
        InlineKeyboardButton("📞 Получить консультацию",
                             url=f"https://t.me/{context.bot.username}")
    ]]

    await context.bot.send_message(
        CHANNEL_ID,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ================ MAIN ================

async def post_init(application: Application):
    """Инициализация после запуска"""
    global ai_enhanced_manager

    # Инициализируем Enhanced AI
    try:
        log.info("🚀 Starting Enhanced AI initialization...")
        ai_enhanced_manager = AIEnhancedManager()
        await ai_enhanced_manager.initialize()
        print("✅ Enhanced AI initialized successfully")
        log.info("Enhanced AI system started")
    except Exception as e:
        print(f"❌ Failed to initialize Enhanced AI: {e}")
        log.error(f"Enhanced AI initialization error: {e}")
        import traceback
        log.error(f"Enhanced AI traceback: {traceback.format_exc()}")
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


async def main():
    """Точка входа"""
    # Инициализируем БД
    await init_db()

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

    app.router.add_static(
        "/webapp/", path=Path(__file__).parent.parent / "webapp")

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CallbackQueryHandler(admin_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        ai_chat
    ))

    # Джобы
    application.job_queue.run_repeating(
        autopost_job,
        interval=timedelta(hours=2),
        first=timedelta(minutes=10)
    )

    # Инициализация после запуска
    application.post_init = post_init

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

        # Уведомляем админа
        try:
            await application.bot.send_message(
                ADMIN_CHAT_ID,
                "🚀 Бот запущен!\n\n"
                "Команды:\n"
                "/admin - админ панель\n"
                "/start - приветствие"
            )
        except:
            pass

        # Держим бота живым
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
