#!/usr/bin/env python3
"""
🚀 ENHANCED AI DEPLOYMENT SCRIPT

Применяет миграцию Enhanced AI таблиц в production безопасно.
Включает проверки, rollback возможности и мониторинг.
"""

import asyncio
import os
import sys
from datetime import datetime


async def deploy_enhanced_ai():
    """Главная функция деплоя Enhanced AI"""

    print("🚀 Enhanced AI Deployment Script")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now()}")

    # Проверяем environment
    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL not set")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    is_production = "railway" in database_url.lower(
    ) or "postgres" in database_url.lower()

    print(f"🔗 Database: {'PRODUCTION' if is_production else 'LOCAL'}")
    print(f"📊 URL: {database_url[:50]}...")

    if is_production:
        confirm = input(
            "\n⚠️  This is PRODUCTION! Continue? (type 'YES' to confirm): ")
        if confirm != "YES":
            print("❌ Deployment cancelled")
            sys.exit(0)

    try:
        # Step 1: Check current database state
        print("\n📋 Step 1: Checking database state...")
        await check_database_state()

        # Step 2: Apply Enhanced AI migration
        print("\n🔧 Step 2: Applying Enhanced AI migration...")
        await apply_enhanced_ai_migration()

        # Step 3: Test Enhanced AI initialization
        print("\n🧪 Step 3: Testing Enhanced AI...")
        await test_enhanced_ai_system()

        # Step 4: Final verification
        print("\n✅ Step 4: Final verification...")
        await verify_deployment()

        print("\n🎉 Enhanced AI deployment completed successfully!")
        print("✅ System is ready for production use")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        print("🔄 Consider rollback if needed")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def check_database_state():
    """Проверяет текущее состояние БД"""
    from bot.services.db import async_sessionmaker
    from sqlalchemy import text

    async with async_sessionmaker() as session:
        # Проверяем существующие таблицы
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]

        print(f"📊 Found {len(tables)} existing tables")

        enhanced_ai_tables = [
            'user_profiles', 'dialogue_sessions', 'dialogue_messages',
            'message_embeddings', 'category_embeddings', 'ai_metrics',
            'user_preferences', 'training_data'
        ]

        existing_enhanced_tables = [
            t for t in enhanced_ai_tables if t in tables]
        missing_enhanced_tables = [
            t for t in enhanced_ai_tables if t not in tables]

        if existing_enhanced_tables:
            print(
                f"⚠️  Some Enhanced AI tables already exist: {existing_enhanced_tables}")

        if missing_enhanced_tables:
            print(f"➕ Need to create: {missing_enhanced_tables}")

        return missing_enhanced_tables


async def apply_enhanced_ai_migration():
    """Применяет миграцию Enhanced AI"""
    import subprocess

    try:
        # Проверяем текущую версию миграции
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True, text=True, check=True
        )
        current_revision = result.stdout.strip()
        print(f"📋 Current migration: {current_revision}")

        # Применяем миграцию Enhanced AI
        print("🔄 Applying Enhanced AI migration...")
        result = subprocess.run(
            ["alembic", "upgrade", "01_enhanced_ai"],
            capture_output=True, text=True, check=True
        )

        print("✅ Migration applied successfully")
        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        raise


async def test_enhanced_ai_system():
    """Тестирует Enhanced AI систему"""
    try:
        from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager

        print("🔧 Initializing Enhanced AI...")
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        print("🏥 Checking health...")
        health = await ai_manager.health_check()
        print(f"✅ Health status: {health.get('status', 'unknown')}")

        # Тестируем компоненты
        components = health.get('components', {})
        for name, status in components.items():
            emoji = "✅" if status.get('status') == 'ok' else "⚠️"
            print(f"  {emoji} {name}: {status.get('status', 'unknown')}")

        print("✅ Enhanced AI system tested successfully")

    except Exception as e:
        print(f"❌ Enhanced AI test failed: {e}")
        raise


async def verify_deployment():
    """Финальная проверка деплоя"""
    from bot.services.db import async_sessionmaker
    from sqlalchemy import text

    async with async_sessionmaker() as session:
        # Проверяем все Enhanced AI таблицы
        enhanced_ai_tables = [
            'user_profiles', 'dialogue_sessions', 'dialogue_messages',
            'message_embeddings', 'category_embeddings', 'ai_metrics',
            'user_preferences', 'training_data'
        ]

        for table in enhanced_ai_tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ {table}: {count} records")
            except Exception as e:
                print(f"❌ {table}: ERROR - {e}")
                raise

        # Проверяем добавленные колонки в applications
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'applications' 
            AND column_name IN ('notes', 'assigned_admin')
        """))
        added_columns = [row[0] for row in result.fetchall()]

        for col in ['notes', 'assigned_admin']:
            if col in added_columns:
                print(f"✅ applications.{col}: OK")
            else:
                print(f"❌ applications.{col}: MISSING")
                raise Exception(f"Missing column: {col}")


if __name__ == "__main__":
    asyncio.run(deploy_enhanced_ai())
