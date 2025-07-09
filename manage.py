#!/usr/bin/env python3
"""
🛠️ MANAGEMENT COMMANDS

Набор команд для управления приложением:
- database operations
- Enhanced AI management
- health checks
- diagnostics
"""

import asyncio
import os
import sys
import click
import subprocess
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@click.group()
def cli():
    """🛠️ Management commands for Enhanced AI system"""
    pass


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed information')
def health_check(detailed):
    """🏥 Check system health"""
    click.echo("🏥 System Health Check")
    click.echo("=" * 30)

    asyncio.run(_health_check_async(detailed))


async def _health_check_async(detailed):
    """Async health check implementation"""
    try:
        # Database check
        from bot.services.db import async_sessionmaker
        async with async_sessionmaker() as session:
            await session.execute("SELECT 1")
        click.echo("✅ Database: Connected")

        # Enhanced AI check
        try:
            from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager
            ai_manager = AIEnhancedManager()
            await ai_manager.initialize()

            if ai_manager._initialized:
                click.echo("✅ Enhanced AI: Initialized")

                if detailed:
                    health = await ai_manager.health_check()
                    components = health.get('components', {})
                    for name, status in components.items():
                        emoji = "✅" if status.get('status') == 'ok' else "⚠️"
                        click.echo(
                            f"  {emoji} {name}: {status.get('status', 'unknown')}")
            else:
                click.echo("❌ Enhanced AI: Not initialized")

        except Exception as e:
            click.echo(f"❌ Enhanced AI: Error - {e}")

        # Environment check
        if detailed:
            click.echo("\n🌍 Environment:")
            env_vars = ["DATABASE_URL", "BOT_TOKEN", "OPENROUTER_API_KEY"]
            for var in env_vars:
                status = "✅" if os.getenv(var) else "❌"
                click.echo(
                    f"  {status} {var}: {'SET' if os.getenv(var) else 'NOT SET'}")

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")


@cli.command()
def enhanced_ai_deploy():
    """🚀 Deploy Enhanced AI system"""
    click.echo("🚀 Deploying Enhanced AI system...")

    asyncio.run(basic_enhanced_ai_deployment())


async def basic_enhanced_ai_deployment():
    """Basic Enhanced AI deployment without full script"""
    import subprocess

    click.echo("📋 Checking current migration state...")

    try:
        # Apply Enhanced AI migration
        click.echo("🔄 Applying Enhanced AI migration...")
        result = subprocess.run(
            ["alembic", "upgrade", "01_enhanced_ai"],
            capture_output=True, text=True, check=True
        )
        click.echo("✅ Migration applied successfully")

        # Test Enhanced AI
        click.echo("🧪 Testing Enhanced AI initialization...")
        from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        health = await ai_manager.health_check()
        click.echo(f"✅ Enhanced AI health: {health.get('status', 'unknown')}")

        click.echo("🎉 Enhanced AI deployment completed!")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Migration failed: {e}")
        click.echo(f"STDERR: {e.stderr}")
        raise
    except Exception as e:
        click.echo(f"❌ Enhanced AI test failed: {e}")
        raise


@cli.command()
def migration_status():
    """📋 Check migration status"""
    try:
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True, text=True, check=True
        )
        current = result.stdout.strip()
        click.echo(f"📋 Current migration: {current}")

        result = subprocess.run(
            ["alembic", "heads"],
            capture_output=True, text=True, check=True
        )
        heads = result.stdout.strip()
        click.echo(f"🎯 Latest migration: {heads}")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Migration check failed: {e}")


@cli.command()
def diagnostics():
    """🔍 Run production diagnostics"""
    click.echo("🔍 Running production diagnostics...")

    asyncio.run(_run_diagnostics())


