#!/usr/bin/env python3
"""
User command and callback handlers.
Handles all user-facing interactions including commands, AI chat, consultations.
"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any

from telegram import Update, MenuButtonWebApp, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy import select

from bot.services.db import async_sessionmaker, User, Application as AppModel, Category, Admin
from bot.services.sheets import append_lead
from bot.services.ai_unified import unified_ai_service

# FORCE DISABLE Enhanced AI imports to prevent Azure calls
import os
logger = logging.getLogger(__name__)

DISABLE_ENHANCED_AI = os.getenv("DISABLE_ENHANCED_AI", "true").lower() == "true"
if not DISABLE_ENHANCED_AI:
    # Import only if not disabled
    pass  # from bot.services.ai_enhanced import AIEnhancedManager
else:
    logger.info("🚫 Enhanced AI imports BLOCKED - Azure prevention active")

from bot.services.notifications import notify_client_application_received
from bot.config.settings import (
    ADMIN_USERS, WEBAPP_URL, TARGET_CHANNEL_USERNAME,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, 
    user_request_counts, blocked_users, SYSTEM_METRICS
)
from bot.core.rate_limiter import check_rate_limit, record_user_request
from bot.core.metrics import increment_total_requests, increment_successful_requests, increment_failed_requests, increment_ai_requests
from bot.utils.helpers import extract_user_info, format_datetime, format_phone_number

logger = logging.getLogger(__name__)

# FORCE DISABLE Enhanced AI via Environment Variable
import os
FORCE_DISABLE_ENHANCED_AI = os.getenv("DISABLE_ENHANCED_AI", "true").lower() == "true"

# DISABLED Enhanced AI Manager - using unified_ai_service only
ai_enhanced_manager = None

async def initialize_ai_manager():
    """Initialize AI Manager - Enhanced AI DISABLED"""
    global ai_enhanced_manager
    if FORCE_DISABLE_ENHANCED_AI:
        logger.info("🚫 Enhanced AI FORCE DISABLED via DISABLE_ENHANCED_AI=true")
        return
    # DISABLED: Enhanced AI causes Azure API calls
    # ai_enhanced_manager = AIEnhancedManager()
    logger.info("🤖 Enhanced AI DISABLED - using unified_ai_service only")

# ================ COMMAND HANDLERS ================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Record metrics
        increment_total_requests()
        record_user_request(user.id)
        
        # Set menu button with webapp
        try:
            webapp = WebAppInfo(url=WEBAPP_URL)
            menu_button = MenuButtonWebApp(text="📄 Подать заявку", web_app=webapp)
            await context.bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)
            logger.info(f"✅ Menu button set successfully for user {user.id}")
        except Exception as e:
            logger.error(f"❌ Failed to set menu button: {e}")
        
        # Register/update user in database
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(select(User).where(User.tg_id == user.id))
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Update existing user
                    existing_user.first_name = user.first_name or existing_user.first_name
                    existing_user.last_name = user.last_name or existing_user.last_name
                    existing_user.username = user.username or existing_user.username
                    existing_user.last_activity = datetime.now()
                else:
                    # Create new user
                    new_user = User(
                        tg_id=user.id,
                        first_name=user.first_name or "Пользователь",
                        last_name=user.last_name or "",
                        username=user.username or "",
                        preferred_contact="telegram",
                        last_activity=datetime.now()
                    )
                    session.add(new_user)
                
                await session.commit()
                logger.info(f"✅ User {user.id} registered/updated in database")
        except Exception as e:
            logger.error(f"❌ Database error for user {user.id}: {e}")
        
        # Welcome message
        welcome_text = f"""🏛️ **Добро пожаловать в Юридический Центр!**

👋 Здравствуйте, {user.first_name or 'пользователь'}!

Я ваш персональный помощник по юридическим вопросам. Вы можете:

🤖 **Задать вопрос** - получить AI-консультацию
📞 **Заказать звонок** - связаться с юристом  
💰 **Узнать цены** - ознакомиться с тарифами
📄 **Подать заявку** - через Telegram Mini App

