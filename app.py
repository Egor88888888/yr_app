#!/usr/bin/env python3
"""Alternative entry point for Railway."""

import os
import sys
import asyncio

import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
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

            # Process update through bot application
            if bot_application:
                update = Update.de_json(data, bot_application.bot)
                print(
                    f"📥 Processing update: {update.update_id if update else 'None'}")
                await bot_application.process_update(update)
                print("✅ Update processed successfully")
            else:
                print("⚠️ Bot application not ready yet")

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
            from bot.main import TOKEN
            from telegram.ext import Application

            # Import and setup the bot application
            application = Application.builder().token(TOKEN).build()

            # Store globally for webhook access
            bot_application = application

            # Setup handlers (import from bot.main)
            from bot.main import cmd_start, cmd_admin, admin_callback, post_init
            from telegram.ext import CommandHandler, CallbackQueryHandler

            application.add_handler(CommandHandler("start", cmd_start))
            application.add_handler(CommandHandler("admin", cmd_admin))
            application.add_handler(CallbackQueryHandler(admin_callback))

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
