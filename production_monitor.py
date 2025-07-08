#!/usr/bin/env python3
"""
🔍 PRODUCTION MONITOR
Мониторинг системы в реальном времени
"""

import asyncio
import logging
import time
from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, Any

# Простая система метрик


class ProductionMetrics:
    def __init__(self):
        self.start_time = datetime.now()
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.errors = deque(maxlen=100)
        self.active_users = set()

    def increment(self, metric: str, value: int = 1):
        """Увеличить счетчик"""
        self.counters[metric] += value

    def record_time(self, metric: str, duration: float):
        """Записать время выполнения"""
        self.timers[metric].append(duration)
        # Оставляем только последние 100 записей
        if len(self.timers[metric]) > 100:
            self.timers[metric] = self.timers[metric][-100:]

    def log_error(self, error: str, user_id: int = None):
        """Логировать ошибку"""
        self.errors.append({
            'timestamp': datetime.now(),
            'error': error,
            'user_id': user_id
        })
        self.increment('errors')

    def add_active_user(self, user_id: int):
        """Добавить активного пользователя"""
        self.active_users.add(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        uptime = datetime.now() - self.start_time

        # Средние времена выполнения
        avg_times = {}
        for metric, times in self.timers.items():
            if times:
                avg_times[metric] = sum(times) / len(times)

        return {
            'uptime_seconds': int(uptime.total_seconds()),
            'counters': dict(self.counters),
            'average_times': avg_times,
            'active_users': len(self.active_users),
            'recent_errors': len([e for e in self.errors if (datetime.now() - e['timestamp']).seconds < 3600])
        }


# Глобальный инстанс метрик
metrics = ProductionMetrics()

# Rate limiting
user_requests = defaultdict(list)
RATE_LIMIT = 10  # запросов в минуту


def is_rate_limited(user_id: int) -> bool:
    """Проверка rate limiting"""
    now = time.time()
    user_reqs = user_requests[user_id]

    # Убираем запросы старше минуты
    user_reqs[:] = [t for t in user_reqs if now - t < 60]

    if len(user_reqs) >= RATE_LIMIT:
        metrics.increment('rate_limited')
        return True

    user_reqs.append(now)
    return False

# Декоратор для мониторинга функций


def monitor_function(metric_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                metrics.increment(f'{metric_name}_success')
                return result
            except Exception as e:
                metrics.log_error(f'{metric_name}: {str(e)}')
                metrics.increment(f'{metric_name}_error')
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_time(metric_name, duration)
        return wrapper
    return decorator

# Простой health check


async def health_check() -> Dict[str, Any]:
    """Простая проверка здоровья"""
    stats = metrics.get_stats()

    # Определяем статус на основе метрик
    status = 'healthy'
    if stats['recent_errors'] > 10:
        status = 'degraded'
    if stats.get('counters', {}).get('errors', 0) > stats.get('counters', {}).get('requests', 1) * 0.1:
        status = 'unhealthy'

    return {
        'status': status,
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    }

# Логирование для production


def setup_production_logging():
    """Настройка логирования для production"""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Отключаем verbose логи библиотек
    logging.getLogger('httpx').setLevel(logging.ERROR)
    logging.getLogger('telegram').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
