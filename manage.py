#!/usr/bin/env python3
"""Management commands for the bot"""

import asyncio
import os
import click
from sqlalchemy import text
from bot.services.db import async_sessionmaker
from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager


@click.group()
def cli():
    """Legal Bot Management Commands"""
    pass


@cli.command()
async def init_db():
    """🚀 Initialize database tables"""
    click.echo("Creating database tables...")
    from bot.services.db import init_db
    await init_db()
    click.echo("✅ Database initialized")


@cli.command()
async def health_check():
    """🏥 Проверка здоровья всех компонентов"""
    click.echo("🔍 Running health check...")

    health_status = {
        "database": "🔄 checking...",
        "ai_enhanced": "🔄 checking...",
        "external_apis": "🔄 checking...",
        "file_system": "🔄 checking..."
    }

    # Проверка БД
    try:
        async with async_sessionmaker() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar():
                health_status["database"] = "✅ healthy"
            else:
                health_status["database"] = "❌ unhealthy"
    except Exception as e:
        health_status["database"] = f"❌ error: {e}"

    # Проверка Enhanced AI
    try:
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()
        health = await ai_manager.health_check()
        if health.get("status") == "healthy":
            health_status["ai_enhanced"] = "✅ healthy"
        else:
            health_status["ai_enhanced"] = f"⚠️ degraded: {health.get('status')}"
    except Exception as e:
        health_status["ai_enhanced"] = f"❌ error: {e}"

    # Проверка внешних API
    external_checks = []
    if os.getenv("OPENROUTER_API_KEY"):
        external_checks.append("OpenRouter")
    if os.getenv("GOOGLE_SHEETS_CREDS_JSON"):
        external_checks.append("Google Sheets")
    if os.getenv("CLOUDPAYMENTS_PUBLIC_ID"):
        external_checks.append("CloudPayments")

    if external_checks:
        health_status["external_apis"] = f"✅ configured: {', '.join(external_checks)}"
    else:
        health_status["external_apis"] = "⚠️ no external APIs configured"

    # Проверка файловой системы
    try:
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=True) as f:
            f.write(b"test")
            health_status["file_system"] = "✅ healthy"
    except Exception as e:
        health_status["file_system"] = f"❌ error: {e}"

    # Вывод результатов
    click.echo("\n📊 HEALTH CHECK RESULTS:")
    for component, status in health_status.items():
        click.echo(f"  {component}: {status}")


@cli.command()
@click.option('--force', is_flag=True, help='Force deployment without confirmation')
async def deploy_enhanced_ai(force):
    """🚀 Deploy Enhanced AI system to production"""

    if not force:
        click.echo("⚠️  This will deploy Enhanced AI system to production")
        if not click.confirm("Do you want to continue?"):
            click.echo("❌ Deployment cancelled")
            return

    try:
        # Import deployment script
        from deploy_enhanced_ai import deploy_enhanced_ai
        await deploy_enhanced_ai()

    except ImportError:
        # If deployment script not available, do basic deployment
        click.echo("🔧 Running basic Enhanced AI deployment...")
        await basic_enhanced_ai_deployment()


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
async def test_enhanced_ai():
    """🧪 Test Enhanced AI system functionality"""
    click.echo("🔧 Testing Enhanced AI system...")

    try:
        ai_manager = AIEnhancedManager()
        await ai_manager.initialize()

        # Health check
        health = await ai_manager.health_check()
        click.echo(f"📊 Health status: {health.get('status', 'unknown')}")

        # Test components
        components = health.get('components', {})
        for name, status in components.items():
            emoji = "✅" if status.get('status') == 'ok' else "⚠️"
            click.echo(f"  {emoji} {name}: {status.get('status', 'unknown')}")

        # Test response generation
        click.echo("\n🧪 Testing response generation...")
        test_message = "Вопрос о семейном праве: как подать на развод?"

        response = await ai_manager.generate_response(
            user_id=999999,  # Test user ID
            message=test_message
        )

        click.echo(f"✅ Generated response ({len(response)} chars)")
        click.echo(f"📝 Sample: {response[:100]}...")

        click.echo("\n🎉 Enhanced AI test completed successfully!")

    except Exception as e:
        click.echo(f"❌ Enhanced AI test failed: {e}")
        import traceback
        traceback.print_exc()


@cli.command()
async def migrate():
    """🔄 Apply database migrations"""
    import subprocess

    try:
        click.echo("🔄 Applying database migrations...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, check=True
        )
        click.echo("✅ Migrations applied successfully")
        click.echo(result.stdout)

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Migration failed: {e}")
        click.echo(f"STDERR: {e.stderr}")


@cli.command()
async def check_tables():
    """📊 Check database tables"""
    click.echo("📊 Checking database tables...")

    async with async_sessionmaker() as session:
        # Get all tables
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))

        tables = [row[0] for row in result.fetchall()]

        click.echo(f"\n📋 Found {len(tables)} tables:")

        # Basic tables
        basic_tables = ['users', 'categories',
                        'applications', 'admins', 'payments', 'logs']
        enhanced_ai_tables = [
            'user_profiles', 'dialogue_sessions', 'dialogue_messages',
            'message_embeddings', 'category_embeddings', 'ai_metrics',
            'user_preferences', 'training_data'
        ]

        click.echo("\n🏗️  Basic tables:")
        for table in basic_tables:
            emoji = "✅" if table in tables else "❌"
            click.echo(f"  {emoji} {table}")

        click.echo("\n🤖 Enhanced AI tables:")
        for table in enhanced_ai_tables:
            emoji = "✅" if table in tables else "❌"
            click.echo(f"  {emoji} {table}")

        # Check for any missing Enhanced AI tables
        missing_enhanced = [t for t in enhanced_ai_tables if t not in tables]
        if missing_enhanced:
            click.echo(f"\n⚠️  Missing Enhanced AI tables: {missing_enhanced}")
            click.echo("💡 Run: python manage.py deploy-enhanced-ai")


if __name__ == "__main__":
    # Run async commands
    import inspect

    def run_async_command(cmd):
        def wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(cmd):
                return asyncio.run(cmd(*args, **kwargs))
            return cmd(*args, **kwargs)
        return wrapper

    # Wrap async commands
    for command in cli.commands.values():
        if hasattr(command, 'callback') and inspect.iscoroutinefunction(command.callback):
            command.callback = run_async_command(command.callback)

    cli()
