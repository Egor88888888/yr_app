# 📡 API REFERENCE - Документация API

## 📋 Полная документация API системы

---

## 🎯 ОБЗОР API

### Доступные API:

- **🤖 Bot API** - Telegram Bot API интеграция
- **🌐 Web API** - REST API для веб-интерфейса
- **🔍 Monitoring API** - API системы мониторинга
- **💳 Payment API** - API платежной системы
- **🧠 AI API** - API искусственного интеллекта
- **📊 Analytics API** - API аналитики и отчетов

### Базовые принципы:

- **RESTful** архитектура
- **JSON** формат данных
- **HTTP/HTTPS** протокол
- **JWT** авторизация (где применимо)
- **Rate limiting** защита от злоупотреблений

---

## 🤖 TELEGRAM BOT API

### 1. Основные команды

#### Bot Commands

```python
# Пользовательские команды
/start          # Запуск бота
/help           # Справка по использованию

# Админские команды
/admin          # Админ панель
/quick_fix      # Быстрые исправления и мониторинг
/production_test # Продакшн тестирование
/add_admin      # Добавление админа
/list_admins    # Список админов
```

#### Callback Query Patterns

```python
# Quick fixes callbacks
"fix_channel"           # Исправление канала
"fix_comments"          # Исправление комментариев
"test_markdown"         # Тест markdown
"production_admin"      # Продакшн админ панель
"system_dashboard"      # Системная dashboard

# Monitoring callbacks
"monitoring_start"      # Запуск мониторинга
"monitoring_stop"       # Остановка мониторинга
"monitoring_dashboard"  # Dashboard мониторинга
"monitoring_alerts"     # Алерты мониторинга

# Testing callbacks
"test_quick"           # Быстрое тестирование
"test_full"            # Полное тестирование
"test_monitoring"      # Тест мониторинга
"test_performance"     # Тест производительности
```

### 2. Bot Handler Architecture

#### Handler Registration

```python
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Основные хэндлеры
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("admin", cmd_admin))
application.add_handler(CallbackQueryHandler(universal_callback_handler))

# SMM админ хэндлеры
from bot.handlers.smm_admin import register_smm_admin_handlers
register_smm_admin_handlers(application)

# Quick fixes хэндлеры
from bot.handlers.quick_fixes import register_quick_fixes_handlers
register_quick_fixes_handlers(application)

# Production testing хэндлеры
from bot.handlers.production_testing import register_production_testing_handlers
register_production_testing_handlers(application)
```

#### Message Processing Flow

```python
async def universal_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик callback запросов"""
    query = update.callback_query
    data = query.data

    # Роутинг по типу callback
    if data.startswith("cat_"):
        await handle_category_selection(update, context)
    elif data.startswith("service_"):
        await handle_service_selection(update, context)
    elif data == "create_application":
        await handle_create_application(update, context)
    # ... другие обработчики
```

---

## 🌐 WEB API

### 1. Base Configuration

#### Base URL

```
Production: https://your-app.railway.app
Development: http://localhost:8000
```

#### Headers

```http
Content-Type: application/json
Authorization: Bearer <jwt_token>  # Для защищенных endpoint'ов
```

### 2. Health Check API

#### GET /health

Проверка состояния системы

**Request:**

```http
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 86400,
  "version": "1.0.0",
  "environment": "production"
}
```

#### GET /health/detailed

