#!/usr/bin/env python3
"""Alternative entry point for Railway."""

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

print("✅ Environment variables OK")
print(f"🔗 Database URL: {os.getenv('DATABASE_URL')[:30]}...")

# Start bot
try:
    from bot.main import main as bot_main
    print("✅ Bot module imported")
    asyncio.run(bot_main())
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
