"""
Response Optimizer - оптимизация и улучшение AI ответов.

Финальная обработка ответов: проверка качества, добавление CTA, форматирование.
"""

import logging
import re
from typing import Dict, Any, Optional

from ..ai_enhanced_models import UserProfile
from ..core.context_builder import AIContext

logger = logging.getLogger(__name__)


class ResponseOptimizer:
    """Оптимизатор ответов"""

    def __init__(self):
        self.initialized = False

        # Паттерны для улучшения ответов
        self.cta_templates = {
            "consultation": "💼 Для детальной консультации нажмите /start и заполните заявку.",
            "application": "📝 Готовы подать заявку? Нажмите /start для начала процедуры.",
            "pricing": "💰 Точную стоимость услуг можно узнать, подав заявку через /start",
            "default": "📞 Для персональной консультации обращайтесь через /start"
        }

        # Эмодзи для разных категорий
        self.category_emojis = {
            "Семейное право": "👨‍👩‍👧‍👦",
            "Наследство": "🏠",
            "Трудовые споры": "👔",
            "Жилищные вопросы": "🏘️",
            "Банкротство физлиц": "💳",
            "Налоговые консультации": "📊",
            "Административные штрафы": "🚫",
            "Защита прав потребителей": "🛡️",
            "Миграционное право": "🌍"
        }

    async def initialize(self):
        """Инициализация оптимизатора"""
        try:
            logger.info("🔧 Initializing Response Optimizer...")
            self.initialized = True
            logger.info("✅ Response Optimizer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Response Optimizer: {e}")
            self.initialized = False

    async def optimize_response(
        self,
        response: str,
        context: AIContext,
        user_profile: Optional[UserProfile] = None
    ) -> str:
        """Оптимизация финального ответа"""
        try:
            optimized = response

            # 1. Улучшаем форматирование
            optimized = await self._improve_formatting(optimized)

            # 2. Добавляем эмодзи для категории
            optimized = await self._add_category_emoji(optimized, context)

            # 3. Улучшаем структуру ответа
            optimized = await self._improve_structure(optimized)

            # 4. Добавляем персонализированный CTA
            optimized = await self._add_personalized_cta(optimized, context, user_profile)

            # 5. Финальная проверка качества
            optimized = await self._quality_check(optimized)

            return optimized

        except Exception as e:
            logger.error(f"Failed to optimize response: {e}")
            return response

    async def _improve_formatting(self, response: str) -> str:
        """Улучшение форматирования ответа"""
        try:
            # Добавляем переносы строк для лучшей читаемости
            response = re.sub(r'\.([А-ЯЁ])', r'.\n\n\1', response)

            # Выделяем важные моменты
            response = re.sub(
                r'(Важно|ВАЖНО|Внимание|ВНИМАНИЕ)(:?\s*)',
                r'⚠️ **\1**\2',
                response
            )

            # Выделяем списки
            response = re.sub(r'^(\d+\.)', r'**\1**',
                              response, flags=re.MULTILINE)
            response = re.sub(r'^([-•])', r'▪️', response, flags=re.MULTILINE)

            return response.strip()

        except Exception as e:
            logger.error(f"Failed to improve formatting: {e}")
            return response

    async def _add_category_emoji(self, response: str, context: AIContext) -> str:
        """Добавление эмодзи для категории"""
        try:
            if context.predicted_category in self.category_emojis:
                emoji = self.category_emojis[context.predicted_category]
                if not response.startswith(emoji):
                    response = f"{emoji} {response}"

            return response

        except Exception as e:
            logger.error(f"Failed to add category emoji: {e}")
            return response

    async def _improve_structure(self, response: str) -> str:
        """Улучшение структуры ответа"""
        try:
            # Разбиваем длинные абзацы
            paragraphs = response.split('\n\n')
            improved_paragraphs = []

            for paragraph in paragraphs:
                if len(paragraph) > 300:
                    # Разбиваем длинный абзац на предложения
                    sentences = paragraph.split('. ')
                    current_paragraph = ""

                    for sentence in sentences:
                        if len(current_paragraph + sentence) > 200:
                            if current_paragraph:
                                improved_paragraphs.append(
                                    current_paragraph.strip())
                            current_paragraph = sentence + '. '
                        else:
                            current_paragraph += sentence + '. '

                    if current_paragraph:
                        improved_paragraphs.append(current_paragraph.strip())
                else:
                    improved_paragraphs.append(paragraph)

            return '\n\n'.join(improved_paragraphs)

        except Exception as e:
            logger.error(f"Failed to improve structure: {e}")
            return response

    async def _add_personalized_cta(
        self,
        response: str,
        context: AIContext,
        user_profile: Optional[UserProfile]
    ) -> str:
        """Добавление персонализированного призыва к действию"""
        try:
            # Выбираем подходящий CTA на основе намерения
            intent = context.detected_intent or "default"
            cta = self.cta_templates.get(intent, self.cta_templates["default"])

            # Персонализируем CTA
            if user_profile:
                if user_profile.total_interactions > 5:
                    cta = "🤝 Как постоянному клиенту, предлагаем подать заявку для приоритетного рассмотрения через /start"
                elif user_profile.experience_level == "advanced":
                    cta = "⚖️ Для профессиональной консультации по вашему вопросу используйте /start"

            # Добавляем CTA если его еще нет
            if "/start" not in response and "заявк" not in response.lower():
                response += f"\n\n{cta}"

            return response

        except Exception as e:
            logger.error(f"Failed to add personalized CTA: {e}")
            return response

    async def _quality_check(self, response: str) -> str:
        """Финальная проверка качества"""
        try:
            # Проверяем минимальную длину
            if len(response) < 50:
                response += "\n\nЕсли у вас есть дополнительные вопросы, я готов помочь!"

            # Проверяем максимальную длину
            if len(response) > 1500:
                # Сокращаем до разумных пределов
                sentences = response.split('. ')
                truncated = []
                current_length = 0

                for sentence in sentences:
                    if current_length + len(sentence) > 1200:
                        break
                    truncated.append(sentence)
                    current_length += len(sentence)

                response = '. '.join(truncated)
                if not response.endswith('.'):
                    response += '.'

                response += "\n\n📞 Для получения полной консультации обращайтесь через /start"

            # Убираем двойные пробелы и переносы
            response = re.sub(r'\s+', ' ', response)
            response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)

            return response.strip()

        except Exception as e:
            logger.error(f"Failed to perform quality check: {e}")
            return response

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья оптимизатора"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "cta_templates": len(self.cta_templates),
            "category_emojis": len(self.category_emojis)
        }
