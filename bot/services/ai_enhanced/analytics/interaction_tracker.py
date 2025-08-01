"""
Interaction Tracker - отслеживание взаимодействий с AI.

Собирает метрики и статистику для анализа производительности и качества AI.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select
from ...db import async_sessionmaker
from ...ai_enhanced_models import AIMetrics
from ..core.context_builder import AIContext

logger = logging.getLogger(__name__)


class InteractionTracker:
    """Трекер взаимодействий с AI"""

    def __init__(self):
        self.initialized = False
        self.daily_metrics = {}  # кэш дневных метрик

    async def initialize(self):
        """Инициализация трекера"""
        try:
            logger.info("🔧 Initializing Interaction Tracker...")
            self.initialized = True
            logger.info("✅ Interaction Tracker initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Interaction Tracker: {e}")
            self.initialized = False

    async def track_interaction(
        self,
        user_id: int,
        session_id: int,
        message: str,
        response: str,
        context: AIContext,
        response_time_ms: int
    ):
        """Отслеживание взаимодействия"""
        try:
            # Обновляем дневные метрики
            today = datetime.now().date()

            if today not in self.daily_metrics:
                self.daily_metrics[today] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'total_response_time': 0,
                    'total_tokens': 0
                }

            metrics = self.daily_metrics[today]
            metrics['total_requests'] += 1
            # считаем успешным если нет ошибок
            metrics['successful_requests'] += 1
            metrics['total_response_time'] += response_time_ms

            # Примерная оценка токенов (для реальной системы нужно получать из API)
            estimated_tokens = (len(message) + len(response)) // 4
            metrics['total_tokens'] += estimated_tokens

            logger.debug(
                f"Tracked interaction for user {user_id}: {response_time_ms}ms")

        except Exception as e:
            logger.error(f"Failed to track interaction: {e}")

    async def save_daily_metrics(self):
        """Сохранение дневных метрик в БД"""
        try:
            today = datetime.now().date()

            if today not in self.daily_metrics:
                return

            metrics = self.daily_metrics[today]

            async with async_sessionmaker() as session:
                # Создаем или обновляем запись метрик
                ai_metrics = AIMetrics(
                    metric_date=datetime.now(),
                    total_requests=metrics['total_requests'],
                    successful_requests=metrics['successful_requests'],
                    average_response_time=metrics['total_response_time'] / max(
                        metrics['total_requests'], 1),
                    total_tokens_used=metrics['total_tokens'],
                    # примерная стоимость
                    total_cost_usd=metrics['total_tokens'] * 0.00001
                )

                session.add(ai_metrics)
                await session.commit()

            logger.info(
                f"Saved daily metrics: {metrics['total_requests']} requests")

        except Exception as e:
            logger.error(f"Failed to save daily metrics: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья трекера"""
        today = datetime.now().date()
        today_metrics = self.daily_metrics.get(today, {})

        return {
            "status": "ok" if self.initialized else "not_initialized",
            "today_requests": today_metrics.get('total_requests', 0),
            "cached_days": len(self.daily_metrics)
        }
