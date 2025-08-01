"""
Enhanced AI Database Models - дополнительные модели для AI системы.

Новые таблицы:
- UserProfile: профили пользователей с предпочтениями и настройками AI
- DialogueSession: сессии диалогов с контекстом
- MessageEmbedding: векторные представления сообщений
- AIMetrics: метрики качества и производительности AI
- UserPreference: детальные предпочтения пользователей
- CategoryEmbedding: эмбеддинги категорий услуг
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Integer, DateTime, Boolean, Numeric, ForeignKey, Text, JSON, func, LargeBinary, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
    """Расширенный профиль пользователя для AI персонализации"""
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # AI персонализация
    experience_level: Mapped[str] = mapped_column(
        String(20), default="beginner")  # beginner/intermediate/advanced
    preferred_style: Mapped[str] = mapped_column(
        String(20), default="friendly")  # formal/friendly/professional
    communication_speed: Mapped[str] = mapped_column(
        String(20), default="normal")  # slow/normal/fast
    detail_preference: Mapped[str] = mapped_column(
        String(20), default="medium")  # brief/medium/detailed

    # Статистика взаимодействий
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    successful_resolutions: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[Optional[float]] = mapped_column(Float)

    # История категорий
    frequent_categories: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON)  # {category_id: count}
    last_categories: Mapped[Optional[List[int]]] = mapped_column(
        JSON)  # последние 10 категорий

    # AI настройки
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    personalization_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class DialogueSession(Base, TimestampMixin):
    """Сессия диалога с пользователем"""
    __tablename__ = "dialogue_sessions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_uuid: Mapped[str] = mapped_column(String(36), unique=True)

    # Контекст сессии
    context_summary: Mapped[Optional[str]] = mapped_column(
        Text)  # сжатое описание контекста
    detected_intent: Mapped[Optional[str]] = mapped_column(String(50))
    detected_categories: Mapped[Optional[List[int]]] = mapped_column(JSON)

    # Статистика сессии
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    resolution_status: Mapped[str] = mapped_column(
        String(20), default="ongoing")  # ongoing/resolved/abandoned
    satisfaction_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5

    # Timestamps
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True))

    # Связи
    messages: Mapped[List["DialogueMessage"]
                     ] = relationship(back_populates="session")


class DialogueMessage(Base, TimestampMixin):
    """Сообщение в диалоге"""
    __tablename__ = "dialogue_messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("dialogue_sessions.id"))

    # Содержимое сообщения
    role: Mapped[str] = mapped_column(String(10))  # user/assistant/system
    content: Mapped[str] = mapped_column(Text)

    # AI метаданные
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float)
    category_predictions: Mapped[Optional[Dict[str, float]]] = mapped_column(
        JSON)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Связи
    session: Mapped["DialogueSession"] = relationship(
        back_populates="messages")


class MessageEmbedding(Base):
    """Векторные представления сообщений для семантического поиска"""
    __tablename__ = "message_embeddings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("dialogue_messages.id"), unique=True)

    # Эмбеддинг
    embedding: Mapped[bytes] = mapped_column(
        LargeBinary)  # сериализованный numpy array
    model_name: Mapped[str] = mapped_column(
        String(50))  # модель для эмбеддинга

    # Метаданные
    dimension: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())


class CategoryEmbedding(Base):
    """Эмбеддинги категорий услуг для ML классификации"""
    __tablename__ = "category_embeddings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), unique=True)

    # Эмбеддинг
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    model_name: Mapped[str] = mapped_column(String(50))

    # Метаданные
    training_samples: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float)
    last_retrained: Mapped[Optional[datetime]
                           ] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())


class AIMetrics(Base):
    """Метрики качества и производительности AI"""
    __tablename__ = "ai_metrics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    metric_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())

    # Метрики производительности
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    average_response_time: Mapped[float] = mapped_column(Float, default=0.0)

    # Метрики качества
    average_satisfaction: Mapped[Optional[float]] = mapped_column(Float)
    classification_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    intent_detection_accuracy: Mapped[Optional[float]] = mapped_column(Float)

    # Использование ресурсов
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float)

    # Персонализация
    personalized_requests: Mapped[int] = mapped_column(Integer, default=0)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float)


class UserPreference(Base, TimestampMixin):
    """Детальные предпочтения пользователя"""
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Предпочтение
    # style_formality, response_length, etc.
    preference_key: Mapped[str] = mapped_column(String(50))
    preference_value: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(
        Float, default=0.5)  # насколько уверены в предпочтении

    # Метаданные
    source: Mapped[str] = mapped_column(
        String(20), default="inferred")  # explicit/inferred/default
    usage_count: Mapped[int] = mapped_column(Integer, default=1)
    last_used: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())


class TrainingData(Base, TimestampMixin):
    """Данные для обучения ML моделей"""
    __tablename__ = "training_data"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)

    # Исходные данные
    input_text: Mapped[str] = mapped_column(Text)
    expected_category_id: Mapped[Optional[int]
                                 ] = mapped_column(ForeignKey("categories.id"))
    expected_intent: Mapped[Optional[str]] = mapped_column(String(50))

    # Метаданные
    source: Mapped[str] = mapped_column(
        String(20))  # manual/automatic/imported
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Использование
    used_in_training: Mapped[bool] = mapped_column(Boolean, default=False)
    training_accuracy: Mapped[Optional[float]] = mapped_column(Float)
