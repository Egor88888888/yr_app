#!/usr/bin/env python3
"""Alternative entry point for Railway."""

from bot.main import main as bot_main
import os
import sys
import asyncio

print("🚀 Starting from app.py...")

# Set environment
os.environ.setdefault("PYTHONPATH", ".")

# Check env vars
if not os.getenv("BOT_TOKEN"):
    print("❌ BOT_TOKEN not set")
    sys.exit(1)

if not os.getenv("DATABASE_URL"):
    print("❌ DATABASE_URL not set")
    sys.exit(1)

# Start bot
asyncio.run(bot_main())