async def _run_diagnostics():
    """Production diagnostics implementation"""

    click.echo(f"⏰ Diagnostics started: {datetime.now()}")

    # Environment check
    click.echo("\n🌍 Environment Check:")
    env_vars = ["DATABASE_URL", "BOT_TOKEN", "RAILWAY_ENVIRONMENT"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == "DATABASE_URL":
                display = f"{value[:15]}...{value[-10:]}" if len(
                    value) > 25 else "***"
            elif var == "BOT_TOKEN":
                display = f"{value[:10]}...{value[-10:]}" if len(
                    value) > 20 else "***"
            else:
                display = value
            click.echo(f"  ✅ {var}: {display}")
        else:
            click.echo(f"  ❌ {var}: NOT SET")

    # Database connection
    click.echo("\n🗄️ Database Check:")
    try:
        from bot.services.db import async_sessionmaker
        async with async_sessionmaker() as session:
            await session.execute("SELECT 1")
        click.echo("  ✅ Connection: OK")
    except Exception as e:
        click.echo(f"  ❌ Connection failed: {e}")

    # Enhanced AI tables
    click.echo("\n🗃️ Enhanced AI Tables:")
    tables = ["user_profiles", "dialogue_sessions", "ai_metrics"]
    try:
        from bot.services.db import async_sessionmaker
        async with async_sessionmaker() as session:
            for table in tables:
                try:
                    result = await session.execute(f"SELECT COUNT(*) FROM {table}")
                    count = result.scalar()
                    click.echo(f"  ✅ {table}: {count} rows")
                except:
                    click.echo(f"  ❌ {table}: NOT EXISTS")
    except Exception as e:
        click.echo(f"  ❌ Table check failed: {e}")

    # Enhanced AI test
    click.echo("\n🤖 Enhanced AI Test:")
    try:
        from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        if ai_manager._initialized:
            click.echo("  ✅ Initialization: SUCCESS")
            health = await ai_manager.health_check()
            click.echo(f"  ✅ Health: {health.get('status', 'unknown')}")
        else:
            click.echo("  ❌ Initialization: FAILED")
    except Exception as e:
        click.echo(f"  ❌ Enhanced AI error: {e}")

    click.echo(f"\n⏰ Diagnostics completed: {datetime.now()}")


@cli.command()
def force_migration():
    """🔧 Force apply Enhanced AI migration"""
    click.echo("🔧 Force applying Enhanced AI migration...")

    try:
        # Reset to base
        result = subprocess.run(
            ["alembic", "stamp", "base"],
            capture_output=True, text=True, check=True
        )
        click.echo("✅ Reset to base")

        # Apply all migrations
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, check=True
        )
        click.echo("✅ Applied all migrations")

        click.echo("🎉 Force migration completed!")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Force migration failed: {e}")
        click.echo(f"STDERR: {e.stderr}")


@cli.command()
def test_content_intelligence():
    """🧠 Test Content Intelligence System"""
    click.echo("🧠 Testing Content Intelligence System...")

    asyncio.run(_test_content_intelligence())


async def _test_content_intelligence():
    """Test Content Intelligence System implementation"""

    try:
        # Import and initialize
        from bot.services.content_intelligence import ContentIntelligenceSystem

        click.echo("📦 Importing Content Intelligence...")
        content_system = ContentIntelligenceSystem()

        click.echo("🚀 Initializing system...")
        await content_system.initialize()

        click.echo("🔍 Testing news collection...")
        posts = await content_system.collect_and_process_news()

        click.echo(f"📝 Generated {len(posts)} posts:")
        for i, post in enumerate(posts[:3], 1):
            click.echo(f"\n📄 Post {i}:")
            click.echo(f"Length: {len(post)} chars")
            click.echo(f"Preview: {post[:100]}...")

        click.echo("\n✅ Content Intelligence test completed!")

    except Exception as e:
        click.echo(f"❌ Content Intelligence test failed: {e}")
        import traceback
        click.echo(f"Error details: {traceback.format_exc()}")


@cli.command()
def test_news_parser():
    """📰 Test News Parser only"""
    click.echo("📰 Testing News Parser...")

    asyncio.run(_test_news_parser())


async def _test_news_parser():
    """Test news parser implementation"""

    try:
        from bot.services.content_intelligence import NewsParser

        click.echo("📡 Testing news sources...")

        async with NewsParser() as parser:
            news_items = await parser.parse_all_sources()

        click.echo(f"📰 Collected {len(news_items)} news items:")

        # Group by source
        by_source = {}
        for item in news_items:
            by_source.setdefault(item.source, []).append(item)

        for source, items in by_source.items():
            click.echo(f"\n📍 {source}: {len(items)} items")
            for item in items[:2]:  # Show first 2 from each source
                click.echo(f"  • {item.title[:60]}...")
                click.echo(f"    Category: {item.category}")
                click.echo(f"    Score: {item.relevance_score}")

        click.echo("\n✅ News parser test completed!")

    except Exception as e:
        click.echo(f"❌ News parser test failed: {e}")
        import traceback
        click.echo(f"Error details: {traceback.format_exc()}")


if __name__ == "__main__":
    cli()
