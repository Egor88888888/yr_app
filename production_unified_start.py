#!/usr/bin/env python3
"""
🚀 PRODUCTION UNIFIED STARTUP SCRIPT
Railway Production Entry Point

Запускает одновременно:
- FastAPI Web Server (webapp, API, admin panel)  
- Telegram Bot (background process)
"""

import os
import sys
import asyncio
import threading
import signal
import time
import uvicorn
from multiprocessing import Process

# Set environment
os.environ.setdefault("PYTHONPATH", ".")

print("🚀 PRODUCTION UNIFIED STARTUP")
print("="*50)
print(f"📅 Starting at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🐍 Python: {sys.version}")
print(f"📍 Working Directory: {os.getcwd()}")


def validate_environment():
    """Проверка критических переменных окружения"""
    print("\n🔍 Environment Validation...")

    required_vars = {
        'BOT_TOKEN': 'Telegram Bot Token',
        'DATABASE_URL': 'Database Connection',
        'ADMIN_CHAT_ID': 'Admin Chat ID'
    }

    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"❌ {var} ({desc})")
            print(f"❌ Missing: {var}")
        else:
            print(f"✅ {var}: configured")

    if missing:
        print(f"\n🚨 CRITICAL: Missing environment variables:")
        for var in missing:
            print(f"   {var}")
        print("\n💡 Set these variables in Railway dashboard")
        return False

    print("✅ Environment validation passed")
    return True


def start_telegram_bot():
    """Запуск Telegram Bot в отдельном процессе"""
    try:
        print("\n🤖 Starting Telegram Bot...")

        # Import here to avoid circular imports
        from bot.main import main as bot_main

        # Run bot in async context
        asyncio.run(bot_main())

    except Exception as e:
        print(f"❌ Telegram Bot Error: {e}")
        import traceback
        traceback.print_exc()


def start_web_server():
    """Запуск FastAPI Web Server"""
    try:
        print("\n🌐 Starting Web Server...")

        # Import FastAPI app from app.py
        from app import app

        # Get port from environment (Railway sets this)
        port = int(os.getenv("PORT", 8000))
        host = "0.0.0.0"

        print(f"🌐 Web Server starting on {host}:{port}")

        # Start uvicorn server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            loop="asyncio"
        )

    except Exception as e:
        print(f"❌ Web Server Error: {e}")
        import traceback
        traceback.print_exc()


def signal_handler(signum, frame):
    """Graceful shutdown handler"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main production entry point"""

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Validate environment
    if not validate_environment():
        print("🚨 Environment validation failed, exiting...")
        sys.exit(1)

    try:
        # На Railway мы запускаем только Web Server
        # Bot будет запущен отдельным worker процессом
        print("\n🚀 Starting in Railway Production Mode...")
        print("📋 Mode: Web Server Only (Bot runs as separate worker)")

        start_web_server()

    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal, shutting down...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
