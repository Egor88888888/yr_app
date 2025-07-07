"""
User Profiler - профилирование пользователей для персонализации.

Создает и обновляет профили пользователей на основе их поведения.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select
from ...db import async_sessionmaker, User
from ..ai_enhanced_models import UserProfile

logger = logging.getLogger(__name__)


class UserProfiler:
    """Профайлер пользователей"""

    def __init__(self):
        self.initialized = False
        self.profiles_cache = {}

    async def initialize(self):
        """Инициализация профайлера"""
        try:
            logger.info("🔧 Initializing User Profiler...")
            self.initialized = True
            logger.info("✅ User Profiler initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize User Profiler: {e}")
            self.initialized = False

    async def get_or_create_profile(self, user_id: int) -> Optional[UserProfile]:
        """Получение или создание профиля пользователя"""
        try:
            # Проверяем кэш
            if user_id in self.profiles_cache:
                return self.profiles_cache[user_id]

            async with async_sessionmaker() as session:
                # Ищем существующий профиль
                result = await session.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile = result.scalar_one_or_none()

                if not profile:
                    # Создаем новый профиль
                    profile = UserProfile(
                        user_id=user_id,
                        experience_level="beginner",
                        preferred_style="friendly",
                        communication_speed="normal",
                        detail_preference="medium"
                    )
                    session.add(profile)
                    await session.commit()
                    await session.refresh(profile)

                # Кэшируем профиль
                self.profiles_cache[user_id] = profile
                return profile

        except Exception as e:
            logger.error(
                f"Failed to get/create profile for user {user_id}: {e}")
            return None

    async def update_profile_from_interaction(
        self,
        user_id: int,
        message: str,
        category: str = None
    ):
        """Обновление профиля на основе взаимодействия"""
        try:
            profile = await self.get_or_create_profile(user_id)
            if not profile:
                return

            # Увеличиваем счетчик взаимодействий
            profile.total_interactions += 1

            # Обновляем частые категории
            if category:
                if not profile.frequent_categories:
                    profile.frequent_categories = {}

                if category in profile.frequent_categories:
                    profile.frequent_categories[category] += 1
                else:
                    profile.frequent_categories[category] = 1

                # Обновляем последние категории
                if not profile.last_categories:
                    profile.last_categories = []

                # избегаем дублей
                if category not in profile.last_categories[-3:]:
                    profile.last_categories.append(category)
                    if len(profile.last_categories) > 10:
                        profile.last_categories = profile.last_categories[-10:]

            # Определяем уровень опыта по количеству взаимодействий
            if profile.total_interactions > 20:
                profile.experience_level = "advanced"
            elif profile.total_interactions > 5:
                profile.experience_level = "intermediate"

            # Сохраняем изменения
            async with async_sessionmaker() as session:
                await session.merge(profile)
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to update profile for user {user_id}: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья профайлера"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "cached_profiles": len(self.profiles_cache)
        }
