#!/usr/bin/env python3
"""Railway startup script."""

import os
import sys
import asyncio


def main():
    print("🚀 Starting Telegram Bot...")

    # Check critical env vars
    if not os.getenv("BOT_TOKEN"):
        print("❌ BOT_TOKEN not set")
        sys.exit(1)

    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    # Start bot
    from bot.main import main as bot_main
    asyncio.run(bot_main())


if __name__ == "__main__":
    main()
