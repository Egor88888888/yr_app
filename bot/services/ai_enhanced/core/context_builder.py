"""
ContextBuilder - построение контекста для AI с учетом всех данных.

Собирает:
- Профиль пользователя
- Историю диалогов
- Результаты ML классификации
- Предыдущие взаимодействия
- Дополнительный контекст

Возвращает AIContext - полный контекст для генерации ответа.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import async_sessionmaker
from ...ai_enhanced_models import (
    UserProfile, DialogueSession, DialogueMessage, UserPreference
)

logger = logging.getLogger(__name__)


@dataclass
class AIContext:
    """Полный контекст для AI генерации"""
    # Основное сообщение
    message: str
    user_id: int

    # Профиль пользователя
    user_profile: Optional[UserProfile] = None

    # История диалога
    dialogue_history: List[DialogueMessage] = None
    current_session: Optional[DialogueSession] = None

    # ML результаты
    predicted_category: Optional[str] = None
    category_confidence: Optional[float] = None
    category_predictions: Optional[Dict[str, float]] = None

    detected_intent: Optional[str] = None
    intent_confidence: Optional[float] = None

    # Персонализация
    user_preferences: Dict[str, Any] = None
    communication_style: Optional[str] = None
    experience_level: Optional[str] = None

    # Дополнительный контекст
    additional_context: Optional[Dict[str, Any]] = None

    # Метаданные
    context_timestamp: datetime = None

    def __post_init__(self):
        if self.context_timestamp is None:
            self.context_timestamp = datetime.now()
        if self.dialogue_history is None:
            self.dialogue_history = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.category_predictions is None:
            self.category_predictions = {}


class ContextBuilder:
    """Построитель контекста для AI"""

    def __init__(self):
        self.max_history_messages = 10  # максимум сообщений в истории
        self.history_timeframe_hours = 24  # рассматриваем историю за последние 24 часа

    async def build_context(
        self,
        user_id: int,
        message: str,
        user_profile: Optional[UserProfile] = None,
        session: Optional[DialogueSession] = None,
        classification: Optional[Dict[str, Any]] = None,
        intent: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AIContext:
        """Построение полного контекста для AI"""
        try:
            # Создаем базовый контекст
            context = AIContext(
                message=message,
                user_id=user_id,
                additional_context=additional_context or {}
            )

            # Заполняем контекст данными
            context.user_profile = user_profile
            context.current_session = session

            # Добавляем ML результаты
            if classification:
                context.predicted_category = classification.get('category')
                context.category_confidence = classification.get('confidence')
                context.category_predictions = classification.get(
                    'all_predictions', {})

            if intent:
                context.detected_intent = intent.get('intent')
                context.intent_confidence = intent.get('confidence')

            # Заполняем стиль общения из профиля
            if context.user_profile:
                context.communication_style = context.user_profile.preferred_style
                context.experience_level = context.user_profile.experience_level

            return context

        except Exception as e:
            logger.error(f"Failed to build context for user {user_id}: {e}")
            # Возвращаем минимальный контекст при ошибке
            return AIContext(message=message, user_id=user_id)
