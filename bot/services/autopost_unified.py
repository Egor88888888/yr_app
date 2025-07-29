#!/usr/bin/env python3
"""
Unified Autopost System - consolidates all autopost functionality.
Replaces simple_autopost, enhanced_autopost, and deploy_autopost with single system.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, func
from telegram.ext import Application as TelegramApplication

from bot.services.db import async_sessionmaker, ContentFingerprint
from bot.services.ai_unified import unified_ai_service, AIModel
from bot.services.content_deduplication_pg import PostgreSQLContentDeduplicationSystem
from bot.config.settings import (
    POST_INTERVAL_HOURS, TARGET_CHANNEL_ID, TARGET_CHANNEL_USERNAME,
    ADMIN_USERS, PRODUCTION_MODE
)

logger = logging.getLogger(__name__)

class PostStatus(Enum):
    """Post status enumeration"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

class PostType(Enum):
    """Post type enumeration"""
    REGULAR = "regular"
    DEPLOY = "deploy"
    MANUAL = "manual"
    SMART = "smart"

@dataclass
class PostContent:
    """Post content structure"""
    title: str
    content: str
    hashtags: List[str]
    category: Optional[str] = None
    source_topic: Optional[str] = None

@dataclass
class ScheduledPost:
    """Scheduled post structure"""
    id: str
    content: PostContent
    post_type: PostType
    scheduled_time: datetime
    status: PostStatus
    created_at: datetime
    attempts: int = 0
    last_error: Optional[str] = None

