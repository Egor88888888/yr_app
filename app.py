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

    app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")
    app.mount("/admin", StaticFiles(directory="webapp", html=True), name="admin")

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

    @app.get("/ai_status")
    async def ai_status():
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        return await ai_manager.health_check()

    @app.post("/ai_chat_test")
    async def ai_chat_test(payload: dict):
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
            "category": "test_category",  # Placeholder, adapt if needed
            "intent": "test_intent"
        }

    @app.get("/api/stats")
    async def api_stats():
        return {
            "total_requests": 0,
            "success_rate": 0.0,
            "ai_requests": 0
        }

    async def main():
        config = uvicorn.Config(app, host="0.0.0.0",
                                port=int(os.environ.get("PORT", 8080)))
        server = uvicorn.Server(config)

        await asyncio.gather(
            server.serve(),
            bot_main()
        )

    if __name__ == "__main__":
        asyncio.run(main())
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
