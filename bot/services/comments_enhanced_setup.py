"""
🚀 ENHANCED COMMENTS SETUP - PRODUCTION READY
Умная система настройки и управления комментариями для продакшн среды
"""

import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType, ParseMode

logger = logging.getLogger(__name__)


class EnhancedCommentsManager:
    """Продакшн система управления комментариями с автоматическими fallback"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.discussion_groups_cache = {}
        self.fallback_enabled = True
        self.admin_notifications_enabled = True
        self.stats = {
            "comments_requests": 0,
            "fallback_used": 0,
            "discussion_groups_found": 0,
            "manual_setup_required": 0
        }

    async def ensure_comments_production_ready(self, channel_id: str, message_id: int = None) -> Dict[str, Any]:
        """
        ПРОДАКШН метод обеспечения работающих комментариев для поста

        Args:
            channel_id: ID канала
            message_id: ID сообщения (опционально)

        Returns:
            dict: Полная информация о настройке комментариев
        """
        try:
            self.stats["comments_requests"] += 1

            # 1. Проверяем кэш
            if channel_id in self.discussion_groups_cache:
                cached_info = self.discussion_groups_cache[channel_id]
                if cached_info["status"] == "working" and cached_info["last_check"] > datetime.now() - timedelta(hours=1):
                    return await self._create_working_comments_response(cached_info, message_id)

            # 2. Проводим полную диагностику
            diagnostic_result = await self._run_enhanced_diagnostic(channel_id)

            # 3. Обновляем кэш
            self.discussion_groups_cache[channel_id] = {
                "status": "working" if diagnostic_result["comments_working"] else "requires_setup",
                "last_check": datetime.now(),
                "diagnostic": diagnostic_result
            }

            # 4. Возвращаем результат в зависимости от статуса
            if diagnostic_result["comments_working"]:
                self.stats["discussion_groups_found"] += 1
                return await self._create_working_comments_response(diagnostic_result, message_id)
            else:
                self.stats["manual_setup_required"] += 1
                return await self._create_setup_required_response(diagnostic_result, channel_id, message_id)

        except Exception as e:
            logger.error(
                f"❌ Критическая ошибка в ensure_comments_production_ready: {e}")
            return await self._create_fallback_response(channel_id, message_id, str(e))

    async def _run_enhanced_diagnostic(self, channel_id: str) -> Dict[str, Any]:
        """Расширенная диагностика системы комментариев"""
        try:
            logger.info(f"🔍 Enhanced diagnostic for channel: {channel_id}")

            # Проверяем канал
            channel = await self.bot.get_chat(channel_id)

            # Проверяем группу обсуждений
            discussion_group_info = None
            has_discussion_group = False

            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                try:
                    discussion_group = await self.bot.get_chat(channel.linked_chat_id)
                    discussion_group_info = {
                        "id": discussion_group.id,
                        "title": discussion_group.title,
                        "type": discussion_group.type.value,
                        "member_count": getattr(discussion_group, 'member_count', 0)
                    }
                    has_discussion_group = True
                    logger.info(
                        f"✅ Discussion group found: {discussion_group.title}")
                except Exception as e:
                    logger.warning(f"⚠️ Discussion group access error: {e}")

            # Проверяем права бота
            bot_permissions = await self._check_bot_permissions(channel_id)

            return {
                "comments_working": has_discussion_group,
                "channel_info": {
                    "id": channel.id,
                    "title": channel.title,
                    "username": getattr(channel, 'username', None),
                    "type": channel.type.value
                },
                "discussion_group": discussion_group_info,
                "bot_permissions": bot_permissions,
                "diagnostic_time": datetime.now(),
                "needs_setup": not has_discussion_group
            }

        except Exception as e:
            logger.error(f"❌ Enhanced diagnostic failed: {e}")
            return {
                "comments_working": False,
                "error": str(e),
                "needs_setup": True,
                "diagnostic_time": datetime.now()
            }

    async def _check_bot_permissions(self, channel_id: str) -> Dict[str, Any]:
        """Проверка прав бота в канале"""
        try:
            bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)

            return {
                "status": bot_member.status,
                "can_post": bot_member.status in ['administrator', 'creator'],
                "can_delete": getattr(bot_member, 'can_delete_messages', False),
                "can_pin": getattr(bot_member, 'can_pin_messages', False)
            }
        except Exception as e:
            logger.warning(f"⚠️ Cannot check bot permissions: {e}")
            return {
                "status": "unknown",
                "can_post": False,
                "error": str(e)
            }

    async def _create_working_comments_response(self, info: Dict[str, Any], message_id: int = None) -> Dict[str, Any]:
        """Создание ответа для работающих комментариев"""
        try:
            comments_url = self._generate_comments_url(info, message_id)

            return {
                "success": True,
                "comments_working": True,
                "comments_url": comments_url,
                "button_text": "💬 Обсудить в группе",
                "button_url": comments_url,
                "status_message": "Комментарии настроены и работают",
                "discussion_group": info.get("discussion_group") or info.get("diagnostic", {}).get("discussion_group"),
                "fallback_used": False
            }
        except Exception as e:
            logger.error(f"❌ Error creating working comments response: {e}")
            return await self._create_fallback_response(info.get("channel_info", {}).get("id", "unknown"), message_id, str(e))

    async def _create_setup_required_response(self, diagnostic: Dict[str, Any], channel_id: str, message_id: int = None) -> Dict[str, Any]:
        """Создание ответа когда требуется настройка"""
        try:
            if self.fallback_enabled:
                self.stats["fallback_used"] += 1
                fallback_url = await self._generate_fallback_url(channel_id, message_id)

                # Уведомляем админа о необходимости настройки
                if self.admin_notifications_enabled:
                    asyncio.create_task(
                        self._notify_admin_setup_required(diagnostic))

                return {
                    "success": True,
                    "comments_working": False,
                    "comments_url": fallback_url,
                    "button_text": "📱 Получить консультацию",
                    "button_url": fallback_url,
                    "status_message": "Комментарии требуют настройки, используется fallback",
                    "setup_required": True,
                    "setup_instructions": self._generate_setup_instructions(diagnostic),
                    "fallback_used": True
                }
            else:
                return {
                    "success": False,
                    "comments_working": False,
                    "error": "Комментарии не настроены и fallback отключен",
                    "setup_required": True,
                    "setup_instructions": self._generate_setup_instructions(diagnostic)
                }

        except Exception as e:
            logger.error(f"❌ Error creating setup required response: {e}")
            return await self._create_fallback_response(channel_id, message_id, str(e))

    async def _create_fallback_response(self, channel_id: str, message_id: int = None, error: str = None) -> Dict[str, Any]:
        """Создание fallback ответа при критических ошибках"""
        try:
            fallback_url = await self._generate_fallback_url(channel_id, message_id)
            self.stats["fallback_used"] += 1

            return {
                "success": True,
                "comments_working": False,
                "comments_url": fallback_url,
                "button_text": "📱 Получить консультацию",
                "button_url": fallback_url,
                "status_message": f"Использован fallback{': ' + error if error else ''}",
                "fallback_used": True,
                "error": error
            }
        except Exception as e:
            logger.error(f"❌ Critical fallback error: {e}")
            # Последняя линия защиты
            return {
                "success": False,
                "comments_working": False,
                "error": f"Critical failure: {e}",
                "button_text": "📱 Получить консультацию",
                "button_url": f"https://t.me/{os.getenv('BOT_USERNAME', 'yur_lawyer_bot').replace('@', '')}",
                "fallback_used": True
            }

    def _generate_comments_url(self, info: Dict[str, Any], message_id: int = None) -> str:
        """Генерация URL для комментариев"""
        try:
            # Получаем информацию о канале
            channel_info = info.get("channel_info") or info.get(
                "diagnostic", {}).get("channel_info", {})
            channel_id = channel_info.get("id")
            channel_username = channel_info.get("username")

            if not message_id:
                message_id = 1  # Fallback к первому сообщению

            # Если есть username канала
            if channel_username:
                return f"https://t.me/{channel_username}/{message_id}?comment=1"

            # Если есть численный ID
            elif channel_id:
                if str(channel_id).startswith('-100'):
                    numeric_id = str(channel_id)[4:]  # Убираем -100 префикс
                    return f"https://t.me/c/{numeric_id}/{message_id}?comment=1"

            # Fallback
            raise Exception(
                "Cannot generate comments URL - insufficient channel info")

        except Exception as e:
            logger.warning(f"⚠️ Cannot generate comments URL: {e}")
            raise

    async def _generate_fallback_url(self, channel_id: str, message_id: int = None) -> str:
        """Генерация fallback URL"""
        try:
            bot_username = self.bot.username.replace(
                "@", "") if self.bot.username else os.getenv("BOT_USERNAME", "yur_lawyer_bot").replace("@", "")

            if message_id:
                return f"https://t.me/{bot_username}?start=discuss_{message_id}"
            else:
                return f"https://t.me/{bot_username}?start=consultation"

        except Exception as e:
            logger.warning(f"⚠️ Fallback URL generation error: {e}")
            return f"https://t.me/{os.getenv('BOT_USERNAME', 'yur_lawyer_bot').replace('@', '')}"

    def _generate_setup_instructions(self, diagnostic: Dict[str, Any]) -> str:
        """Генерация персонализированных инструкций по настройке"""
        try:
            channel_info = diagnostic.get("channel_info", {})
            channel_name = channel_info.get("title", "Ваш канал")
            channel_id = channel_info.get(
                "username") or channel_info.get("id", "your_channel")

            return f"""📋 **НАСТРОЙКА КОММЕНТАРИЕВ ДЛЯ "{channel_name}"**