class UnifiedAutopostSystem:
    """Unified autopost system managing all posting functionality"""
    
    def __init__(self, bot_application: TelegramApplication):
        self.bot_application = bot_application
        self.deduplication_service = PostgreSQLContentDeduplicationSystem()
        self.scheduled_posts: Dict[str, ScheduledPost] = {}
        self.is_running = False
        self.stats = {
            "total_posts": 0,
            "successful_posts": 0,
            "failed_posts": 0,
            "deduplication_blocks": 0,
            "last_post_time": None
        }
        
        # Content topics for automatic posting
        self.legal_topics = [
            "Права потребителей в России",
            "Трудовые споры и их решение",
            "Семейное право: развод и алименты",
            "Защита прав при покупке недвижимости",
            "Налоговые льготы для граждан",
            "Административная ответственность",
            "Защита персональных данных",
            "Права пациентов в медицинских учреждениях",
            "Банкротство физических лиц",
            "Наследственное право в России",
            "Защита прав автомобилистов",
            "Жилищные права граждан",
            "Трудовые права беременных женщин",
            "Права пенсионеров",
            "Защита от мошенничества"
        ]
        
        # Hashtag sets
        self.hashtag_sets = [
            ["#ЮридическаяПомощь", "#ПраваГраждан", "#ЮрКонсультация"],
            ["#ЗащитаПрав", "#ЮридическиеУслуги", "#Юрист"],
            ["#ПравоваяПомощь", "#ЮридическийЦентр", "#КонсультацияЮриста"],
            ["#СемейноеПраво", "#ТрудовоеПраво", "#ГражданскоеПраво"],
            ["#ЮридическаяКонсультация", "#ПомощьЮриста", "#ПравовыеВопросы"]
        ]
    
    async def initialize(self):
        """Initialize autopost system"""
        try:
            # Deduplication system doesn't need async initialization
            logger.info("✅ Unified autopost system initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize autopost system: {e}")
    
    async def start_autopost_loop(self):
        """Start the main autopost loop"""
        if self.is_running:
            logger.warning("Autopost loop is already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting unified autopost loop")
        
        # Start background tasks
        asyncio.create_task(self._regular_autopost_loop())
        asyncio.create_task(self._deploy_autopost_loop())
        asyncio.create_task(self._scheduled_posts_processor())
    
    async def stop_autopost_loop(self):
        """Stop the autopost loop"""
        self.is_running = False
        logger.info("🛑 Stopping unified autopost loop")
    
    async def _regular_autopost_loop(self):
        """Regular autopost loop - posts every few hours"""
        await asyncio.sleep(60)  # Initial delay
        
        while self.is_running:
            try:
                if await self._should_create_regular_post():
                    await self._create_and_publish_regular_post()
                
                # Wait for next interval
                wait_time = POST_INTERVAL_HOURS * 3600 + random.randint(-1800, 1800)  # ±30 min
                logger.info(f"⏰ Next regular post in {wait_time // 3600}h {(wait_time % 3600) // 60}m")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"❌ Regular autopost loop error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _deploy_autopost_loop(self):
        """Deploy autopost loop - creates deployment posts"""
        await asyncio.sleep(300)  # 5 minute delay
        
        while self.is_running:
            try:
                # Create deploy post every 24 hours
                await self._create_and_publish_deploy_post()
                
                # Wait 24 hours
                await asyncio.sleep(24 * 3600)
                
            except Exception as e:
                logger.error(f"❌ Deploy autopost loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _scheduled_posts_processor(self):
        """Process scheduled posts"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                for post_id, post in list(self.scheduled_posts.items()):
                    if (post.status == PostStatus.SCHEDULED and 
                        post.scheduled_time <= current_time):
                        
                        await self._publish_scheduled_post(post)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Scheduled posts processor error: {e}")
                await asyncio.sleep(300)
    
    async def _should_create_regular_post(self) -> bool:
        """Check if we should create a regular post"""
        if not PRODUCTION_MODE:
            return False
        
        # Get last post time from database
        try:
            async with async_sessionmaker() as session:
                result = await session.execute(
                    select(func.max(ContentFingerprint.created_at))
                )
                last_post_time = result.scalar()
                
                if not last_post_time:
                    return True  # No posts yet
                
                time_since_last = datetime.now() - last_post_time
                return time_since_last.total_seconds() >= POST_INTERVAL_HOURS * 3600
                
        except Exception as e:
            logger.error(f"Error checking last post time: {e}")
            return True  # Default to allowing post
    
    async def _create_and_publish_regular_post(self):
        """Create and publish a regular post"""
        try:
            # Select random topic
            topic = random.choice(self.legal_topics)
            
            # Generate content
            content = await self._generate_post_content(topic, PostType.REGULAR)
            
            if content:
                await self._publish_post(content, PostType.REGULAR)
                logger.info(f"✅ Regular post published: {topic}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create regular post: {e}")
    
    async def _create_and_publish_deploy_post(self):
        """Create and publish a deploy post"""
        try:
            # Generate deploy announcement
            deploy_content = await self._generate_deploy_content()
            
            if deploy_content:
                await self._publish_post(deploy_content, PostType.DEPLOY)
                logger.info("✅ Deploy post published")
            
        except Exception as e:
            logger.error(f"❌ Failed to create deploy post: {e}")
    
    async def _generate_post_content(self, topic: str, post_type: PostType) -> Optional[PostContent]:
        """Generate post content using AI"""
        try:
            # Generate main content
            ai_response = await unified_ai_service.generate_content(
                topic=topic,
                content_type="post",
                model=AIModel.GPT_4O_MINI
            )
            
            if not ai_response.success:
                logger.error(f"AI content generation failed: {ai_response.error}")
                return None
            
            content_text = ai_response.content
            
            # Check for duplicates and register content
            is_valid, reason = await self.deduplication_service.validate_and_register_content(
                title=topic,
                content=content_text,
                content_type="autopost"
            )
            
            if not is_valid:
                logger.info(f"Content rejected: {reason}")
                self.stats["deduplication_blocks"] += 1
                return None
            
            # Select hashtags
            hashtags = random.choice(self.hashtag_sets)
            
            return PostContent(
                title=topic,
                content=content_text,
                hashtags=hashtags,
                source_topic=topic
            )
            
        except Exception as e:
            logger.error(f"Error generating post content: {e}")
            return None
    
    async def _generate_deploy_content(self) -> Optional[PostContent]:
        """Generate deployment announcement content"""
        try:
            deploy_topics = [
                "Обновление нашей системы юридических консультаций",
                "Улучшения в работе AI-помощника",
                "Новые возможности нашего бота",
                "Оптимизация системы обработки заявок"
            ]
            
            topic = random.choice(deploy_topics)
            
            ai_response = await unified_ai_service.generate_content(
                topic=f"Создайте объявление об обновлении системы: {topic}",
                content_type="post",
                model=AIModel.GPT_4O_MINI
            )
            
            if not ai_response.success:
                return None
            
            return PostContent(
                title="🚀 Обновление системы",
                content=ai_response.content,
                hashtags=["#Обновление", "#ЮридическийЦентр", "#НовыеВозможности"],
                source_topic=topic
            )
            
        except Exception as e:
            logger.error(f"Error generating deploy content: {e}")
            return None
    
    async def _publish_post(self, content: PostContent, post_type: PostType):
        """Publish post to channel"""
        try:
            # Format final message
            message_text = f"""📋 **{content.title}**

{content.content}

{' '.join(content.hashtags)}

💬 Остались вопросы? Обращайтесь к нашему AI-консультанту: {TARGET_CHANNEL_USERNAME}"""
            
            # Send to channel
            await self.bot_application.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=message_text,
                parse_mode="Markdown"
            )
            
            # Update stats
            self.stats["total_posts"] += 1
            self.stats["successful_posts"] += 1
            self.stats["last_post_time"] = datetime.now()
            
            logger.info(f"✅ Post published successfully: {content.title}")
            
        except Exception as e:
            self.stats["total_posts"] += 1
            self.stats["failed_posts"] += 1
            logger.error(f"❌ Failed to publish post: {e}")
    
    async def schedule_post(
        self, 
        content: PostContent, 
        scheduled_time: datetime,
        post_type: PostType = PostType.MANUAL
    ) -> str:
        """Schedule a post for later publication"""
        import uuid
        
        post_id = str(uuid.uuid4())
        
        scheduled_post = ScheduledPost(
            id=post_id,
            content=content,
            post_type=post_type,
            scheduled_time=scheduled_time,
            status=PostStatus.SCHEDULED,
            created_at=datetime.now()
        )
        
        self.scheduled_posts[post_id] = scheduled_post
        
        logger.info(f"📅 Post scheduled for {scheduled_time}: {content.title}")
        return post_id
    
    async def _publish_scheduled_post(self, post: ScheduledPost):
        """Publish a scheduled post"""
        try:
            post.status = PostStatus.PUBLISHED
            await self._publish_post(post.content, post.post_type)
            
            # Remove from scheduled posts
            self.scheduled_posts.pop(post.id, None)
            
        except Exception as e:
            post.attempts += 1
            post.last_error = str(e)
            
            if post.attempts >= 3:
                post.status = PostStatus.FAILED
                logger.error(f"❌ Scheduled post failed after 3 attempts: {e}")
            else:
                # Retry in 10 minutes
                post.scheduled_time = datetime.now() + timedelta(minutes=10)
                logger.warning(f"⚠️ Scheduled post failed, retrying: {e}")
    
    async def create_manual_post(self, topic: str) -> bool:
        """Create and publish a manual post immediately"""
        try:
            content = await self._generate_post_content(topic, PostType.MANUAL)
            
            if content:
                await self._publish_post(content, PostType.MANUAL)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Manual post creation failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get autopost statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "scheduled_posts_count": len(self.scheduled_posts),
            "pending_scheduled": len([p for p in self.scheduled_posts.values() 
                                   if p.status == PostStatus.SCHEDULED]),
            "success_rate": (self.stats["successful_posts"] / max(self.stats["total_posts"], 1)) * 100
        }
    
    def get_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Get list of scheduled posts"""
        return [
            {
                "id": post.id,
                "title": post.content.title,
                "scheduled_time": post.scheduled_time.isoformat(),
                "status": post.status.value,
                "post_type": post.post_type.value,
                "attempts": post.attempts
            }
            for post in self.scheduled_posts.values()
        ]
    
    async def cancel_scheduled_post(self, post_id: str) -> bool:
        """Cancel a scheduled post"""
        if post_id in self.scheduled_posts:
            self.scheduled_posts.pop(post_id)
            logger.info(f"📅 Scheduled post cancelled: {post_id}")
            return True
        return False

# Global autopost system instance (will be initialized with bot application)
autopost_system: Optional[UnifiedAutopostSystem] = None

def initialize_autopost_system(bot_application: TelegramApplication):
    """Initialize the global autopost system"""
    global autopost_system
    autopost_system = UnifiedAutopostSystem(bot_application)
    return autopost_system

# ================ LEGACY COMPATIBILITY FUNCTIONS ================

async def should_create_autopost() -> bool:
    """Legacy compatibility function"""
    if autopost_system:
        return await autopost_system._should_create_regular_post()
    return False

async def get_enhanced_autopost_status() -> Dict[str, Any]:
    """Legacy compatibility function"""
    if autopost_system:
        return autopost_system.get_stats()
    return {"status": "not_initialized"}

async def schedule_smart_post(topic: str, scheduled_time: datetime) -> str:
    """Legacy compatibility function"""
    if not autopost_system:
        raise RuntimeError("Autopost system not initialized")
    
    content = await autopost_system._generate_post_content(topic, PostType.SMART)
    if content:
        return await autopost_system.schedule_post(content, scheduled_time, PostType.SMART)
    raise RuntimeError("Failed to generate post content")

async def get_scheduled_posts() -> List[Dict[str, Any]]:
    """Legacy compatibility function"""
    if autopost_system:
        return autopost_system.get_scheduled_posts()
    return []

async def publish_post_now(topic: str) -> bool:
    """Legacy compatibility function"""
    if autopost_system:
        return await autopost_system.create_manual_post(topic)
    return False

async def get_autopost_dashboard() -> Dict[str, Any]:
    """Legacy compatibility function"""
    if autopost_system:
        stats = autopost_system.get_stats()
        scheduled = autopost_system.get_scheduled_posts()
        
        return {
            "stats": stats,
            "scheduled_posts": scheduled,
            "available_topics": autopost_system.legal_topics[:10]  # Sample topics
        }
    
    return {"error": "Autopost system not initialized"}