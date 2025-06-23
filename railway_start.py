#!/usr/bin/env python3
"""Startup script for Railway deployment."""

import os
import sys
import asyncio
from pathlib import Path


def check_env():
    """Check required environment variables"""
    required = ["BOT_TOKEN", "DATABASE_URL", "ADMIN_CHAT_ID"]
    missing = []

    for var in required:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(
            f"❌ Missing required environment variables: {', '.join(missing)}")
        print("📖 See SETUP.md for configuration instructions")
        sys.exit(1)

    print("✅ All required environment variables set")


def main():
    """Main entry point"""
    print("🚀 Starting Telegram Bot on Railway...")

    # Check environment
    check_env()

    # Import and run the bot
    try:
        from bot.main import main as bot_main
        asyncio.run(bot_main())
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
