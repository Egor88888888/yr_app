"""
📺 CHANNEL & COMMENTS FIX
Исправление проблем с каналами и комментариями
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any
from telegram import Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType

logger = logging.getLogger(__name__)


class ChannelCommentsSetup:
    """Настройка каналов и комментариев"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def setup_channel_with_comments(self, channel_username: str) -> Dict[str, Any]:
        """
        Настройка канала с поддержкой комментариев

        Args:
            channel_username: Username канала (например, @legalcenter_pro)

        Returns:
            dict: Информация о настройке канала
        """
        try:
            # Проверяем существование канала
            try:
                channel = await self.bot.get_chat(channel_username)
                logger.info(f"✅ Канал найден: {channel.title}")
            except Exception as e:
                logger.error(f"❌ Канал {channel_username} не найден: {e}")
                return {
                    "success": False,
                    "error": f"Канал {channel_username} не найден",
                    "suggestion": "Создайте канал или проверьте правильность username"
                }

            # Проверяем права бота
            try:
                bot_member = await self.bot.get_chat_member(channel_username, self.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    logger.error(
                        f"❌ Бот не является администратором канала {channel_username}")
                    return {
                        "success": False,
                        "error": "Бот не является администратором канала",
                        "suggestion": "Добавьте бота как администратора канала"
                    }
                logger.info(f"✅ Бот является {bot_member.status} канала")
            except Exception as e:
                logger.error(f"❌ Ошибка проверки прав: {e}")
                return {
                    "success": False,
                    "error": "Не удалось проверить права бота",
                    "suggestion": "Убедитесь что бот добавлен в канал"
                }

            # Проверяем наличие связанной группы обсуждений
            discussion_group = None
            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                try:
                    discussion_group = await self.bot.get_chat(channel.linked_chat_id)
                    logger.info(
                        f"✅ Найдена группа обсуждений: {discussion_group.title}")
                except Exception as e:
                    logger.warning(f"⚠️ Группа обсуждений недоступна: {e}")

            # Создаем тестовый пост для проверки
            test_post = await self._create_test_post(channel_username)

            return {
                "success": True,
                "channel_id": channel.id,
                "channel_username": channel_username,
                "channel_title": channel.title,
                "discussion_group": {
                    "id": discussion_group.id if discussion_group else None,
                    "title": discussion_group.title if discussion_group else None,
                    "available": discussion_group is not None
                },
                "test_post": test_post,
                "bot_status": bot_member.status,
                "comments_enabled": discussion_group is not None
            }

        except Exception as e:
            logger.error(f"❌ Критическая ошибка настройки канала: {e}")
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Проверьте настройки канала и права бота"
            }

    async def _create_test_post(self, channel_username: str) -> Dict[str, Any]:
        """Создание тестового поста для проверки"""
        try:
            # Тест с исправленным markdown
            from .markdown_fix import prepare_telegram_message

            test_content = """🧪 **ТЕСТОВЫЙ ПОСТ**

✅ **Проверка системы:**
• Канал подключен
• Бот работает
• Комментарии настроены

💬 **Проверьте комментарии:** можете ли вы оставить комментарий под этим постом?

📱 **Консультация:** /start"""

            message_data = prepare_telegram_message(test_content)

            # Добавляем кнопку для проверки
            keyboard = [[
                InlineKeyboardButton("📱 Проверить бота",
                                     url=f"https://t.me/{self.bot.username}")
            ]]

            message = await self.bot.send_message(
                channel_username,
                **message_data,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            logger.info(f"✅ Тестовый пост создан: {message.message_id}")
            return {
                "success": True,
                "message_id": message.message_id,
                "url": f"https://t.me/{channel_username.replace('@', '')}/{message.message_id}"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка создания тестового поста: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def enable_comments_for_channel(self, channel_username: str) -> Dict[str, Any]:
        """
        Включение комментариев для канала

        Инструкция для администратора:
        1. Создать группу обсуждений
        2. Связать её с каналом
        3. Добавить бота в группу как администратора
        """
        try:
            instructions = f"""📝 **НАСТРОЙКА КОММЕНТАРИЕВ ДЛЯ КАНАЛА**

🔧 **Автоматическая настройка невозможна**
Telegram API не позволяет создавать группы обсуждений автоматически.

📋 **Ручная настройка (для админа канала):**

1️⃣ **Создать группу обсуждений:**
   • Создайте новую группу
   • Название: "{channel_username} - Обсуждения"
   • Добавьте бота @{self.bot.username} как администратора

2️⃣ **Связать группу с каналом:**
   • Зайдите в настройки канала {channel_username}
   • Выберите "Управление" → "Обсуждения"
   • Выберите созданную группу

3️⃣ **Проверить настройки:**
   • Опубликуйте тестовый пост в канале
   • Проверьте что под постом есть кнопка "Комментарии"
   • Убедитесь что комментарии работают

✅ **После настройки комментарии будут работать автоматически!**"""

            return {
                "success": True,
                "instructions": instructions,
                "auto_setup_possible": False,
                "next_steps": [
                    "Создать группу обсуждений",
                    "Связать с каналом",
                    "Добавить бота в группу",
                    "Проверить функциональность"
                ]
            }

        except Exception as e:
            logger.error(f"❌ Ошибка генерации инструкций: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def quick_channel_fix(bot: Bot, channel_username: str = None) -> Dict[str, Any]:
    """
    Быстрое исправление проблем с каналом

    Args:
        bot: Telegram Bot instance
        channel_username: Username канала (по умолчанию создаст новый)
    """
    setup = ChannelCommentsSetup(bot)

    # Если канал не указан, предлагаем создать новый
    if not channel_username:
        return {
            "success": False,
            "error": "Канал не указан",
            "suggestion": "Создайте канал и вызовите: quick_channel_fix(bot, '@your_channel')",
            "recommended_channel": "@legalcenter_pro"
        }

    # Настраиваем канал
    result = await setup.setup_channel_with_comments(channel_username)

    if result["success"]:
        # Обновляем переменные окружения для production
        env_update = {
            "TARGET_CHANNEL_ID": result["channel_username"],
            "CHANNEL_ID": result["channel_username"],
            "CHANNEL_USERNAME": result["channel_username"]
        }

        result["env_update"] = env_update
        result["deployment_instructions"] = f"""
🚀 **ДЛЯ ОБНОВЛЕНИЯ PRODUCTION:**

1️⃣ **Обновить переменные окружения в Railway:**
   TARGET_CHANNEL_ID={result["channel_username"]}
   CHANNEL_ID={result["channel_username"]}

2️⃣ **Перезапустить приложение:**
   git push origin main

3️⃣ **Проверить автопостинг:**
   /admin → SMM → Принудительный пост
"""

    return result


def get_channel_status_report(bot: Bot) -> Dict[str, Any]:
    """Получение отчета о статусе канала"""
    current_channel = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
        'CHANNEL_ID') or '@test_legal_channel'

    return {
        "current_channel": current_channel,
        "channel_exists": current_channel != '@test_legal_channel',
        "issues": {
            "channel_not_found": current_channel == '@test_legal_channel',
            "no_comments": True,  # Предполагаем что нет комментариев
            "markdown_broken": True  # Предполагаем что markdown сломан
        },
        "fixes_available": True,
        "next_action": "Вызвать quick_channel_fix() для исправления"
    }