🎯 **БЫСТРАЯ НАСТРОЙКА (5 минут):**

1️⃣ **Создать группу обсуждений:**
   • Telegram → Новая группа
   • Название: "{channel_name} - Обсуждения"
   • Добавить @{self.bot.username} как админа

2️⃣ **Связать с каналом:**
   • Настройки канала → Управление → Обсуждения
   • Выбрать созданную группу

3️⃣ **Проверить результат:**
   • Опубликовать тестовый пост
   • Убедиться что появилась кнопка комментариев

✅ **ПОСЛЕ НАСТРОЙКИ:**
Все посты будут автоматически поддерживать комментарии!

⚠️ **ВАЖНО:** Эта настройка делается только один раз."""

        except Exception as e:
            logger.error(f"❌ Error generating setup instructions: {e}")
            return "Требуется ручная настройка группы обсуждений через интерфейс Telegram"

    async def _notify_admin_setup_required(self, diagnostic: Dict[str, Any]):
        """Уведомление администратора о необходимости настройки"""
        try:
            admin_chat_id = os.getenv('ADMIN_CHAT_ID')
            if not admin_chat_id:
                return

            channel_info = diagnostic.get("channel_info", {})
            channel_name = channel_info.get("title", "Unknown")

            notification = f"""🔔 **ТРЕБУЕТСЯ НАСТРОЙКА КОММЕНТАРИЕВ**

