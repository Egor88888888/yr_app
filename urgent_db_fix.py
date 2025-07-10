#!/usr/bin/env python3
"""
🚨 URGENT DATABASE FIX: Telegram ID Overflow
Запускается один раз на Railway для исправления INTEGER → BIGINT
"""

import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


async def urgent_fix():
    """Критический фикс БД прямо на Railway"""

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL не найден!")
        return False

    # Фикс для asyncpg
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1)

    print("🚨 КРИТИЧЕСКИЙ ФИКС: Telegram ID overflow")
    print("🔧 Конвертация INTEGER → BIGINT...")

    try:
        engine = create_async_engine(DATABASE_URL)

        async with engine.begin() as conn:

            # Исправляем users.tg_id
            print("🔧 Фиксим users.tg_id...")
            await conn.execute(text("ALTER TABLE users ALTER COLUMN tg_id TYPE BIGINT;"))

            # Исправляем admins.tg_id
            print("🔧 Фиксим admins.tg_id...")
            await conn.execute(text("ALTER TABLE admins ALTER COLUMN tg_id TYPE BIGINT;"))

            print("✅ ФИКС ПРИМЕНЕН!")
            print("🎯 Тестируем проблемный ID...")

            # Тест
            await conn.execute(text("""
                INSERT INTO users (tg_id, first_name, preferred_contact, created_at, updated_at)
                VALUES (6922033571, 'Test User', 'telegram', NOW(), NOW())
                ON CONFLICT (tg_id) DO UPDATE SET updated_at = NOW()
            """))

            print("✅ Большие Telegram ID теперь работают!")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(urgent_fix())
    if result:
        print("🎉 ГОТОВО! Перезапускайте бота!")
    else:
        print("❌ Фикс не удался!")
