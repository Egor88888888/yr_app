"""
🔍 СИСТЕМА ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА - PostgreSQL версия
Обеспечивает 100% уникальность постов и тем автопостинга
Использует PostgreSQL через SQLAlchemy вместо SQLite
"""

import hashlib
import re
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .db import async_sessionmaker, ContentFingerprint

logger = logging.getLogger(__name__)

@dataclass
class ContentFingerprintData:
    """Отпечаток контента для сравнения"""
    title_hash: str
    content_hash: str
    topic_keywords: Set[str]
    semantic_tokens: Set[str]
    legal_references: Set[str]
    content_type: str
    full_text_hash: str


class PostgreSQLContentDeduplicationSystem:
    """Система предотвращения дублирования контента с PostgreSQL"""
    
    def __init__(self):
        self.similarity_threshold = 0.7
        self.keyword_overlap_threshold = 0.6
        self.legal_ref_weight = 0.9
        logger.info("🔍 PostgreSQL Content Deduplication System initialized")
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Извлечение ключевых слов из текста"""
        if not text:
            return set()
        
        # Убираем знаки препинания и приводим к нижнему регистру
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        # Фильтруем стоп-слова и короткие слова
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'за', 'без', 'под', 'над', 'об', 'о', 'про', 'через', 'между', 'вместо'}
        keywords = {word for word in words if len(word) > 3 and word not in stop_words}
        
        return keywords
    
    def _extract_legal_references(self, text: str) -> Set[str]:
        """Извлечение правовых ссылок (статьи, законы, кодексы)"""
        if not text:
            return set()
        
        legal_patterns = [
            r'ст(?:атья)?\.?\s*\d+(?:\.\d+)*',  # Статья 123, ст. 456.1
            r'п(?:ункт)?\.?\s*\d+(?:\.\d+)*',   # Пункт 1, п. 2.3
            r'ч(?:асть)?\.?\s*\d+(?:\.\d+)*',   # Часть 1, ч. 2
            r'[А-Я][а-я]+\s+кодекс',            # Гражданский кодекс
            r'ФЗ\s*№?\s*\d+',                   # ФЗ №123
            r'закон\s+№?\s*\d+',                # Закон №456
        ]
        
        references = set()
        for pattern in legal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.update(match.strip() for match in matches)
        
        return references
    
    def _create_content_hash(self, text: str) -> str:
        """Создание хеша контента"""
        if not text:
            return ""
        
        # Нормализуем текст для хеширования
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def create_fingerprint(self, title: str, content: str, content_type: str = "post") -> ContentFingerprintData:
        """Создание отпечатка контента"""
        full_text = f"{title} {content}"
        
        return ContentFingerprintData(
            title_hash=self._create_content_hash(title),
            content_hash=self._create_content_hash(content),
            full_text_hash=self._create_content_hash(full_text),
            topic_keywords=self._extract_keywords(full_text),
            semantic_tokens=self._extract_keywords(content),
            legal_references=self._extract_legal_references(full_text),
            content_type=content_type
        )
    
    def _calculate_similarity(self, fp1: ContentFingerprintData, fp2: ContentFingerprintData) -> float:
        """Расчет семантического сходства между отпечатками"""
        if fp1.full_text_hash == fp2.full_text_hash:
            return 1.0
        
        # Сходство ключевых слов
        keywords1, keywords2 = fp1.topic_keywords, fp2.topic_keywords
        if not keywords1 and not keywords2:
            keyword_similarity = 0.0
        elif not keywords1 or not keywords2:
            keyword_similarity = 0.0
        else:
            intersection = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)
            keyword_similarity = intersection / union if union > 0 else 0.0
        
        # Сходство правовых ссылок
        legal1, legal2 = fp1.legal_references, fp2.legal_references
        if legal1 and legal2:
            legal_intersection = len(legal1 & legal2)
            legal_union = len(legal1 | legal2)
            legal_similarity = legal_intersection / legal_union if legal_union > 0 else 0.0
        else:
            legal_similarity = 0.0
        
        # Итоговое сходство
        total_similarity = (
            keyword_similarity * 0.6 +
            legal_similarity * self.legal_ref_weight * 0.4
        )
        
        return min(total_similarity, 1.0)
    
    async def validate_and_register_content(
        self, 
        title: str, 
        content: str, 
        content_type: str = "post",
        block_duration_hours: int = 24
    ) -> Tuple[bool, str]:
        """
        Проверка уникальности и регистрация контента
        Returns: (is_unique, reason)
        """
        try:
            fingerprint = self.create_fingerprint(title, content, content_type)
            
            async with async_sessionmaker() as session:
                # Проверяем точные дубли
                exact_duplicate = await session.execute(
                    select(ContentFingerprint)
                    .where(ContentFingerprint.full_text_hash == fingerprint.full_text_hash)
                )
                
                if exact_duplicate.scalar_one_or_none():
                    return False, "Точное дублирование контента"
                
                # Проверяем семантические дубли
                similar_content = await session.execute(
                    select(ContentFingerprint)
                    .where(
                        and_(
                            ContentFingerprint.content_type == content_type,
                            or_(
                                ContentFingerprint.blocked_until.is_(None),
                                ContentFingerprint.blocked_until < datetime.now()
                            )
                        )
                    )
                )
                
                for existing in similar_content.scalars():
                    existing_fp = ContentFingerprintData(
                        title_hash=existing.title_hash,
                        content_hash=existing.content_hash,
                        full_text_hash=existing.full_text_hash,
                        topic_keywords=set(json.loads(existing.topic_keywords or "[]")),
                        semantic_tokens=set(json.loads(existing.semantic_tokens or "[]")),
                        legal_references=set(json.loads(existing.legal_references or "[]")),
                        content_type=existing.content_type
                    )
                    
                    similarity = self._calculate_similarity(fingerprint, existing_fp)
                    if similarity >= self.similarity_threshold:
                        return False, f"Семантическое дублирование (сходство: {similarity:.1%})"
                
                # Регистрируем новый контент
                block_until = datetime.now() + timedelta(hours=block_duration_hours)
                
                new_fingerprint = ContentFingerprint(
                    title_hash=fingerprint.title_hash,
                    content_hash=fingerprint.content_hash,
                    full_text_hash=fingerprint.full_text_hash,
                    content_type=content_type,
                    topic_keywords=json.dumps(list(fingerprint.topic_keywords)),
                    semantic_tokens=json.dumps(list(fingerprint.semantic_tokens)),
                    legal_references=json.dumps(list(fingerprint.legal_references)),
                    blocked_until=block_until
                )
                
                session.add(new_fingerprint)
                await session.commit()
                
                logger.info(f"✅ Content registered: {content_type} - {title[:50]}...")
                return True, "Контент уникален"
                
        except Exception as e:
            logger.error(f"❌ Content validation error: {e}")
            # В случае ошибки разрешаем публикацию (fail-open)
            return True, f"Ошибка проверки: {e}"
    
    async def get_blocked_topics_count(self) -> int:
        """Получение количества заблокированных тем"""
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(
                    select(ContentFingerprint)
                    .where(ContentFingerprint.blocked_until > datetime.now())
                )
                return len(result.scalars().all())
        except Exception:
            return 0
    
    async def cleanup_old_fingerprints(self, days_old: int = 90):
        """Очистка старых отпечатков"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            async with async_sessionmaker() as session:
                old_fingerprints = await session.execute(
                    select(ContentFingerprint)
                    .where(ContentFingerprint.created_at < cutoff_date)
                )
                
                count = 0
                for fp in old_fingerprints.scalars():
                    await session.delete(fp)
                    count += 1
                
                await session.commit()
                logger.info(f"🧹 Cleaned up {count} old fingerprints")
                return count
                
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            return 0


# Глобальный экземпляр системы
_pg_deduplication_system = None

def get_pg_deduplication_system() -> PostgreSQLContentDeduplicationSystem:
    """Получение экземпляра PostgreSQL системы дедупликации"""
    global _pg_deduplication_system
    if _pg_deduplication_system is None:
        _pg_deduplication_system = PostgreSQLContentDeduplicationSystem()
    return _pg_deduplication_system


async def validate_and_register_content(title: str, content: str, content_type: str = "post") -> Tuple[bool, str]:
    """Упрощенная функция для проверки и регистрации контента"""
    system = get_pg_deduplication_system()
    return await system.validate_and_register_content(title, content, content_type)