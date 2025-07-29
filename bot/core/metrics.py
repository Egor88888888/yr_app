#!/usr/bin/env python3
"""
System metrics and monitoring functionality.
Tracks bot performance and usage statistics.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field

from bot.config.settings import SYSTEM_METRICS

logger = logging.getLogger(__name__)

@dataclass
class BotMetrics:
    """Bot performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    ai_requests: int = 0
    autopost_count: int = 0
    start_time: float = field(default_factory=time.time)
    
    def increment_total_requests(self):
        """Increment total request counter"""
        self.total_requests += 1
    
    def increment_successful_requests(self):
        """Increment successful request counter"""
        self.successful_requests += 1
    
    def increment_failed_requests(self):
        """Increment failed request counter"""
        self.failed_requests += 1
    
    def increment_ai_requests(self):
        """Increment AI request counter"""
        self.ai_requests += 1
    
    def increment_autopost_count(self):
        """Increment autopost counter"""
        self.autopost_count += 1
    
    def get_uptime(self) -> float:
        """Get bot uptime in seconds"""
        return time.time() - self.start_time
    
    def get_success_rate(self) -> float:
        """Get request success rate"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        uptime = self.get_uptime()
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.get_success_rate(), 2),
            "ai_requests": self.ai_requests,
            "autopost_count": self.autopost_count,
            "uptime_seconds": round(uptime, 2),
            "uptime_human": format_uptime(uptime),
            "requests_per_minute": round((self.total_requests / (uptime / 60)) if uptime > 0 else 0, 2),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
        }

def format_uptime(seconds: float) -> str:
    """Format uptime in human readable format"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"

# Global metrics instance
metrics = BotMetrics()

def increment_total_requests():
    """Increment total request counter"""
    metrics.increment_total_requests()
    SYSTEM_METRICS["total_requests"] = metrics.total_requests

def increment_successful_requests():
    """Increment successful request counter"""
    metrics.increment_successful_requests()
    SYSTEM_METRICS["successful_requests"] = metrics.successful_requests

def increment_failed_requests():
    """Increment failed request counter"""
    metrics.increment_failed_requests()
    SYSTEM_METRICS["failed_requests"] = metrics.failed_requests

def increment_ai_requests():
    """Increment AI request counter"""
    metrics.increment_ai_requests()
    SYSTEM_METRICS["ai_requests"] = metrics.ai_requests

def increment_autopost_count():
    """Increment autopost counter"""
    metrics.increment_autopost_count()
    SYSTEM_METRICS["autopost_count"] = metrics.autopost_count

def get_system_stats() -> Dict[str, Any]:
    """Get system statistics"""
    return metrics.get_stats()

def log_request_metrics(user_id: int, request_type: str, success: bool, duration: float = None):
    """Log detailed request metrics"""
    increment_total_requests()
    
    if success:
        increment_successful_requests()
        status = "SUCCESS"
    else:
        increment_failed_requests()
        status = "FAILED"
    
    duration_str = f" ({duration:.2f}s)" if duration else ""
    logger.info(f"Request {status}: user={user_id}, type={request_type}{duration_str}")
    
    if request_type == "ai":
        increment_ai_requests()

class MetricsContext:
    """Context manager for tracking request metrics"""
    
    def __init__(self, user_id: int, request_type: str):
        self.user_id = user_id
        self.request_type = request_type
        self.start_time = None
        self.success = False
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.success = exc_type is None
        log_request_metrics(self.user_id, self.request_type, self.success, duration)