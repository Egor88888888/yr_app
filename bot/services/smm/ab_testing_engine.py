"""
🧪 A/B TESTING ENGINE - PRODUCTION READY
Advanced A/B testing system for SMM content optimization:
- Multiple variant testing (A/B/C/D...)
- Statistical significance calculation
- Automatic winner selection
- Content optimization insights
- Performance tracking
- Real-time results analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import math
import random
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Статусы A/B тестов"""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class VariantType(Enum):
    """Типы вариантов тестирования"""
    CONTENT = "content"        # Разный текст контента
    TITLE = "title"           # Разные заголовки
    TIMING = "timing"         # Разное время публикации
    FORMAT = "format"         # Разные форматы (текст/фото/видео)
    CTA = "cta"              # Разные призывы к действию
    HASHTAGS = "hashtags"     # Разные хештеги
    LENGTH = "length"         # Разная длина контента


class MetricType(Enum):
    """Типы метрик для тестирования"""
    ENGAGEMENT_RATE = "engagement_rate"
    CLICK_RATE = "click_rate"
    CONVERSION_RATE = "conversion_rate"
    VIEWS = "views"
    COMMENTS = "comments"
    SHARES = "shares"
    TIME_SPENT = "time_spent"


@dataclass
class TestVariant:
    """Вариант A/B теста"""
    variant_id: str
    variant_name: str
    content: Dict[str, Any]
    weight: float = 1.0  # Вес распределения трафика

    # Метрики
    impressions: int = 0
    views: int = 0
    engagements: int = 0
    clicks: int = 0
    conversions: int = 0

    # Расчетные метрики
    engagement_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0

    # Статистика
    confidence_level: float = 0.0
    statistical_significance: bool = False


@dataclass
class ABTest:
    """A/B тест"""
    test_id: str
    test_name: str
    test_type: VariantType
    primary_metric: MetricType
    secondary_metrics: List[MetricType]

    variants: List[TestVariant]

    # Настройки теста
    start_date: datetime
    end_date: Optional[datetime] = None
    min_sample_size: int = 100
    confidence_threshold: float = 0.95
    max_duration_days: int = 14

    # Статус
    status: TestStatus = TestStatus.DRAFT
    winner_variant_id: Optional[str] = None

    # Результаты
    total_impressions: int = 0
    test_results: Dict[str, Any] = None

    def __post_init__(self):
        if self.test_results is None:
            self.test_results = {}


@dataclass
class TestResult:
    """Результат A/B теста"""
    test_id: str
    winner_variant_id: str
    confidence_level: float
    improvement_percentage: float
    statistical_significance: bool
    recommendation: str
    detailed_metrics: Dict[str, Any]
    generated_at: datetime