Просто напишите ваш вопрос или выберите действие ниже:"""
        
        keyboard = [
            [InlineKeyboardButton("🤖 AI Консультация", callback_data="client_flow:ai_consultation")],
            [InlineKeyboardButton("📞 Заказать звонок", callback_data="client_flow:request_call")],
            [InlineKeyboardButton("💰 Узнать цены", callback_data="client_flow:get_price")],
            [InlineKeyboardButton(f"📢 Наш канал", url=f"https://t.me/{TARGET_CHANNEL_USERNAME.replace('@', '')}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        increment_successful_requests()
        logger.info(f"✅ Start command completed for user {user.id}")
        
    except Exception as e:
        increment_failed_requests()
        logger.error(f"❌ Start command error for user {user.id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )

# ================ AI CHAT HANDLERS ================

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI chat requests"""
    
    # Safety checks
    if not update or not update.effective_user or not update.message or not update.message.text:
        logger.warning("⚠️ Invalid update data in ai_chat")
        return
    
    user = update.effective_user
    message_text = update.message.text
    
    try:
        # FIRST - Check OpenAI API key immediately
        from bot.config.settings import OPENAI_API_KEY
        import os
        api_gpt = os.getenv("API_GPT")
        logger.info(f"🔍 Environment API_GPT: {'SET' if api_gpt else 'NOT SET'}")
        logger.info(f"🔍 Settings OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
        
        if not OPENAI_API_KEY:
            logger.error("❌ OPENAI_API_KEY not configured!")
            await update.message.reply_text("❌ OpenAI API ключ не настроен. Обратитесь к администратору.")
            return
            
        logger.info(f"✅ OpenAI API key configured: {OPENAI_API_KEY[:12]}...")
        
        # Check rate limiting
        if check_rate_limit(user.id):
            await update.message.reply_text(
                f"⏰ Превышен лимит запросов ({RATE_LIMIT_REQUESTS} запросов в {RATE_LIMIT_WINDOW} секунд). "
                "Подождите немного и попробуйте снова."
            )
            return
        
        # Record request
        logger.info(f"🔄 Recording request for user {user.id}")
        increment_total_requests()
        increment_ai_requests()
        record_user_request(user.id)
        
        # Skip complex initialization and get straight to AI
        logger.info(f"🤖 DIRECTLY calling OpenAI for user {user.id}: {message_text[:50]}...")
        
        # Direct AI call without any extra steps
        try:
            ai_response_obj = await unified_ai_service.generate_legal_consultation(
                user_message=message_text,
                category="Общий юридический вопрос"
            )
            ai_response = ai_response_obj.content
            logger.info(f"✅ OpenAI SUCCESS for user {user.id}: {ai_response[:100]}...")
            
            # Send response directly
            full_response = f"{ai_response}\n\n📞 Для детальной консультации нажмите /start"
            await update.message.reply_text(full_response)
            logger.info(f"✅ Response sent to user {user.id}")
            
        except Exception as e:
            logger.error(f"❌ OpenAI FAILED for user {user.id}: {e}")
            logger.error(f"❌ Full error: {traceback.format_exc()}")
            await update.message.reply_text(f"❌ Ошибка AI: {str(e)}")
        
        increment_successful_requests()
        logger.info(f"✅ AI chat completed for user {user.id}")
        
    except Exception as e:
        increment_failed_requests()
        logger.error(f"❌ AI chat error for user {user.id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте позже."
        )

async def enhanced_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced message handler with category detection"""
    
    logger.info(f"🔍 ENHANCED HANDLER started for user: {update.effective_user.id if update and update.effective_user else 'Unknown'}")
    
    # Safety checks
    if not update or not update.effective_user or not update.message or not update.message.text:
        logger.warning("⚠️ Invalid update data in enhanced_message_handler")
        return
    
    user = update.effective_user
    message_text = update.message.text
    
    logger.info(f"🔍 ENHANCED HANDLER processing: User {user.id}, Message: {message_text[:50]}...")
    
    try:
        # Process for all users (admins and regular users)
        logger.info(f"🤖 Starting AI processing for user {user.id}")
        
        # Detect legal category
        detected_category = await detect_category(message_text)
        
        # Process with AI
        await ai_chat(update, context)
        
        # Log category detection
        if detected_category:
            logger.info(f"Detected category '{detected_category}' for user {user.id}")
        
    except Exception as e:
        logger.error(f"Enhanced message handler error: {e}")
        # Safety check before fallback
        if update and update.message and update.message.text:
            await ai_chat(update, context)  # Fallback to regular AI chat

async def message_handler_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route messages based on user type and context"""
    
    logger.info(f"🔍 RECEIVED MESSAGE from user: {update.effective_user.id if update and update.effective_user else 'Unknown'}")
    
    # Safety checks
    if not update or not update.effective_user:
        logger.warning("⚠️ Received update without user information")
        return
        
    if not update.message or not update.message.text:
        logger.warning("⚠️ Received update without message text")
        return
    
    user = update.effective_user
    message_text = update.message.text
    
    logger.info(f"🔍 Processing message from user {user.id}: {message_text[:50]}...")
    
    # Admin check - BUT STILL ALLOW AI PROCESSING
    if user.id in ADMIN_USERS:
        logger.info(f"👤 Admin user {user.id} - processing with AI anyway")
    else:
        logger.info(f"👤 Regular user {user.id}")
    
    logger.info(f"🤖 Routing to AI handler for user {user.id}")
    # All users get AI processing
    await enhanced_message_handler(update, context)

# ================ CALLBACK HANDLERS ================

async def client_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle client flow callbacks"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    try:
        await query.answer()
        
        # Parse callback data
        if not data.startswith("client_flow:"):
            return
        
        action = data.split(":", 1)[1]
        
        # Route to appropriate handler
        if action == "request_call":
            await handle_request_call(update, context)
        elif action == "ai_consultation":
            await handle_chat_consultation(update, context)
        elif action == "get_price":
            await handle_get_price(update, context)
        elif action.startswith("consultation_category:"):
            category = action.split(":", 1)[1]
            await handle_consultation_category(update, context, category)
        elif action == "back_to_chat":
            await handle_back_to_chat(update, context)
        elif action == "enter_phone":
            await handle_enter_phone(update, context)
        elif action == "submit_call_request":
            await handle_submit_call_request(update, context)
        else:
            logger.warning(f"Unknown client flow action: {action}")
            
    except Exception as e:
        logger.error(f"Client flow callback error: {e}")
        await query.message.reply_text("Произошла ошибка. Попробуйте снова.")

async def handle_request_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle call request"""
    query = update.callback_query
    
    text = """📞 **Заказать обратный звонок**

Наш юрист свяжется с вами в удобное время для подробной консультации.

Укажите ваш номер телефона:"""
    
    keyboard = [
        [InlineKeyboardButton("📱 Ввести номер", callback_data="client_flow:enter_phone")],
        [InlineKeyboardButton("🔙 Назад", callback_data="client_flow:back_to_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_chat_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat consultation selection"""
    query = update.callback_query
    
    text = """🤖 **AI Консультация**

Выберите категорию вашего вопроса для более точной консультации:"""
    
    # Get categories from database
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(select(Category))
            categories = result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to load categories: {e}")
        categories = []
    
    keyboard = []
    for category in categories[:8]:  # Limit to 8 categories
        keyboard.append([InlineKeyboardButton(
            category.name, 
            callback_data=f"client_flow:consultation_category:{category.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="client_flow:back_to_chat")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle price information request"""
    query = update.callback_query
    
    text = """💰 **Наши тарифы**

📋 **Консультация** - 3,000 ₽
└ Устная консультация до 1 часа

📄 **Анализ документов** - 5,000 ₽  
└ Проверка и заключение по документам

⚖️ **Представительство** - от 15,000 ₽
└ Ведение дела в суде

📝 **Составление документов** - от 7,000 ₽
└ Договоры, иски, жалобы

🎯 **Комплексное сопровождение** - индивидуально
└ Полное ведение юридических вопросов

*Точная стоимость определяется после консультации"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Заказать звонок", callback_data="client_flow:request_call")],
        [InlineKeyboardButton("🔙 Назад", callback_data="client_flow:back_to_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_consultation_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: str):
    """Handle specific consultation category"""
    query = update.callback_query
    
    try:
        # Get category info
        async with async_sessionmaker() as session:
            result = await session.execute(select(Category).where(Category.id == int(category_id)))
            category = result.scalar_one_or_none()
        
        if not category:
            await query.message.reply_text("Категория не найдена.")
            return
        
        text = f"""📋 **{category.name}**

{category.description}

Опишите вашу ситуацию подробно, и наш AI-консультант даст первичную рекомендацию:"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 К категориям", callback_data="client_flow:ai_consultation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Store category context for next message
        context.user_data["consultation_category"] = category_id
        
    except Exception as e:
        logger.error(f"Consultation category error: {e}")
        await query.message.reply_text("Произошла ошибка. Попробуйте снова.")

async def handle_back_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to main chat menu"""
    query = update.callback_query
    user = query.from_user
    
    welcome_text = f"""🏛️ **Юридический Центр**

👋 {user.first_name or 'Пользователь'}, выберите действие:"""
    
    keyboard = [
        [InlineKeyboardButton("🤖 AI Консультация", callback_data="client_flow:ai_consultation")],
        [InlineKeyboardButton("📞 Заказать звонок", callback_data="client_flow:request_call")],
        [InlineKeyboardButton("💰 Узнать цены", callback_data="client_flow:get_price")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number entry"""
    query = update.callback_query
    
    text = """📱 **Введите ваш номер телефона**

Отправьте сообщение с номером телефона в формате:
+7 (999) 123-45-67 или 8 999 123 45 67

После этого мы свяжемся с вами для консультации."""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="client_flow:request_call")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set context for phone input
    context.user_data["waiting_for_phone"] = True

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input from user"""
    user = update.effective_user
    phone = update.message.text.strip()
    
    # Validate phone format
    import re
    phone_clean = re.sub(r'[^\d]', '', phone)
    if not (len(phone_clean) >= 10 and len(phone_clean) <= 11):
        await update.message.reply_text(
            "❌ Неверный формат номера. Введите номер в формате +7 (999) 123-45-67"
        )
        return
    
    # Store phone and confirm
    context.user_data["phone"] = phone
    context.user_data["waiting_for_phone"] = False
    
    formatted_phone = format_phone_number(phone)
    
    text = f"""✅ **Заявка на обратный звонок**

📱 Номер телефона: {formatted_phone}
👤 Имя: {user.first_name or 'Не указано'}

Подтвердите заявку:"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="client_flow:submit_call_request")],
        [InlineKeyboardButton("✏️ Изменить номер", callback_data="client_flow:enter_phone")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="client_flow:back_to_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_submit_call_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle call request submission"""
    query = update.callback_query
    user = query.from_user
    
    phone = context.user_data.get("phone")
    if not phone:
        await query.message.reply_text("❌ Номер телефона не указан. Попробуйте снова.")
        return
    
    try:
        # Save to database
        async with async_sessionmaker() as session:
            # Create application
            new_app = AppModel(
                user_id=user.id,
                category_id=1,  # Default category
                description=f"Заявка на обратный звонок",
                phone=phone,
                status="new",
                created_at=datetime.now()
            )
            session.add(new_app)
            await session.commit()
            
            # Save to Google Sheets if available
            try:
                lead_data = {
                    "timestamp": datetime.now().isoformat(),
                    "name": user.first_name or "Не указано",
                    "phone": phone,
                    "service": "Обратный звонок",
                    "telegram_id": user.id,
                    "username": user.username or "Не указано"
                }
                await append_lead(lead_data)
            except Exception as e:
                logger.error(f"Failed to save to Google Sheets: {e}")
            
            # Notify admins
            await notify_all_admins(f"""📞 **Новая заявка на звонок**

👤 {user.first_name or 'Пользователь'} (@{user.username or 'без username'})
📱 {format_phone_number(phone)}
🆔 ID: {user.id}
🕐 {format_datetime(datetime.now())}""")
            
            # Notify client
            try:
                await notify_client_application_received(user.id, context.bot)
            except Exception as e:
                logger.error(f"Failed to send client notification: {e}")
            
            # Success message
            await query.edit_message_text(
                f"""✅ **Заявка принята!**

Ваша заявка на обратный звонок принята.
Наш юрист свяжется с вами в ближайшее время.

📱 Номер: {format_phone_number(phone)}
🕐 Время подачи: {format_datetime(datetime.now())}

Спасибо за обращение! 🙏""",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Call request submission error: {e}")
        await query.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

# ================ HELPER FUNCTIONS ================

async def notify_all_admins(message: str, keyboard: InlineKeyboardMarkup = None):
    """Notify all admins with message"""
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(select(Admin))
            admins = result.scalars().all()
            
            for admin in admins:
                try:
                    # Use context.bot if available, otherwise this won't work
                    # This function needs to be called from a handler with access to bot
                    pass  # Implementation depends on having bot instance
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin.tg_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Failed to notify admins: {e}")

async def notify_all_admins_with_keyboard(message: str, keyboard: InlineKeyboardMarkup):
    """Notify all admins with inline keyboard"""
    await notify_all_admins(message, keyboard)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USERS

def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited (legacy function)"""
    return check_rate_limit(user_id)

def log_request(user_id: int, request_type: str, success: bool = True):
    """Log request for monitoring"""
    increment_total_requests()
    if success:
        increment_successful_requests()
    else:
        increment_failed_requests()
    
    if request_type == "ai":
        increment_ai_requests()
    
    logger.info(f"Request logged: user={user_id}, type={request_type}, success={success}")

async def detect_category(message_text: str) -> str:
    """Detect legal category from message text"""
    keywords = {
        "business_law": ["бизнес", "предприниматель", "ооо", "ип", "регистрация", "налоги"],
        "family_law": ["развод", "алименты", "брак", "опека", "усыновление"],
        "real_estate": ["квартира", "дом", "недвижимость", "аренда", "покупка", "продажа"],
        "criminal_law": ["уголовное", "преступление", "суд", "штраф", "наказание"],
        "labor_law": ["работа", "увольнение", "зарплата", "трудовой", "отпуск"]
    }
    
    message_lower = message_text.lower()
    
    for category, words in keywords.items():
        if any(word in message_lower for word in words):
            return category
    
    return "other"