Детальная проверка состояния

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 45,
      "last_check": "2024-01-15T10:29:30Z"
    },
    "telegram_api": {
      "status": "healthy",
      "response_time_ms": 123,
      "last_check": "2024-01-15T10:29:30Z"
    },
    "external_apis": {
      "status": "degraded",
      "details": "OpenAI API slow response"
    }
  }
}
```

### 3. Application Management API

#### POST /api/applications

Создание новой заявки

**Request:**

```json
{
  "user_id": 123456789,
  "category_id": 1,
  "service_type": "consultation",
  "description": "Консультация по семейному праву",
  "client_name": "Иван Иванов",
  "client_phone": "+7 900 123-45-67",
  "client_email": "ivan@example.com",
  "files": [
    {
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size": 1024000
    }
  ]
}
```

**Response:**

```json
{
  "application_id": "app_67890",
  "status": "created",
  "estimated_cost": 3000,
  "estimated_completion": "2024-01-20T00:00:00Z",
  "payment_required": true,
  "payment_url": "https://pay.cloudpayments.ru/...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/applications/{application_id}

Получение информации о заявке

**Response:**

```json
{
  "application_id": "app_67890",
  "status": "in_progress",
  "category": "Семейное право",
  "service_type": "consultation",
  "description": "Консультация по семейному праву",
  "client": {
    "name": "Иван Иванов",
    "phone": "+7 900 123-45-67",
    "email": "ivan@example.com"
  },
  "cost": 3000,
  "payment_status": "paid",
  "assigned_admin": "admin_123",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "history": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "action": "created",
      "details": "Заявка создана"
    },
    {
      "timestamp": "2024-01-15T10:45:00Z",
      "action": "payment_received",
      "details": "Получена оплата 3000 ₽"
    },
    {
      "timestamp": "2024-01-15T11:00:00Z",
      "action": "assigned",
      "details": "Назначен ответственный admin_123"
    }
  ]
}
```

#### PUT /api/applications/{application_id}/status

Обновление статуса заявки

**Request:**

```json
{
  "status": "completed",
  "comment": "Консультация проведена, документы подготовлены",
  "admin_id": "admin_123"
}
```

**Response:**

```json
{
  "success": true,
  "status": "completed",
  "updated_at": "2024-01-15T15:30:00Z"
}
```

---

## 🔍 MONITORING API

### 1. Production Monitoring System

#### Class: ProductionMonitoringSystem

```python
class ProductionMonitoringSystem:
    """Production-ready система мониторинга"""

    def __init__(self, bot: Bot, admin_chat_id: str):
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.health_checks: Dict[str, Callable] = {}
        self.system_health: Dict[str, SystemHealth] = {}

    async def start_monitoring(self):
        """Запуск автоматического мониторинга"""

    async def stop_monitoring(self):
        """Остановка мониторинга"""

    async def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Получение dashboard мониторинга"""
```

#### GET /api/monitoring/dashboard

Получение dashboard мониторинга

**Response:**

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "monitoring_active": true,
  "uptime_seconds": 86400,
  "total_systems": 7,
  "total_checks": 1440,
  "total_alerts": 15,
  "active_alerts_count": 2,
  "system_status_counts": {
    "healthy": 5,
    "warning": 1,
    "degraded": 1,
    "down": 0
  },
  "system_health": {
    "autopost_system": {
      "status": "healthy",
      "last_check": "10:29:30",
      "response_time": 45.2
    },
    "comments_system": {
      "status": "healthy",
      "last_check": "10:29:30",
      "response_time": null
    },
    "telegram_api": {
      "status": "warning",
      "last_check": "10:29:30",
      "response_time": 850.1
    }
  },
  "recent_alerts": [
    {
      "level": "warning",
      "system": "telegram_api",
      "message": "High response time detected: 850ms",
      "timestamp": "10:25:15"
    }
  ]
}
```

#### POST /api/monitoring/alerts

Создание алерта

**Request:**

```json
{
  "level": "warning",
  "system": "custom_system",
  "message": "Custom alert message",
  "metadata": {
    "additional_info": "value"
  }
}
```

### 2. Health Checks API

#### Health Check Functions

```python
# Registered health checks
health_checks = {
    "autopost_system": _check_autopost_health,
    "comments_system": _check_comments_health,
    "smm_integration": _check_smm_health,
    "telegram_api": _check_telegram_health,
    "database": _check_database_health,
    "memory_usage": _check_memory_health,
    "response_time": _check_response_time
}
```

#### GET /api/health/checks

Выполнение всех health checks

**Response:**

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "healthy",
  "checks": {
    "autopost_system": {
      "status": "healthy",
      "response_time_ms": 45.2,
      "details": {
        "channel_accessible": true,
        "last_post_time": "2024-01-15T08:00:00Z"
      }
    },
    "telegram_api": {
      "status": "warning",
      "response_time_ms": 850.1,
      "details": {
        "bot_username": "your_bot",
        "api_accessible": true,
        "slow_response": true
      }
    },
    "database": {
      "status": "healthy",
      "response_time_ms": 23.8,
      "details": {
        "connection_pool_size": 10,
        "active_connections": 3
      }
    }
  }
}
```

