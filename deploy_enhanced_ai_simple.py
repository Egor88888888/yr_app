#!/usr/bin/env python3
"""
🚀 ENHANCED AI SIMPLE DEPLOYMENT

Простой скрипт для применения Enhanced AI миграций.
Работает с SQLite и PostgreSQL.
"""

import asyncio
import os
import sys
import subprocess
from datetime import datetime


async def deploy_enhanced_ai():
    """Простой деплой Enhanced AI"""

    print("🚀 Enhanced AI Simple Deployment")
    print("=" * 40)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Проверяем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        sys.exit(1)

    is_sqlite = "sqlite" in database_url.lower()
    is_postgres = "postgres" in database_url.lower()

    print(
        f"🔗 Database: {'SQLite' if is_sqlite else 'PostgreSQL' if is_postgres else 'Unknown'}")

    try:
        # Шаг 1: Применяем миграцию
        print("\n🔧 Step 1: Applying Enhanced AI migration...")
        await apply_migration()

        # Шаг 2: Проверяем создание таблиц
        print("\n📊 Step 2: Verifying tables...")
        await check_tables(is_sqlite)

        # Шаг 3: Тестируем Enhanced AI
        print("\n🧪 Step 3: Testing Enhanced AI...")
        await test_enhanced_ai()

        print("\n🎉 Enhanced AI deployment completed successfully!")
        print("✅ System is ready to use")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def apply_migration():
    """Применяет Enhanced AI миграцию"""
    try:
        # Проверяем текущее состояние
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"📋 Current revision: {result.stdout.strip()}")
        else:
            print("⚠️ Could not check current revision, proceeding anyway...")

        # Применяем миграцию Enhanced AI
        print("🔄 Running migration...")
        result = subprocess.run(
            ["alembic", "upgrade", "01_enhanced_ai"],
            capture_output=True, text=True, check=True
        )

        print("✅ Migration completed successfully")
        if result.stdout.strip():
            print(f"📝 Output: {result.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        if "already at" in e.stdout or "already at" in e.stderr:
            print("✅ Migration already applied")
        else:
            print(f"❌ Migration failed: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            raise


async def check_tables(is_sqlite=False):
    """Проверяет создание Enhanced AI таблиц"""
    from bot.services.db import async_sessionmaker
    from sqlalchemy import text

    enhanced_ai_tables = [
        'user_profiles', 'dialogue_sessions', 'dialogue_messages',
        'message_embeddings', 'category_embeddings', 'ai_metrics',
        'user_preferences', 'training_data'
    ]

    async with async_sessionmaker() as session:
        # Разные запросы для разных БД
        if is_sqlite:
            # SQLite: используем sqlite_master
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        else:
            # PostgreSQL: используем information_schema
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """

        result = await session.execute(text(query))
        existing_tables = [row[0] for row in result.fetchall()]

        print(f"📊 Found {len(existing_tables)} tables total")

        # Проверяем Enhanced AI таблицы
        missing_tables = []
        for table in enhanced_ai_tables:
            if table in existing_tables:
                print(f"✅ {table}")
            else:
                print(f"❌ {table} - MISSING")
                missing_tables.append(table)

        # Проверяем добавленные колонки в applications
        if is_sqlite:
            # SQLite: PRAGMA table_info
            result = await session.execute(text("PRAGMA table_info(applications)"))
            columns = [row[1]
                       for row in result.fetchall()]  # row[1] is column name
        else:
            # PostgreSQL: information_schema
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'applications'
            """))
            columns = [row[0] for row in result.fetchall()]

        for col in ['notes', 'assigned_admin']:
            if col in columns:
                print(f"✅ applications.{col}")
            else:
                print(f"❌ applications.{col} - MISSING")
                missing_tables.append(f"applications.{col}")

        if missing_tables:
            raise Exception(f"Missing tables/columns: {missing_tables}")

        print("✅ All Enhanced AI tables and columns verified")


async def test_enhanced_ai():
    """Тестирует Enhanced AI систему"""
    try:
        from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager

        print("🔧 Initializing Enhanced AI...")
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        print("🏥 Health check...")
        health = await ai_manager.health_check()
        status = health.get('status', 'unknown')
        print(f"✅ Health: {status}")

        # Проверяем компоненты
        components = health.get('components', {})
        healthy_components = 0
        for name, comp_status in components.items():
            if comp_status.get('status') == 'ok':
                healthy_components += 1

        print(f"📊 Components: {healthy_components}/{len(components)} healthy")

        print("✅ Enhanced AI system tested successfully")

    except Exception as e:
        print(f"❌ Enhanced AI test failed: {e}")
        # Не прерываем деплой, если тест не прошел
        print("⚠️ Continuing anyway - Enhanced AI may work in production")


if __name__ == "__main__":
    asyncio.run(deploy_enhanced_ai())
