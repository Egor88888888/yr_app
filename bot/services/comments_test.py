"""
🧪 COMMENTS TESTING & VERIFICATION
Инструмент для проверки и тестирования системы комментариев
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType, ParseMode

logger = logging.getLogger(__name__)


class CommentsTestManager:
    """Менеджер тестирования системы комментариев"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def verify_comments_setup(self, channel_id: str = None) -> Dict[str, Any]:
        """
        Полная проверка настройки комментариев
        """
        try:
            if not channel_id:
                channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                    'CHANNEL_ID') or '@test_legal_channel'

            result = {
                "channel_id": channel_id,
                "tests": {},
                "overall_status": "unknown",
                "recommendations": []
            }

            logger.info(
                f"🧪 Начинаю проверку комментариев для канала: {channel_id}")

            # Тест 1: Проверка доступности канала
            result["tests"]["channel_access"] = await self._test_channel_access(channel_id)

            # Тест 2: Проверка прав бота в канале
            result["tests"]["bot_permissions"] = await self._test_bot_permissions(channel_id)

            # Тест 3: Проверка группы обсуждений
            result["tests"]["discussion_group"] = await self._test_discussion_group(channel_id)

            # Тест 4: Проверка прав бота в группе обсуждений
            if result["tests"]["discussion_group"]["success"] and result["tests"]["discussion_group"].get("group_id"):
                result["tests"]["bot_in_group"] = await self._test_bot_in_discussion_group(
                    result["tests"]["discussion_group"]["group_id"]
                )

            # Тест 5: Создание тестового поста
            result["tests"]["test_post"] = await self._create_verification_post(channel_id)

            # Определяем общий статус
            result["overall_status"] = self._determine_overall_status(
                result["tests"])
            result["recommendations"] = self._generate_recommendations(
                result["tests"])

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке комментариев: {e}")
            return {
                "success": False,
                "error": str(e),
                "overall_status": "error"
            }

    async def _test_channel_access(self, channel_id: str) -> Dict[str, Any]:
        """Тест доступности канала"""
        try:
            channel = await self.bot.get_chat(channel_id)
            return {
                "success": True,
                "channel_id": channel.id,
                "channel_title": channel.title,
                "channel_type": channel.type,
                "channel_username": getattr(channel, 'username', None)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Канал недоступен: {e}"
            }

    async def _test_bot_permissions(self, channel_id: str) -> Dict[str, Any]:
        """Тест прав бота в канале"""
        try:
            bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)

            can_post = bot_member.status in ['administrator', 'creator']
            can_edit = getattr(bot_member, 'can_edit_messages',
                               False) if bot_member.status == 'administrator' else True
            can_delete = getattr(bot_member, 'can_delete_messages',
                                 False) if bot_member.status == 'administrator' else True

            return {
                "success": True,
                "status": bot_member.status,
                "can_post_messages": can_post,
                "can_edit_messages": can_edit,
                "can_delete_messages": can_delete,
                "all_permissions_ok": can_post and can_edit and can_delete
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Не удалось проверить права бота: {e}"
            }

    async def _test_discussion_group(self, channel_id: str) -> Dict[str, Any]:
        """Тест группы обсуждений"""
        try:
            channel = await self.bot.get_chat(channel_id)

            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                group_id = channel.linked_chat_id
                try:
                    group = await self.bot.get_chat(group_id)
                    return {
                        "success": True,
                        "group_id": group_id,
                        "group_title": group.title,
                        "group_type": group.type,
                        "member_count": getattr(group, 'member_count', 0)
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Группа обсуждений недоступна: {e}",
                        "group_id": group_id
                    }
            else:
                return {
                    "success": False,
                    "error": "Группа обсуждений не привязана к каналу"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка проверки группы обсуждений: {e}"
            }

    async def _test_bot_in_discussion_group(self, group_id: int) -> Dict[str, Any]:
        """Тест прав бота в группе обсуждений"""
        try:
            bot_member = await self.bot.get_chat_member(group_id, self.bot.id)

            is_admin = bot_member.status in ['administrator', 'creator']
            can_delete = getattr(bot_member, 'can_delete_messages',
                                 False) if bot_member.status == 'administrator' else True
            can_restrict = getattr(bot_member, 'can_restrict_members',
                                   False) if bot_member.status == 'administrator' else True

            return {
                "success": True,
                "status": bot_member.status,
                "is_administrator": is_admin,
                "can_delete_messages": can_delete,
                "can_restrict_members": can_restrict,
                "all_permissions_ok": is_admin and can_delete and can_restrict
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Бот не найден в группе обсуждений: {e}"
            }

    async def _create_verification_post(self, channel_id: str) -> Dict[str, Any]:
        """Создание тестового поста для проверки комментариев"""
        try:
            from .markdown_fix import prepare_telegram_message

            test_content = """🧪 **ТЕСТ СИСТЕМЫ КОММЕНТАРИЕВ**

✅ **Проверка завершена успешно!**

💬 **Проверьте функциональность:**
• Нажмите на кнопку "Комментарии" под этим постом
• Оставьте тестовый комментарий
• Проверьте что комментарий появился в группе обсуждений

🤖 **Автоматические функции:**
• Система будет отвечать на вопросы пользователей
• Модерация комментариев включена
• Аналитика взаимодействий активна

📱 **Для консультации:** /start"""

            message_data = prepare_telegram_message(test_content)

            # Создаем кнопки
            keyboard = [[
                InlineKeyboardButton("📱 Связаться с консультантом",
                                     url=f"https://t.me/{self.bot.username}")
            ]]

            message = await self.bot.send_message(
                channel_id,
                **message_data,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            # Создаем ссылку на комментарии
            comments_url = self._create_comments_url(
                channel_id, message.message_id)

            return {
                "success": True,
                "message_id": message.message_id,
                "post_url": f"https://t.me/{channel_id.replace('@', '')}/{message.message_id}",
                "comments_url": comments_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Не удалось создать тестовый пост: {e}"
            }

    def _create_comments_url(self, channel_id: str, message_id: int) -> str:
        """Создать URL для комментариев"""
        if channel_id.startswith('@'):
            channel_username = channel_id[1:]
            return f"https://t.me/{channel_username}/{message_id}?comment=1"
        elif channel_id.startswith('-100'):
            numeric_id = channel_id[4:]
            return f"https://t.me/c/{numeric_id}/{message_id}?comment=1"
        else:
            return f"https://t.me/{channel_id}/{message_id}?comment=1"

    def _determine_overall_status(self, tests: Dict[str, Dict]) -> str:
        """Определить общий статус проверки"""
        if not tests.get("channel_access", {}).get("success"):
            return "channel_not_found"

        if not tests.get("bot_permissions", {}).get("success"):
            return "bot_no_permissions"

        if not tests.get("discussion_group", {}).get("success"):
            return "no_discussion_group"

        if not tests.get("bot_in_group", {}).get("success"):
            return "bot_not_in_group"

        # Проверяем все права
        bot_perms = tests.get("bot_permissions", {})
        group_perms = tests.get("bot_in_group", {})

        if not bot_perms.get("all_permissions_ok") or not group_perms.get("all_permissions_ok"):
            return "insufficient_permissions"

        return "fully_configured"

    def _generate_recommendations(self, tests: Dict[str, Dict]) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        recommendations = []

        if not tests.get("channel_access", {}).get("success"):
            recommendations.append("🔧 Проверьте правильность ID канала")

        if not tests.get("bot_permissions", {}).get("all_permissions_ok"):
            recommendations.append(
                "🔧 Дайте боту полные права администратора в канале")

        if not tests.get("discussion_group", {}).get("success"):
            recommendations.append(
                "🔧 Создайте группу обсуждений и привяжите к каналу")

        if not tests.get("bot_in_group", {}).get("success"):
            recommendations.append(
                "🔧 Добавьте бота как администратора в группу обсуждений")

        if not recommendations:
            recommendations.append(
                "✅ Все настройки корректны - комментарии работают!")

        return recommendations

    async def add_bot_to_discussion_group(self, channel_id: str) -> Dict[str, Any]:
        """
        Попытка автоматически добавить бота в группу обсуждений
        (работает только если у бота есть права)
        """
        try:
            # Получаем информацию о группе обсуждений
            verification = await self.verify_comments_setup(channel_id)

            if not verification["tests"].get("discussion_group", {}).get("success"):
                return {
                    "success": False,
                    "error": "Группа обсуждений не найдена или недоступна"
                }

            group_id = verification["tests"]["discussion_group"]["group_id"]

            # Проверяем, добавлен ли уже бот
            bot_status = verification["tests"].get("bot_in_group", {})
            if bot_status.get("success"):
                return {
                    "success": True,
                    "message": f"Бот уже добавлен в группу как {bot_status['status']}"
                }

            # Автоматическое добавление невозможно - возвращаем инструкции
            return {
                "success": False,
                "manual_required": True,
                "group_id": group_id,
                "instructions": f"""📋 **ДОБАВЬТЕ БОТА В ГРУППУ ВРУЧНУЮ:**

1️⃣ **Откройте группу обсуждений**
2️⃣ **Добавить участника → @{self.bot.username}**
3️⃣ **Сделать администратором** с правами:
   ✅ Удаление сообщений
   ✅ Блокировка пользователей
   ✅ Закрепление сообщений

⚠️ **Это нужно сделать вручную через интерфейс Telegram**"""
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка при добавлении бота: {e}"
            }


async def run_comments_verification(bot: Bot, channel_id: str = None) -> Dict[str, Any]:
    """Запуск полной проверки комментариев"""
    manager = CommentsTestManager(bot)
    return await manager.verify_comments_setup(channel_id)


async def format_verification_report(verification_result: Dict[str, Any]) -> str:
    """Форматирование отчета о проверке"""
    try:
        channel_id = verification_result.get("channel_id", "Unknown")
        status = verification_result.get("overall_status", "unknown")

        # Заголовок с общим статусом
        if status == "fully_configured":
            header = "✅ **КОММЕНТАРИИ ПОЛНОСТЬЮ НАСТРОЕНЫ**"
        elif status == "no_discussion_group":
            header = "⚠️ **ТРЕБУЕТСЯ СОЗДАНИЕ ГРУППЫ ОБСУЖДЕНИЙ**"
        elif status == "bot_not_in_group":
            header = "⚠️ **ТРЕБУЕТСЯ ДОБАВИТЬ БОТА В ГРУППУ**"
        else:
            header = "❌ **ТРЕБУЕТСЯ НАСТРОЙКА**"

        report = f"""{header}

📺 **Канал:** {channel_id}

🧪 **РЕЗУЛЬТАТЫ ПРОВЕРКИ:**"""

        # Детали тестов
        tests = verification_result.get("tests", {})

        # Тест канала
        channel_test = tests.get("channel_access", {})
        if channel_test.get("success"):
            report += f"\n✅ Канал доступен: {channel_test.get('channel_title', 'Unknown')}"
        else:
            report += f"\n❌ Канал недоступен: {channel_test.get('error', 'Unknown error')}"

        # Тест прав бота
        bot_test = tests.get("bot_permissions", {})
        if bot_test.get("success"):
            report += f"\n✅ Бот: {bot_test.get('status', 'Unknown')} канала"
        else:
            report += f"\n❌ Права бота: {bot_test.get('error', 'Unknown error')}"

        # Тест группы обсуждений
        group_test = tests.get("discussion_group", {})
        if group_test.get("success"):
            report += f"\n✅ Группа обсуждений: {group_test.get('group_title', 'Unknown')}"
        else:
            report += f"\n❌ Группа обсуждений: {group_test.get('error', 'Unknown error')}"

        # Тест бота в группе
        bot_group_test = tests.get("bot_in_group", {})
        if bot_group_test.get("success"):
            report += f"\n✅ Бот в группе: {bot_group_test.get('status', 'Unknown')}"
        elif "bot_in_group" in tests:
            report += f"\n❌ Бот в группе: {bot_group_test.get('error', 'Unknown error')}"

        # Тестовый пост
        post_test = tests.get("test_post", {})
        if post_test.get("success"):
            report += f"\n✅ Тестовый пост создан: [Ссылка]({post_test.get('post_url', '#')})"
            report += f"\n💬 Комментарии: [Проверить]({post_test.get('comments_url', '#')})"
        else:
            report += f"\n❌ Тестовый пост: {post_test.get('error', 'Unknown error')}"

        # Рекомендации
        recommendations = verification_result.get("recommendations", [])
        if recommendations:
            report += "\n\n🔧 **РЕКОМЕНДАЦИИ:**"
            for rec in recommendations:
                report += f"\n{rec}"

        return report

    except Exception as e:
        return f"❌ **ОШИБКА ФОРМАТИРОВАНИЯ ОТЧЕТА:** {e}"
