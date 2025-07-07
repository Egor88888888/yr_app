"""
Dialogue Memory - система памяти диалогов.

Управляет долгосрочной памятью диалогов, извлекает релевантный контекст.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, desc
from ...db import async_sessionmaker
from ..ai_enhanced_models import DialogueSession, DialogueMessage, UserProfile

logger = logging.getLogger(__name__)


class DialogueMemory:
    """Система памяти диалогов"""

    def __init__(self):
        self.initialized = False
        self.memory_cache = {}  # кэш для быстрого доступа

    async def initialize(self):
        """Инициализация системы памяти"""
        try:
            logger.info("🔧 Initializing Dialogue Memory...")
            self.initialized = True
            logger.info("✅ Dialogue Memory initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Dialogue Memory: {e}")
            self.initialized = False

    async def get_relevant_context(
        self,
        user_id: int,
        current_message: str,
        limit: int = 5
    ) -> List[DialogueMessage]:
        """Получение релевантного контекста из истории"""
        try:
            async with async_sessionmaker() as session:
                # Получаем последние сообщения пользователя
                result = await session.execute(
                    select(DialogueMessage)
                    .join(DialogueSession)
                    .where(DialogueSession.user_id == user_id)
                    .order_by(desc(DialogueMessage.created_at))
                    .limit(limit * 2)  # берем больше для фильтрации
                )

                messages = result.scalars().all()

                # Простая фильтрация по релевантности (можно улучшить ML)
                relevant_messages = []
                current_lower = current_message.lower()

                for msg in messages:
                    # Проверяем совпадение ключевых слов
                    msg_lower = msg.content.lower()
                    common_words = set(current_lower.split()
                                       ) & set(msg_lower.split())

                    if len(common_words) > 1:  # есть общие слова
                        relevant_messages.append(msg)

                    if len(relevant_messages) >= limit:
                        break

                return relevant_messages

        except Exception as e:
            logger.error(f"Failed to get relevant context: {e}")
            return []

    async def store_interaction(
        self,
        session_id: int,
        user_message: str,
        ai_response: str
    ):
        """Сохранение взаимодействия в память"""
        try:
            async with async_sessionmaker() as db_session:
                # Сохраняем сообщение пользователя
                user_msg = DialogueMessage(
                    session_id=session_id,
                    role="user",
                    content=user_message
                )
                db_session.add(user_msg)

                # Сохраняем ответ AI
                ai_msg = DialogueMessage(
                    session_id=session_id,
                    role="assistant",
                    content=ai_response
                )
                db_session.add(ai_msg)

                await db_session.commit()

        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья системы памяти"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "cache_size": len(self.memory_cache)
        }