---

## 💳 PAYMENT API

### 1. CloudPayments Integration

#### POST /api/payments/create

Создание платежа

**Request:**

```json
{
  "application_id": "app_67890",
  "amount": 3000,
  "currency": "RUB",
  "description": "Консультация по семейному праву",
  "client_email": "ivan@example.com",
  "success_url": "https://your-app.com/payment/success",
  "fail_url": "https://your-app.com/payment/fail"
}
```

**Response:**

```json
{
  "payment_id": "pay_123456",
  "payment_url": "https://pay.cloudpayments.ru/...",
  "amount": 3000,
  "currency": "RUB",
  "status": "pending",
  "expires_at": "2024-01-16T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST /webhook/payment

Webhook уведомлений о платежах

**Request (CloudPayments):**

```json
{
  "TransactionId": 12345,
  "Amount": 3000.0,
  "Currency": "RUB",
  "PaymentAmount": 3000.0,
  "PaymentCurrency": "RUB",
  "InvoiceId": "app_67890",
  "AccountId": "ivan@example.com",
  "Email": "ivan@example.com",
  "DateTime": "2024-01-15T10:45:00Z",
  "IpAddress": "192.168.1.1",
  "Status": "Completed",
  "TestMode": false
}
```

**Response:**

```json
{
  "code": 0,
  "success": true,
  "message": "Payment processed successfully"
}
```

### 2. Payment Management

#### GET /api/payments/{payment_id}

Информация о платеже

**Response:**

```json
{
  "payment_id": "pay_123456",
  "application_id": "app_67890",
  "amount": 3000,
  "currency": "RUB",
  "status": "completed",
  "transaction_id": "12345",
  "payment_method": "card",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "client": {
    "email": "ivan@example.com",
    "ip_address": "192.168.1.1"
  }
}
```

---

## 🧠 AI API

### 1. AI Enhanced System

#### Class: AIEnhancedManager

```python
class AIEnhancedManager:
    """Управляющий класс для enhanced AI системы"""

    async def process_message(self, message: str, user_context: Dict) -> Dict[str, Any]:
        """Обработка сообщения через AI"""

    async def classify_intent(self, message: str) -> str:
        """Классификация намерения пользователя"""

    async def generate_response(self, intent: str, context: Dict) -> str:
        """Генерация ответа на основе намерения"""
