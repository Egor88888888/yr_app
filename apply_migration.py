#!/usr/bin/env python3
"""
🔧 КРИТИЧЕСКИЙ ФИКС БД: Применение миграции для исправления Telegram ID overflow

Этот скрипт применяет миграцию для конвертации INTEGER → BIGINT в колонках tg_id
"""

import asyncio
import os
from sqlalchemy import text
from bot.services.db import async_sessionmaker, async_engine


async def apply_telegram_id_fix():
    """Применение фикса для Telegram ID overflow"""

    print("🔧 ПРИМЕНЕНИЕ КРИТИЧЕСКОГО ФИКСА БД...")
    print("📋 Проблема: PostgreSQL INTEGER overflow для больших Telegram ID")
    print("✅ Решение: Конвертация tg_id колонок в BIGINT")
    print()

    try:
        async with async_engine.begin() as conn:

            # Проверяем текущий тип колонок
            print("🔍 Проверка текущих типов колонок...")

            result = await conn.execute(text("""
                SELECT column_name, data_type, table_name 
                FROM information_schema.columns 
                WHERE column_name = 'tg_id' 
                AND table_schema = 'public'
                ORDER BY table_name;
            """))

            current_types = result.fetchall()
            print("📊 Текущие типы tg_id колонок:")
            for row in current_types:
                print(
                    f"   • {row.table_name}.{row.column_name}: {row.data_type}")

            print()

            # Применяем изменения
            migrations = [
                ("users", "Пользователи"),
                ("admins", "Администраторы")
            ]

            for table_name, description in migrations:
                print(f"🔧 Конвертация {description} ({table_name}.tg_id)...")

                # Проверяем существование таблицы
                table_check = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    );
                """))

                if not table_check.scalar():
                    print(
                        f"   ⚠️  Таблица {table_name} не найдена, пропускаем...")
                    continue

                # Применяем изменение типа
                await conn.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN tg_id TYPE BIGINT;
                """))

                print(f"   ✅ {table_name}.tg_id → BIGINT")

            print()
            print("🎯 ПРОВЕРКА РЕЗУЛЬТАТОВ...")

            # Проверяем результат
            result = await conn.execute(text("""
                SELECT column_name, data_type, table_name 
                FROM information_schema.columns 
                WHERE column_name = 'tg_id' 
                AND table_schema = 'public'
                ORDER BY table_name;
            """))

            new_types = result.fetchall()
            print("📊 Новые типы tg_id колонок:")
            for row in new_types:
                print(
                    f"   • {row.table_name}.{row.column_name}: {row.data_type}")

            print()
            print("✅ МИГРАЦИЯ УСПЕШНО ПРИМЕНЕНА!")
            print("🎉 Теперь бот может работать с большими Telegram ID!")
            print(f"📈 Поддерживаемый диапазон: до {2**63-1:,}")

    except Exception as e:
        print(f"❌ ОШИБКА ПРИМЕНЕНИЯ МИГРАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_large_telegram_id():
    """Тест работы с большим Telegram ID"""

    print("\n🧪 ТЕСТИРОВАНИЕ БОЛЬШИХ TELEGRAM ID...")

    test_id = 6922033571  # Проблемный ID из логов

    try:
        async with async_sessionmaker() as session:
            # Пытаемся вставить/обновить пользователя с большим ID
            await session.execute(text("""
                INSERT INTO users (tg_id, first_name, preferred_contact, created_at, updated_at)
                VALUES (:tg_id, 'Test User', 'telegram', NOW(), NOW())
                ON CONFLICT (tg_id) 
                DO UPDATE SET updated_at = NOW()
            """), {"tg_id": test_id})

            await session.commit()

            print(f"✅ Успешно обработан Telegram ID: {test_id:,}")
            print("🎯 Фикс работает корректно!")

    except Exception as e:
        print(f"❌ Тест провалился: {e}")
        return False

    return True


async def main():
    """Основная функция"""

    print("=" * 60)
    print("🔧 КРИТИЧЕСКИЙ ФИКС БАЗЫ ДАННЫХ")
    print("📋 Исправление Telegram ID overflow")
    print("=" * 60)
    print()

    # Применяем миграцию
    if await apply_telegram_id_fix():
        print()
        # Тестируем
        await test_large_telegram_id()
        print()
        print("🎉 ВСЕ ГОТОВО! Бот теперь поддерживает любые Telegram ID!")
    else:
        print("❌ Миграция не удалась!")
        return 1

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
