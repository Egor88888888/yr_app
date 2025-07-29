"""
Enhanced AI Manager - главный компонент системы улучшенного ИИ.

Объединяет все подсистемы Enhanced AI:
- ML классификация и детекция намерений
- Память диалогов и профилирование пользователей  
- Персонализация и адаптация стиля
- Аналитика и оптимизация ответов

Обеспечивает обратную совместимость с существующим AI API.
"""

import asyncio
import logging
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import async_sessionmaker, User
from ...ai import generate_ai_response as basic_ai_response
from ...ai_enhanced_models import (
    UserProfile, DialogueSession, DialogueMessage, AIMetrics
)
from .context_builder import ContextBuilder, AIContext
from .response_optimizer import ResponseOptimizer
try:
    from ..classification.ml_classifier import MLClassifier, HAS_NUMPY
    ML_AVAILABLE = True
except ImportError:
    HAS_NUMPY = False
    ML_AVAILABLE = False
    # Fallback ML Classifier

    class MLClassifier:
        def __init__(self, *args, **kwargs):
            pass

        async def classify_category(self, *args, **kwargs):
            return {"category": "Семейное право", "confidence": 0.5}
from ..classification.intent_detector import IntentDetector
from ..memory.dialogue_memory import DialogueMemory
from ..memory.user_profiler import UserProfiler
from ..memory.session_manager import SessionManager
from ..personalization.style_adapter import StyleAdapter
from ..analytics.interaction_tracker import InteractionTracker
from ..analytics.quality_analyzer import QualityAnalyzer

logger = logging.getLogger(__name__)


