"""
ML Classification modules - машинное обучение для классификации.

- ml_classifier: ML классификация категорий с использованием эмбеддингов
- intent_detector: определение намерений пользователя
- embeddings_manager: управление векторными представлениями
"""

from .ml_classifier import MLClassifier
from .intent_detector import IntentDetector
from .embeddings_manager import EmbeddingsManager

__all__ = ["MLClassifier", "IntentDetector", "EmbeddingsManager"]
