#!/usr/bin/env python3
"""
🛠️ PRODUCTION MANAGEMENT SCRIPT
Утилиты для управления продакшен сервисом

Commands:
- init_db: Инициализация базы данных
- health_check: Проверка здоровья системы
- backup: Создание backup базы данных  
- restore: Восстановление из backup
- stats: Статистика системы
- clean_logs: Очистка старых логов
- monitor: Мониторинг в реальном времени
"""

import asyncio
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import click
from sqlalchemy import text, func, select
from bot.services.db import async_sessionmaker, init_db, User, Application as AppModel, Payment
from bot.services.ai_enhanced import AIEnhancedManager

# Ensure project is importable
sys.path.append(str(Path(__file__).parent))


@click.group()
def cli():
    """��️ Юридический Центр - Management CLI"""
    pass


@cli.command()
async def init_database():
    """🗃️ Инициализация базы данных"""
    click.echo("🚀 Initializing database...")
    try:
        await init_db()
        click.echo("✅ Database initialized successfully!")
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}")
        sys.exit(1)


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
        webapp_path = Path("webapp")
        if webapp_path.exists() and (webapp_path / "index.html").exists():
            health_status["file_system"] = "✅ webapp files present"
        else:
            health_status["file_system"] = "❌ webapp files missing"
    except Exception as e:
        health_status["file_system"] = f"❌ error: {e}"

    # Вывод результатов
    click.echo("\n🏥 HEALTH CHECK RESULTS:")
    click.echo("=" * 40)
    for component, status in health_status.items():
        click.echo(f"{component.replace('_', ' ').title()}: {status}")

    # Общий статус
    if all("✅" in status for status in health_status.values()):
        click.echo("\n🎉 ALL SYSTEMS HEALTHY!")
        return True
    else:
        click.echo("\n⚠️ SOME ISSUES DETECTED")
        return False


@cli.command()
async def backup_database():
    """💾 Создание backup базы данных"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.json"

    click.echo(f"💾 Creating backup: {backup_file}")

    try:
        backup_data = {
            "timestamp": timestamp,
            "users": [],
            "applications": [],
            "payments": []
        }

        async with async_sessionmaker() as session:
            # Backup users
            users = await session.execute(select(User))
            for user in users.scalars():
                backup_data["users"].append({
                    "id": user.id,
                    "tg_id": user.tg_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                })

            # Backup applications
            apps = await session.execute(select(AppModel))
            for app in apps.scalars():
                backup_data["applications"].append({
                    "id": app.id,
                    "user_id": app.user_id,
                    "subcategory": app.subcategory,
                    "description": app.description,
                    "status": app.status,
                    "price": float(app.price) if app.price else None,
                    "created_at": app.created_at.isoformat() if app.created_at else None
                })

            # Backup payments
            payments = await session.execute(select(Payment))
            for payment in payments.scalars():
                backup_data["payments"].append({
                    "id": payment.id,
                    "app_id": payment.app_id,
                    "amount": float(payment.amount) if payment.amount else None,
                    "status": payment.status,
                    "created_at": payment.created_at.isoformat() if payment.created_at else None
                })

        # Сохраняем backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        click.echo(f"✅ Backup created successfully: {backup_file}")
        click.echo(f"📊 Users: {len(backup_data['users'])}")
        click.echo(f"📋 Applications: {len(backup_data['applications'])}")
        click.echo(f"💳 Payments: {len(backup_data['payments'])}")

    except Exception as e:
        click.echo(f"❌ Backup failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('backup_file')
async def restore_database(backup_file):
    """♻️ Восстановление из backup"""
    click.echo(f"♻️ Restoring from backup: {backup_file}")

    if not Path(backup_file).exists():
        click.echo(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        click.echo(f"📅 Backup timestamp: {backup_data['timestamp']}")
        click.echo(f"📊 Users: {len(backup_data['users'])}")
        click.echo(f"📋 Applications: {len(backup_data['applications'])}")
        click.echo(f"💳 Payments: {len(backup_data['payments'])}")

        if not click.confirm("Continue with restore?"):
            click.echo("Restore cancelled.")
            return

        # Здесь был бы код восстановления
        # В production нужна более сложная логика
        click.echo(
            "⚠️ Restore functionality requires custom implementation for your specific DB schema")

    except Exception as e:
        click.echo(f"❌ Restore failed: {e}")
        sys.exit(1)


@cli.command()
async def system_stats():
    """📊 Статистика системы"""
    click.echo("📊 SYSTEM STATISTICS")
    click.echo("=" * 40)

    try:
        async with async_sessionmaker() as session:
            # Общая статистика
            total_users = await session.scalar(select(func.count(User.id)))
            total_apps = await session.scalar(select(func.count(AppModel.id)))

            # Статистика за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            new_users_week = await session.scalar(
                select(func.count(User.id)).where(User.created_at >= week_ago)
            )
            new_apps_week = await session.scalar(
                select(func.count(AppModel.id)).where(
                    AppModel.created_at >= week_ago)
            )

            # По статусам заявок
            status_stats = await session.execute(
                select(AppModel.status, func.count(AppModel.id))
                .group_by(AppModel.status)
            )

            click.echo(f"👥 Total Users: {total_users}")
            click.echo(f"📋 Total Applications: {total_apps}")
            click.echo(f"🆕 New Users (7 days): {new_users_week}")
            click.echo(f"📝 New Applications (7 days): {new_apps_week}")
            click.echo("\n📊 Application Status:")

            for status, count in status_stats:
                click.echo(f"   {status}: {count}")

    except Exception as e:
        click.echo(f"❌ Stats failed: {e}")


@cli.command()
def clean_logs():
    """🧹 Очистка старых логов"""
    click.echo("🧹 Cleaning old logs...")

    log_files = ["bot.log", "error.log", "access.log"]
    cleaned = 0

    for log_file in log_files:
        if Path(log_file).exists():
            try:
                # Архивируем старые логи
                timestamp = datetime.now().strftime("%Y%m%d")
                archived_name = f"{log_file}.{timestamp}"
                Path(log_file).rename(archived_name)
                Path(log_file).touch()  # Создаем новый пустой лог
                cleaned += 1
                click.echo(f"📦 Archived: {log_file} -> {archived_name}")
            except Exception as e:
                click.echo(f"❌ Failed to clean {log_file}: {e}")

    click.echo(f"✅ Cleaned {cleaned} log files")


@cli.command()
@click.option('--interval', default=30, help='Monitoring interval in seconds')
async def monitor(interval):
    """📈 Мониторинг системы в реальном времени"""
    click.echo(f"📈 Starting system monitor (interval: {interval}s)")
    click.echo("Press Ctrl+C to stop...")

    try:
        while True:
            await asyncio.sleep(interval)

            # Проверяем здоровье
            health_ok = await health_check()

            # Показываем timestamp и статус
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "🟢 HEALTHY" if health_ok else "🔴 ISSUES"
            click.echo(f"[{now}] System Status: {status}")

    except KeyboardInterrupt:
        click.echo("\n👋 Monitoring stopped")

if __name__ == '__main__':
    # Поддержка async команд
    for cmd_name, cmd in cli.commands.items():
        if asyncio.iscoroutinefunction(cmd.callback):
            cmd.callback = lambda *args, **kwargs: asyncio.run(
                cmd.callback(*args, **kwargs))

    cli()
