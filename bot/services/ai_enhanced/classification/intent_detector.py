"""
Intent Detector - определение намерений пользователя в сообщениях.

Классифицирует намерения:
- consultation: пользователь хочет консультацию
- application: пользователь хочет подать заявку
- information: пользователь ищет информацию
- complaint: пользователь жалуется
- pricing: вопросы о стоимости
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class IntentDetector:
    """Детектор намерений пользователя"""

    def __init__(self):
        self.intent_patterns = {
            "consultation": [
                "консультац", "совет", "помог", "что делать", "как поступ",
                "юрист", "правов", "закон", "вопрос"
            ],
            "application": [
                "заявк", "подать", "оформ", "услуг", "заказать", "нужно",
                "требуется", "хочу", "записат"
            ],
            "information": [
                "как", "что", "когда", "где", "почему", "информац",
                "расскаж", "объясн", "процедур"
            ],
            "pricing": [
                "стоимост", "цена", "сколько", "тариф", "оплат", "деньги",
                "рубл", "бесплатн", "платн"
            ],
            "complaint": [
                "жалоб", "нарушен", "незакон", "обман", "мошен", "винова",
                "несправедлив", "нарушил"
            ]
        }
        self.initialized = False

    async def initialize(self):
        """Инициализация детектора"""
        try:
            logger.info("🔧 Initializing Intent Detector...")
            self.initialized = True
            logger.info("✅ Intent Detector initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Intent Detector: {e}")
            self.initialized = False

    async def detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Определение намерения в сообщении

        Returns:
            {
                'intent': str,
                'confidence': float,
                'all_intents': Dict[str, float]
            }
        """
        try:
            if not self.initialized:
                await self.initialize()

            message_lower = message.lower()
            intent_scores = {}

            # Подсчитываем совпадения для каждого намерения
            for intent, patterns in self.intent_patterns.items():
                score = 0
                for pattern in patterns:
                    if pattern in message_lower:
                        score += 1

                if score > 0:
                    # Нормализуем по количеству паттернов
                    intent_scores[intent] = score / len(patterns)

            if not intent_scores:
                return {
                    'intent': 'consultation',  # по умолчанию
                    'confidence': 0.3,
                    'all_intents': {}
                }

            # Находим намерение с максимальным скором
            best_intent = max(intent_scores, key=intent_scores.get)
            # усиливаем уверенность
            confidence = min(intent_scores[best_intent] * 3, 0.9)

            return {
                'intent': best_intent,
                'confidence': confidence,
                'all_intents': intent_scores
            }

        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return {
                'intent': 'consultation',
                'confidence': 0.3,
                'all_intents': {}
            }

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья детектора"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "intents_available": list(self.intent_patterns.keys())
        }
