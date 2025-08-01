"""
Enhanced AI System - максимальный AI с ML-классификацией, памятью диалогов и персонализацией.

Компоненты:
- core: основные AI менеджеры 
- classification: ML классификация и intent detection
- memory: система памяти диалогов и профилирование пользователей
- personalization: адаптация стиля и персональные рекомендации
- analytics: метрики качества и аналитика взаимодействий

Использование:
    from bot.services.ai_enhanced import AIEnhancedManager
    
    ai_manager = AIEnhancedManager()
    response = await ai_manager.generate_response(user_id, message, context)
"""

from .core.ai_manager import AIEnhancedManager
from .core.context_builder import ContextBuilder, AIContext
from .core.response_optimizer import ResponseOptimizer

__all__ = [
    "AIEnhancedManager",
    "ContextBuilder",
    "AIContext",
    "ResponseOptimizer"
]
