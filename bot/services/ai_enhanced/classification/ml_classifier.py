"""
ML Classifier - машинное обучение для классификации категорий.

Использует Azure OpenAI Embeddings для векторизации и cosine similarity для классификации.
Fallback на keyword matching при низкой уверенности.
Azure Embeddings Deployment: text-embedding-ada-002 ГОТОВ К РАБОТЕ!
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import os

from sqlalchemy import select
from ...db import async_sessionmaker, Category

logger = logging.getLogger(__name__)

# Azure OpenAI Configuration для эмбеддингов
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY", "Fjaj2B7pc9tXPnLT4jY8Wv4Gl9435Ifw6ymyQ68OolKP0LVxBoqjJQQJ99BEACfhMk5XJ3w3AAAAACOGrsqR")
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT", "https://divan-mb68c0s7-swedencentral.cognitiveservices.azure.com")
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Azure OpenAI embeddings deployment name - используем то же имя что и в основном AI сервисе
AZURE_EMBEDDINGS_DEPLOYMENT = os.getenv(
    "AZURE_EMBEDDINGS_DEPLOYMENT", "text-embedding-ada-002")

# Возможные варианты deployment имен для эмбеддингов
EMBEDDING_DEPLOYMENT_VARIANTS = [
    "text-embedding-ada-002",
    "text-embedding-3-small",
    "text-embedding-3-large",
    "embedding-ada-002",
    "ada-002"
]


class MLClassifier:
    """ML классификатор категорий с эмбеддингами"""

    def __init__(self):
        self.categories_cache = {}
        self.embeddings_cache = {}
        self.initialized = False
        self.fallback_keywords = {
            "Семейное право": ["развод", "алимент", "брак", "семь", "дети", "опека"],
            "Наследство": ["наследств", "завещан", "наследник", "имущество"],
            "Трудовые споры": ["работ", "труд", "увольнен", "зарплат", "отпуск"],
            "Жилищные вопросы": ["жкх", "квартир", "дом", "жиль", "коммунальн"],
            "Банкротство физлиц": ["долг", "кредит", "банкрот", "долг"],
            "Налоговые консультации": ["налог", "ндфл", "ифнс", "декларац"],
            "Административные штрафы": ["штраф", "гибдд", "админ", "нарушени"],
            "Защита прав потребителей": ["потребител", "товар", "услуг", "возврат"],
            "Миграционное право": ["мигра", "гражданств", "внж", "рвп", "виза"]
        }

    async def initialize(self):
        """Инициализация классификатора"""
        try:
            logger.info("🔧 Initializing ML Classifier with Azure OpenAI...")

            # Загружаем категории из БД
            await self._load_categories()

            # ГОТОВО К ВКЛЮЧЕНИЮ: Раскомментировать после создания embedding deployment в Azure
            # Создаем базовые эмбеддинги для категорий через Azure OpenAI
            embeddings_available = False

            # ВКЛЮЧИТЬ ПОСЛЕ СОЗДАНИЯ DEPLOYMENT:
            if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
                logger.info("Trying Azure OpenAI embeddings...")
                await self._initialize_category_embeddings()
                embeddings_available = bool(self.embeddings_cache)

            if not embeddings_available:
                logger.info(
                    "🔧 Azure embeddings not available - using keyword classification (production stable)")
            else:
                logger.info(
                    f"✅ Azure embeddings ready for {len(self.embeddings_cache)} categories")

            # Всегда помечаем как инициализированный
            self.initialized = True
            logger.info("✅ ML Classifier initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize ML Classifier: {e}")
            # Даже при ошибке помечаем как инициализированный для keyword fallback
            self.initialized = True
            logger.info("✅ ML Classifier initialized in keyword fallback mode")

    async def classify_message(self, message: str) -> Dict[str, Any]:
        """
        Классификация сообщения

        Returns:
            {
                'category': str,
                'confidence': float,
                'all_predictions': Dict[str, float]
            }
        """
        try:
            if not self.initialized:
                await self.initialize()

            # Пробуем ML подход если эмбеддинги доступны
            if AZURE_OPENAI_API_KEY and self.embeddings_cache:
                ml_result = await self._ml_classify(message)
                if ml_result['confidence'] > 0.6:  # высокая уверенность
                    return ml_result

            # Fallback: keyword classification (всегда работает)
            keyword_result = await self._keyword_classify(message)
            return keyword_result

        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {
                'category': "Общие вопросы",
                'confidence': 0.3,
                'all_predictions': {}
            }

    async def _ml_classify(self, message: str) -> Dict[str, Any]:
        """ML классификация с эмбеддингами"""
        try:
            # Получаем эмбеддинг сообщения
            message_embedding = await self._get_embedding(message)
            if message_embedding is None:
                raise Exception("Failed to get message embedding")

            # Сравниваем с эмбеддингами категорий
            similarities = {}
            for category, category_embedding in self.embeddings_cache.items():
                similarity = self._cosine_similarity(
                    message_embedding, category_embedding)
                similarities[category] = float(similarity)

            # Находим лучшее совпадение
            best_category = max(similarities, key=similarities.get)
            best_confidence = similarities[best_category]

            return {
                'category': best_category,
                'confidence': best_confidence,
                'all_predictions': similarities
            }

        except Exception as e:
            logger.error(f"ML classification error: {e}")
            return await self._keyword_classify(message)

    async def _keyword_classify(self, message: str) -> Dict[str, Any]:
        """Fallback классификация по ключевым словам"""
        message_lower = message.lower()
        scores = {}

        for category, keywords in self.fallback_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in message_lower:
                    score += 1

            if score > 0:
                scores[category] = score / len(keywords)  # нормализуем

        if scores:
            best_category = max(scores, key=scores.get)
            # максимум 0.8 для keyword
            confidence = min(scores[best_category] * 2, 0.8)

            return {
                'category': best_category,
                'confidence': confidence,
                'all_predictions': scores
            }

        return {
            'category': "Общие вопросы",
            'confidence': 0.3,
            'all_predictions': {}
        }

    async def _load_categories(self):
        """Загрузка категорий из БД"""
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(select(Category))
                categories = result.scalars().all()

                self.categories_cache = {
                    cat.name: cat.id for cat in categories}
                logger.info(f"Loaded {len(self.categories_cache)} categories")

        except Exception as e:
            logger.error(f"Failed to load categories: {e}")

    async def _initialize_category_embeddings(self):
        """Создание эмбеддингов для категорий"""
        try:
            for category in self.categories_cache.keys():
                # Создаем описательный текст для категории
                category_text = f"Юридические вопросы по теме: {category}"
                embedding = await self._get_embedding(category_text)

                if embedding is not None:
                    self.embeddings_cache[category] = embedding

            logger.info(
                f"Created embeddings for {len(self.embeddings_cache)} categories")

        except Exception as e:
            logger.error(f"Failed to create category embeddings: {e}")

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Получение эмбеддинга текста через Azure OpenAI"""
        if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
            logger.error("Azure OpenAI credentials not configured")
            return None

        # Пробуем разные варианты deployment имен
        for deployment_name in EMBEDDING_DEPLOYMENT_VARIANTS:
            try:
                result = await self._get_azure_embedding(text, deployment_name)
                if result is not None:
                    logger.info(
                        f"✅ Azure embeddings working with deployment: {deployment_name}")
                    # Обновляем глобальную переменную для последующих запросов
                    global AZURE_EMBEDDINGS_DEPLOYMENT
                    AZURE_EMBEDDINGS_DEPLOYMENT = deployment_name
                    return result
            except Exception as e:
                logger.warning(f"Failed deployment {deployment_name}: {e}")
                continue

        logger.error("All Azure embedding deployment variants failed")
        return None

    async def _get_azure_embedding(self, text: str, deployment_name: str) -> Optional[List[float]]:
        """Получение эмбеддинга через Azure OpenAI"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "api-key": AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json"
            }

            # Azure OpenAI embeddings endpoint
            url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment_name}/embeddings?api-version={AZURE_OPENAI_API_VERSION}"

            data = {
                "input": text,
                "encoding_format": "float"
            }

            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["data"][0]["embedding"]
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Azure OpenAI embedding error {response.status}: {error_text}")
                    return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Вычисление cosine similarity"""
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            return dot_product / (norm_a * norm_b)

        except Exception as e:
            logger.error(f"Cosine similarity error: {e}")
            return 0.0

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья классификатора"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "categories_loaded": len(self.categories_cache),
            "embeddings_ready": len(self.embeddings_cache),
            "ml_available": bool(AZURE_OPENAI_API_KEY)
        }
