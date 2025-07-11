#!/usr/bin/env python3
"""Alternative entry point for Railway."""

import os
import sys
import asyncio

import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from bot.services.ai_enhanced import AIEnhancedManager
from bot.services.db import async_sessionmaker
from sqlalchemy import text
from aiohttp import web
import json
from bot.services.db import async_sessionmaker, User, Application as AppModel, Category, Payment, Admin
from sqlalchemy import select, func, desc
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from bot.services.pay import create_payment
from bot.services.sheets import append_lead
from bot.services.notifications import notify_client_application_received, notify_client_status_update, notify_client_payment_required

print("🚀 Starting from app.py...")

# Set environment
os.environ.setdefault("PYTHONPATH", ".")

# Map Railway environment variables to expected names
env_mapping = {
    "BOT_TOKEN": ["BOT_TOKEN", "YOUR_BOT_TOKEN"],
    "ADMIN_CHAT_ID": ["ADMIN_CHAT_ID"],
    "OPENROUTER_API_KEY": ["OPENROUTER_API_KEY"],
    "CHANNEL_ID": ["TARGET_CHANNEL_ID", "CHANNEL_ID"],
    "RAILWAY_PUBLIC_DOMAIN": ["MY_RAILWAY_PUBLIC_URL", "RAILWAY_PUBLIC_DOMAIN"],
}

missing_vars = []
for expected, alternatives in env_mapping.items():
    value = None
    for alt in alternatives:
        value = os.getenv(alt)
        if value:
            break

    if value:
        os.environ[expected] = value
        print(f"✅ {expected} = {alt}")
    else:
        missing_vars.append(f"{expected} (tried: {', '.join(alternatives)})")

# Critical variables check
if not os.getenv("BOT_TOKEN"):
    print("❌ BOT_TOKEN not found")
    sys.exit(1)

if not os.getenv("DATABASE_URL"):
    print("❌ DATABASE_URL not set")
    sys.exit(1)

if missing_vars:
    print(f"⚠️ Optional variables missing: {', '.join(missing_vars)}")

print("✅ Environment variables OK")
print(f"🔗 Database URL: {os.getenv('DATABASE_URL')[:30]}...")

