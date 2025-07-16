"""
Embeddings Manager - управление векторными представлениями.

Кэширует эмбеддинги, обеспечивает быстрый доступ к векторам.
"""

import logging
from typing import Dict, Optional

# Optional numpy import for production compatibility
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # Fallback - simple list operations

    class np:
        # Fallback ndarray type
        ndarray = list

        @staticmethod
        def array(data):
            return data

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Менеджер векторных представлений"""

    def __init__(self):
        self.cache = {}
        self.initialized = False

    async def initialize(self):
        """Инициализация менеджера"""
        try:
            logger.info("🔧 Initializing Embeddings Manager...")
            self.initialized = True
            logger.info("✅ Embeddings Manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Embeddings Manager: {e}")
            self.initialized = False

    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Получение эмбеддинга (с кэшированием)"""
        if text in self.cache:
            return self.cache[text]
        return None

    async def store_embedding(self, text: str, embedding: np.ndarray):
        """Сохранение эмбеддинга в кэш"""
        self.cache[text] = embedding

    async def health_check(self) -> Dict[str, any]:
        """Проверка здоровья менеджера"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "cached_embeddings": len(self.cache)
        }
