#!/usr/bin/env python3
"""
🏥 HEALTH CHECK SYSTEM
Production-ready мониторинг и диагностика
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from aiohttp import web
from sqlalchemy import text
from bot.services.db import async_sessionmaker
from bot.services.ai_enhanced import AIEnhancedManager
from production_config import monitor, ProductionConfig


class HealthChecker:
    """Система проверки здоровья"""

    def __init__(self):
        self.last_check = None
        self.check_interval = 60  # секунд
        self.component_status = {}

    async def perform_full_health_check(self) -> Dict[str, Any]:
        """Полная проверка здоровья всех компонентов"""
        start_time = time.time()

        health_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "metrics": monitor.get_health_status(),
            "check_duration_ms": 0
        }

        # Проверка базы данных
        db_status = await self._check_database()
        health_data["components"]["database"] = db_status

        # Проверка Enhanced AI
        ai_status = await self._check_ai_system()
        health_data["components"]["ai_system"] = ai_status

        # Проверка файловой системы
        fs_status = await self._check_filesystem()
        health_data["components"]["filesystem"] = fs_status

        # Проверка внешних API
        api_status = await self._check_external_apis()
        health_data["components"]["external_apis"] = api_status

        # Проверка системных ресурсов
        resources_status = await self._check_system_resources()
        health_data["components"]["system_resources"] = resources_status

        # Определение общего статуса
        all_statuses = [comp["status"]
                        for comp in health_data["components"].values()]

        if any(status == "critical" for status in all_statuses):
            health_data["overall_status"] = "critical"
        elif any(status == "warning" for status in all_statuses):
            health_data["overall_status"] = "warning"
        else:
            health_data["overall_status"] = "healthy"

        # Время выполнения проверки
        end_time = time.time()
        health_data["check_duration_ms"] = round(
            (end_time - start_time) * 1000, 2)

        self.last_check = datetime.now()
        return health_data

    async def _check_database(self) -> Dict[str, Any]:
        """Проверка базы данных"""
        try:
            start_time = time.time()

            async with async_sessionmaker() as session:
                # Простой SELECT запрос
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()

                if test_value == 1:
                    # Проверяем время отклика
                    response_time = (time.time() - start_time) * 1000

                    status = "healthy"
                    if response_time > 1000:  # > 1 секунды
                        status = "warning"
                    elif response_time > 5000:  # > 5 секунд
                        status = "critical"

                    return {
                        "status": status,
                        "response_time_ms": round(response_time, 2),
                        "message": "Database connection successful"
                    }
                else:
                    return {
                        "status": "critical",
                        "response_time_ms": 0,
                        "message": "Database query returned unexpected result"
                    }

        except Exception as e:
            return {
                "status": "critical",
                "response_time_ms": 0,
                "message": f"Database connection failed: {str(e)}"
            }

    async def _check_ai_system(self) -> Dict[str, Any]:
        """Проверка AI системы"""
        try:
            if not os.getenv("OPENROUTER_API_KEY"):
                return {
                    "status": "warning",
                    "message": "OpenRouter API key not configured",
                    "components": {
                        "enhanced_ai": "not_configured",
                        "basic_ai": "not_configured"
                    }
                }

            # Проверяем Enhanced AI
            ai_manager = AIEnhancedManager()
            ai_health = await ai_manager.health_check()

            if ai_health.get("status") == "healthy":
                return {
                    "status": "healthy",
                    "message": "Enhanced AI system operational",
                    "components": ai_health.get("components", {})
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Enhanced AI issues: {ai_health.get('status')}",
                    "components": ai_health.get("components", {})
                }

        except Exception as e:
            return {
                "status": "warning",
                "message": f"AI system check failed: {str(e)}",
                "fallback": "Basic AI available"
            }

    async def _check_filesystem(self) -> Dict[str, Any]:
        """Проверка файловой системы"""
        try:
            checks = {
                "webapp_files": False,
                "log_directory": False,
                "write_permissions": False
            }

            # Проверяем webapp файлы
            webapp_path = Path("webapp")
            if webapp_path.exists() and (webapp_path / "index.html").exists():
                checks["webapp_files"] = True

            # Проверяем папку логов (если не production)
            if not ProductionConfig.PRODUCTION_MODE:
                log_dir = Path("logs")
                if log_dir.exists() or log_dir.mkdir(exist_ok=True):
                    checks["log_directory"] = True
            else:
                checks["log_directory"] = True  # В production логи не в файлы

            # Проверяем права на запись
            try:
                test_file = Path("health_check_test.tmp")
                test_file.write_text("test")
                test_file.unlink()
                checks["write_permissions"] = True
            except:
                pass

            all_ok = all(checks.values())

            return {
                "status": "healthy" if all_ok else "warning",
                "message": "Filesystem checks completed",
                "checks": checks
            }

        except Exception as e:
            return {
                "status": "warning",
                "message": f"Filesystem check failed: {str(e)}"
            }

    async def _check_external_apis(self) -> Dict[str, Any]:
        """Проверка внешних API"""
        api_status = {
            "openrouter": "not_configured",
            "google_sheets": "not_configured",
            "cloudpayments": "not_configured"
        }

        # Проверяем наличие API ключей
        if os.getenv("OPENROUTER_API_KEY"):
            api_status["openrouter"] = "configured"

        if os.getenv("GOOGLE_SHEETS_CREDS_JSON"):
            api_status["google_sheets"] = "configured"

        if os.getenv("CLOUDPAYMENTS_PUBLIC_ID"):
            api_status["cloudpayments"] = "configured"

        configured_count = sum(
            1 for status in api_status.values() if status == "configured")

        overall_status = "healthy"
        if configured_count == 0:
            overall_status = "warning"

        return {
            "status": overall_status,
            "message": f"{configured_count}/3 external APIs configured",
            "apis": api_status
        }

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Проверка системных ресурсов"""
        try:
            import psutil

            # CPU использование
            cpu_percent = psutil.cpu_percent(interval=1)

            # Память
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Диск
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # Определяем статус на основе использования ресурсов
            status = "healthy"
            if cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = "warning"
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                status = "critical"

            return {
                "status": status,
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory_percent, 1),
                "disk_percent": round(disk_percent, 1),
                "message": "System resources monitored"
            }

        except ImportError:
            return {
                "status": "warning",
                "message": "psutil not available - resource monitoring disabled"
            }
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Resource check failed: {str(e)}"
            }


