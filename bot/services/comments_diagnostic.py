"""
💬 ДИАГНОСТИКА КОММЕНТАРИЕВ
Система диагностики и настройки комментариев для Telegram каналов
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any
from telegram import Bot, Chat
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType

logger = logging.getLogger(__name__)


class CommentsDiagnostic:
    """Диагностика системы комментариев"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def diagnose_comments_system(self, channel_id: str = None) -> Dict[str, Any]:
        """
        Полная диагностика системы комментариев

        Args:
            channel_id: ID канала для проверки

        Returns:
            dict: Результат диагностики с инструкциями
        """
        try:
            # Используем канал из переменных окружения если не указан
            if not channel_id:
                channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                    'CHANNEL_ID') or '@test_legal_channel'

            logger.info(f"🔍 Диагностика комментариев для канала: {channel_id}")

            # Проверяем канал
            channel_status = await self._check_channel_access(channel_id)
            if not channel_status["success"]:
                return channel_status

            # Проверяем группу обсуждений
            discussion_status = await self._check_discussion_group(channel_id)

            # Проверяем права бота
            bot_permissions = await self._check_bot_permissions(channel_id)

            # Собираем полный отчет
            report = {
                "success": True,
                "channel_id": channel_id,
                "channel_info": channel_status.get("channel_info"),
                "discussion_group": discussion_status,
                "bot_permissions": bot_permissions,
                "comments_working": discussion_status.get("has_discussion_group", False),
                "next_steps": self._generate_next_steps(discussion_status, bot_permissions),
                "manual_setup_required": not discussion_status.get("has_discussion_group", False)
            }

            return report

        except Exception as e:
            logger.error(f"❌ Ошибка диагностики комментариев: {e}")
            return {
                "success": False,
                "error": str(e),
                "manual_setup_required": True,
                "next_steps": self._get_basic_setup_instructions(channel_id or "ваш_канал")
            }

    async def _check_channel_access(self, channel_id: str) -> Dict[str, Any]:
        """Проверка доступа к каналу"""
        try:
            channel = await self.bot.get_chat(channel_id)

            return {
                "success": True,
                "channel_info": {
                    "id": channel.id,
                    "title": channel.title,
                    "username": channel.username,
                    "type": channel.type.value
                }
            }

        except Exception as e:
            logger.error(f"❌ Канал {channel_id} недоступен: {e}")
            return {
                "success": False,
                "error": f"Канал недоступен: {e}",
                "next_steps": [
                    "1. Проверьте правильность ID канала",
                    "2. Убедитесь что бот добавлен в канал как администратор",
                    "3. Проверьте переменную TARGET_CHANNEL_ID в Railway"
                ]
            }

    async def _check_discussion_group(self, channel_id: str) -> Dict[str, Any]:
        """Проверка группы обсуждений"""
        try:
            channel = await self.bot.get_chat(channel_id)

            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                try:
                    discussion_group = await self.bot.get_chat(channel.linked_chat_id)
                    return {
                        "has_discussion_group": True,
                        "group_info": {
                            "id": discussion_group.id,
                            "title": discussion_group.title,
                            "type": discussion_group.type.value
                        },
                        "status": "✅ Группа обсуждений настроена и работает"
                    }
                except Exception as e:
                    return {
                        "has_discussion_group": False,
                        "error": f"Группа обсуждений недоступна: {e}",
                        "status": "⚠️ Группа обсуждений существует, но недоступна боту"
                    }
            else:
                return {
                    "has_discussion_group": False,
                    "status": "❌ Группа обсуждений не настроена"
                }

        except Exception as e:
            return {
                "has_discussion_group": False,
                "error": str(e),
                "status": "❌ Не удалось проверить группу обсуждений"
            }

    async def _check_bot_permissions(self, channel_id: str) -> Dict[str, Any]:
        """Проверка прав бота в канале"""
        try:
            bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)

            permissions = {
                "is_admin": bot_member.status in ['administrator', 'creator'],
                "can_post": getattr(bot_member, 'can_post_messages', False),
                "can_edit": getattr(bot_member, 'can_edit_messages', False),
                "can_delete": getattr(bot_member, 'can_delete_messages', False),
                "status": bot_member.status
            }

            return {
                "success": True,
                "permissions": permissions,
                "sufficient_permissions": permissions["is_admin"] and permissions["can_post"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sufficient_permissions": False
            }

    def _generate_next_steps(self, discussion_status: Dict, bot_permissions: Dict) -> list:
        """Генерация следующих шагов для настройки"""
        steps = []

        if not discussion_status.get("has_discussion_group"):
            steps.extend([
                "🎯 **НАСТРОЙКА КОММЕНТАРИЕВ (ОБЯЗАТЕЛЬНО РУЧНАЯ)**",
                "",
                "📱 **ШАГ 1: Создание группы обсуждений**",
                "• Telegram → Новый чат → Новая группа",
                "• Название: 'Legal Center - Обсуждения'",
                "• Добавьте себя как единственного участника",
                "",
                f"🤖 **ШАГ 2: Добавление бота в группу**",
                f"• В группе: Участники → Добавить участника",
                f"• Найдите: @{self.bot.username}",
                f"• Добавьте бота в группу",
                f"• Сделайте бота администратором группы",
                f"• Дайте ВСЕ права администратора",
                "",
                "🔗 **ШАГ 3: Связывание группы с каналом**",
                "• Откройте настройки канала",
                "• Управление → Обсуждения",
                "• Выберите созданную группу",
                "• Сохраните изменения",
                "",
                "✅ **РЕЗУЛЬТАТ:**",
                "• Под каждым постом появится кнопка 'Комментарии'",
                "• Пользователи смогут оставлять комментарии",
                "• Комментарии будут отображаться в группе обсуждений"
            ])
        else:
            steps.extend([
                "✅ **КОММЕНТАРИИ УЖЕ НАСТРОЕНЫ**",
                "",
                f"✅ Группа обсуждений: {discussion_status.get('group_info', {}).get('title', 'Найдена')}",
                "✅ Комментарии под постами работают автоматически",
                "",
                "💡 **ПРОВЕРКА:**",
                "• Опубликуйте тестовый пост в канале",
                "• Убедитесь что появилась кнопка 'Комментарии'",
                "• Попробуйте оставить комментарий"
            ])

        if not bot_permissions.get("sufficient_permissions", False):
            steps.extend([
                "",
                "⚠️ **ДОПОЛНИТЕЛЬНО: Права бота**",
                "• Проверьте что бот админ канала",
                "• Дайте боту права на отправку сообщений",
                "• Дайте боту права на редактирование сообщений"
            ])

        return steps

    def _get_basic_setup_instructions(self, channel_id: str) -> list:
        """Базовые инструкции по настройке"""
        return [
            "📋 **НАСТРОЙКА КОММЕНТАРИЕВ ДЛЯ TELEGRAM КАНАЛА**",
            "",
            "❗ **ВАЖНО: Комментарии настраиваются только ВРУЧНУЮ**",
            "",
            "1️⃣ Создайте группу обсуждений",
            f"2️⃣ Добавьте @{self.bot.username} как админа группы",
            "3️⃣ В настройках канала свяжите группу",
            "4️⃣ Проверьте результат тестовым постом",
            "",
            "💡 После настройки комментарии будут работать автоматически!"
        ]

    async def test_comments_functionality(self, channel_id: str = None) -> Dict[str, Any]:
        """Тестирование функциональности комментариев"""
        try:
            if not channel_id:
                channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                    'CHANNEL_ID') or '@test_legal_channel'

            # Проверяем состояние
            diagnosis = await self.diagnose_comments_system(channel_id)

            if not diagnosis.get("comments_working"):
                return {
                    "success": False,
                    "message": "Комментарии не настроены",
                    "diagnosis": diagnosis
                }

            # Создаем тестовый пост
            test_message = """🧪 **ТЕСТ КОММЕНТАРИЕВ**

Это тестовый пост для проверки работы комментариев.

💬 Если вы видите кнопку "Комментарии" под этим постом - система работает правильно!

⏱ Тестовый пост будет удален через 2 минуты."""

            sent_message = await self.bot.send_message(
                chat_id=channel_id,
                text=test_message,
                parse_mode='Markdown'
            )

            # Планируем удаление через 2 минуты
            asyncio.create_task(self._delete_test_message_later(
                channel_id, sent_message.message_id))

            return {
                "success": True,
                "message": "Тестовый пост создан для проверки комментариев",
                "test_post_id": sent_message.message_id,
                "diagnosis": diagnosis
            }

        except Exception as e:
            logger.error(f"❌ Ошибка тестирования комментариев: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Не удалось создать тестовый пост"
            }

    async def _delete_test_message_later(self, chat_id: str, message_id: int):
        """Удаление тестового сообщения через 2 минуты"""
        try:
            await asyncio.sleep(120)  # 2 минуты
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"🗑 Тестовый пост {message_id} удален")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить тестовый пост: {e}")


def get_comments_diagnostic(bot: Bot) -> CommentsDiagnostic:
    """Получить экземпляр диагностики комментариев"""
    return CommentsDiagnostic(bot)