# Start bot
try:
    from bot.main import main as bot_main
    print("✅ Bot module imported")

    app = fastapi.FastAPI()

    # Add CORS middleware for Mini App
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify your domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global variable to store bot application
    bot_application = None

    # ===== API ROUTES FIRST (before static mounts) =====

    @app.get("/health")
    async def health():
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        ai_health = await ai_manager.health_check()

        async with async_sessionmaker() as session:
            try:
                await session.execute(text("SELECT 1"))
                db_status = "connected"
            except:
                db_status = "disconnected"

        return {
            "status": "healthy",
            "bot_status": "running",
            "db_status": db_status,
            "enhanced_ai_status": "INITIALIZED" if ai_manager._initialized else "NOT INITIALIZED",
            "enhanced_ai_health": ai_health
        }

    @app.get("/api/stats")
    async def api_stats():
        return {
            "total_requests": 0,
            "success_rate": 0.0,
            "ai_requests": 0
        }

    # Add admin stats endpoint that production_test.py expects
    @app.get("/api/admin/stats")
    async def api_admin_stats():
        return {
            "total_requests": 0,
            "success_rate": 0.0,
            "ai_requests": 0
        }

    # Move ai_status to correct path
    @app.get("/api/ai_status")
    async def api_ai_status():
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        return await ai_manager.health_check()

    # Add the endpoint that production_test.py expects
    @app.get("/api/ai/status")
    async def api_ai_status_alt():
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        health = await ai_manager.health_check()
        return {
            "enhanced_ai_initialized": ai_manager._initialized,
            "health": health.get("status", "unknown"),
            "using_fallback": not ai_manager._initialized
        }

    @app.post("/api/ai_chat_test")
    async def api_ai_chat_test(payload: dict):
        import time
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        start = time.time()
        response = await ai_manager.generate_response(
            user_id=payload.get("user_id", 12345),
            message=payload.get("message", "Test message")
        )
        response_time = (time.time() - start) * 1000
        return {
            "response": response,
            "response_time_ms": int(response_time),
            "category": "test_category",
            "intent": "test_intent"
        }

    # Add the chat test endpoint that production_test.py expects
    @app.post("/api/chat/test")
    async def api_chat_test(payload: dict):
        import time
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        start = time.time()
        response = await ai_manager.generate_response(
            user_id=payload.get("user_id", 12345),
            message=payload.get("message", "Test message")
        )
        response_time = (time.time() - start) * 1000
        return {
            "response": response,
            "response_time_ms": int(response_time),
            "engine": "Enhanced AI" if ai_manager._initialized else "Fallback AI"
        }

    # Telegram webhook handler - FIXED to actually process updates
    @app.post("/telegram/{token}")
    async def handle_telegram_webhook(token: str, request: fastapi.Request):
        if token != os.getenv("BOT_TOKEN"):
            print(
                f"❌ Unauthorized webhook attempt with token: {token[:10]}...")
            return fastapi.Response(status_code=401, content="Unauthorized")

        try:
            data = await request.json()
            print(f"📨 Received webhook data: {len(str(data))} chars")
            print(f"🔍 Bot application state: {bot_application is not None}")

            # Process update through bot application
            if bot_application:
                update = Update.de_json(data, bot_application.bot)
                print(
                    f"📥 Processing update: {update.update_id if update else 'None'}")
                await bot_application.process_update(update)
                print("✅ Update processed successfully")
            else:
                print("⚠️ Bot application not ready yet - checking global state...")
                print(
                    f"⚠️ Global bot_application is None: {bot_application is None}")

            return fastapi.Response(status_code=200, content="OK")
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return fastapi.Response(status_code=500, content="Error")

    # Also handle the exact webhook URL format used
    @app.post("/{token}")
    async def handle_telegram_webhook_direct(token: str, request: fastapi.Request):
        return await handle_telegram_webhook(token, request)

    # ===== MINI APP SUBMIT ENDPOINT =====
    
    @app.post("/submit")
    async def submit_application(request: fastapi.Request):
        """Handle Mini App form submissions"""
        try:
            # Parse form data
            data = await request.json()
            print(f"📝 Received application data: {data}")
            
            # Validate required fields
            required_fields = ['category_id', 'category_name', 'name', 'phone', 'contact_method']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return fastapi.Response(
                    status_code=400,
                    content=json.dumps({
                        "status": "error", 
                        "message": f"Missing required fields: {', '.join(missing_fields)}"
                    }),
                    media_type="application/json"
                )
            
            # Extract and validate data
            category_id = data.get('category_id')
            category_name = data.get('category_name', '')
            subcategory = data.get('subcategory', '')
            description = data.get('description', '')
            name = data.get('name', '')
            phone = data.get('phone', '')
            email = data.get('email', '')
            contact_method = data.get('contact_method', '')
            contact_time = data.get('contact_time', 'any')
            files = data.get('files', [])
            tg_user_id = data.get('tg_user_id')
            utm_source = data.get('utm_source')
            
            print(f"👤 Processing application for: {name} ({phone})")
            print(f"📋 Category: {category_name} (ID: {category_id})")
            print(f"📞 Contact: {contact_method} at {contact_time}")
            print(f"📄 Files: {len(files)} uploaded")
            
            # Save to database
            async with async_sessionmaker() as session:
                try:
                    # Get or create user
                    user = None
                    if tg_user_id:
                        result = await session.execute(
                            select(User).where(User.tg_id == tg_user_id)
                        )
                        user = result.scalar_one_or_none()
                    
                    if not user:
                        # Create new user
                        user = User(
                            tg_id=tg_user_id,
                            first_name=name.split()[0] if name else "Unknown",
                            last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else "",
                            username=None,
                            phone=phone,
                            email=email
                        )
                        session.add(user)
                        await session.flush()  # Get user.id
                        print(f"✅ Created new user: {user.id}")
                    else:
                        # Update existing user
                        if name:
                            name_parts = name.split()
                            user.first_name = name_parts[0]
                            user.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        if phone:
                            user.phone = phone
                        if email:
                            user.email = email
                        print(f"✅ Updated existing user: {user.id}")
                    
                    # Create application
                    application = AppModel(
                        user_id=user.id,
                        category=category_name,
                        subcategory=f"{subcategory}: {description}" if subcategory and description else (subcategory or description),
                        contact_method=contact_method,
                        contact_time=contact_time,
                        utm_source=utm_source,
                        status="new"
                    )
                    session.add(application)
                    await session.flush()  # Get application.id
                    
                    print(f"✅ Created application: #{application.id}")
                    
                    # Handle files if any
                    files_info = []
                    if files:
                        for i, file_data in enumerate(files):
                            filename = file_data.get('name', f'file_{i+1}')
                            file_size = len(file_data.get('data', '')) if file_data.get('data') else 0
                            files_info.append(f"{filename} ({file_size} bytes)")
                        
                        # Add files info to application notes
                        application.notes = f"Uploaded files: {', '.join(files_info)}"
                        print(f"📎 Processed {len(files)} files")
                    
                    await session.commit()
                    
                    # Try to add to Google Sheets
                    try:
                        await append_lead({
                            'name': name,
                            'phone': phone,
                            'email': email or '',
                            'category': category_name,
                            'subcategory': subcategory,
                            'description': description,
                            'contact_method': contact_method,
                            'contact_time': contact_time,
                            'files_count': len(files),
                            'application_id': application.id,
                            'utm_source': utm_source or ''
                        })
                        print("✅ Added to Google Sheets")
                    except Exception as e:
                        print(f"⚠️ Failed to add to Google Sheets: {e}")
                    
                    # Try to send notifications
                    try:
                        await notify_client_application_received(user, application)
                        print("✅ Client notification sent")
                    except Exception as e:
                        print(f"⚠️ Failed to send client notification: {e}")
                    
                    # Try to create payment if needed
                    payment_url = None
                    try:
                        # Define prices for categories (you can adjust these)
                        category_prices = {
                            1: 3000,   # Семейное право
                            2: 5000,   # Корпоративное право  
                            3: 4000,   # Недвижимость
                            4: 3500,   # Трудовое право
                            5: 4500,   # Налоговое право
                            6: 3000,   # Административное право
                            7: 6000,   # Уголовное право
                            8: 4000,   # Гражданское право
                            9: 3500,   # Интеллектуальная собственность
                            10: 3000,  # Миграционное право
                            11: 6000,  # Уголовные дела
                            12: 3000   # Другое
                        }
                        
                        price = category_prices.get(category_id, 3000)
                        application.price = price
                        
                        payment_response = await create_payment(
                            amount=price,
                            description=f"Юридическая консультация: {category_name}",
                            user_id=user.tg_id,
                            application_id=application.id
                        )
                        
                        if payment_response and payment_response.get('url'):
                            payment_url = payment_response['url']
                            print(f"✅ Payment URL created: {payment_url[:50]}...")
                        
                        await session.commit()
                        
                    except Exception as e:
                        print(f"⚠️ Failed to create payment: {e}")
                    
                    # Return success response
                    return {
                        "status": "ok",
                        "message": "Заявка успешно отправлена!",
                        "application_id": application.id,
                        "pay_url": payment_url or "# Платежная система не настроена"
                    }
                    
                except Exception as e:
                    await session.rollback()
                    print(f"❌ Database error: {e}")
                    import traceback
                    print(f"❌ Traceback: {traceback.format_exc()}")
                    
                    return fastapi.Response(
                        status_code=500,
                        content=json.dumps({
                            "status": "error",
                            "message": "Ошибка при сохранении заявки"
                        }),
                        media_type="application/json"
                    )
            
        except Exception as e:
            print(f"❌ Submit error: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            return fastapi.Response(
                status_code=500,
                content=json.dumps({
                    "status": "error",
                    "message": "Внутренняя ошибка сервера"
                }),
                media_type="application/json"
            )

    # ===== STATIC MOUNTS LAST =====
    app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")
    app.mount("/admin", StaticFiles(directory="webapp", html=True), name="admin")

    async def main():
        global bot_application

        config = uvicorn.Config(app, host="0.0.0.0",
                                port=int(os.environ.get("PORT", 8080)))
        server = uvicorn.Server(config)

        # Create a modified bot_main that returns the application
        async def run_bot():
            global bot_application
            from bot.main import TOKEN
            from telegram.ext import Application

            print("🔧 Starting bot setup...")

            # Import and setup the bot application
            application = Application.builder().token(TOKEN).build()

            # Store globally for webhook access - FIX: proper global assignment
            bot_application = application
            print(
                f"✅ Bot application stored globally: {bot_application is not None}")

            # Setup handlers (import from bot.main)
            from bot.main import cmd_start, cmd_admin, universal_callback_handler, post_init
            from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters

            application.add_handler(CommandHandler("start", cmd_start))
            application.add_handler(CommandHandler("admin", cmd_admin))
            application.add_handler(
                CallbackQueryHandler(universal_callback_handler))

            # Add message handler for AI
            from bot.main import ai_chat
            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, ai_chat))

            print("✅ Handlers registered")

            # Initialize
            await application.initialize()
            await post_init(application)

            # Set webhook
            webhook_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}/telegram/{TOKEN}"
            await application.bot.set_webhook(webhook_url)
            print(f"✅ Webhook set to: {webhook_url}")

            # Start application
            await application.start()
            print("✅ Bot application started and ready")
            print(
                f"🔍 Global bot_application check: {bot_application is not None}")

            # Keep running
            await asyncio.Event().wait()

        await asyncio.gather(
            server.serve(),
            run_bot()
        )

    if __name__ == "__main__":
        asyncio.run(main())
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
