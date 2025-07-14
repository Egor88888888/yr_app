"""
🚀 TELEGRAM PUBLISHER - PRODUCTION READY
Real Telegram publishing with advanced features:
- Channel publishing with media support
- Error handling and retry logic
- Rate limiting and queue management
- A/B testing variants
- Message editing and deletion
- Analytics integration
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import random
import json

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import TelegramError, RetryAfter, BadRequest, Forbidden
from telegram.constants import ParseMode, ChatType

logger = logging.getLogger(__name__)


class PublishStatus(Enum):
    """Статусы публикации"""
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """Типы сообщений"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    POLL = "poll"


@dataclass
class PublishResult:
    """Результат публикации"""
    success: bool
    message_id: Optional[int] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    channel_id: Optional[str] = None
    retry_count: int = 0


@dataclass
class PublishRequest:
    """Запрос на публикацию"""
    post_id: str
    channel_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    parse_mode: ParseMode = ParseMode.HTML
    reply_markup: Optional[InlineKeyboardMarkup] = None
    media_url: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    max_retries: int = 3
    priority: int = 1
    ab_test_variant: Optional[str] = None
    track_analytics: bool = True


class TelegramPublisher:
    """Production-ready Telegram publisher"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.publish_queue: List[PublishRequest] = []
        self.published_messages: Dict[str, PublishResult] = {}
        self.rate_limiter = RateLimiter()
        self.retry_manager = RetryManager()
        self.analytics_tracker = PublishAnalyticsTracker()

        # Настройки
        self.max_queue_size = 1000
        self.processing_batch_size = 5
        self.queue_check_interval = 30  # секунд

        self.is_running = False

    async def start_publisher(self):
        """Запуск системы публикации"""
        self.is_running = True
        logger.info("🚀 Starting Telegram Publisher")

        # Запускаем основные процессы в фоне (не ждем их завершения)
        asyncio.create_task(self._process_publish_queue())
        asyncio.create_task(self._monitor_published_messages())
        asyncio.create_task(self._cleanup_old_data())

        logger.info("✅ Telegram Publisher background tasks started")

    async def stop_publisher(self):
        """Остановка системы публикации"""
        self.is_running = False
        logger.info("🛑 Stopping Telegram Publisher")

    async def schedule_publish(self, request: PublishRequest) -> str:
        """Планирование публикации"""
        try:
            # Валидация запроса
            await self._validate_publish_request(request)

            # Проверяем очередь
            if len(self.publish_queue) >= self.max_queue_size:
                raise Exception(
                    f"Publish queue is full ({self.max_queue_size} items)")

            # Добавляем в очередь
            self.publish_queue.append(request)

            logger.info(
                f"📅 Scheduled publish for post {request.post_id} to {request.channel_id}")

            # Немедленная публикация если время пришло
            if request.scheduled_time and request.scheduled_time <= datetime.now():
                await self._immediate_publish(request)

            return request.post_id

        except Exception as e:
            logger.error(f"Failed to schedule publish: {e}")
            raise

    async def publish_now(self, request: PublishRequest) -> PublishResult:
        """Немедленная публикация"""
        try:
            # Валидация
            await self._validate_publish_request(request)

            # Проверка rate limit
            await self.rate_limiter.wait_if_needed(request.channel_id)

            # Публикация
            result = await self._execute_publish(request)

            # Сохраняем результат
            self.published_messages[request.post_id] = result

            # Трекинг аналитики
            if request.track_analytics:
                await self.analytics_tracker.track_publish(request, result)

            return result

        except Exception as e:
            logger.error(f"Failed to publish post {request.post_id}: {e}")
            result = PublishResult(
                success=False,
                error_message=str(e),
                channel_id=request.channel_id
            )
            self.published_messages[request.post_id] = result
            return result

    async def _process_publish_queue(self):
        """Обработка очереди публикации"""
        while self.is_running:
            try:
                current_time = datetime.now()

                # Находим посты для публикации
                ready_requests = [
                    req for req in self.publish_queue
                    if req.scheduled_time and req.scheduled_time <= current_time
                ]

                # Сортируем по приоритету
                ready_requests.sort(
                    key=lambda x: (-x.priority, x.scheduled_time))

                # Обрабатываем batch
                batch = ready_requests[:self.processing_batch_size]

                for request in batch:
                    try:
                        await self.publish_now(request)
                        self.publish_queue.remove(request)
                    except Exception as e:
                        logger.error(f"Error processing publish request: {e}")
                        await self._handle_publish_error(request, e)

                await asyncio.sleep(self.queue_check_interval)

            except Exception as e:
                logger.error(f"Error in publish queue processing: {e}")
                await asyncio.sleep(60)

    async def _execute_publish(self, request: PublishRequest) -> PublishResult:
        """Выполнение публикации"""
        try:
            message = None

            if request.message_type == MessageType.TEXT:
                message = await self.bot.send_message(
                    chat_id=request.channel_id,
                    text=request.content,
                    parse_mode=request.parse_mode,
                    reply_markup=request.reply_markup,
                    disable_web_page_preview=False
                )

            elif request.message_type == MessageType.PHOTO:
                message = await self.bot.send_photo(
                    chat_id=request.channel_id,
                    photo=request.media_url,
                    caption=request.content,
                    parse_mode=request.parse_mode,
                    reply_markup=request.reply_markup
                )

            elif request.message_type == MessageType.VIDEO:
                message = await self.bot.send_video(
                    chat_id=request.channel_id,
                    video=request.media_url,
                    caption=request.content,
                    parse_mode=request.parse_mode,
                    reply_markup=request.reply_markup
                )

            elif request.message_type == MessageType.POLL:
                poll_data = json.loads(request.content)
                message = await self.bot.send_poll(
                    chat_id=request.channel_id,
                    question=poll_data['question'],
                    options=poll_data['options'],
                    is_anonymous=poll_data.get('is_anonymous', True),
                    allows_multiple_answers=poll_data.get(
                        'multiple_answers', False)
                )

            if message:
                return PublishResult(
                    success=True,
                    message_id=message.message_id,
                    published_at=datetime.now(),
                    channel_id=request.channel_id
                )
            else:
                raise Exception("Message was not sent")

        except RetryAfter as e:
            # Telegram rate limit
            logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            raise

        except Forbidden as e:
            # Бот не имеет доступа к каналу
            logger.error(f"Bot forbidden in channel {request.channel_id}: {e}")
            raise

        except BadRequest as e:
            # Неверный запрос
            logger.error(f"Bad request for channel {request.channel_id}: {e}")
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error publishing to {request.channel_id}: {e}")
            raise

    async def _validate_publish_request(self, request: PublishRequest):
        """Валидация запроса на публикацию"""
        if not request.post_id:
            raise ValueError("post_id is required")

        if not request.channel_id:
            raise ValueError("channel_id is required")

        if not request.content and request.message_type == MessageType.TEXT:
            raise ValueError("content is required for text messages")

        if request.message_type in [MessageType.PHOTO, MessageType.VIDEO] and not request.media_url:
            raise ValueError(
                f"media_url is required for {request.message_type.value} messages")

        # Проверяем доступность канала
        try:
            chat = await self.bot.get_chat(request.channel_id)
            if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                raise ValueError(f"Invalid chat type: {chat.type}")
        except Exception as e:
            raise ValueError(
                f"Cannot access channel {request.channel_id}: {e}")

    async def _handle_publish_error(self, request: PublishRequest, error: Exception):
        """Обработка ошибок публикации"""
        request.max_retries -= 1

        if request.max_retries > 0:
            # Retry with exponential backoff
            delay = 2 ** (3 - request.max_retries) * 60  # 1, 2, 4 minutes
            request.scheduled_time = datetime.now() + timedelta(seconds=delay)

            logger.info(
                f"Retrying post {request.post_id} in {delay} seconds ({request.max_retries} retries left)")
        else:
            # Failed permanently
            self.publish_queue.remove(request)

            result = PublishResult(
                success=False,
                error_message=str(error),
                channel_id=request.channel_id
            )
            self.published_messages[request.post_id] = result

            logger.error(f"Post {request.post_id} failed permanently: {error}")

    async def edit_message(
        self,
        post_id: str,
        new_content: str,
        new_reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Редактирование опубликованного сообщения"""
        if post_id not in self.published_messages:
            return False

        result = self.published_messages[post_id]
        if not result.success or not result.message_id:
            return False

        try:
            await self.bot.edit_message_text(
                chat_id=result.channel_id,
                message_id=result.message_id,
                text=new_content,
                parse_mode=ParseMode.HTML,
                reply_markup=new_reply_markup
            )

            logger.info(
                f"Edited message {result.message_id} in {result.channel_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to edit message {result.message_id}: {e}")
            return False

    async def delete_message(self, post_id: str) -> bool:
        """Удаление опубликованного сообщения"""
        if post_id not in self.published_messages:
            return False

        result = self.published_messages[post_id]
        if not result.success or not result.message_id:
            return False

        try:
            await self.bot.delete_message(
                chat_id=result.channel_id,
                message_id=result.message_id
            )

            logger.info(
                f"Deleted message {result.message_id} from {result.channel_id}")

            # Помечаем как удаленное
            result.message_id = None
            return True

        except Exception as e:
            logger.error(f"Failed to delete message {result.message_id}: {e}")
            return False

    async def get_publish_status(self, post_id: str) -> Optional[PublishResult]:
        """Получение статуса публикации"""
        return self.published_messages.get(post_id)

    async def _monitor_published_messages(self):
        """Мониторинг опубликованных сообщений"""
        while self.is_running:
            try:
                # Здесь можно добавить логику мониторинга:
                # - Проверка доступности сообщений
                # - Сбор метрик просмотров (если доступно)
                # - Уведомления об удалении сообщений

                await asyncio.sleep(300)  # Проверяем каждые 5 минут

            except Exception as e:
                logger.error(f"Error in message monitoring: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_data(self):
        """Очистка старых данных"""
        while self.is_running:
            try:
                cutoff_time = datetime.now() - timedelta(days=7)

                # Удаляем старые результаты публикации
                old_posts = [
                    post_id for post_id, result in self.published_messages.items()
                    if result.published_at and result.published_at < cutoff_time
                ]

                for post_id in old_posts:
                    del self.published_messages[post_id]

                if old_posts:
                    logger.info(
                        f"Cleaned up {len(old_posts)} old publish results")

                await asyncio.sleep(3600)  # Очищаем каждый час

            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(1800)

    async def _immediate_publish(self, request: PublishRequest):
        """Немедленная публикация для готовых постов"""
        try:
            await self.publish_now(request)
            self.publish_queue.remove(request)
        except Exception as e:
            logger.error(f"Failed immediate publish: {e}")


class RateLimiter:
    """Rate limiter для Telegram API"""

    def __init__(self):
        self.channel_timings: Dict[str, List[datetime]] = {}
        self.global_timings: List[datetime] = []

        # Лимиты Telegram API
        self.channel_limit = 20  # сообщений в минуту на канал
        self.global_limit = 30   # общий лимит в секунду

    async def wait_if_needed(self, channel_id: str):
        """Ожидание если нужно соблюсти rate limit"""
        current_time = datetime.now()

        # Проверяем лимит канала
        if channel_id not in self.channel_timings:
            self.channel_timings[channel_id] = []

        channel_times = self.channel_timings[channel_id]

        # Удаляем старые записи (старше минуты)
        cutoff = current_time - timedelta(minutes=1)
        channel_times[:] = [t for t in channel_times if t > cutoff]

        # Проверяем лимит
        if len(channel_times) >= self.channel_limit:
            wait_time = 60 - (current_time - channel_times[0]).total_seconds()
            if wait_time > 0:
                logger.info(
                    f"Rate limit reached for {channel_id}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        # Записываем время публикации
        self.channel_timings[channel_id].append(current_time)
        self.global_timings.append(current_time)

        # Очищаем глобальные записи
        global_cutoff = current_time - timedelta(seconds=1)
        self.global_timings[:] = [
            t for t in self.global_timings if t > global_cutoff]


class RetryManager:
    """Менеджер повторных попыток"""

    def __init__(self):
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = 3

    def should_retry(self, post_id: str, error: Exception) -> bool:
        """Определяет, нужно ли повторить попытку"""
        if post_id not in self.retry_counts:
            self.retry_counts[post_id] = 0

        if self.retry_counts[post_id] >= self.max_retries:
            return False

        # Определяем, стоит ли повторять для данного типа ошибки
        if isinstance(error, RetryAfter):
            return True

        if isinstance(error, (Forbidden, BadRequest)):
            return False  # Эти ошибки не исправятся повтором

        return True

    def get_retry_delay(self, post_id: str) -> int:
        """Получает задержку для повторной попытки (exponential backoff)"""
        retry_count = self.retry_counts.get(post_id, 0)
        return min(2 ** retry_count * 60, 3600)  # максимум час

    def increment_retry(self, post_id: str):
        """Увеличивает счетчик попыток"""
        if post_id not in self.retry_counts:
            self.retry_counts[post_id] = 0
        self.retry_counts[post_id] += 1


class PublishAnalyticsTracker:
    """Трекер аналитики публикаций"""

    def __init__(self):
        self.publish_stats: Dict[str, Dict[str, Any]] = {}

    async def track_publish(self, request: PublishRequest, result: PublishResult):
        """Трекинг публикации"""
        try:
            self.publish_stats[request.post_id] = {
                'channel_id': request.channel_id,
                'message_type': request.message_type.value,
                'published_at': result.published_at,
                'success': result.success,
                'ab_variant': request.ab_test_variant,
                'retry_count': result.retry_count
            }

            logger.info(f"📊 Tracked publish for post {request.post_id}")

        except Exception as e:
            logger.error(f"Failed to track publish analytics: {e}")

    def get_publish_stats(self, days_back: int = 7) -> Dict[str, Any]:
        """Получение статистики публикаций"""
        cutoff_time = datetime.now() - timedelta(days=days_back)

        recent_stats = [
            stats for stats in self.publish_stats.values()
            if stats.get('published_at') and stats['published_at'] > cutoff_time
        ]

        total_posts = len(recent_stats)
        successful_posts = len([s for s in recent_stats if s['success']])
        failed_posts = total_posts - successful_posts

        return {
            'total_posts': total_posts,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts,
            'success_rate': successful_posts / total_posts if total_posts > 0 else 0,
            'channels': list(set(s['channel_id'] for s in recent_stats)),
            'message_types': {
                mt: len([s for s in recent_stats if s['message_type'] == mt])
                for mt in set(s['message_type'] for s in recent_stats)
            }
        }
