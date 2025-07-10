#!/usr/bin/env python3
"""
🚀 RAILWAY MIGRATION: Критический фикс Telegram ID overflow

Этот скрипт применяется напрямую на Railway для исправления БД
"""

import os
import asyncio
import asyncpg
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_telegram_id_overflow():
    """Исправление PostgreSQL INTEGER → BIGINT для tg_id колонок"""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL не найден!")
        return False

    # Убираем postgresql:// и заменяем на postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        # asyncpg использует другой формат
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1)

    logger.info("🔧 КРИТИЧЕСКИЙ ФИКС: Telegram ID overflow")
    logger.info("📋 Конвертация INTEGER → BIGINT для tg_id колонок")

    try:
        # Подключаемся к PostgreSQL напрямую
        conn = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))

        logger.info("✅ Подключение к БД установлено")

        # Проверяем текущие типы
        logger.info("🔍 Проверка текущих типов колонок...")

        current_types = await conn.fetch("""
            SELECT column_name, data_type, table_name 
            FROM information_schema.columns 
            WHERE column_name = 'tg_id' 
            AND table_schema = 'public'
            ORDER BY table_name;
        """)

        logger.info("📊 Текущие типы tg_id колонок:")
        for row in current_types:
            logger.info(
                f"   • {row['table_name']}.{row['column_name']}: {row['data_type']}")

        # Применяем изменения
        tables_to_fix = [
            ("users", "Пользователи"),
            ("admins", "Администраторы")
        ]

        for table_name, description in tables_to_fix:
            logger.info(f"🔧 Конвертация {description} ({table_name}.tg_id)...")

            # Проверяем существование таблицы
            table_exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table_name}'
                );
            """)

            if not table_exists:
                logger.warning(
                    f"   ⚠️  Таблица {table_name} не найдена, пропускаем...")
                continue

            # Применяем изменение типа
            await conn.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN tg_id TYPE BIGINT;
            """)

            logger.info(f"   ✅ {table_name}.tg_id → BIGINT")

        logger.info("🎯 ПРОВЕРКА РЕЗУЛЬТАТОВ...")

        # Проверяем результат
        new_types = await conn.fetch("""
            SELECT column_name, data_type, table_name 
            FROM information_schema.columns 
            WHERE column_name = 'tg_id' 
            AND table_schema = 'public'
            ORDER BY table_name;
        """)

        logger.info("📊 Новые типы tg_id колонок:")
        for row in new_types:
            logger.info(
                f"   • {row['table_name']}.{row['column_name']}: {row['data_type']}")

        # Тестируем проблемный Telegram ID
        test_id = 6922033571  # ID из логов
        logger.info(f"🧪 Тестирование большого Telegram ID: {test_id:,}")

        await conn.execute("""
            INSERT INTO users (tg_id, first_name, preferred_contact, created_at, updated_at)
            VALUES ($1, 'Test User', 'telegram', NOW(), NOW())
            ON CONFLICT (tg_id) 
            DO UPDATE SET updated_at = NOW()
        """, test_id)

        logger.info(f"✅ Успешно обработан Telegram ID: {test_id:,}")

        await conn.close()

        logger.info("🎉 МИГРАЦИЯ УСПЕШНО ПРИМЕНЕНА!")
        logger.info("✅ Бот теперь поддерживает любые Telegram ID!")
        logger.info(f"📈 Поддерживаемый диапазон: до {2**63-1:,}")

        return True

    except Exception as e:
        logger.error(f"❌ ОШИБКА МИГРАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Основная функция для Railway"""

    logger.info("=" * 60)
    logger.info("🚀 RAILWAY: Критический фикс БД")
    logger.info("📋 Исправление Telegram ID overflow")
    logger.info("=" * 60)

    success = await fix_telegram_id_overflow()

    if success:
        logger.info("🎉 ВСЕ ГОТОВО! Можно перезапускать бота!")
        return 0
    else:
        logger.error("❌ Миграция провалилась!")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
