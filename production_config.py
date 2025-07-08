#!/usr/bin/env python3
"""
🚀 PRODUCTION CONFIGURATION
Production-ready настройки для бота
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# ================ PRODUCTION SETTINGS ================


class ProductionConfig:
    """Production настройки"""

    # Основные настройки
    PRODUCTION_MODE = os.getenv("RAILWAY_ENVIRONMENT") == "production"
    DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

    # Rate Limiting
    RATE_LIMIT_REQUESTS = 15  # запросов в минуту
    RATE_LIMIT_WINDOW = 60   # секунд
    RATE_LIMIT_BAN_TIME = 300  # блокировка на 5 минут

    # Безопасность
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILES_PER_REQUEST = 5
    ALLOWED_FILE_TYPES = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']

    # Производительность
    MAX_CONCURRENT_REQUESTS = 50
    DATABASE_POOL_SIZE = 20
    AI_REQUEST_TIMEOUT = 30  # секунд

    # Логирование
    LOG_LEVEL = logging.WARNING if PRODUCTION_MODE else logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Мониторинг
    HEALTH_CHECK_INTERVAL = 60  # секунд
    METRICS_RETENTION_DAYS = 7

    @classmethod
    def setup_logging(cls):
        """Настройка production логирования"""
        handlers = [logging.StreamHandler()]

        if not cls.PRODUCTION_MODE:
            # В dev режиме сохраняем логи в файлы
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            handlers.extend([
                logging.FileHandler(log_dir / "bot.log"),
                logging.FileHandler(log_dir / "error.log", level=logging.ERROR)
            ])

        logging.basicConfig(
            level=cls.LOG_LEVEL,
            format=cls.LOG_FORMAT,
            handlers=handlers
        )

        # Настройка логгеров внешних библиотек
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# ================ MONITORING SYSTEM ================


class SystemMonitor:
    """Система мониторинга"""

    def __init__(self):
        self.metrics = {
            "start_time": datetime.now(),
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "ai_requests": 0,
            "rate_limited_requests": 0,
            "active_users": set(),
            "peak_concurrent_users": 0,
            "last_health_check": None,
            "components_status": {}
        }

        self.error_log = []
        self.performance_log = []

    def log_request(self, user_id: int, request_type: str, success: bool, error: str = None, duration: float = None):
        """Логирование запроса"""
        self.metrics["total_requests"] += 1

        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
            if error:
                self.error_log.append({
                    "timestamp": datetime.now(),
                    "user_id": user_id,
                    "type": request_type,
                    "error": error
                })

        if request_type == "ai":
            self.metrics["ai_requests"] += 1

        # Трекинг активных пользователей
        self.metrics["active_users"].add(user_id)
        if len(self.metrics["active_users"]) > self.metrics["peak_concurrent_users"]:
            self.metrics["peak_concurrent_users"] = len(
                self.metrics["active_users"])

        # Логирование производительности
        if duration:
            self.performance_log.append({
                "timestamp": datetime.now(),
                "type": request_type,
                "duration": duration
            })

    def log_rate_limit(self, user_id: int):
        """Логирование rate limiting"""
        self.metrics["rate_limited_requests"] += 1
        logging.warning(f"Rate limit exceeded for user {user_id}")

    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья системы"""
        uptime = datetime.now() - self.metrics["start_time"]
        success_rate = 0

        if self.metrics["total_requests"] > 0:
            success_rate = self.metrics["successful_requests"] / \
                self.metrics["total_requests"]

        # Очищаем старые активные пользователи (старше 1 часа)
        # В реальной реализации нужна более сложная логика

        return {
            "status": "healthy" if success_rate > 0.95 else "degraded",
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime),
            "total_requests": self.metrics["total_requests"],
            "success_rate": round(success_rate * 100, 2),
            "active_users": len(self.metrics["active_users"]),
            "peak_concurrent_users": self.metrics["peak_concurrent_users"],
            "ai_requests": self.metrics["ai_requests"],
            "rate_limited": self.metrics["rate_limited_requests"],
            "components": self.metrics["components_status"],
            "last_check": self.metrics["last_health_check"]
        }

    def update_component_status(self, component: str, status: str, details: str = None):
        """Обновление статуса компонента"""
        self.metrics["components_status"][component] = {
            "status": status,
            "details": details,
            "last_update": datetime.now()
        }

    def get_error_summary(self, last_hours: int = 1) -> Dict[str, Any]:
        """Получение сводки ошибок"""
        cutoff = datetime.now() - timedelta(hours=last_hours)
        recent_errors = [
            err for err in self.error_log if err["timestamp"] >= cutoff]

        # Группировка ошибок по типам
        error_types = {}
        for error in recent_errors:
            error_type = error["error"][:50] + \
                "..." if len(error["error"]) > 50 else error["error"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(recent_errors),
            "error_types": error_types,
            "period_hours": last_hours
        }

# ================ SECURITY HELPERS ================


class SecurityManager:
    """Менеджер безопасности"""

    def __init__(self):
        self.blocked_users = set()
        self.suspicious_activity = {}

    def sanitize_input(self, text: str) -> str:
        """Санитизация пользовательского ввода"""
        if not text:
            return ""

        # Убираем HTML теги
        sanitized = text.replace('<', '&lt;').replace('>', '&gt;')

        # Убираем потенциально опасные символы
        dangerous_chars = ['<script', 'javascript:', 'data:', 'vbscript:']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char.lower(), '')
            sanitized = sanitized.replace(char.upper(), '')

        # Ограничиваем длину
        if len(sanitized) > 4000:
            sanitized = sanitized[:4000] + "..."

        return sanitized.strip()

    def validate_file_upload(self, file_data: dict) -> bool:
        """Валидация загружаемого файла"""
        try:
            # Проверяем размер
            if file_data.get("size", 0) > ProductionConfig.MAX_FILE_SIZE:
                return False

            # Проверяем тип файла
            file_extension = file_data.get("name", "").split(".")[-1].lower()
            if file_extension not in ProductionConfig.ALLOWED_FILE_TYPES:
                return False

            # Проверяем содержимое (base64)
            if not file_data.get("data", "").startswith("data:"):
                return False

            return True

        except Exception:
            return False

    def check_suspicious_activity(self, user_id: int, activity_type: str) -> bool:
        """Проверка подозрительной активности"""
        if user_id not in self.suspicious_activity:
            self.suspicious_activity[user_id] = {}

        user_activity = self.suspicious_activity[user_id]

        # Подсчет активности по типам
        if activity_type not in user_activity:
            user_activity[activity_type] = []

        now = datetime.now()
        user_activity[activity_type].append(now)

        # Очищаем старые записи (старше 1 часа)
        cutoff = now - timedelta(hours=1)
        user_activity[activity_type] = [
            timestamp for timestamp in user_activity[activity_type]
            if timestamp >= cutoff
        ]

        # Проверяем лимиты
        limits = {
            "form_submit": 5,    # максимум 5 заявок в час
            "ai_request": 20,    # максимум 20 AI запросов в час
            "file_upload": 10    # максимум 10 загрузок файлов в час
        }

        if len(user_activity[activity_type]) > limits.get(activity_type, 100):
            self.blocked_users.add(user_id)
            logging.warning(
                f"User {user_id} blocked for suspicious activity: {activity_type}")
            return True

        return False


# Глобальные инстансы
monitor = SystemMonitor()
security = SecurityManager()

# Настройка логирования при импорте
ProductionConfig.setup_logging()
