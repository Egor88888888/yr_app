"""
Personalization modules - персонализация AI ответов.

- style_adapter: адаптация стиля общения под пользователя
- preference_tracker: отслеживание предпочтений пользователя
- recommendation_engine: персональные рекомендации
"""

from .style_adapter import StyleAdapter
from .preference_tracker import PreferenceTracker
from .recommendation_engine import RecommendationEngine

__all__ = ["StyleAdapter", "PreferenceTracker", "RecommendationEngine"]