class AIEnhancedManager:
    """Главный менеджер Enhanced AI системы"""

    def __init__(self):
        # Основные компоненты
        self.context_builder = ContextBuilder()
        self.response_optimizer = ResponseOptimizer()

        # ML компоненты с статусом
        self.ml_classifier = MLClassifier()
        self.intent_detector = IntentDetector()

        # Log ML status
        if ML_AVAILABLE and HAS_NUMPY:
            logger.info(
                "🧠 AI Enhanced: Full ML capabilities enabled with numpy")
        elif ML_AVAILABLE:
            logger.warning(
                "🧠 AI Enhanced: ML enabled with fallback (no numpy)")
        else:
            logger.warning(
                "🧠 AI Enhanced: ML disabled, using fallback classifier")

        # Память
        self.dialogue_memory = DialogueMemory()
        self.user_profiler = UserProfiler()
        self.session_manager = SessionManager()

        # Персонализация
        self.style_adapter = StyleAdapter()

        # Аналитика
        self.interaction_tracker = InteractionTracker()
        self.quality_analyzer = QualityAnalyzer()

        # Инициализация
        self._initialized = False

    async def initialize(self):
        """Инициализация всех компонентов"""
        if self._initialized:
            return

        try:
            logger.info("Initializing Enhanced AI system...")

            # Инициализируем компоненты параллельно
            await asyncio.gather(
                self.ml_classifier.initialize(),
                self.intent_detector.initialize(),
                self.dialogue_memory.initialize(),
                self.user_profiler.initialize(),
                self.style_adapter.initialize(),
                return_exceptions=True
            )

            self._initialized = True
            logger.info("Enhanced AI system initialized successfully")

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to initialize Enhanced AI: %s", e)
            raise

    async def generate_response(
        self,
        user_id: int,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Главная функция генерации AI ответа с полным функционалом.

        Args:
            user_id: ID пользователя
            message: сообщение пользователя
            context: дополнительный контекст (опционально)

        Returns:
            Персонализированный AI ответ
        """
        start_time = time.time()

        try:
            # Инициализируем систему если нужно
            if not self._initialized:
                await self.initialize()

            # 1. Получаем/создаем профиль пользователя
            user_profile = await self.user_profiler.get_or_create_profile(user_id)

            # 2. Получаем/создаем сессию диалога
            session = await self.session_manager.get_or_create_session(user_id)

            # 3. Классифицируем сообщение
            classification_result = await self.ml_classifier.classify_message(message)
            intent_result = await self.intent_detector.detect_intent(message)

            # 4. Строим контекст для AI
            ai_context = await self.context_builder.build_context(
                user_id=user_id,
                message=message,
                user_profile=user_profile,
                session=session,
                classification=classification_result,
                intent=intent_result,
                additional_context=context
            )

            # 5. Генерируем базовый ответ
            base_response = await self._generate_base_response(ai_context)

            # 6. Персонализируем ответ
            personalized_response = await self.style_adapter.adapt_response(
                response=base_response,
                user_profile=user_profile,
                context=ai_context
            )

            # 7. Оптимизируем финальный ответ
            final_response = await self.response_optimizer.optimize_response(
                response=personalized_response,
                context=ai_context,
                user_profile=user_profile
            )

            # 8. Сохраняем взаимодействие в память
            await self._save_interaction(
                user_id=user_id,
                session=session,
                user_message=message,
                ai_response=final_response,
                ai_context=ai_context,
                response_time=time.time() - start_time
            )

            # 9. Трекинг для аналитики
            await self.interaction_tracker.track_interaction(
                user_id=user_id,
                session_id=session.id,
                message=message,
                response=final_response,
                context=ai_context,
                response_time_ms=int((time.time() - start_time) * 1000)
            )

            return final_response

        except (ValueError, RuntimeError) as e:
            logger.error("Enhanced AI error for user %s: %s", user_id, e)
            return await self._fallback_response(message, str(e))

    async def _generate_base_response(self, context: AIContext) -> str:
        """Генерация базового AI ответа"""
        # Формируем сообщения для AI
        messages = []

        # Системный промпт с учетом контекста
        system_prompt = self._build_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})

        # Добавляем память диалога если есть
        if context.dialogue_history:
            for msg in context.dialogue_history[-5:]:  # последние 5 сообщений
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": context.message})

        # Вызываем базовый AI с улучшенным контекстом
        return await basic_ai_response(
            messages=messages,
            model="openai/gpt-4o",  # используем более мощную модель
            max_tokens=1000
        )

    def _build_system_prompt(self, context: AIContext) -> str:
        """Строим системный промпт с учетом контекста"""
        base_prompt = """Ты - опытный юрист-консультант в российском юридическом центре.
Твоя задача - давать профессиональные, понятные и полезные советы по правовым вопросам."""

        # Добавляем персонализацию
        if context.user_profile:
            profile = context.user_profile

            if profile.experience_level == "beginner":
                base_prompt += "\nОбъясняй сложные термины простыми словами."
            elif profile.experience_level == "advanced":
                base_prompt += "\nМожешь использовать профессиональную юридическую терминологию."

            if profile.preferred_style == "formal":
                base_prompt += "\nИспользуй формальный стиль общения."
            elif profile.preferred_style == "friendly":
                base_prompt += "\nОбщайся дружелюбно и неформально."

            if profile.detail_preference == "brief":
                base_prompt += "\nДавай краткие, сжатые ответы."
            elif profile.detail_preference == "detailed":
                base_prompt += "\nДавай подробные, развернутые объяснения."

        # Добавляем контекст категории
        if context.predicted_category:
            base_prompt += f"\nТема вопроса: {context.predicted_category}"

        # Добавляем контекст намерения
        if context.detected_intent:
            if context.detected_intent == "consultation":
                base_prompt += "\nПользователь ищет юридическую консультацию."
            elif context.detected_intent == "application":
                base_prompt += "\nПользователь хочет подать заявку на услуги."
            elif context.detected_intent == "information":
                base_prompt += "\nПользователь ищет информацию о процедурах."

        base_prompt += "\n\nВ конце ответа всегда предлагай подать заявку для детальной консультации."

        return base_prompt

    async def _save_interaction(
        self,
        user_id: int,
        session: DialogueSession,
        user_message: str,
        ai_response: str,
        ai_context: AIContext,
        response_time: float
    ):
        """Сохранение взаимодействия в базу данных"""
        try:
            # Проверяем, что session имеет id (не fallback)
            if not hasattr(session, 'id') or session.id is None:
                logger.warning(f"Skipping interaction save - session has no id (fallback mode)")
                return

            async with async_sessionmaker() as db_session:
                # Сохраняем сообщение пользователя
                user_msg = DialogueMessage(
                    session_id=session.id,
                    role="user",
                    content=user_message,
                    intent_confidence=ai_context.intent_confidence,
                    category_predictions=ai_context.category_predictions
                )
                db_session.add(user_msg)

                # Сохраняем ответ AI
                ai_msg = DialogueMessage(
                    session_id=session.id,
                    role="assistant",
                    content=ai_response,
                    response_time_ms=int(response_time * 1000)
                )
                db_session.add(ai_msg)

                # Обновляем сессию
                session.message_count += 2
                session.last_activity = datetime.now()

                if ai_context.predicted_category:
                    if not session.detected_categories:
                        session.detected_categories = []
                    if ai_context.predicted_category not in session.detected_categories:
                        session.detected_categories.append(
                            ai_context.predicted_category)

                await db_session.commit()

        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")

    async def _fallback_response(self, message: str, error: str) -> str:
        """Fallback к базовому AI при ошибке Enhanced системы"""
        logger.warning(f"Using fallback AI due to error: {error}")

        try:
            # Используем старый простой метод
            from ...ai import generate_ai_response

            # Простая категоризация без import dependency
            message_lower = message.lower()
            if any(word in message_lower for word in ["развод", "алимент", "брак", "семья"]):
                category = "Семейное право"
            elif any(word in message_lower for word in ["наследств", "завещан"]):
                category = "Наследство"
            elif any(word in message_lower for word in ["работ", "труд", "увольнен"]):
                category = "Трудовые споры"
            elif any(word in message_lower for word in ["жкх", "квартир", "дом"]):
                category = "Жилищные вопросы"
            elif any(word in message_lower for word in ["долг", "кредит", "банкрот"]):
                category = "Банкротство физлиц"
            elif any(word in message_lower for word in ["налог", "ндфл"]):
                category = "Налоговые консультации"
            elif any(word in message_lower for word in ["штраф", "гибдд"]):
                category = "Административные штрафы"
            elif any(word in message_lower for word in ["потребител", "товар", "услуг"]):
                category = "Защита прав потребителей"
            elif any(word in message_lower for word in ["мигра", "гражданств", "виза"]):
                category = "Миграционное право"
            else:
                category = "Общие юридические вопросы"

            system_prompt = f"""Ты - опытный юрист-консультант. 
Отвечаешь на вопросы по теме: {category}.
Даёшь практические советы, ссылаешься на законы РФ.
В конце предлагаешь записаться на консультацию."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]

            response = await generate_ai_response(messages)
            response += "\n\n💼 Для детальной консультации нажмите /start и заполните заявку."

            return response

        except Exception as fallback_error:
            logger.error(f"Fallback AI also failed: {fallback_error}")
            return "🤖 Извините, AI консультант временно недоступен. Попробуйте позже или обратитесь к администратору."

    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Получение сводки аналитики"""
        try:
            async with async_sessionmaker() as session:
                # Получаем последние метрики
                result = await session.execute(
                    select(AIMetrics).order_by(
                        AIMetrics.metric_date.desc()).limit(1)
                )
                latest_metrics = result.scalar_one_or_none()

                if not latest_metrics:
                    return {"status": "no_data"}

                return {
                    "total_requests": latest_metrics.total_requests,
                    "success_rate": latest_metrics.successful_requests / max(latest_metrics.total_requests, 1),
                    "avg_response_time": latest_metrics.average_response_time,
                    "avg_satisfaction": latest_metrics.average_satisfaction,
                    "classification_accuracy": latest_metrics.classification_accuracy,
                    "tokens_used": latest_metrics.total_tokens_used,
                    "estimated_cost": latest_metrics.total_cost_usd
                }

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья Enhanced AI системы"""
        health = {
            "status": "healthy",
            "components": {},
            "initialized": self._initialized
        }

        try:
            # Проверяем компоненты
            components_to_check = [
                ("ml_classifier", self.ml_classifier),
                ("intent_detector", self.intent_detector),
                ("dialogue_memory", self.dialogue_memory),
                ("user_profiler", self.user_profiler),
                ("style_adapter", self.style_adapter)
            ]

            for name, component in components_to_check:
                try:
                    if hasattr(component, 'health_check'):
                        component_health = await component.health_check()
                        health["components"][name] = component_health
                    else:
                        health["components"][name] = {"status": "ok"}
                except Exception as e:
                    health["components"][name] = {
                        "status": "error", "error": str(e)}
                    health["status"] = "degraded"

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)

        return health
