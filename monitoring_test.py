"""
🔍 MONITORING SYSTEM TEST
Тестирование производственной системы мониторинга
"""

import asyncio
import os
import logging
from telegram import Bot
from bot.services.production_monitoring_system import ProductionMonitoringSystem

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_monitoring_system():
    """Тестирование системы мониторинга"""

    print("🔍 Starting Production Monitoring System Test")
    print("=" * 50)

    # Проверяем переменные окружения
    bot_token = os.getenv('BOT_TOKEN')
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')

    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return

    if not admin_chat_id:
        print("❌ ADMIN_CHAT_ID not found in environment")
        return

    print(f"✅ Environment variables configured")
    print(f"   - Bot Token: {'*' * 10}{bot_token[-5:]}")
    print(f"   - Admin Chat ID: {admin_chat_id}")

    try:
        # Создание бота
        bot = Bot(token=bot_token)
        print("\n🤖 Creating Telegram Bot...")

        # Проверка подключения к Telegram
        bot_info = await bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")

        # Создание системы мониторинга
        print("\n🔍 Creating Production Monitoring System...")
        monitoring_system = ProductionMonitoringSystem(bot, admin_chat_id)

        # Тестирование health checks
        print("\n🏥 Testing Health Checks...")

        health_checks = [
            "autopost_system",
            "comments_system",
            "smm_integration",
            "telegram_api",
            "database",
            "memory_usage",
            "response_time"
        ]

        for check_name in health_checks:
            try:
                check_function = monitoring_system.health_checks.get(
                    check_name)
                if check_function:
                    result = await check_function()
                    status = result.get("status", "unknown")
                    status_emoji = {
                        "healthy": "🟢",
                        "warning": "🟡",
                        "degraded": "🟠",
                        "error": "🔴",
                        "unknown": "⚪"
                    }.get(status, "⚪")

                    print(f"   {status_emoji} {check_name}: {status}")

                    # Выводим детали для некоторых проверок
                    if status in ["error", "warning"] and result.get("details"):
                        details = result["details"]
                        if "error" in details:
                            print(f"      Error: {details['error']}")
                else:
                    print(f"   ⚪ {check_name}: check function not found")

            except Exception as e:
                print(f"   🔴 {check_name}: Exception - {e}")

        # Тестирование dashboard
        print("\n📊 Testing Monitoring Dashboard...")
        dashboard = await monitoring_system.get_monitoring_dashboard()

        print(f"   - Monitoring Active: {dashboard['monitoring_active']}")
        print(f"   - Total Systems: {dashboard['total_systems']}")
        print(f"   - Total Checks: {dashboard['total_checks']}")
        print(f"   - Total Alerts: {dashboard['total_alerts']}")
        print(f"   - Active Alerts: {dashboard['active_alerts_count']}")

        # Тестирование алертов
        print("\n🚨 Testing Alert System...")

        # Отправка тестового алерта
        from bot.services.production_monitoring_system import AlertLevel
        await monitoring_system._send_admin_alert(
            AlertLevel.INFO,
            "monitoring_test",
            "🧪 Test alert from monitoring system test"
        )
        print("   ✅ Test alert sent successfully")

        # Краткий тест автоматического мониторинга
        print("\n⚡ Testing Automatic Monitoring (10 seconds)...")
        await monitoring_system.start_monitoring()
        print("   🚀 Monitoring started")

        # Ждем 10 секунд для нескольких проверок
        await asyncio.sleep(10)

        # Остановка мониторинга
        await monitoring_system.stop_monitoring()
        print("   🛑 Monitoring stopped")

        # Финальная dashboard
        final_dashboard = await monitoring_system.get_monitoring_dashboard()
        print(f"\n📈 Final Results:")
        print(
            f"   - Total Checks Performed: {final_dashboard['total_checks']}")
        print(
            f"   - Total Alerts Generated: {final_dashboard['total_alerts']}")

        # Статус систем
        if final_dashboard['system_health']:
            print(f"   - System Health Summary:")
            for system, health in final_dashboard['system_health'].items():
                status_emoji = {
                    "healthy": "🟢",
                    "warning": "🟡",
                    "degraded": "🟠",
                    "down": "🔴",
                    "unknown": "⚪"
                }.get(health["status"], "⚪")
                print(f"     {status_emoji} {system}: {health['status']}")

        print("\n🎉 Monitoring System Test Completed Successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Основная функция"""
    await test_monitoring_system()


if __name__ == "__main__":
    asyncio.run(main())
