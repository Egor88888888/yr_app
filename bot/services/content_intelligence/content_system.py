"""
🧠 MAIN CONTENT INTELLIGENCE SYSTEM
Главная система умного контента
+ ИНТЕГРИРОВАНА СИСТЕМА ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from ..db import async_sessionmaker
from ..ai_unified import unified_ai_service
from .models import NewsItem, ContentItem, PostHistory
from .news_parser import NewsParser
from .content_analyzer import ContentAnalyzer
from .post_generator import PostGenerator
from ..content_deduplication import validate_and_register_content, get_deduplication_system

logger = logging.getLogger(__name__)

class ContentIntelligenceSystem:
    """Главный класс системы контентной аналитики"""
    
    def __init__(self):
        self.analyzer = ContentAnalyzer()
        self.generator = PostGenerator()
        
    async def initialize(self):
        """Инициализация системы"""
        logger.info("🧠 Initializing Content Intelligence System...")
        logger.info("✅ Content Intelligence System initialized")
    
    async def collect_and_process_news(self) -> List[str]:
        """Сбор и обработка новостей, возврат готовых постов"""
        posts = []
        
        try:
            # 1. Парсинг новостей
            async with NewsParser() as parser:
                news_items = await parser.parse_all_sources()
            
            logger.info(f"📰 Collected {len(news_items)} news items")
            
            # 2. Фильтрация релевантных
            relevant_items = []
            for item in news_items:
                relevance = await self.analyzer.analyze_relevance(item)
                if relevance > 0.3:
                    item.relevance_score = relevance
                    relevant_items.append(item)
            
            # 3. Проверка дубликатов
            unique_items = await self._filter_duplicates(relevant_items)
            logger.info(f"🔍 Filtered to {len(unique_items)} unique items")
            
            # 4. Сохранение и генерация постов
            saved_items = await self._save_items(unique_items)
            
            for item in saved_items[:3]:  # Максимум 3 поста
                try:
                    post_text = await self.generator.generate_post(item)
                    
                    # НОВАЯ СИСТЕМА ПРОВЕРКИ УНИКАЛЬНОСТИ
                    title = item.title[:100]  # Используем заголовок новости как title
                    is_valid, message = validate_and_register_content(
                        title=title,
                        content=post_text,
                        content_type="intelligence_post",
                        source_system="content_intelligence"
                    )
                    
                    if is_valid:
                        await self._save_post_history(post_text)
                        posts.append(post_text)
                        logger.info(f"✅ Unique intelligence post created from: {item.source}")
                    else:
                        logger.warning(f"❌ Intelligence post not unique: {message}")
                        # Блокируем тему/источник временно
                        dedup_system = get_deduplication_system()
                        dedup_system.block_topic_temporarily(
                            f"{item.source}:{item.category}", 
                            f"Intelligence duplicate: {message}", 
                            hours=6
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to generate post: {e}")
            
            logger.info(f"📝 Generated {len(posts)} posts")
            
        except Exception as e:
            logger.error(f"❌ Content processing failed: {e}")
        
        return posts
    
    async def _filter_duplicates(self, items: List[NewsItem]) -> List[NewsItem]:
        """Фильтрация дубликатов"""
        unique_items = []
        existing_hashes = await self._get_existing_hashes()
        
        for item in items:
            if item.content_hash not in existing_hashes:
                unique_items.append(item)
                existing_hashes.add(item.content_hash)
        
        return unique_items
    
    async def _get_existing_hashes(self) -> set:
        """Получение существующих hash из БД"""
        try:
            async with async_sessionmaker() as session:
                cutoff_date = datetime.now() - timedelta(days=30)
                result = await session.execute(
                    select(ContentItem.content_hash)
                    .where(ContentItem.created_at > cutoff_date)
                )
                return {row[0] for row in result.fetchall()}
        except Exception:
            return set()
    
    async def _save_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """Сохранение в БД"""
        saved_items = []
        try:
            async with async_sessionmaker() as session:
                for item in items:
                    db_item = ContentItem(
                        title=item.title,
                        content=item.content,
                        url=item.url,
                        source=item.source,
                        publish_date=item.publish_date,
                        category=item.category,
                        relevance_score=item.relevance_score,
                        content_hash=item.content_hash,
                    )
                    session.add(db_item)
                    saved_items.append(item)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save items: {e}")
        return saved_items
    
    async def _is_post_duplicate(self, post_text: str) -> bool:
        """Проверка дублирования постов"""
        try:
            post_hash = hashlib.sha256(post_text.encode()).hexdigest()
            async with async_sessionmaker() as session:
                result = await session.execute(
                    select(PostHistory).where(PostHistory.post_hash == post_hash)
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            return False
    
    async def _save_post_history(self, post_text: str):
        """Сохранение истории постов"""
        try:
            post_hash = hashlib.sha256(post_text.encode()).hexdigest()
            async with async_sessionmaker() as session:
                post_record = PostHistory(
                    post_text=post_text,
                    post_hash=post_hash,
                    channel_id="auto_generated"
                )
                session.add(post_record)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save post history: {e}")
