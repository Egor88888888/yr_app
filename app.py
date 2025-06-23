#!/usr/bin/env python3
"""Alternative entry point for Railway."""

import os
import sys
import asyncio

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
    asyncio.run(bot_main())
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
