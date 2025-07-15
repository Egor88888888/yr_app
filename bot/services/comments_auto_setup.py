"""
🔧 AUTOMATIC COMMENTS SETUP
Автоматическая настройка комментариев для всех постов
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType, ParseMode

logger = logging.getLogger(__name__)


class AutoCommentsManager:
    """Автоматическое управление комментариями для всех постов"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.discussion_groups = {}  # Кэш групп обсуждений для каналов

    async def setup_channel_comments_auto(self, channel_id: str) -> Dict[str, Any]:
        """
        Автоматическая настройка комментариев для канала

        Args:
            channel_id: ID канала (@legalcenter_pro или числовой ID)

        Returns:
            dict: Результат настройки комментариев
        """
        try:
            logger.info(f"🔧 Настройка комментариев для канала: {channel_id}")

            # Проверяем канал
            try:
                channel = await self.bot.get_chat(channel_id)
            except Exception as e:
                logger.error(f"❌ Канал {channel_id} не найден: {e}")
                return {
                    "success": False,
                    "error": f"Канал не найден: {e}",
                    "comments_enabled": False
                }

            # Проверяем есть ли уже группа обсуждений
            discussion_group = None
            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                try:
                    discussion_group = await self.bot.get_chat(channel.linked_chat_id)
                    logger.info(
                        f"✅ Найдена существующая группа: {discussion_group.title}")

                    # Сохраняем в кэш
                    self.discussion_groups[channel_id] = {
                        'id': discussion_group.id,
                        'title': discussion_group.title,
                        'enabled': True
                    }

                    return {
                        "success": True,
                        "comments_enabled": True,
                        "discussion_group": {
                            "id": discussion_group.id,
                            "title": discussion_group.title
                        },
                        "message": "Комментарии уже настроены и работают"
                    }

                except Exception as e:
                    logger.warning(f"⚠️ Группа обсуждений недоступна: {e}")

            # Если группы нет, возвращаем инструкции по ручной настройке
            return {
                "success": False,
                "comments_enabled": False,
                "needs_manual_setup": True,
                "instructions": self._get_manual_setup_instructions(channel_id),
                "error": "Требуется ручная настройка группы обсуждений"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка настройки комментариев: {e}")
            return {
                "success": False,
                "error": str(e),
                "comments_enabled": False
            }

    def _get_manual_setup_instructions(self, channel_id: str) -> str:
        """Получить инструкции по ручной настройке"""
        return f"""📋 **НАСТРОЙКА КОММЕНТАРИЕВ ДЛЯ {channel_id}**

🔧 **ПОШАГОВАЯ ИНСТРУКЦИЯ:**

1️⃣ **Создать группу обсуждений:**
   • Telegram → Создать группу
   • Название: "Legal Center - Обсуждения"
   • Добавить @{self.bot.username} как админа
   • Дать боту ВСЕ права администратора

2️⃣ **Связать группу с каналом:**
   • Настройки канала {channel_id}
   • "Управление" → "Обсуждения"
   • Выбрать созданную группу
   • Сохранить изменения

3️⃣ **Проверить результат:**
   • Опубликовать тестовый пост
   • Проверить что появилась кнопка комментариев
   • Убедиться что комментарии работают

✅ **ПОСЛЕ НАСТРОЙКИ:**
Все новые посты будут автоматически поддерживать комментарии!"""

    async def ensure_comments_for_post(
        self,
        channel_id: str,
        message_id: int,
        fallback_to_bot: bool = True
    ) -> str:
        """
        Убедиться что для поста доступны комментарии

        Args:
            channel_id: ID канала
            message_id: ID сообщения
            fallback_to_bot: Использовать бота как fallback если комментарии не настроены

        Returns:
            str: URL для комментариев
        """
        try:
            # Проверяем есть ли кэшированная информация о группе
            if channel_id in self.discussion_groups:
                group_info = self.discussion_groups[channel_id]
                if group_info['enabled']:
                    # Возвращаем ссылку на пост с комментариями
                    return self._create_comments_url(channel_id, message_id)

            # Пытаемся автоматически настроить комментарии
            setup_result = await self.setup_channel_comments_auto(channel_id)

            if setup_result.get('comments_enabled'):
                # Комментарии работают, возвращаем ссылку
                return self._create_comments_url(channel_id, message_id)

            # Если комментарии не настроены и разрешен fallback
            if fallback_to_bot:
                logger.warning(
                    f"⚠️ Комментарии не настроены для {channel_id}, используем fallback")
                try:
                    bot_username = self.bot.username
                    return f"https://t.me/{bot_username}?start=discuss_{message_id}"
                except Exception:
                    # Если бот не инициализирован, используем общий fallback
                    return f"https://t.me/your_bot?start=discuss_{message_id}"

            # Возвращаем ссылку на пост без параметра comment
            return self._create_post_url(channel_id, message_id)

        except Exception as e:
            logger.error(f"❌ Ошибка проверки комментариев: {e}")
            # Fallback на бота с защитой от ошибок инициализации
            try:
                bot_username = self.bot.username
                return f"https://t.me/{bot_username}"
            except Exception:
                # Финальный fallback если бот не инициализирован
                return "https://t.me/your_bot"

    def _create_comments_url(self, channel_id: str, message_id: int) -> str:
        """Создать URL для комментариев к посту"""
        try:
            # Если channel_id начинается с @, это username
            if channel_id.startswith('@'):
                channel_username = channel_id[1:]  # Убираем @
                return f"https://t.me/{channel_username}/{message_id}?comment=1"

            # Если это численный ID канала (например -1001234567890)
            elif channel_id.startswith('-100'):
                # Для численных ID каналов нужен формат t.me/c/ID/MESSAGE_ID
                numeric_id = channel_id[4:]  # Убираем -100 префикс
                return f"https://t.me/c/{numeric_id}/{message_id}?comment=1"

            # Если это обычный численный ID
            elif channel_id.startswith('-'):
                numeric_id = channel_id[1:]  # Убираем - префикс
                return f"https://t.me/c/{numeric_id}/{message_id}?comment=1"

            # Fallback - предполагаем что это username без @
            else:
                return f"https://t.me/{channel_id}/{message_id}?comment=1"

        except Exception as e:
            logger.error(f"❌ Ошибка создания URL комментариев: {e}")
            try:
                bot_username = self.bot.username
                return f"https://t.me/{bot_username}"
            except Exception:
                # Fallback если бот не инициализирован
                return "https://t.me/your_bot"

    def _create_post_url(self, channel_id: str, message_id: int) -> str:
        """Создать URL поста без комментариев"""
        return self._create_comments_url(channel_id, message_id).replace('?comment=1', '')

    async def get_comments_status_for_channels(self, channel_ids: List[str]) -> Dict[str, Dict]:
        """Получить статус комментариев для нескольких каналов"""
        status_results = {}

        for channel_id in channel_ids:
            try:
                result = await self.setup_channel_comments_auto(channel_id)
                status_results[channel_id] = result
            except Exception as e:
                status_results[channel_id] = {
                    "success": False,
                    "error": str(e),
                    "comments_enabled": False
                }

        return status_results

    async def enable_comments_for_all_posts(self, channel_id: str) -> Dict[str, Any]:
        """
        Включить комментарии для всех будущих постов в канале

        ВАЖНО: Это не включает комментарии автоматически, а только проверяет
        готовность канала к поддержке комментариев
        """
        try:
            # Проверяем текущий статус
            status = await self.setup_channel_comments_auto(channel_id)

            if status['comments_enabled']:
                return {
                    "success": True,
                    "message": "✅ Комментарии включены для всех постов",
                    "details": status
                }
            else:
                return {
                    "success": False,
                    "message": "❌ Требуется ручная настройка канала",
                    "instructions": status.get('instructions'),
                    "details": status
                }

        except Exception as e:
            logger.error(f"❌ Ошибка включения комментариев: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_auto_comments_manager(bot):
    """Получить экземпляр менеджера автокомментариев"""
    return AutoCommentsManager(bot)


# Глобальный экземпляр для использования в других модулях
_auto_comments_manager = None


def get_auto_comments_manager(bot: Bot) -> AutoCommentsManager:
    """Получить глобальный экземпляр менеджера комментариев"""
    global _auto_comments_manager
    if _auto_comments_manager is None:
        _auto_comments_manager = AutoCommentsManager(bot)
    return _auto_comments_manager
