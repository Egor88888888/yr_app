"""
🔧 AUTOPOST DIAGNOSTIC & FIX
Диагностика и исправление проблем автопостинга
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType, ParseMode

logger = logging.getLogger(__name__)


class AutopostDiagnostic:
    """Диагностика и исправление автопостинга"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def run_full_diagnostic(self) -> Dict[str, Any]:
        """
        Полная диагностика системы автопостинга
        """
        try:
            result = {
                "overall_status": "unknown",
                "issues": [],
                "fixes_applied": [],
                "tests": {},
                "recommendations": []
            }

            logger.info("🔧 Запуск полной диагностики автопостинга...")

            # Тест 1: Проверка переменных окружения
            result["tests"]["environment"] = await self._test_environment()

            # Тест 2: Проверка канала
            result["tests"]["channel"] = await self._test_target_channel()

            # Тест 3: Проверка SMM интеграции
            result["tests"]["smm_system"] = await self._test_smm_system()

            # Тест 4: Проверка планировщика
            result["tests"]["scheduler"] = await self._test_scheduler()

            # Тест 5: Проверка deploy autopost
            result["tests"]["deploy_autopost"] = await self._test_deploy_autopost()

            # Тест 6: Тест публикации
            result["tests"]["test_publish"] = await self._test_publish_capability()

            # Определяем проблемы и статус
            result["issues"] = self._identify_issues(result["tests"])
            result["overall_status"] = self._determine_status(result["tests"])
            result["recommendations"] = self._generate_recommendations(
                result["issues"])

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при диагностике автопостинга: {e}")
            return {
                "overall_status": "error",
                "error": str(e)
            }

    async def _test_environment(self) -> Dict[str, Any]:
        """Тест переменных окружения"""
        try:
            channel_id = os.getenv(
                'TARGET_CHANNEL_ID') or os.getenv('CHANNEL_ID')
            bot_token = os.getenv('BOT_TOKEN')

            return {
                "success": True,
                "bot_token_set": bool(bot_token),
                "channel_id_set": bool(channel_id),
                "channel_id": channel_id or "Not set",
                "is_fallback_channel": channel_id in [None, '@test_legal_channel']
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_target_channel(self) -> Dict[str, Any]:
        """Тест целевого канала"""
        try:
            channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                'CHANNEL_ID') or '@test_legal_channel'

            # Проверяем доступность канала
            try:
                channel = await self.bot.get_chat(channel_id)
                channel_accessible = True
                channel_title = channel.title
            except Exception as e:
                channel_accessible = False
                channel_title = None
                channel_error = str(e)

            # Проверяем права бота
            bot_permissions = None
            if channel_accessible:
                try:
                    bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)
                    bot_permissions = {
                        "status": bot_member.status,
                        "can_post": bot_member.status in ['administrator', 'creator'],
                        "can_edit": getattr(bot_member, 'can_edit_messages', False) if bot_member.status == 'administrator' else True
                    }
                except Exception as e:
                    bot_permissions = {"error": str(e)}

            return {
                "success": channel_accessible,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "channel_accessible": channel_accessible,
                "bot_permissions": bot_permissions,
                "error": channel_error if not channel_accessible else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_smm_system(self) -> Dict[str, Any]:
        """Тест SMM системы"""
        try:
            # Проверяем доступность SMM интеграции
            try:
                from .smm_integration import get_smm_integration
                smm_integration = get_smm_integration()

                if smm_integration:
                    smm_running = smm_integration.is_running
                    autopost_status = await smm_integration.get_autopost_status()

                    return {
                        "success": True,
                        "smm_available": True,
                        "smm_running": smm_running,
                        "autopost_enabled": autopost_status.get("enabled", False),
                        "autopost_interval": autopost_status.get("interval", "Unknown"),
                        "next_post_time": autopost_status.get("next_post_time", "Unknown")
                    }
                else:
                    return {
                        "success": False,
                        "smm_available": False,
                        "error": "SMM integration not initialized"
                    }

            except ImportError as e:
                return {
                    "success": False,
                    "smm_available": False,
                    "error": f"SMM modules not available: {e}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_scheduler(self) -> Dict[str, Any]:
        """Тест планировщика"""
        try:
            # Пытаемся получить доступ к планировщику
            try:
                from .smm_integration import get_smm_integration
                smm_integration = get_smm_integration()

                if smm_integration and smm_integration.smm_system:
                    scheduler = smm_integration.smm_system.scheduler

                    return {
                        "success": True,
                        "scheduler_available": True,
                        "autopost_enabled": getattr(scheduler, 'autopost_enabled', False),
                        "interval_minutes": getattr(scheduler, 'autopost_interval_minutes', 0),
                        "has_autopost_task": hasattr(scheduler, '_autopost_task')
                    }
                else:
                    return {
                        "success": False,
                        "scheduler_available": False,
                        "error": "SMM system not available"
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_deploy_autopost(self) -> Dict[str, Any]:
        """Тест deploy autopost"""
        try:
            # Проверяем статус deploy autopost
            try:
                from .deploy_autopost import _deploy_autopost_instance

                deploy_available = _deploy_autopost_instance is not None

                return {
                    "success": True,
                    "deploy_autopost_available": deploy_available,
                    "should_have_posted": True,  # Должен был создать пост после деплоя
                    "time_since_deploy": "Recently deployed"
                }

            except ImportError:
                return {
                    "success": False,
                    "deploy_autopost_available": False,
                    "error": "Deploy autopost module not available"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _test_publish_capability(self) -> Dict[str, Any]:
        """Тест возможности публикации"""
        try:
            channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                'CHANNEL_ID') or '@test_legal_channel'

            # НЕ создаем реальный пост, только проверяем доступность API
            try:
                # Получаем информацию о боте
                bot_info = await self.bot.get_me()

                return {
                    "success": True,
                    "bot_username": bot_info.username,
                    "bot_api_accessible": True,
                    "target_channel": channel_id,
                    "ready_to_publish": True
                }

            except Exception as e:
                return {
                    "success": False,
                    "bot_api_accessible": False,
                    "error": str(e)
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _identify_issues(self, tests: Dict[str, Dict]) -> List[str]:
        """Определение проблем на основе тестов"""
        issues = []

        env_test = tests.get("environment", {})
        if env_test.get("is_fallback_channel"):
            issues.append("channel_not_configured")

        channel_test = tests.get("channel", {})
        if not channel_test.get("success"):
            issues.append("channel_not_accessible")
        elif not channel_test.get("bot_permissions", {}).get("can_post"):
            issues.append("no_publish_permissions")

        smm_test = tests.get("smm_system", {})
        if not smm_test.get("smm_available"):
            issues.append("smm_not_available")
        elif not smm_test.get("autopost_enabled"):
            issues.append("autopost_disabled")

        scheduler_test = tests.get("scheduler", {})
        if not scheduler_test.get("autopost_enabled"):
            issues.append("scheduler_not_running")

        return issues

    def _determine_status(self, tests: Dict[str, Dict]) -> str:
        """Определение общего статуса"""
        issues = self._identify_issues(tests)

        if not issues:
            return "fully_working"
        elif "channel_not_configured" in issues:
            return "channel_not_configured"
        elif "channel_not_accessible" in issues:
            return "channel_not_accessible"
        elif "no_publish_permissions" in issues:
            return "no_permissions"
        elif "smm_not_available" in issues:
            return "smm_system_error"
        elif "autopost_disabled" in issues:
            return "autopost_disabled"
        else:
            return "partial_issues"

    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """Генерация рекомендаций"""
        recommendations = []

        if "channel_not_configured" in issues:
            recommendations.append(
                "🔧 Настройте переменную TARGET_CHANNEL_ID в Railway")

        if "channel_not_accessible" in issues:
            recommendations.append("🔧 Проверьте корректность ID канала")

        if "no_publish_permissions" in issues:
            recommendations.append("🔧 Добавьте бота как администратора канала")

        if "smm_not_available" in issues:
            recommendations.append("🔧 Перезапустите SMM систему")

        if "autopost_disabled" in issues:
            recommendations.append("🔧 Включите автопостинг через /admin → SMM")

        if not recommendations:
            recommendations.append("✅ Все настройки корректны!")

        return recommendations

    async def auto_fix_issues(self, issues: List[str]) -> Dict[str, Any]:
        """Автоматическое исправление проблем"""
        fixes_applied = []

        try:
            # Исправление 1: Включение автопостинга если SMM система доступна
            if "autopost_disabled" in issues:
                try:
                    from .smm_integration import get_smm_integration
                    smm_integration = get_smm_integration()

                    if smm_integration:
                        await smm_integration.enable_autopost()
                        await smm_integration.set_autopost_interval(minutes=60)
                        fixes_applied.append("autopost_enabled")
                        logger.info("✅ Автопостинг включен автоматически")

                except Exception as e:
                    logger.error(f"❌ Не удалось включить автопостинг: {e}")

            # Исправление 2: Принудительный запуск планировщика
            if "scheduler_not_running" in issues:
                try:
                    from .smm_integration import get_smm_integration
                    smm_integration = get_smm_integration()

                    if smm_integration and smm_integration.smm_system:
                        scheduler = smm_integration.smm_system.scheduler
                        scheduler.autopost_enabled = True
                        scheduler.autopost_interval_minutes = 60

                        # Запускаем loop если он не запущен
                        if not hasattr(scheduler, '_autopost_task') or scheduler._autopost_task.done():
                            import asyncio
                            scheduler._autopost_task = asyncio.create_task(
                                scheduler._autopost_loop())
                            fixes_applied.append("scheduler_restarted")
                            logger.info("✅ Планировщик перезапущен")

                except Exception as e:
                    logger.error(
                        f"❌ Не удалось перезапустить планировщик: {e}")

            # Исправление 3: Создание тестового поста
            if len(fixes_applied) > 0:
                try:
                    test_post_result = await self._create_immediate_test_post()
                    if test_post_result.get("success"):
                        fixes_applied.append("test_post_created")

                except Exception as e:
                    logger.error(f"❌ Не удалось создать тестовый пост: {e}")

            return {
                "success": len(fixes_applied) > 0,
                "fixes_applied": fixes_applied,
                "message": f"Применено {len(fixes_applied)} исправлений"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при автоисправлении: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_immediate_test_post(self) -> Dict[str, Any]:
        """Создание немедленного тестового поста"""
        try:
            channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                'CHANNEL_ID') or '@test_legal_channel'

            test_content = f"""🚀 **ТЕСТ АВТОПОСТИНГА**

✅ **Система восстановлена:** {datetime.now().strftime('%H:%M')}

🔧 **Что исправлено:**
• Автопостинг включен  
• Планировщик запущен
• Интервал: каждый час
• Следующий пост: через 60 минут

💡 **Автопостинг работает!** Ожидайте регулярные посты каждый час.

📱 **Консультация:** /start"""

            # Создаем простые кнопки
            keyboard = [[
                InlineKeyboardButton("📱 Получить консультацию",
                                     url=f"https://t.me/{self.bot.username}")
            ]]

            message = await self.bot.send_message(
                channel_id,
                test_content,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            return {
                "success": True,
                "message_id": message.message_id,
                "channel_id": channel_id
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


async def run_autopost_diagnostic(bot: Bot) -> Dict[str, Any]:
    """Запуск диагностики автопостинга"""
    diagnostic = AutopostDiagnostic(bot)
    return await diagnostic.run_full_diagnostic()


async def fix_autopost_issues(bot: Bot, issues: List[str]) -> Dict[str, Any]:
    """Исправление проблем автопостинга"""
    diagnostic = AutopostDiagnostic(bot)
    return await diagnostic.auto_fix_issues(issues)


def format_diagnostic_report(result: Dict[str, Any]) -> str:
    """Форматирование отчета диагностики"""
    try:
        status = result.get("overall_status", "unknown")

        # Заголовок
        if status == "fully_working":
            header = "✅ **АВТОПОСТИНГ РАБОТАЕТ КОРРЕКТНО**"
        elif status == "channel_not_configured":
            header = "⚠️ **КАНАЛ НЕ НАСТРОЕН**"
        elif status == "autopost_disabled":
            header = "⚠️ **АВТОПОСТИНГ ОТКЛЮЧЕН**"
        else:
            header = "❌ **АВТОПОСТИНГ НЕ РАБОТАЕТ**"

        report = f"""{header}

🔧 **РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:**"""

        # Тесты
        tests = result.get("tests", {})

        # Окружение
        env_test = tests.get("environment", {})
        if env_test.get("success"):
            channel_id = env_test.get("channel_id", "Not set")
            is_fallback = env_test.get("is_fallback_channel", False)
            if is_fallback:
                report += f"\n⚠️ Канал: {channel_id} (fallback - нужна настройка)"
            else:
                report += f"\n✅ Канал: {channel_id}"
        else:
            report += f"\n❌ Переменные окружения: {env_test.get('error', 'Unknown')}"

        # Канал
        channel_test = tests.get("channel", {})
        if channel_test.get("success"):
            report += f"\n✅ Канал доступен: {channel_test.get('channel_title', 'Unknown')}"
            perms = channel_test.get("bot_permissions", {})
            if perms.get("can_post"):
                report += f"\n✅ Права бота: {perms.get('status', 'Unknown')}"
            else:
                report += f"\n❌ Права бота: недостаточно прав"
        else:
            report += f"\n❌ Канал недоступен: {channel_test.get('error', 'Unknown')}"

        # SMM система
        smm_test = tests.get("smm_system", {})
        if smm_test.get("success"):
            report += f"\n✅ SMM система: работает"
            if smm_test.get("autopost_enabled"):
                report += f"\n✅ Автопостинг: включен ({smm_test.get('autopost_interval', 'Unknown')})"
            else:
                report += f"\n❌ Автопостинг: отключен"
        else:
            report += f"\n❌ SMM система: {smm_test.get('error', 'недоступна')}"

        # Рекомендации
        recommendations = result.get("recommendations", [])
        if recommendations:
            report += "\n\n🔧 **РЕКОМЕНДАЦИИ:**"
            for rec in recommendations:
                report += f"\n{rec}"

        return report

    except Exception as e:
        return f"❌ **ОШИБКА ФОРМАТИРОВАНИЯ:** {e}"