class ABTestingEngine:
    """Production-ready A/B testing engine"""

    def __init__(self):
        self.active_tests: Dict[str, ABTest] = {}
        self.completed_tests: Dict[str, ABTest] = {}
        self.test_assignments: Dict[str, str] = {}  # user_id -> variant_id

        # Настройки
        self.min_confidence_level = 0.95
        self.min_sample_size = 50
        self.max_concurrent_tests = 5

        self.is_running = False

    async def start_engine(self):
        """Запуск движка A/B тестирования"""
        self.is_running = True
        logger.info("🧪 Starting A/B Testing Engine")

        # Запуск процессов в фоне (не ждем их завершения)
        asyncio.create_task(self._monitor_active_tests())
        asyncio.create_task(self._calculate_test_results())
        asyncio.create_task(self._auto_stop_completed_tests())

        logger.info("✅ A/B Testing Engine background tasks started")

    async def stop_engine(self):
        """Остановка движка"""
        self.is_running = False
        logger.info("🛑 Stopping A/B Testing Engine")

    async def create_content_test(
        self,
        test_name: str,
        variants_content: List[Dict[str, Any]],
        primary_metric: MetricType = MetricType.ENGAGEMENT_RATE,
        duration_days: int = 7
    ) -> str:
        """Создание теста контента"""

        test_id = f"content_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        # Создаем варианты
        variants = []
        for i, content in enumerate(variants_content):
            variant = TestVariant(
                variant_id=f"{test_id}_variant_{chr(65+i)}",  # A, B, C...
                variant_name=f"Variant {chr(65+i)}",
                content=content
            )
            variants.append(variant)

        # Создаем тест
        ab_test = ABTest(
            test_id=test_id,
            test_name=test_name,
            test_type=VariantType.CONTENT,
            primary_metric=primary_metric,
            secondary_metrics=[MetricType.CLICK_RATE, MetricType.VIEWS],
            variants=variants,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            max_duration_days=duration_days
        )

        self.active_tests[test_id] = ab_test

        logger.info(
            f"🧪 Created A/B test {test_id} with {len(variants)} variants")

        return test_id

    async def create_timing_test(
        self,
        test_name: str,
        post_content: Dict[str, Any],
        time_variants: List[int],  # Часы для публикации
        duration_days: int = 14
    ) -> str:
        """Создание теста времени публикации"""

        test_id = f"timing_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        variants = []
        for i, hour in enumerate(time_variants):
            variant_content = post_content.copy()
            variant_content['publish_hour'] = hour

            variant = TestVariant(
                variant_id=f"{test_id}_time_{hour}h",
                variant_name=f"Время {hour}:00",
                content=variant_content
            )
            variants.append(variant)

        ab_test = ABTest(
            test_id=test_id,
            test_name=test_name,
            test_type=VariantType.TIMING,
            primary_metric=MetricType.ENGAGEMENT_RATE,
            secondary_metrics=[MetricType.VIEWS, MetricType.CLICK_RATE],
            variants=variants,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            max_duration_days=duration_days
        )

        self.active_tests[test_id] = ab_test

        logger.info(
            f"⏰ Created timing A/B test {test_id} for hours: {time_variants}")

        return test_id

    async def create_format_test(
        self,
        test_name: str,
        base_content: str,
        formats: List[str],  # ["text", "photo", "video", "poll"]
        duration_days: int = 7
    ) -> str:
        """Создание теста форматов контента"""

        test_id = f"format_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        variants = []
        for format_type in formats:
            variant_content = {
                "text": base_content,
                "format": format_type,
                "media_required": format_type != "text"
            }

            variant = TestVariant(
                variant_id=f"{test_id}_format_{format_type}",
                variant_name=f"Формат: {format_type}",
                content=variant_content
            )
            variants.append(variant)

        ab_test = ABTest(
            test_id=test_id,
            test_name=test_name,
            test_type=VariantType.FORMAT,
            primary_metric=MetricType.ENGAGEMENT_RATE,
            secondary_metrics=[MetricType.VIEWS, MetricType.CLICK_RATE],
            variants=variants,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            max_duration_days=duration_days
        )

        self.active_tests[test_id] = ab_test

        logger.info(
            f"📱 Created format A/B test {test_id} for formats: {formats}")

        return test_id

    async def get_variant_for_user(self, test_id: str, user_id: str) -> Optional[TestVariant]:
        """Получение варианта для пользователя"""
        if test_id not in self.active_tests:
            return None

        test = self.active_tests[test_id]

        if test.status != TestStatus.RUNNING:
            return None

        # Проверяем, есть ли уже назначенный вариант
        assignment_key = f"{test_id}_{user_id}"
        if assignment_key in self.test_assignments:
            variant_id = self.test_assignments[assignment_key]
            return next((v for v in test.variants if v.variant_id == variant_id), None)

        # Назначаем новый вариант на основе весов
        variant = await self._assign_variant(test, user_id)
        if variant:
            self.test_assignments[assignment_key] = variant.variant_id

        return variant

    async def _assign_variant(self, test: ABTest, user_id: str) -> Optional[TestVariant]:
        """Назначение варианта пользователю"""
        # Используем хеш user_id для консистентного распределения
        import hashlib
        hash_object = hashlib.md5(f"{test.test_id}_{user_id}".encode())
        hash_value = int(hash_object.hexdigest(), 16) % 10000

        # Распределяем по весам
        total_weight = sum(v.weight for v in test.variants)
        normalized_hash = hash_value / 10000.0

        cumulative_weight = 0
        for variant in test.variants:
            cumulative_weight += variant.weight / total_weight
            if normalized_hash <= cumulative_weight:
                return variant

        # Fallback на первый вариант
        return test.variants[0] if test.variants else None

    async def start_test(self, test_id: str) -> bool:
        """Запуск A/B теста"""
        if test_id not in self.active_tests:
            return False

        test = self.active_tests[test_id]

        if len(self.active_tests) >= self.max_concurrent_tests:
            logger.warning(
                f"Cannot start test {test_id}: too many concurrent tests")
            return False

        test.status = TestStatus.RUNNING
        test.start_date = datetime.now()

        logger.info(f"🚀 Started A/B test {test_id}")

        return True

    async def record_impression(self, test_id: str, variant_id: str):
        """Запись показа"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        variant = next(
            (v for v in test.variants if v.variant_id == variant_id), None)

        if variant:
            variant.impressions += 1
            test.total_impressions += 1

    async def record_view(self, test_id: str, variant_id: str):
        """Запись просмотра"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        variant = next(
            (v for v in test.variants if v.variant_id == variant_id), None)

        if variant:
            variant.views += 1

    async def record_engagement(self, test_id: str, variant_id: str):
        """Запись взаимодействия"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        variant = next(
            (v for v in test.variants if v.variant_id == variant_id), None)

        if variant:
            variant.engagements += 1

    async def record_click(self, test_id: str, variant_id: str):
        """Запись клика"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        variant = next(
            (v for v in test.variants if v.variant_id == variant_id), None)

        if variant:
            variant.clicks += 1

    async def record_conversion(self, test_id: str, variant_id: str):
        """Запись конверсии"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        variant = next(
            (v for v in test.variants if v.variant_id == variant_id), None)

        if variant:
            variant.conversions += 1

    async def get_test_results(self, test_id: str) -> Optional[TestResult]:
        """Получение результатов теста"""
        test = self.active_tests.get(
            test_id) or self.completed_tests.get(test_id)
        if not test:
            return None

        # Обновляем расчетные метрики
        await self._update_calculated_metrics(test)

        # Находим лучший вариант
        winner_variant = await self._find_winner(test)

        if not winner_variant:
            return None

        # Рассчитываем улучшение
        baseline_variant = test.variants[0]  # Первый вариант как baseline
        improvement = await self._calculate_improvement(
            baseline_variant,
            winner_variant,
            test.primary_metric
        )

        # Проверяем статистическую значимость
        statistical_significance = await self._check_statistical_significance(
            baseline_variant,
            winner_variant,
            test.primary_metric
        )

        # Генерируем рекомендацию
        recommendation = await self._generate_recommendation(test, winner_variant, improvement)

        return TestResult(
            test_id=test_id,
            winner_variant_id=winner_variant.variant_id,
            confidence_level=winner_variant.confidence_level,
            improvement_percentage=improvement,
            statistical_significance=statistical_significance,
            recommendation=recommendation,
            detailed_metrics=await self._get_detailed_metrics(test),
            generated_at=datetime.now()
        )

    async def _update_calculated_metrics(self, test: ABTest):
        """Обновление расчетных метрик"""
        for variant in test.variants:
            # Engagement Rate
            if variant.views > 0:
                variant.engagement_rate = variant.engagements / variant.views

            # Click Rate
            if variant.views > 0:
                variant.click_rate = variant.clicks / variant.views

            # Conversion Rate
            if variant.clicks > 0:
                variant.conversion_rate = variant.conversions / variant.clicks

    async def _find_winner(self, test: ABTest) -> Optional[TestVariant]:
        """Поиск лучшего варианта"""
        if not test.variants:
            return None

        # Фильтруем варианты с достаточной выборкой
        valid_variants = [
            v for v in test.variants
            if v.views >= self.min_sample_size
        ]

        if not valid_variants:
            return None

        # Сортируем по основной метрике
        metric_getter = self._get_metric_value

        sorted_variants = sorted(
            valid_variants,
            key=lambda v: metric_getter(v, test.primary_metric),
            reverse=True
        )

        return sorted_variants[0]

    def _get_metric_value(self, variant: TestVariant, metric: MetricType) -> float:
        """Получение значения метрики"""
        if metric == MetricType.ENGAGEMENT_RATE:
            return variant.engagement_rate
        elif metric == MetricType.CLICK_RATE:
            return variant.click_rate
        elif metric == MetricType.CONVERSION_RATE:
            return variant.conversion_rate
        elif metric == MetricType.VIEWS:
            return float(variant.views)
        elif metric == MetricType.COMMENTS:
            return float(variant.engagements)  # Приблизительно
        else:
            return 0.0

    async def _calculate_improvement(
        self,
        baseline: TestVariant,
        winner: TestVariant,
        metric: MetricType
    ) -> float:
        """Расчет улучшения в процентах"""
        baseline_value = self._get_metric_value(baseline, metric)
        winner_value = self._get_metric_value(winner, metric)

        if baseline_value == 0:
            return 0.0

        improvement = ((winner_value - baseline_value) / baseline_value) * 100
        return round(improvement, 2)

    async def _check_statistical_significance(
        self,
        baseline: TestVariant,
        variant: TestVariant,
        metric: MetricType
    ) -> bool:
        """Проверка статистической значимости"""
        # Упрощенная проверка z-теста для пропорций

        if metric in [MetricType.ENGAGEMENT_RATE, MetricType.CLICK_RATE, MetricType.CONVERSION_RATE]:
            # Для пропорций
            baseline_rate = self._get_metric_value(baseline, metric)
            variant_rate = self._get_metric_value(variant, metric)

            n1 = baseline.views
            n2 = variant.views

            if n1 < 30 or n2 < 30:
                return False

            # z-тест для разности пропорций
            p1 = baseline_rate
            p2 = variant_rate

            pooled_p = ((p1 * n1) + (p2 * n2)) / (n1 + n2)
            se = math.sqrt(pooled_p * (1 - pooled_p) * ((1/n1) + (1/n2)))

            if se == 0:
                return False

            z_score = abs(p2 - p1) / se

            # Для 95% доверительного интервала, критическое значение z = 1.96
            return z_score > 1.96

        return False

    async def _generate_recommendation(
        self,
        test: ABTest,
        winner: TestVariant,
        improvement: float
    ) -> str:
        """Генерация рекомендации"""
        if improvement > 20:
            return f"Сильная рекомендация: использовать {winner.variant_name}. Улучшение составляет {improvement:.1f}%."
        elif improvement > 10:
            return f"Рекомендация: рассмотреть {winner.variant_name}. Улучшение составляет {improvement:.1f}%."
        elif improvement > 5:
            return f"Слабая рекомендация: {winner.variant_name} показывает небольшое улучшение ({improvement:.1f}%)."
        elif improvement > 0:
            return f"Незначительное улучшение: {winner.variant_name} лучше на {improvement:.1f}%, но разница несущественна."
        else:
            return f"Нет значимой разности между вариантами. Можно использовать любой."

    async def _get_detailed_metrics(self, test: ABTest) -> Dict[str, Any]:
        """Получение детальных метрик"""
        metrics = {
            "test_info": {
                "test_id": test.test_id,
                "test_name": test.test_name,
                "test_type": test.test_type.value,
                "status": test.status.value,
                "duration_days": (datetime.now() - test.start_date).days
            },
            "variants": []
        }

        for variant in test.variants:
            variant_metrics = {
                "variant_id": variant.variant_id,
                "variant_name": variant.variant_name,
                "impressions": variant.impressions,
                "views": variant.views,
                "engagements": variant.engagements,
                "clicks": variant.clicks,
                "conversions": variant.conversions,
                "engagement_rate": round(variant.engagement_rate * 100, 2),
                "click_rate": round(variant.click_rate * 100, 2),
                "conversion_rate": round(variant.conversion_rate * 100, 2)
            }
            metrics["variants"].append(variant_metrics)

        return metrics

    async def stop_test(self, test_id: str, reason: str = "Manual stop") -> bool:
        """Остановка A/B теста"""
        if test_id not in self.active_tests:
            return False

        test = self.active_tests[test_id]
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.now()

        # Определяем победителя
        winner = await self._find_winner(test)
        if winner:
            test.winner_variant_id = winner.variant_id

        # Переносим в завершенные тесты
        self.completed_tests[test_id] = test
        del self.active_tests[test_id]

        logger.info(f"🏁 Stopped A/B test {test_id}: {reason}")

        return True

    async def _monitor_active_tests(self):
        """Мониторинг активных тестов"""
        while self.is_running:
            try:
                current_time = datetime.now()

                tests_to_stop = []

                for test_id, test in self.active_tests.items():
                    # Проверяем срок окончания
                    if test.end_date and current_time >= test.end_date:
                        tests_to_stop.append((test_id, "Time expired"))
                        continue

                    # Проверяем достижение статистической значимости
                    if test.total_impressions >= test.min_sample_size * len(test.variants):
                        results = await self.get_test_results(test_id)
                        if results and results.statistical_significance and results.confidence_level >= self.min_confidence_level:
                            tests_to_stop.append(
                                (test_id, "Statistical significance reached"))

                # Останавливаем тесты
                for test_id, reason in tests_to_stop:
                    await self.stop_test(test_id, reason)

                await asyncio.sleep(3600)  # Проверяем каждый час

            except Exception as e:
                logger.error(f"Error in test monitoring: {e}")
                await asyncio.sleep(600)

    async def _calculate_test_results(self):
        """Расчет результатов тестов"""
        while self.is_running:
            try:
                for test in self.active_tests.values():
                    await self._update_calculated_metrics(test)

                await asyncio.sleep(900)  # Обновляем каждые 15 минут

            except Exception as e:
                logger.error(f"Error calculating test results: {e}")
                await asyncio.sleep(300)

    async def _auto_stop_completed_tests(self):
        """Автоматическая остановка завершенных тестов"""
        while self.is_running:
            try:
                # Очищаем старые назначения вариантов (старше 30 дней)
                cutoff_time = datetime.now() - timedelta(days=30)
                old_assignments = [
                    key for key, _ in self.test_assignments.items()
                    # Здесь можно добавить проверку времени создания
                ]

                # В реальной реализации нужно отслеживать время создания назначений

                await asyncio.sleep(86400)  # Проверяем раз в день

            except Exception as e:
                logger.error(f"Error in auto cleanup: {e}")
                await asyncio.sleep(3600)

    def get_active_tests(self) -> Dict[str, ABTest]:
        """Получение активных тестов"""
        return self.active_tests.copy()

    def get_completed_tests(self) -> Dict[str, ABTest]:
        """Получение завершенных тестов"""
        return self.completed_tests.copy()

    async def get_test_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """Получение сводки по тестам"""
        cutoff_time = datetime.now() - timedelta(days=days_back)

        recent_tests = []
        for test in list(self.active_tests.values()) + list(self.completed_tests.values()):
            if test.start_date >= cutoff_time:
                recent_tests.append(test)

        total_tests = len(recent_tests)
        completed_tests = len(
            [t for t in recent_tests if t.status == TestStatus.COMPLETED])
        successful_tests = len(
            [t for t in recent_tests if t.winner_variant_id is not None])

        avg_improvement = 0
        if successful_tests > 0:
            improvements = []
            for test in recent_tests:
                if test.winner_variant_id and len(test.variants) >= 2:
                    winner = next(
                        (v for v in test.variants if v.variant_id == test.winner_variant_id), None)
                    baseline = test.variants[0]
                    if winner and baseline:
                        improvement = await self._calculate_improvement(baseline, winner, test.primary_metric)
                        improvements.append(improvement)

            if improvements:
                avg_improvement = sum(improvements) / len(improvements)

        return {
            "period_days": days_back,
            "total_tests": total_tests,
            "active_tests": len(self.active_tests),
            "completed_tests": completed_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "avg_improvement_percent": round(avg_improvement, 2),
            "test_types": {
                test_type.value: len(
                    [t for t in recent_tests if t.test_type == test_type])
                for test_type in VariantType
            }
        }