```

#### POST /api/ai/process

Обработка сообщения через AI

**Request:**

```json
{
  "message": "Нужна консультация по разводу",
  "user_id": 123456789,
  "context": {
    "previous_messages": ["Здравствуйте", "Хочу получить юридическую помощь"],
    "user_profile": {
      "location": "Москва",
      "previous_categories": ["family_law"]
    }
  }
}
```

**Response:**

```json
{
  "intent": "family_law_consultation",
  "confidence": 0.95,
  "response": "Понимаю, вам нужна консультация по семейному праву. Развод - это серьезный шаг, и важно правильно оформить все документы.",
  "suggested_actions": [
    {
      "type": "category_selection",
      "category": "family_law",
      "text": "Перейти к семейному праву"
    },
    {
      "type": "create_application",
      "text": "Создать заявку на консультацию"
    }
  ],
  "processing_time_ms": 1150
}
```

#### POST /api/ai/classify

Классификация намерения

**Request:**

```json
{
  "message": "Проблемы с работодателем, не выплачивают зарплату"
}
```

**Response:**

```json
{
  "intent": "labor_law_salary",
  "confidence": 0.92,
  "category": "labor_law",
  "subcategory": "salary_disputes",
  "alternatives": [
    {
      "intent": "labor_law_general",
      "confidence": 0.78
    }
  ]
}
```

### 2. Content Generation

#### POST /api/ai/generate/post

Генерация SMM поста

**Request:**

```json
{
  "topic": "семейное право",
  "style": "professional",
  "length": "medium",
  "include_hashtags": true,
  "target_audience": "general"
}
```

**Response:**

```json
{
  "post_text": "💼 Семейное право: что важно знать при разводе\n\n🔍 Основные аспекты:\n• Раздел имущества\n• Алименты на детей\n• Определение места жительства детей\n\n📞 Нужна консультация? Обращайтесь к нашим специалистам!\n\n#семейноеправо #развод #алименты #юрист #консультация",
  "hashtags": ["#семейноеправо", "#развод", "#алименты", "#юрист"],
  "estimated_reach": 5000,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

---

## 📊 ANALYTICS API

### 1. Statistics API

#### GET /api/analytics/dashboard

Основная аналитика

**Response:**

```json
{
  "period": "today",
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "users": {
      "total": 15420,
      "new_today": 45,
      "active_today": 320
    },
    "applications": {
      "total": 5680,
      "new_today": 25,
      "completed_today": 18,
      "pending": 45
    },
    "revenue": {
      "total": 12500000,
      "today": 125000,
      "pending": 85000
    },
    "bot_usage": {
      "messages_today": 1250,
      "ai_requests_today": 420,
      "avg_response_time_ms": 1100
    }
  }
}
```

#### GET /api/analytics/applications

Аналитика заявок

**Query Parameters:**

- `period`: today, week, month, year
- `category`: ID категории (опционально)
- `status`: статус заявок (опционально)

**Response:**

```json
{
  "period": "month",
  "total_applications": 450,
  "by_category": {
    "family_law": {
      "count": 150,
      "percentage": 33.3,
      "avg_amount": 3500
    },
    "labor_law": {
      "count": 120,
      "percentage": 26.7,
      "avg_amount": 2800
    }
  },
  "by_status": {
    "completed": 380,
    "in_progress": 45,
    "pending_payment": 15,
    "cancelled": 10
  },
  "trends": {
    "growth_rate": 15.5,
    "completion_rate": 84.4,
    "avg_processing_time_hours": 48.5
  }
}
```

### 2. Performance Metrics

#### GET /api/analytics/performance

Метрики производительности

**Response:**

```json
{
  "system_performance": {
    "uptime_percentage": 99.95,
    "avg_response_time_ms": 1150,
    "error_rate_percentage": 0.12,
    "throughput_requests_per_minute": 45.8
  },
  "ai_performance": {
    "classification_accuracy": 96.5,
    "avg_processing_time_ms": 1200,
    "successful_responses": 98.2
  },
  "payment_performance": {
    "success_rate": 97.8,
    "avg_processing_time_seconds": 15.5,
    "refund_rate": 1.2
  }
}
```

---

## 🧪 TESTING API

### 1. Production Testing

#### POST /api/test/quick

Быстрое тестирование системы

**Response:**

```json
{
  "test_id": "test_123456",
  "type": "quick_check",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:15Z",
  "duration_seconds": 15,
  "overall_result": "passed",
  "success_rate": 100,
  "tests": [
    {
      "name": "Environment",
      "status": "passed",
      "details": "4/4 environment variables configured"
    },
    {
      "name": "Telegram API",
      "status": "passed",
      "details": "Bot: @your_bot_name"
    },
    {
      "name": "Admin Panel",
      "status": "passed",
      "details": "Operational"
    },
    {
      "name": "Monitoring",
      "status": "passed",
      "details": "7 health checks available"
    },
    {
      "name": "Autopost",
      "status": "passed",
      "details": "System ready"
    }
  ]
}
```

#### POST /api/test/full

Полное тестирование системы

**Response:**

```json
{
  "test_id": "test_789012",
  "type": "comprehensive",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:45Z",
  "duration_seconds": 165,
  "overall_result": "passed",
  "success_rate": 95,
  "test_groups": {
    "environment": {
      "passed": 4,
      "total": 4,
      "summary": "Environment configured (4/4 variables)"
    },
    "core_systems": {
      "passed": 3,
      "total": 3,
      "summary": "Core systems operational (3/3)"
    },
    "new_features": {
      "passed": 2,
      "total": 2,
      "summary": "New features available (2/2)"
    },
    "integration": {
      "passed": 1,
      "total": 2,
      "summary": "Integration and performance OK (1/2)"
    }
  },
  "recommendations": [
    "System ready for production deployment",
    "Consider setting up continuous monitoring"
  ]
}
```

---

## 🔒 AUTHENTICATION & AUTHORIZATION

### 1. Admin Authentication

#### Admin Verification

```python
def verify_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    admin_users = {6373924442, 343688708}  # Configured admin IDs
    return user_id in admin_users
```

#### Access Control Decorator

```python
def admin_required(func):
    """Декоратор для функций, требующих админ права"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not verify_admin(user_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        return await func(update, context)
    return wrapper
```

### 2. Rate Limiting

#### Rate Limit Configuration

```python
rate_limits = {
    "default": {"requests": 30, "window": 60},  # 30 requests per minute
    "ai_requests": {"requests": 10, "window": 60},  # 10 AI requests per minute
    "payment_requests": {"requests": 5, "window": 300}  # 5 payment requests per 5 minutes
}
```

---

## 📝 ERROR HANDLING

### 1. Standard Error Responses

#### Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "amount",
      "reason": "Amount must be greater than 0"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

#### Error Codes

```
400 BAD_REQUEST
401 UNAUTHORIZED
403 FORBIDDEN
404 NOT_FOUND
422 VALIDATION_ERROR
429 RATE_LIMIT_EXCEEDED
500 INTERNAL_SERVER_ERROR
503 SERVICE_UNAVAILABLE
```

### 2. Error Handling Examples

#### Telegram Bot Error Handling

```python
async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок бота"""
    logger.error(f"Exception while handling update: {context.error}")

    if update.effective_message:
        await update.effective_message.reply_text(
            "😔 Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )
```

---

## 📊 RATE LIMITS

### API Rate Limits

| Endpoint               | Limit         | Window    |
| ---------------------- | ------------- | --------- |
| `/api/applications`    | 10 requests   | 1 minute  |
| `/api/payments/create` | 5 requests    | 5 minutes |
| `/api/ai/process`      | 20 requests   | 1 minute  |
| `/health`              | 100 requests  | 1 minute  |
| `/webhook/*`           | 1000 requests | 1 minute  |

### Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1642248000
```

---

## 🔧 SDK & EXAMPLES

### 1. Python SDK Example

```python
import aiohttp
import asyncio

class JuridicalBotAPI:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key

    async def create_application(self, application_data: dict):
        """Создание заявки"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/applications",
                json=application_data,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return await response.json()

    async def get_monitoring_dashboard(self):
        """Получение мониторинг dashboard"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/monitoring/dashboard"
            ) as response:
                return await response.json()

# Использование
api = JuridicalBotAPI("https://your-app.railway.app")
dashboard = await api.get_monitoring_dashboard()
```

### 2. JavaScript SDK Example

```javascript
class JuridicalBotAPI {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async createApplication(applicationData) {
    const response = await fetch(`${this.baseUrl}/api/applications`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(applicationData),
    });
    return response.json();
  }

  async getHealthStatus() {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }
}

// Использование
const api = new JuridicalBotAPI("https://your-app.railway.app");
const health = await api.getHealthStatus();
```

---

**📡 API готов к использованию в продакшне!**