# Глобальный health checker
health_checker = HealthChecker()

# ================ WEB ENDPOINTS ================


async def health_endpoint(request: web.Request) -> web.Response:
    """HTTP endpoint для проверки здоровья"""
    try:
        # Быстрая проверка или полная?
        detailed = request.query.get('detailed', 'false').lower() == 'true'

        if detailed:
            health_data = await health_checker.perform_full_health_check()
        else:
            # Быстрая проверка - только основные метрики
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - monitor.metrics["start_time"]).total_seconds(),
                "total_requests": monitor.metrics["total_requests"],
                "last_full_check": health_checker.last_check.isoformat() if health_checker.last_check else None
            }

        # Определяем HTTP статус код
        status_code = 200
        if health_data.get("overall_status") == "warning":
            status_code = 200  # Warning но всё ещё работает
        elif health_data.get("overall_status") == "critical":
            status_code = 503  # Service Unavailable

        return web.json_response(health_data, status=status_code)

    except Exception as e:
        # Если даже health check падает - критическая ошибка
        error_data = {
            "status": "critical",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return web.json_response(error_data, status=503)


async def metrics_endpoint(request: web.Request) -> web.Response:
    """HTTP endpoint для метрик"""
    try:
        metrics_data = monitor.get_health_status()

        # Добавляем дополнительную статистику
        if request.query.get('errors') == 'true':
            hours = int(request.query.get('hours', '1'))
            metrics_data['recent_errors'] = monitor.get_error_summary(hours)

        return web.json_response(metrics_data)

    except Exception as e:
        error_data = {
            "error": f"Metrics collection failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return web.json_response(error_data, status=500)


async def status_endpoint(request: web.Request) -> web.Response:
    """Простой статус endpoint для load balancer"""
    return web.Response(text="OK", status=200)

# ================ STARTUP HEALTH CHECK ================


async def startup_health_check():
    """Проверка здоровья при запуске"""
    print("🏥 Running startup health check...")

    health_data = await health_checker.perform_full_health_check()

    print(f"Overall Status: {health_data['overall_status']}")
    print(f"Components checked: {len(health_data['components'])}")

    for component, status in health_data['components'].items():
        emoji = "✅" if status['status'] == "healthy" else "⚠️" if status['status'] == "warning" else "❌"
        print(f"  {emoji} {component}: {status['status']}")

    if health_data['overall_status'] == 'critical':
        print("❌ CRITICAL ISSUES DETECTED - Review logs before proceeding")
        return False

    print("🎉 System health check passed!")
    return True
