#!/usr/bin/env python3
"""
🔥 CLEAN START - NO AZURE AI 
Absolutely clean startup script that cannot import ai_enhanced
"""

import os
import sys
import asyncio
import threading
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

# BLOCK any ai_enhanced imports
class BlockedAIEnhanced:
    def __getattr__(self, name):
        raise ImportError("🚫 AI Enhanced is BLOCKED - no Azure allowed!")

# Install import blocker  
sys.modules['bot.services.ai_enhanced'] = BlockedAIEnhanced()
sys.modules['bot.services.ai_enhanced.classification.ml_classifier'] = BlockedAIEnhanced()

print("🚫 AI Enhanced imports BLOCKED")
print("🤖 Starting CLEAN bot with OpenAI only...")

# Create simple FastAPI app for health check and webhooks
app = FastAPI(title="Clean Legal Bot")

# Mount static files for webapp
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "ai_enhanced": "blocked"})

@app.get("/test")
async def test_page():
    """Serve test Mini App page"""
    from fastapi.responses import FileResponse
    return FileResponse("webapp/test-simple.html")

@app.post("/submit")
async def submit_application(request: Request):
    """Handle application submission from Mini App"""
    try:
        data = await request.json()
        print(f"📋 Application received: {data}")
        
        # Process application data
        from bot.services.db import async_sessionmaker, Application as AppModel, User, Category
        from datetime import datetime
        from sqlalchemy import select
        
        # Create or get user (we don't have telegram user, so create temporary)
        async with async_sessionmaker() as session:
            # Try to find user by phone or create temporary
            phone = data.get('phone', '')
            name = data.get('name', 'Аноним')
            
            # Get or create category
            category_id = data.get('category_id', 1)
            
            # Create temporary user if not exists
            user_result = await session.execute(select(User).where(User.phone == phone))
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Generate unique negative tg_id for webapp users
                import random
                webapp_tg_id = -random.randint(1000000, 9999999)
                
                user = User(
                    tg_id=webapp_tg_id,  # Negative ID for webapp users
                    first_name=name,
                    phone=phone,
                    email=data.get('email', ''),
                    preferred_contact=data.get('contact_method', 'phone')
                )
                session.add(user)
                await session.flush()  # Get user.id
            
            # Create application record
            application = AppModel(
                user_id=user.id,
                category_id=category_id,
                subcategory=data.get('subcategory', ''),
                description=data.get('description', ''),
                contact_method=data.get('contact_method', 'phone'),
                contact_time=data.get('contact_time', 'any'),
                status='new'
            )
            session.add(application)
            await session.commit()
            
        print(f"✅ Application saved to database: ID {application.id}")
        
        return {"status": "success", "message": "Заявка принята! Мы свяжемся с вами в ближайшее время.", "id": application.id}
        
    except Exception as e:
        print(f"❌ Submit error: {e}")
        import traceback
        print(f"❌ Full error: {traceback.format_exc()}")
        return {"status": "error", "message": f"Ошибка при обработке заявки: {str(e)}"}

@app.post("/notify-client")
async def notify_client(request: Request):
    """Send notification to admin about new application"""
    try:
        data = await request.json()
        print(f"📨 Admin notification request: {data}")
        
        # TODO: Send telegram message to admins
        application_id = data.get('application_id')
        
        if bot_instance and bot_instance.application:
            from bot.config.settings import ADMIN_USERS
            
            # Extract user data from nested structure
            user_data = data.get('user_data', data)
            
            message = f"📋 Новая заявка #{application_id}\n"
            message += f"👤 Имя: {user_data.get('name', 'Не указано')}\n"
            message += f"📞 Телефон: {user_data.get('phone', 'Не указано')}\n"
            message += f"📧 Email: {user_data.get('email', 'Не указано')}\n"
            message += f"📂 Категория: {user_data.get('category_name', 'Не указано')}\n"
            message += f"📝 Подкатегория: {user_data.get('subcategory', 'Не указано')}\n"
            message += f"💬 Описание: {user_data.get('description', 'Не указано')}\n"
            message += f"📱 Способ связи: {user_data.get('contact_method', 'Не указано')}\n"
            message += f"⏰ Время связи: {user_data.get('contact_time', 'Не указано')}"
            
            # Send to all admins
            for admin_id in ADMIN_USERS:
                try:
                    await bot_instance.application.bot.send_message(
                        chat_id=admin_id,
                        text=message
                    )
                    print(f"✅ Notification sent to admin {admin_id}")
                except Exception as e:
                    print(f"❌ Failed to notify admin {admin_id}: {e}")
        
        return {"status": "success", "message": "Уведомления отправлены"}
        
    except Exception as e:
        print(f"❌ Notification error: {e}")
        return {"status": "error", "message": str(e)}

# Global bot instance for webhook handling
bot_instance = None

@app.post("/telegram/{token}")
async def webhook_handler(token: str, request: Request):
    """Handle Telegram webhook updates"""
    if bot_instance and bot_instance.application:
        try:
            from telegram import Update
            update_dict = await request.json()
            update = Update.de_json(update_dict, bot_instance.application.bot)
            await bot_instance.application.process_update(update)
            return {"status": "ok"}
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            return {"status": "error", "error": str(e)}
    return {"status": "bot_not_ready"}

async def start_combined():
    """Start both bot and web server concurrently"""
    try:
        print("🚀 Starting CLEAN Legal Center Bot...")
        
        # Import main bot function
        from bot.main import main
        
        # Start bot and web server concurrently
        port = int(os.getenv("PORT", 8000))
        print(f"🌐 Starting web server on port {port}")
        
        # Create uvicorn config for async startup
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None)
        server = uvicorn.Server(config)
        
        # Run bot and server concurrently with exception handling
        async def run_bot():
            try:
                global bot_instance
                from bot.main import bot
                bot_instance = bot
                await main()
            except Exception as e:
                print(f"❌ Bot error: {e}")
                
        async def run_server():
            try:
                await server.serve()
            except Exception as e:
                print(f"❌ Server error: {e}")
        
        # Start both services
        await asyncio.gather(
            run_bot(),
            run_server(),
            return_exceptions=True
        )
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(start_combined())
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)