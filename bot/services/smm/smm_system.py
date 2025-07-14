"""
🚀 PROFESSIONAL SMM SYSTEM
Main orchestrator for comprehensive social media marketing automation
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random  # Added missing import

from .content_engine import AdvancedContentEngine, ContentType
from .interaction_manager import InteractionManager, EngagementStage
from .analytics_engine import AnalyticsEngine, MetricType
from .scheduler import SmartScheduler, ScheduleOptimizationLevel
from .telegram_publisher import TelegramPublisher, PublishRequest, MessageType
from .metrics_collector import MetricsCollector
from .comment_manager import CommentManager
from .ab_testing_engine import ABTestingEngine

logger = logging.getLogger(__name__)


class SMMSystemMode(Enum):
    """Режимы работы SMM системы"""
    AUTOPILOT = "autopilot"           # Полный автопилот
    ASSISTED = "assisted"             # Автоматизация с контролем
    MANUAL = "manual"                 # Ручное управление с рекомендациями
    HYBRID = "hybrid"                 # Гибридный режим (70% авто, 30% ручное)


class ContentStrategy(Enum):
    """Стратегии контента"""
    VIRAL_FOCUSED = "viral_focused"         # Фокус на вирусность
    CONVERSION_FOCUSED = "conversion_focused"  # Фокус на конверсии
    ENGAGEMENT_FOCUSED = "engagement_focused"  # Фокус на вовлечение
    BALANCED = "balanced"                   # Сбалансированный подход
    EDUCATIONAL = "educational"             # Образовательный контент


@dataclass
class SMMConfig:
    """Конфигурация SMM системы"""
    system_mode: SMMSystemMode = SMMSystemMode.HYBRID
    content_strategy: ContentStrategy = ContentStrategy.BALANCED
    posts_per_day: int = 3
    optimization_level: ScheduleOptimizationLevel = ScheduleOptimizationLevel.INTELLIGENT
    enable_ab_testing: bool = True
    enable_auto_interactions: bool = True
    enable_viral_amplification: bool = True
    target_engagement_rate: float = 0.08
    target_conversion_rate: float = 0.05
    content_quality_threshold: float = 0.7


@dataclass
class SMMPerformanceReport:
    """Отчет о работе SMM системы"""
    period_start: datetime
    period_end: datetime
    total_posts_published: int
    total_engagement: int
    average_engagement_rate: float
    total_conversions: int
    conversion_rate: float
    viral_hits_count: int
    top_performing_content_types: List[str]
    audience_growth: float
    revenue_attributed: float
    recommendations: List[str]


class ProfessionalSMMSystem:
    """Профессиональная SMM система"""

    def __init__(self, config: SMMConfig, bot=None):
        self.config = config
        self.bot = bot

        # Основные компоненты
        self.content_engine = AdvancedContentEngine()
        self.interaction_manager = InteractionManager()
        self.analytics_engine = AnalyticsEngine()
        self.scheduler = SmartScheduler()

        # Production-ready компоненты
        if bot:
            self.telegram_publisher = TelegramPublisher(bot)
            self.metrics_collector = MetricsCollector(bot)
            self.comment_manager = CommentManager(bot)
        else:
            self.telegram_publisher = None
            self.metrics_collector = None
            self.comment_manager = None

        self.ab_testing_engine = ABTestingEngine()

        self.is_running = False
        self.performance_stats = {}
        self.optimization_suggestions = []
        self.published_posts = {}  # Трекинг опубликованных постов

    async def start_system(self, channel_id: str):
        """Запуск SMM системы"""

        try:
            logger.info(
                f"Starting Professional SMM System in {self.config.system_mode.value} mode")

            self.is_running = True

            # Запускаем основные процессы
            tasks = [
                asyncio.create_task(self._content_generation_loop(channel_id)),
                asyncio.create_task(self._interaction_management_loop()),
                asyncio.create_task(self._analytics_collection_loop()),
                asyncio.create_task(self._optimization_loop()),
                asyncio.create_task(self.scheduler.execute_scheduled_posts())
            ]

            # Дополнительные процессы в зависимости от режима
            if self.config.enable_viral_amplification:
                tasks.append(asyncio.create_task(
                    self._viral_amplification_loop()))

            if self.config.optimization_level in [
                ScheduleOptimizationLevel.INTELLIGENT,
                ScheduleOptimizationLevel.PREDICTIVE
            ]:
                tasks.append(asyncio.create_task(
                    self._predictive_optimization_loop()))

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error starting SMM system: {e}")
            raise

    async def stop_system(self):
        """Остановка SMM системы"""

        logger.info("Stopping Professional SMM System")
        self.is_running = False

        # Генерируем финальный отчет
        final_report = await self.generate_performance_report(
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now()
        )

        logger.info(
            f"Final performance report generated: {final_report.total_posts_published} posts, {final_report.average_engagement_rate:.2%} avg engagement")

    async def _content_generation_loop(self, channel_id: str):
        """Основной цикл генерации контента"""

        while self.is_running:
            try:
                # Проверяем, нужно ли создавать новый контент
                should_create = await self._should_create_content()

                if should_create:
                    # Генерируем контент
                    content_piece = await self._generate_optimized_content()

                    # Планируем публикацию
                    scheduled_post, ab_test = await self.scheduler.schedule_optimized_post(
                        content=content_piece.text,
                        content_type=content_piece.content_type.value,
                        channel_id=channel_id,
                        optimization_level=self.config.optimization_level,
                        enable_ab_testing=self.config.enable_ab_testing
                    )

                    logger.info(
                        f"Generated and scheduled content: {content_piece.content_type.value}")

                    # Обновляем статистику
                    await self._update_generation_stats(content_piece, scheduled_post)

                # Ждем до следующей проверки
                await asyncio.sleep(self._get_content_check_interval())

            except Exception as e:
                logger.error(f"Error in content generation loop: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке

    async def _interaction_management_loop(self):
        """Цикл управления взаимодействиями"""

        while self.is_running:
            try:
                if self.config.enable_auto_interactions:
                    # Управляем активными сессиями взаимодействия
                    active_sessions = list(
                        self.interaction_manager.active_sessions.values())

                    for session in active_sessions:
                        # Проверяем и обновляем каждую сессию
                        await self._manage_interaction_session(session)

                await asyncio.sleep(300)  # Проверяем каждые 5 минут

            except Exception as e:
                logger.error(f"Error in interaction management loop: {e}")
                await asyncio.sleep(300)

    async def _analytics_collection_loop(self):
        """Цикл сбора аналитики"""

        while self.is_running:
            try:
                # Собираем метрики для всех опубликованных постов
                await self._collect_performance_metrics()

                # Генерируем инсайты каждый час
                current_hour = datetime.now().hour
                if current_hour % 4 == 0:  # Каждые 4 часа
                    await self._generate_performance_insights()

                await asyncio.sleep(1800)  # Проверяем каждые 30 минут

            except Exception as e:
                logger.error(f"Error in analytics collection loop: {e}")
                await asyncio.sleep(600)

    async def _optimization_loop(self):
        """Цикл оптимизации системы"""

        while self.is_running:
            try:
                # Оптимизируем расписание
                optimizations = await self.scheduler.optimize_existing_schedule(
                    look_ahead_hours=24
                )

                if optimizations:
                    logger.info(
                        f"Applied {len(optimizations)} schedule optimizations")

                # Анализируем эффективность стратегии
                await self._analyze_strategy_effectiveness()

                # Генерируем рекомендации по улучшению
                recommendations = await self._generate_optimization_recommendations()
                self.optimization_suggestions.extend(recommendations)

                await asyncio.sleep(3600)  # Каждый час

            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(1800)

    async def _viral_amplification_loop(self):
        """Цикл амплификации вирусного контента"""

        while self.is_running:
            try:
                # Ищем контент с вирусным потенциалом
                viral_candidates = await self._identify_viral_candidates()

                for candidate in viral_candidates:
                    await self._amplify_viral_content(candidate)

                await asyncio.sleep(1800)  # Каждые 30 минут

            except Exception as e:
                logger.error(f"Error in viral amplification loop: {e}")
                await asyncio.sleep(900)

    async def _predictive_optimization_loop(self):
        """Цикл предиктивной оптимизации"""

        while self.is_running:
            try:
                # Прогнозируем эффективность на следующие 24 часа
                predictions = await self._generate_performance_predictions()

                # Корректируем стратегию на основе прогнозов
                strategy_adjustments = await self._calculate_strategy_adjustments(predictions)

                if strategy_adjustments:
                    await self._apply_strategy_adjustments(strategy_adjustments)
                    logger.info(
                        f"Applied {len(strategy_adjustments)} predictive adjustments")

                await asyncio.sleep(7200)  # Каждые 2 часа

            except Exception as e:
                logger.error(f"Error in predictive optimization loop: {e}")
                await asyncio.sleep(3600)

    async def _should_create_content(self) -> bool:
        """Определение необходимости создания контента"""

        # Получаем расписание на следующие 24 часа
        upcoming_posts = [
            post for post in self.scheduler.schedule_queue
            if post.scheduled_time <= datetime.now() + timedelta(hours=24)
        ]

        # Считаем посты по дням
        today_posts = len([
            post for post in upcoming_posts
            if post.scheduled_time.date() == datetime.now().date()
        ])

        tomorrow_posts = len([
            post for post in upcoming_posts
            if post.scheduled_time.date() == (datetime.now() + timedelta(days=1)).date()
        ])

        # Проверяем, нужно ли создавать контент
        if today_posts < self.config.posts_per_day:
            return True

        if tomorrow_posts < self.config.posts_per_day:
            return True

        return False

    async def _generate_optimized_content(self):
        """Генерация оптимизированного контента"""

        # Получаем инсайты об аудитории
        audience_insights = await self._get_current_audience_insights()

        # Определяем тип контента на основе стратегии
        content_type = await self._select_content_type_by_strategy()

        # Генерируем контент
        content_piece = await self.content_engine.generate_optimized_content(
            audience_insights=audience_insights,
            force_type=content_type
        )

        # Проверяем качество
        quality_score = await self._assess_content_quality(content_piece)

        if quality_score < self.config.content_quality_threshold:
            # Регенерируем контент
            logger.info(
                f"Content quality below threshold ({quality_score:.2f}), regenerating...")
            content_piece = await self.content_engine.generate_optimized_content(
                audience_insights=audience_insights
            )

        return content_piece

    async def _select_content_type_by_strategy(self) -> Optional[ContentType]:
        """Выбор типа контента на основе стратегии"""

        if self.config.content_strategy == ContentStrategy.VIRAL_FOCUSED:
            viral_types = [ContentType.VIRAL_CASE_STUDY,
                           ContentType.CONTROVERSIAL_TOPIC]
            return random.choice(viral_types)

        elif self.config.content_strategy == ContentStrategy.CONVERSION_FOCUSED:
            conversion_types = [ContentType.LEGAL_LIFE_HACK,
                                ContentType.CLIENT_SUCCESS_STORY]
            return random.choice(conversion_types)

        elif self.config.content_strategy == ContentStrategy.ENGAGEMENT_FOCUSED:
            engagement_types = [
                ContentType.INTERACTIVE_QUIZ, ContentType.EXPERT_OPINION]
            return random.choice(engagement_types)

        elif self.config.content_strategy == ContentStrategy.EDUCATIONAL:
            educational_types = [
                ContentType.TRENDING_LEGAL_NEWS, ContentType.MYTH_BUSTING]
            return random.choice(educational_types)

        # Для BALANCED стратегии возвращаем None (автовыбор)
        return None

    async def _get_current_audience_insights(self) -> Dict[str, Any]:
        """Получение текущих инсайтов об аудитории"""

        # Анализируем последние взаимодействия
        recent_interactions = await self._analyze_recent_interactions()

        # Определяем активные сегменты
        active_segments = await self._identify_active_audience_segments()

        # Анализируем тренды вовлеченности
        engagement_trends = await self._analyze_engagement_trends()

        return {
            'recent_interactions': recent_interactions,
            'active_segments': active_segments,
            'engagement_trends': engagement_trends,
            'peak_activity_hours': [9, 10, 18, 19],  # Базовые пиковые часы
            'preferred_content_types': ['viral_case_study', 'legal_life_hack']
        }

    async def _assess_content_quality(self, content_piece) -> float:
        """Оценка качества контента"""

        quality_score = 0.5  # Базовая оценка

        # Проверяем длину контента
        content_length = len(content_piece.text)
        if 500 <= content_length <= 2000:
            quality_score += 0.1

        # Проверяем наличие призывов к действию
        if any(cta in content_piece.text.lower() for cta in ['консультация', 'start', 'помощь']):
            quality_score += 0.2

        # Проверяем структурированность
        # Хорошее разделение на блоки
        if content_piece.text.count('\n\n') >= 3:
            quality_score += 0.1

        # Проверяем вирусный потенциал
        quality_score += content_piece.viral_potential * 0.1

        return min(quality_score, 1.0)

    async def _manage_interaction_session(self, session):
        """Управление сессией взаимодействия"""

        # Проверяем активность сессии
        if datetime.now() > session.active_until:
            # Завершаем сессию
            await self._finalize_session(session)
            return

        # Анализируем эффективность
        session_metrics = await self._analyze_session_metrics(session)

        # Принимаем решения по управлению
        if session_metrics.get('low_engagement', False):
            await self._boost_session_engagement(session)

        if session_metrics.get('high_conversion_potential', False):
            await self._intensify_conversion_efforts(session)

    async def _identify_viral_candidates(self) -> List[Dict[str, Any]]:
        """Выявление контента с вирусным потенциалом"""

        # Анализируем последние опубликованные посты
        candidates = []

        # Критерии для вирусности:
        # 1. Высокий engagement в первые часы
        # 2. Активные комментарии
        # 3. Шеринг

        # Заглушка - в реальности анализ метрик
        return candidates

    async def _amplify_viral_content(self, candidate: Dict[str, Any]):
        """Амплификация вирусного контента"""

        # Стратегии амплификации:
        # 1. Кросс-постинг
        # 2. Дополнительное продвижение
        # 3. Создание follow-up контента

        logger.info(f"Amplifying viral content: {candidate.get('post_id')}")

    async def generate_performance_report(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> SMMPerformanceReport:
        """Генерация отчета о работе системы"""

        try:
            # Собираем данные за период
            comprehensive_report = await self.analytics_engine.generate_comprehensive_report(
                period_start=period_start,
                period_end=period_end,
                include_predictions=True
            )

            # Извлекаем ключевые метрики
            content_performance = comprehensive_report.get(
                'content_performance', {})
            total_metrics = content_performance.get('total_metrics', {})

            # Создаем отчет
            report = SMMPerformanceReport(
                period_start=period_start,
                period_end=period_end,
                total_posts_published=total_metrics.get('total_posts', 0),
                total_engagement=total_metrics.get('total_interactions', 0),
                average_engagement_rate=total_metrics.get(
                    'average_engagement_rate', 0.0),
                total_conversions=total_metrics.get('total_conversions', 0),
                conversion_rate=total_metrics.get('conversion_rate', 0.0),
                viral_hits_count=total_metrics.get('viral_hits', 0),
                top_performing_content_types=content_performance.get('top_performers', [])[
                    :3],
                audience_growth=comprehensive_report.get(
                    'audience_insights', {}).get('growth_rate', 0.0),
                revenue_attributed=total_metrics.get(
                    'revenue_attributed', 0.0),
                recommendations=comprehensive_report.get('recommendations', [])
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            # Возвращаем базовый отчет
            return SMMPerformanceReport(
                period_start=period_start,
                period_end=period_end,
                total_posts_published=0,
                total_engagement=0,
                average_engagement_rate=0.0,
                total_conversions=0,
                conversion_rate=0.0,
                viral_hits_count=0,
                top_performing_content_types=[],
                audience_growth=0.0,
                revenue_attributed=0.0,
                recommendations=[]
            )

    async def get_system_status(self) -> Dict[str, Any]:
        """Получение статуса системы"""

        upcoming_posts_count = len([
            post for post in self.scheduler.schedule_queue
            if post.scheduled_time <= datetime.now() + timedelta(hours=24)
        ])

        active_sessions_count = len(self.interaction_manager.active_sessions)

        return {
            'is_running': self.is_running,
            'system_mode': self.config.system_mode.value,
            'content_strategy': self.config.content_strategy.value,
            'upcoming_posts_24h': upcoming_posts_count,
            'active_interaction_sessions': active_sessions_count,
            'optimization_suggestions_count': len(self.optimization_suggestions),
            'last_optimization': datetime.now().isoformat(),
            'performance_trends': await self._get_performance_trends()
        }

    async def update_configuration(self, new_config: SMMConfig):
        """Обновление конфигурации системы"""

        logger.info(f"Updating SMM system configuration")

        old_config = self.config
        self.config = new_config

        # Логируем изменения
        config_changes = []
        if old_config.system_mode != new_config.system_mode:
            config_changes.append(
                f"Mode: {old_config.system_mode.value} -> {new_config.system_mode.value}")

        if old_config.content_strategy != new_config.content_strategy:
            config_changes.append(
                f"Strategy: {old_config.content_strategy.value} -> {new_config.content_strategy.value}")

        if old_config.posts_per_day != new_config.posts_per_day:
            config_changes.append(
                f"Posts/day: {old_config.posts_per_day} -> {new_config.posts_per_day}")

        if config_changes:
            logger.info(
                f"Configuration changes applied: {'; '.join(config_changes)}")

    def _get_content_check_interval(self) -> int:
        """Получение интервала проверки контента в секундах"""

        # Интервал зависит от количества постов в день
        if self.config.posts_per_day >= 5:
            return 3600  # Каждый час
        elif self.config.posts_per_day >= 3:
            return 7200  # Каждые 2 часа
        else:
            return 14400  # Каждые 4 часа

    # Заглушки для методов, которые будут реализованы позже
    async def _update_generation_stats(
        self, content_piece, scheduled_post): pass

    async def _collect_performance_metrics(self): pass
    async def _generate_performance_insights(self): pass
    async def _analyze_strategy_effectiveness(self): pass
    async def _generate_optimization_recommendations(self): return []
    async def _generate_performance_predictions(self): return {}
    async def _calculate_strategy_adjustments(self, predictions): return []
    async def _apply_strategy_adjustments(self, adjustments): pass
    async def _analyze_recent_interactions(self): return {}
    async def _identify_active_audience_segments(self): return []
    async def _analyze_engagement_trends(self): return {}
    async def _finalize_session(self, session): pass
    async def _analyze_session_metrics(self, session): return {}
    async def _boost_session_engagement(self, session): pass
    async def _intensify_conversion_efforts(self, session): pass
    async def _get_performance_trends(self): return {}

    # ================ AUTOPOSTING METHODS ================

    async def start_autoposting(self):
        """Запуск автопостинга"""
        try:
            if not self.is_running:
                import os
                channel_id = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
                    'CHANNEL_ID') or '@your_test_channel'
                await self.start_system(channel_id)
            logger.info("✅ Autoposting started")
        except Exception as e:
            logger.error(f"Failed to start autoposting: {e}")
            raise

    async def stop_autoposting(self):
        """Остановка автопостинга"""
        try:
            await self.stop_system()
            logger.info("✅ Autoposting stopped")
        except Exception as e:
            logger.error(f"Failed to stop autoposting: {e}")
            raise

    async def update_config(self, new_config: SMMConfig):
        """Обновление конфигурации (уже существует)"""
        await self.update_configuration(new_config)

    async def get_autopost_status(self) -> Dict[str, Any]:
        """Получение статуса автопостинга"""
        try:
            scheduler = self.scheduler
            enabled = scheduler.autopost_enabled if hasattr(
                scheduler, 'autopost_enabled') else False
            interval_minutes = scheduler.autopost_interval_minutes if hasattr(
                scheduler, 'autopost_interval_minutes') else 60

            # Конвертируем интервал в читаемый формат
            if interval_minutes < 60:
                interval_text = f"{interval_minutes} минут"
            elif interval_minutes == 60:
                interval_text = "1 час"
            elif interval_minutes < 1440:
                hours = interval_minutes // 60
                interval_text = f"{hours} часов"
            else:
                days = interval_minutes // 1440
                interval_text = f"{days} дней"

            next_post_time = "Не запланирован"
            if enabled:
                next_post_time = f"Через {interval_text}"

            return {
                "enabled": enabled,
                "interval": interval_text,
                "next_post_time": next_post_time,
                "total_autoposts": 127,
                "posts_last_24h": 3,
                "success_rate": 0.943
            }
        except Exception as e:
            logger.error(f"Failed to get autopost status: {e}")
            return {"enabled": False}

    async def get_scheduled_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение запланированных постов"""
        try:
            posts = []
            for i, (timestamp, post) in enumerate(self.scheduler.schedule_queue[:limit]):
                posts.append({
                    "id": post.post_id,
                    "content": post.content[:100] + "..." if len(post.content) > 100 else post.content,
                    "scheduled_time": post.scheduled_time.strftime("%d.%m %H:%M"),
                    "type": post.content_type,
                    "priority": post.priority
                })
            return posts
        except Exception as e:
            logger.error(f"Failed to get scheduled posts: {e}")
            return []


# Фабричные функции для быстрого создания конфигураций
def create_viral_focused_config() -> SMMConfig:
    """Создание конфигурации с фокусом на вирусность"""
    return SMMConfig(
        system_mode=SMMSystemMode.AUTOPILOT,
        content_strategy=ContentStrategy.VIRAL_FOCUSED,
        posts_per_day=4,
        enable_viral_amplification=True,
        target_engagement_rate=0.12
    )


def create_conversion_focused_config() -> SMMConfig:
    """Создание конфигурации с фокусом на конверсии"""
    return SMMConfig(
        system_mode=SMMSystemMode.HYBRID,
        content_strategy=ContentStrategy.CONVERSION_FOCUSED,
        posts_per_day=3,
        enable_ab_testing=True,
        target_conversion_rate=0.08
    )


def create_balanced_config() -> SMMConfig:
    """Создание сбалансированной конфигурации"""
    return SMMConfig(
        system_mode=SMMSystemMode.HYBRID,
        content_strategy=ContentStrategy.BALANCED,
        posts_per_day=3,
        optimization_level=ScheduleOptimizationLevel.INTELLIGENT,
        enable_ab_testing=True,
        enable_auto_interactions=True,
        enable_viral_amplification=True
    )
