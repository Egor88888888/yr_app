#!/usr/bin/env python3
"""
МАКСИМАЛЬНО УПРОЩЕННАЯ АДМИН ПАНЕЛЬ
Только критически важные функции, никакого избыточного кода!
"""

import logging
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from sqlalchemy import select, func

from bot.services.db import async_sessionmaker, User, Application as AppModel
from bot.services.autopost_unified import autopost_system
from bot.config.settings import ADMIN_USERS, TARGET_CHANNEL_ID, is_admin
from bot.core.metrics import get_system_stats

logger = logging.getLogger(__name__)

# ================ ОСНОВНЫЕ АДМИН КОМАНДЫ ================

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное админ меню - ТОЛЬКО основные функции"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton("📝 Создать пост", callback_data="admin:create_post")],
        [InlineKeyboardButton("⚡ Автопостинг", callback_data="admin:autopost")],
        [InlineKeyboardButton("🔧 Система", callback_data="admin:system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠️ **АДМИН ПАНЕЛЬ**\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка админ callbacks"""
    query = update.callback_query
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("❌ Доступ запрещен")
        return
    
    await query.answer()
    data = query.data.split(":", 1)[1]
    
    if data == "stats":
        await show_stats(query, context)
    elif data == "create_post":
        await create_post_menu(query, context)
    elif data == "autopost":
        await autopost_menu(query, context)
    elif data == "system":
        await system_menu(query, context)
    elif data == "autopost_toggle":
        await toggle_autopost(query, context)
    elif data == "back":
        await back_to_main(query, context)

# ================ СТАТИСТИКА ================

async def show_stats(query, context):
    """Показать базовую статистику"""
    try:
        async with async_sessionmaker() as session:
            # Пользователи
            users_count = await session.execute(select(func.count(User.id)))
            total_users = users_count.scalar()
            
            # Заявки
            apps_count = await session.execute(select(func.count(AppModel.id)))
            total_apps = apps_count.scalar()
            
            # Системные метрики
            system_stats = get_system_stats()
            
            # Автопостинг
            autopost_stats = autopost_system.get_stats() if autopost_system else {}
        
        stats_text = f"""📊 **СТАТИСТИКА**

👥 **Пользователи:** {total_users}
📋 **Заявки:** {total_apps}

🤖 **Система:**
• Запросов: {system_stats.get('total_requests', 0)}
• Успешных: {system_stats.get('successful_requests', 0)}
• AI запросов: {system_stats.get('ai_requests', 0)}

📢 **Автопостинг:**
• Постов: {autopost_stats.get('total_posts', 0)}
• Успешных: {autopost_stats.get('successful_posts', 0)}
• Статус: {'🟢 Работает' if autopost_stats.get('is_running') else '🔴 Остановлен'}"""
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin:back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await query.edit_message_text("❌ Ошибка получения статистики")

# ================ СОЗДАНИЕ ПОСТОВ ================

async def create_post_menu(query, context):
    """Меню создания поста"""
    text = """📝 **СОЗДАТЬ ПОСТ**

Напишите тему для поста, и я создам контент с помощью AI.

Например: "Права потребителей при возврате товара" """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin:back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Устанавливаем режим ожидания темы поста
    context.user_data["admin_state"] = "waiting_post_topic"

async def handle_post_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка темы поста от админа"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    if context.user_data.get("admin_state") != "waiting_post_topic":
        return
    
    topic = update.message.text.strip()
    
    try:
        await update.message.reply_text("⏳ Создаю пост...")
        
        # Создаем пост через unified autopost system
        if autopost_system:
            success = await autopost_system.create_manual_post(topic)
            
            if success:
                await update.message.reply_text(f"✅ Пост создан и опубликован!\n\nТема: {topic}")
            else:
                await update.message.reply_text("❌ Ошибка создания поста")
        else:
            await update.message.reply_text("❌ Система автопостинга недоступна")
            
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        await update.message.reply_text("❌ Ошибка создания поста")
    
    # Сбрасываем состояние
    context.user_data.pop("admin_state", None)

# ================ АВТОПОСТИНГ ================

async def autopost_menu(query, context):
    """Меню управления автопостингом"""
    if not autopost_system:
        await query.edit_message_text("❌ Система автопостинга недоступна")
        return
    
    stats = autopost_system.get_stats()
    is_running = stats.get('is_running', False)
    
    text = f"""📢 **АВТОПОСТИНГ**

📊 **Статистика:**
• Всего постов: {stats.get('total_posts', 0)}
• Успешных: {stats.get('successful_posts', 0)}
• Заблокировано дублей: {stats.get('deduplication_blocks', 0)}

⚡ **Статус:** {'🟢 Работает' if is_running else '🔴 Остановлен'}"""
    
    toggle_text = "🔴 Остановить" if is_running else "🟢 Запустить"
    keyboard = [
        [InlineKeyboardButton(toggle_text, callback_data="admin:autopost_toggle")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin:back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def toggle_autopost(query, context):
    """Переключение автопостинга"""
    if not autopost_system:
        await query.answer("❌ Система недоступна")
        return
    
    try:
        if autopost_system.is_running:
            await autopost_system.stop_autopost_loop()
            await query.answer("🔴 Автопостинг остановлен")
        else:
            await autopost_system.start_autopost_loop()
            await query.answer("🟢 Автопостинг запущен")
        
        # Обновляем меню
        await autopost_menu(query, context)
        
    except Exception as e:
        logger.error(f"Error toggling autopost: {e}")
        await query.answer("❌ Ошибка")

# ================ СИСТЕМА ================

async def system_menu(query, context):
    """Системная информация"""
    try:
        stats = get_system_stats()
        
        text = f"""🔧 **СИСТЕМА**

⏱️ **Работает:** {stats.get('uptime_human', 'N/A')}
📈 **Запросов в минуту:** {stats.get('requests_per_minute', 0)}
✅ **Успешность:** {stats.get('success_rate', 0)}%

🤖 **AI запросов:** {stats.get('ai_requests', 0)}
📊 **Всего запросов:** {stats.get('total_requests', 0)}

💾 **Канал:** {TARGET_CHANNEL_ID}"""
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin:back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error showing system info: {e}")
        await query.edit_message_text("❌ Ошибка получения системной информации")

# ================ НАВИГАЦИЯ ================

async def back_to_main(query, context):
    """Возврат в главное меню"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton("📝 Создать пост", callback_data="admin:create_post")],
        [InlineKeyboardButton("⚡ Автопостинг", callback_data="admin:autopost")],
        [InlineKeyboardButton("🔧 Система", callback_data="admin:system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛠️ **АДМИН ПАНЕЛЬ**\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ================ РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ================

def register_simple_admin_handlers(app: Application):
    """Регистрация упрощенных админ хендлеров"""
    
    # Команды
    app.add_handler(CommandHandler("admin", cmd_admin))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(
        admin_callback,
        pattern=r"^admin:"
    ))
    
    # Обработка тем постов от админов
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=list(ADMIN_USERS)),
        handle_post_topic
    ))
    
    logger.info("✅ Simple admin handlers registered")

# ================ NOTIFICATION HELPERS ================

async def notify_admins(message: str, bot):
    """Уведомление всех админов"""
    for admin_id in ADMIN_USERS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🔔 **УВЕДОМЛЕНИЕ**\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

async def alert_critical_error(error_msg: str, bot):
    """Критическое уведомление админов"""
    alert = f"🚨 **КРИТИЧЕСКАЯ ОШИБКА**\n\n{error_msg}\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"
    await notify_admins(alert, bot)