"""
Style Adapter - адаптация стиля ответов под пользователя.

Персонализирует ответы на основе профиля пользователя и его предпочтений.
"""

import logging
import re
from typing import Dict, Any, Optional

from ...ai_enhanced_models import UserProfile
from ..core.context_builder import AIContext

logger = logging.getLogger(__name__)


class StyleAdapter:
    """Адаптер стиля ответов"""

    def __init__(self):
        self.initialized = False

        # Шаблоны для разных стилей
        self.style_templates = {
            "formal": {
                "greeting": ["Здравствуйте", "Добро пожаловать"],
                "closing": ["С уважением", "Всего доброго", "До свидания"],
                "transition": ["Позвольте разъяснить", "Следует отметить", "Важно понимать"]
            },
            "friendly": {
                "greeting": ["Привет", "Здравствуйте", "Добро пожаловать"],
                "closing": ["Удачи", "Всего хорошего", "Обращайтесь"],
                "transition": ["Давайте разберемся", "Объясню проще", "Важный момент"]
            },
            "professional": {
                "greeting": ["Добрый день", "Здравствуйте"],
                "closing": ["С уважением", "Успехов", "До свидания"],
                "transition": ["Рассмотрим детали", "Ключевой аспект", "Следует учесть"]
            }
        }

        # Модификаторы для уровня детализации
        self.detail_modifiers = {
            "brief": {
                "max_length": 300,
                "remove_examples": True,
                "summarize": True
            },
            "medium": {
                "max_length": 600,
                "remove_examples": False,
                "summarize": False
            },
            "detailed": {
                "max_length": 1000,
                "remove_examples": False,
                "add_context": True
            }
        }

    async def initialize(self):
        """Инициализация адаптера"""
        try:
            logger.info("🔧 Initializing Style Adapter...")
            self.initialized = True
            logger.info("✅ Style Adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Style Adapter: {e}")
            self.initialized = False

    async def adapt_response(
        self,
        response: str,
        user_profile: Optional[UserProfile],
        context: AIContext
    ) -> str:
        """Адаптация ответа под стиль пользователя"""
        try:
            if not user_profile:
                return response

            adapted_response = response

            # 1. Адаптируем стиль общения
            adapted_response = await self._adapt_communication_style(
                adapted_response, user_profile.preferred_style
            )

            # 2. Адаптируем уровень детализации
            adapted_response = await self._adapt_detail_level(
                adapted_response, user_profile.detail_preference
            )

            # 3. Адаптируем под уровень опыта
            adapted_response = await self._adapt_experience_level(
                adapted_response, user_profile.experience_level
            )

            # 4. Добавляем персональные элементы
            adapted_response = await self._add_personalization(
                adapted_response, user_profile, context
            )

            return adapted_response

        except Exception as e:
            logger.error(f"Failed to adapt response: {e}")
            return response  # возвращаем оригинал при ошибке

    async def _adapt_communication_style(self, response: str, style: str) -> str:
        """Адаптация стиля общения"""
        try:
            if style not in self.style_templates:
                return response

            templates = self.style_templates[style]

            # Заменяем формальные обращения
            if style == "friendly":
                response = response.replace("Вы можете", "Можете")
                response = response.replace("Вам следует", "Лучше")
                response = response.replace("рекомендуется", "советую")
            elif style == "formal":
                response = response.replace("можете", "Вы можете")
                response = response.replace("лучше", "рекомендуется")
                response = response.replace("советую", "рекомендуется")

            return response

        except Exception as e:
            logger.error(f"Failed to adapt communication style: {e}")
            return response

    async def _adapt_detail_level(self, response: str, detail_level: str) -> str:
        """Адаптация уровня детализации"""
        try:
            if detail_level not in self.detail_modifiers:
                return response

            modifiers = self.detail_modifiers[detail_level]

            if detail_level == "brief":
                # Сокращаем ответ
                sentences = response.split('. ')
                if len(sentences) > 3:
                    response = '. '.join(sentences[:3]) + '.'

                # Убираем примеры
                response = re.sub(r'Например[^.]*\.', '', response)
                response = re.sub(r'К примеру[^.]*\.', '', response)

            elif detail_level == "detailed":
                # Добавляем больше контекста (если нужно)
                if len(response) < 400:
                    response += "\n\n💡 Для получения более детальной консультации по вашему вопросу рекомендуем подать заявку через наш сервис."

            return response

        except Exception as e:
            logger.error(f"Failed to adapt detail level: {e}")
            return response

    async def _adapt_experience_level(self, response: str, experience: str) -> str:
        """Адаптация под уровень опыта"""
        try:
            if experience == "beginner":
                # Упрощаем термины
                response = response.replace(
                    "исковое заявление", "иск (заявление в суд)")
                response = response.replace(
                    "арбитражный суд", "суд по экономическим спорам")
                response = response.replace(
                    "апелляция", "обжалование решения суда")

                # Добавляем пояснения
                if "ГК РФ" in response:
                    response = response.replace(
                        "ГК РФ", "Гражданский кодекс РФ")
                if "ТК РФ" in response:
                    response = response.replace("ТК РФ", "Трудовой кодекс РФ")

            elif experience == "advanced":
                # Можем использовать более специфические термины
                response = response.replace(
                    "заявление в суд", "исковое заявление")
                response = response.replace(
                    "обжалование", "апелляционное обжалование")

            return response

        except Exception as e:
            logger.error(f"Failed to adapt experience level: {e}")
            return response

    async def _add_personalization(
        self,
        response: str,
        user_profile: UserProfile,
        context: AIContext
    ) -> str:
        """Добавление персональных элементов"""
        try:
            # Добавляем ссылку на частые категории пользователя
            if user_profile.frequent_categories:
                most_frequent = max(
                    user_profile.frequent_categories,
                    key=user_profile.frequent_categories.get
                )

                if context.predicted_category != most_frequent:
                    response += f"\n\n💼 Заметил, что вас часто интересуют вопросы по теме '{most_frequent}'. Если есть связанные вопросы, тоже с радостью помогу!"

            # Для опытных пользователей добавляем ссылки на законы
            if user_profile.experience_level == "advanced":
                response += "\n\n📖 Для углубленного изучения рекомендую ознакомиться с соответствующими статьями законодательства."

            return response

        except Exception as e:
            logger.error(f"Failed to add personalization: {e}")
            return response

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья адаптера"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "available_styles": list(self.style_templates.keys()),
            "detail_levels": list(self.detail_modifiers.keys())
        }