📋 **Канал:** {channel_name}
⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🚫 **Статус:** Комментарии не работают

🔧 **Действие:** Настройте группу обсуждений для канала

💡 **Используется fallback** - пользователи перенаправляются к боту"""

            await self.bot.send_message(
                chat_id=admin_chat_id,
                text=notification,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to notify admin: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики работы системы комментариев"""
        return {
            **self.stats,
            "cache_size": len(self.discussion_groups_cache),
            "cache_entries": list(self.discussion_groups_cache.keys()),
            "fallback_percentage": round(self.stats["fallback_used"] / max(self.stats["comments_requests"], 1) * 100, 1),
            "success_rate": round((self.stats["discussion_groups_found"] / max(self.stats["comments_requests"], 1)) * 100, 1)
        }

    async def clear_cache(self):
        """Очистка кэша для принудительной перепроверки"""
        self.discussion_groups_cache.clear()
        logger.info("🧹 Comments cache cleared")

    async def test_comments_system(self, channel_id: str) -> Dict[str, Any]:
        """Тестирование системы комментариев"""
        try:
            logger.info(f"🧪 Testing comments system for {channel_id}")

            # Очищаем кэш для свежей проверки
            if channel_id in self.discussion_groups_cache:
                del self.discussion_groups_cache[channel_id]

            # Проводим полную диагностику
            result = await self.ensure_comments_production_ready(channel_id, 1)

            return {
                "test_passed": result["success"],
                "comments_working": result["comments_working"],
                "fallback_used": result.get("fallback_used", False),
                "test_time": datetime.now(),
                "result": result
            }

        except Exception as e:
            logger.error(f"❌ Comments system test failed: {e}")
            return {
                "test_passed": False,
                "error": str(e),
                "test_time": datetime.now()
            }


# Глобальный экземпляр для использования в других модулях
_enhanced_comments_manager = None


def get_enhanced_comments_manager(bot: Bot = None) -> EnhancedCommentsManager:
    """Получение глобального экземпляра EnhancedCommentsManager"""
    global _enhanced_comments_manager

    if _enhanced_comments_manager is None and bot:
        _enhanced_comments_manager = EnhancedCommentsManager(bot)

    return _enhanced_comments_manager


async def ensure_production_comments(bot: Bot, channel_id: str, message_id: int = None) -> Dict[str, Any]:
    """Быстрый доступ к продакшн системе комментариев"""
    try:
        manager = get_enhanced_comments_manager(bot)
        if not manager:
            # Создаем временный экземпляр если глобального нет
            manager = EnhancedCommentsManager(bot)

        return await manager.ensure_comments_production_ready(channel_id, message_id)

    except Exception as e:
        logger.error(f"❌ Production comments system error: {e}")
        return {
            "success": False,
            "comments_working": False,
            "error": str(e),
            "button_text": "📱 Получить консультацию",
            "button_url": f"https://t.me/{os.getenv('BOT_USERNAME', 'yur_lawyer_bot').replace('@', '')}",
            "fallback_used": True
        }
