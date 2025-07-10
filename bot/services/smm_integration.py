"""
🔗 SMM INTEGRATION - PRODUCTION READY
Integration layer between Professional SMM System and existing bot infrastructure
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from telegram import Bot
from telegram.error import TelegramError

from .smm import (
    ProfessionalSMMSystem,
    SMMConfig,
    create_balanced_config,
    create_viral_focused_config,
    create_conversion_focused_config
)
from .content_intelligence import ContentIntelligenceSystem
from .ai_enhanced import AIEnhancedManager
from .db import async_sessionmaker

logger = logging.getLogger(__name__)


class SMMIntegration:
    """Production-ready SMM интеграция с ботом"""

    def __init__(self, bot: Bot, ai_manager: AIEnhancedManager):
        self.bot = bot
        self.ai_manager = ai_manager

        # Инициализируем SMM систему со сбалансированной конфигурацией
        self.smm_config = create_balanced_config()
        self.smm_system = ProfessionalSMMSystem(self.smm_config, bot=bot)

        # Интеграция с существующими системами
        self.content_intelligence = ContentIntelligenceSystem()

        # Production настройки каналов
        self.channel_configs = {
            'main_channel': {
                'channel_id': '@your_channel',  # Заменить на реальный ID
                'post_frequency': 3,
                'content_strategy': 'balanced',
                'enable_comments': True,
                'enable_ab_testing': True,
                'target_audience': 'legal_professionals'
            }
        }

        self.is_running = False
        self.performance_metrics = {}
        self.active_campaigns = {}

    async def start_smm_system(self):
        """Запуск production SMM системы"""
        try:
            logger.info("🚀 Starting Production SMM Integration")

            self.is_running = True

            # Запускаем все компоненты SMM системы
            if self.smm_system.telegram_publisher:
                await self.smm_system.telegram_publisher.start_publisher()

            if self.smm_system.metrics_collector:
                await self.smm_system.metrics_collector.start_collector()

            if self.smm_system.comment_manager:
                await self.smm_system.comment_manager.start_manager()

            await self.smm_system.ab_testing_engine.start_engine()

            # Настраиваем каналы для комментариев
            for config in self.channel_configs.values():
                if config.get('enable_comments'):
                    await self.smm_system.comment_manager.setup_discussion_group(
                        config['channel_id'],
                        "auto_setup"
                    )

            # Запускаем основную SMM систему
            for config in self.channel_configs.values():
                asyncio.create_task(
                    self.smm_system.start_system(config['channel_id'])
                )

            # Запускаем мониторинг и оптимизацию
            asyncio.create_task(self._integration_monitoring_loop())

            logger.info("✅ Production SMM System fully started")

        except Exception as e:
            logger.error(f"Failed to start SMM system: {e}")
            raise

    async def stop_smm_system(self):
        """Остановка SMM системы"""
        try:
            logger.info("🛑 Stopping Production SMM System")

            self.is_running = False

            # Останавливаем все компоненты
            await self.smm_system.stop_system()

            if self.smm_system.telegram_publisher:
                await self.smm_system.telegram_publisher.stop_publisher()

            if self.smm_system.metrics_collector:
                await self.smm_system.metrics_collector.stop_collector()

            if self.smm_system.comment_manager:
                await self.smm_system.comment_manager.stop_manager()

            await self.smm_system.ab_testing_engine.stop_engine()

            logger.info("✅ SMM System stopped gracefully")

        except Exception as e:
            logger.error(f"Error stopping SMM system: {e}")

    async def create_and_publish_post(
        self,
        content: str,
        channel_id: str,
        enable_ab_testing: bool = True,
        content_variants: List[str] = None
    ) -> Dict[str, Any]:
        """Создание и публикация поста с A/B тестированием"""
        try:
            # Если включено A/B тестирование и есть варианты
            if enable_ab_testing and content_variants and len(content_variants) > 1:
                # Создаем A/B тест
                variants_content = [{"text": variant}
                                    for variant in content_variants]
                test_id = await self.smm_system.ab_testing_engine.create_content_test(
                    test_name=f"Content test {datetime.now().strftime('%Y%m%d_%H%M')}",
                    variants_content=variants_content,
                    duration_days=3
                )

                # Запускаем тест
                await self.smm_system.ab_testing_engine.start_test(test_id)

                # Публикуем первый вариант
                variant = await self.smm_system.ab_testing_engine.get_variant_for_user(
                    test_id, "system_user"
                )

                if variant:
                    content_to_publish = variant.content["text"]
                else:
                    content_to_publish = content

                # Публикуем через production publisher
                publish_request = PublishRequest(
                    post_id=f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    channel_id=channel_id,
                    content=content_to_publish,
                    ab_test_variant=variant.variant_id if variant else None
                )

                result = await self.smm_system.telegram_publisher.publish_now(publish_request)

                if result.success:
                    # Запускаем сбор метрик
                    await self.smm_system.metrics_collector.collect_post_metrics(
                        publish_request.post_id,
                        result.message_id,
                        channel_id
                    )

                    # Записываем A/B тест метрики
                    if variant:
                        await self.smm_system.ab_testing_engine.record_impression(
                            test_id, variant.variant_id
                        )

                return {
                    "success": result.success,
                    "message_id": result.message_id,
                    "ab_test_id": test_id,
                    "variant_id": variant.variant_id if variant else None,
                    "error": result.error_message
                }

            else:
                # Обычная публикация без A/B тестирования
                publish_request = PublishRequest(
                    post_id=f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    channel_id=channel_id,
                    content=content
                )

                result = await self.smm_system.telegram_publisher.publish_now(publish_request)

                if result.success:
                    # Запускаем сбор метрик
                    await self.smm_system.metrics_collector.collect_post_metrics(
                        publish_request.post_id,
                        result.message_id,
                        channel_id
                    )

                return {
                    "success": result.success,
                    "message_id": result.message_id,
                    "error": result.error_message
                }

        except Exception as e:
            logger.error(f"Failed to create and publish post: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_smm_analytics_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Получение детального отчета SMM аналитики"""
        try:
            # Получаем метрики из всех источников
            analytics_summary = self.smm_system.metrics_collector.get_analytics_summary(
                days_back)
            ab_test_summary = await self.smm_system.ab_testing_engine.get_test_summary(days_back)
            system_status = await self.smm_system.get_system_status()

            # Собираем comprehensive отчет
            report = {
                "report_generated_at": datetime.now().isoformat(),
                "period_days": days_back,

                # Основные метрики
                "performance_metrics": analytics_summary,

                # A/B тестирование
                "ab_testing": ab_test_summary,

                # Статус системы
                "system_status": system_status,

                # Каналы
                "channels": self._get_channel_performance(days_back),

                # Рекомендации
                "recommendations": await self._generate_optimization_recommendations()
            }

            return report

        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            return {"error": str(e)}

    def _get_channel_performance(self, days_back: int) -> Dict[str, Any]:
        """Получение производительности каналов"""
        channel_performance = {}

        for channel_name, config in self.channel_configs.items():
            channel_id = config['channel_id']

            # Получаем метрики канала
            channel_metrics = self.smm_system.metrics_collector.get_channel_metrics(
                channel_id)

            if channel_metrics:
                channel_performance[channel_name] = {
                    "channel_id": channel_id,
                    "subscribers": channel_metrics.subscribers_count,
                    "avg_views_per_post": channel_metrics.avg_views_per_post,
                    "avg_engagement_rate": channel_metrics.avg_engagement_rate,
                    "growth_24h": channel_metrics.subscriber_growth_24h,
                    "strategy": config['content_strategy']
                }
            else:
                channel_performance[channel_name] = {
                    "channel_id": channel_id,
                    "status": "metrics_not_available",
                    "strategy": config['content_strategy']
                }

        return channel_performance

    async def _generate_optimization_recommendations(self) -> List[str]:
        """Генерация рекомендаций по оптимизации"""
        recommendations = []

        try:
            # Анализируем A/B тесты
            active_tests = self.smm_system.ab_testing_engine.get_active_tests()
            completed_tests = self.smm_system.ab_testing_engine.get_completed_tests()

            if len(active_tests) == 0:
                recommendations.append(
                    "Рекомендуется запустить A/B тесты для оптимизации контента")

            # Анализируем метрики
            analytics = self.smm_system.metrics_collector.get_analytics_summary(
                7)

            if analytics.get("avg_engagement_rate", 0) < 0.05:
                recommendations.append(
                    "Низкий уровень вовлечения. Рассмотрите изменение стратегии контента")

            if analytics.get("avg_conversion_rate", 0) < 0.03:
                recommendations.append(
                    "Низкая конверсия. Улучшите призывы к действию в постах")

            # Анализируем каналы
            for config in self.channel_configs.values():
                channel_metrics = self.smm_system.metrics_collector.get_channel_metrics(
                    config['channel_id'])
                if channel_metrics and channel_metrics.subscriber_growth_24h < 0:
                    recommendations.append(
                        f"Отток подписчиков в канале {config['channel_id']}. Проанализируйте качество контента")

            if not recommendations:
                recommendations.append(
                    "Система работает оптимально. Продолжайте текущую стратегию")

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Ошибка при генерации рекомендаций"]

    async def _integration_monitoring_loop(self):
        """Цикл мониторинга интеграции"""
        while self.is_running:
            try:
                # Проверяем состояние всех компонентов
                components_status = {
                    "telegram_publisher": self.smm_system.telegram_publisher.is_running if self.smm_system.telegram_publisher else False,
                    "metrics_collector": self.smm_system.metrics_collector.is_running if self.smm_system.metrics_collector else False,
                    "comment_manager": self.smm_system.comment_manager.is_running if self.smm_system.comment_manager else False,
                    "ab_testing_engine": self.smm_system.ab_testing_engine.is_running,
                    "smm_system": self.smm_system.is_running
                }

                # Логируем статус
                failed_components = [
                    name for name, status in components_status.items() if not status]
                if failed_components:
                    logger.warning(
                        f"⚠️ Failed components: {', '.join(failed_components)}")
                else:
                    logger.info("✅ All SMM components running smoothly")

                # Проверяем производительность
                await self._check_performance_issues()

                await asyncio.sleep(1800)  # Проверяем каждые 30 минут

            except Exception as e:
                logger.error(f"Error in integration monitoring: {e}")
                await asyncio.sleep(600)

    async def _check_performance_issues(self):
        """Проверка проблем производительности"""
        try:
            # Проверяем, есть ли проблемы с публикацией
            if self.smm_system.telegram_publisher:
                publish_stats = self.smm_system.telegram_publisher.analytics_tracker.get_publish_stats(
                    1)
                if publish_stats['success_rate'] < 0.9:
                    logger.warning(
                        f"⚠️ Low publish success rate: {publish_stats['success_rate']:.2%}")

            # Проверяем качество метрик
            analytics = self.smm_system.metrics_collector.get_analytics_summary(
                1)
            if analytics.get("data_confidence", 0) < 0.7:
                logger.warning(
                    f"⚠️ Low data confidence: {analytics.get('data_confidence', 0):.2%}")

        except Exception as e:
            logger.error(f"Error checking performance issues: {e}")

    async def handle_new_comment(self, message, post_id: str = None):
        """Обработка нового комментария"""
        try:
            if self.smm_system.comment_manager:
                from .smm.comment_manager import CommentEvent, CommentType

                comment_event = CommentEvent(
                    message_id=message.message_id,
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    text=message.text or "",
                    timestamp=datetime.now(),
                    chat_id=str(message.chat.id),
                    post_id=post_id
                )

                await self.smm_system.comment_manager.process_comment(comment_event)

        except Exception as e:
            logger.error(f"Error handling comment: {e}")

    async def track_post_engagement(self, post_id: str, engagement_type: str, user_id: int = None):
        """Отслеживание взаимодействий с постом"""
        try:
            # Записываем метрики в A/B тесты если применимо
            active_tests = self.smm_system.ab_testing_engine.get_active_tests()

            for test_id, test in active_tests.items():
                if user_id:
                    variant = await self.smm_system.ab_testing_engine.get_variant_for_user(test_id, str(user_id))
                    if variant:
                        if engagement_type == "view":
                            await self.smm_system.ab_testing_engine.record_view(test_id, variant.variant_id)
                        elif engagement_type == "engagement":
                            await self.smm_system.ab_testing_engine.record_engagement(test_id, variant.variant_id)
                        elif engagement_type == "click":
                            await self.smm_system.ab_testing_engine.record_click(test_id, variant.variant_id)
                        elif engagement_type == "conversion":
                            await self.smm_system.ab_testing_engine.record_conversion(test_id, variant.variant_id)

        except Exception as e:
            logger.error(f"Error tracking engagement: {e}")


# Глобальная переменная для хранения экземпляра
_smm_integration_instance = None


async def initialize_smm_integration(bot: Bot, ai_manager: AIEnhancedManager) -> SMMIntegration:
    """Инициализация SMM интеграции"""
    global _smm_integration_instance

    try:
        logger.info("🔧 Initializing SMM Integration")

        _smm_integration_instance = SMMIntegration(bot, ai_manager)

        logger.info("✅ SMM Integration initialized successfully")
        return _smm_integration_instance

    except Exception as e:
        logger.error(f"Failed to initialize SMM integration: {e}")
        raise


async def start_smm_system() -> None:
    """Запуск SMM системы"""
    global _smm_integration_instance

    if _smm_integration_instance:
        await _smm_integration_instance.start_smm_system()
    else:
        raise RuntimeError(
            "SMM Integration not initialized. Call initialize_smm_integration first.")


def get_smm_integration() -> Optional[SMMIntegration]:
    """Получение экземпляра SMM интеграции"""
    return _smm_integration_instance
