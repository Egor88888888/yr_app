# 🛠️ TROUBLESHOOTING GUIDE - Решение проблем

## 📋 Полное руководство по диагностике и устранению проблем

---

## 🎯 ОБЗОР TROUBLESHOOTING

### Основные категории проблем:

- **🤖 Bot Issues** - проблемы с Telegram ботом
- **🗄️ Database Issues** - проблемы с базой данных
- **💳 Payment Issues** - проблемы с платежами
- **🔍 Monitoring Issues** - проблемы с мониторингом
- **📊 Performance Issues** - проблемы с производительностью
- **🌐 Network Issues** - сетевые проблемы
- **🚀 Deployment Issues** - проблемы с деплоем

### Уровни критичности:

- **🚨 CRITICAL** - полная неработоспособность системы
- **❌ HIGH** - значительное влияние на функциональность
- **⚠️ MEDIUM** - частичное влияние на работу
- **ℹ️ LOW** - минорные проблемы

---

## 🤖 BOT ISSUES

### 1. Бот не отвечает на команды

#### Симптомы:

- Бот не реагирует на `/start`
- Нет ответа на любые сообщения
- Webhook не получает обновления

#### Диагностика:

```bash
# 1. Проверка токена бота
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# 2. Проверка webhook
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# 3. Проверка логов
railway logs --follow
# или локально
tail -f logs/bot.log
```

#### Решения:

**A. Неверный BOT_TOKEN:**

```bash
# Проверить переменную окружения
railway variables

# Обновить токен
railway variables set BOT_TOKEN=new_correct_token

# Перезапустить сервис
railway up
```

**B. Проблемы с webhook:**

```bash
# Удалить существующий webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# Установить новый webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-app.railway.app/webhook/<TOKEN>"
```

**C. Процесс бота не запущен:**

```bash
# Railway - проверить статус
railway status

# VPS - проверить systemd
sudo systemctl status jurbot
sudo systemctl restart jurbot
```

### 2. Бот работает медленно

#### Симптомы:

- Большая задержка ответов (>5 секунд)
- Таймауты при обработке команд
- Алерты о медленной работе

#### Диагностика:

```bash
# Проверка производительности
/quick_fix → 🧪 Тесты → 📊 Performance Test

# Мониторинг ресурсов
railway run htop
# или
railway run top

# Проверка памяти
railway run free -h
```

#### Решения:

**A. Высокое использование памяти:**

```python
# Оптимизация в bot/main.py
import gc

# Принудительная очистка памяти
async def cleanup_memory():
    gc.collect()

# Вызывать периодически
context.job_queue.run_repeating(cleanup_memory, interval=3600)
```

**B. Медленные SQL запросы:**

```sql
-- Проверка медленных запросов
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Добавление индексов при необходимости
CREATE INDEX CONCURRENTLY idx_applications_status ON applications(status);
CREATE INDEX CONCURRENTLY idx_applications_created_at ON applications(created_at);
```

**C. Увеличение ресурсов:**

```bash
# Railway - увеличить план
# Через Railway dashboard → Settings → Plan

# VPS - увеличить память/CPU
# Обратиться к хостинг провайдеру
```

### 3. Ошибки при отправке сообщений

#### Симптомы:

- "Bad Request: message is too long"
- "Forbidden: bot was blocked by the user"
- "Bad Request: can't parse entities"

#### Решения:

**A. Слишком длинное сообщение:**

```python
def split_long_message(text: str, max_length: int = 4096) -> List[str]:
    """Разделение длинного сообщения на части"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        # Ищем место для разрыва
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts

# Использование
async def send_long_message(bot, chat_id, text):
    parts = split_long_message(text)
    for part in parts:
        await bot.send_message(chat_id=chat_id, text=part)
```

**B. Проблемы с парсингом Markdown:**

```python
import re

def escape_markdown(text: str) -> str:
    """Экранирование специальных символов Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# Использование
safe_text = escape_markdown(user_input)
await bot.send_message(chat_id=chat_id, text=safe_text, parse_mode="MarkdownV2")
```

---

## 🗄️ DATABASE ISSUES

### 1. Ошибки подключения к БД

#### Симптомы:

- "Connection refused"
- "FATAL: password authentication failed"
- "FATAL: database does not exist"

#### Диагностика:

```bash
# Проверка DATABASE_URL
railway variables | grep DATABASE_URL

# Тест подключения
railway run python -c "
import asyncpg
import asyncio
import os

async def test_db():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        result = await conn.fetchval('SELECT version()')
        print(f'✅ Database connected: {result}')
        await conn.close()
    except Exception as e:
        print(f'❌ Database error: {e}')

asyncio.run(test_db())
"
```

#### Решения:

**A. Неверная строка подключения:**

```bash
# Railway - пересоздать PostgreSQL
railway add postgresql --remove-existing

# Обновить DATABASE_URL в коде
railway variables set DATABASE_URL=postgresql://...
```

**B. Превышение лимита подключений:**

```python
# В database.py
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Отключить пул соединений
    echo=False
)

# Или увеличить размер пула
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)
```

### 2. Медленные запросы

#### Диагностика:

```sql
-- Включить логирование медленных запросов
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1 секунда
SELECT pg_reload_conf();

-- Просмотр медленных запросов
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
WHERE mean_time > 1000 -- больше 1 секунды
ORDER BY total_time DESC;
```

#### Решения:

**A. Добавление индексов:**

```sql
-- Для частых запросов по статусу
CREATE INDEX CONCURRENTLY idx_applications_status ON applications(status);

-- Для поиска по пользователю
CREATE INDEX CONCURRENTLY idx_applications_user_id ON applications(user_id);

-- Для сортировки по дате
CREATE INDEX CONCURRENTLY idx_applications_created_at ON applications(created_at DESC);

-- Составной индекс
CREATE INDEX CONCURRENTLY idx_applications_user_status
ON applications(user_id, status, created_at DESC);
```

**B. Оптимизация запросов:**

```python
# Вместо N+1 запросов
async def get_applications_with_users():
    # Плохо
    applications = await session.execute(select(Application))
    for app in applications:
        user = await session.execute(select(User).where(User.id == app.user_id))

    # Хорошо
    result = await session.execute(
        select(Application, User)
        .join(User, Application.user_id == User.id)
    )
    return result.fetchall()
```

### 3. Ошибки миграций

#### Симптомы:

- "Target database is not up to date"
- "Can't locate revision identified by"
- Alembic migration failures

#### Решения:

**A. Проблемы с версией миграции:**

```bash
# Проверка текущей версии
railway run alembic current

# Просмотр истории
railway run alembic history

# Откат к предыдущей версии
railway run alembic downgrade -1

# Принудительная установка версии
railway run alembic stamp head
```

**B. Конфликты миграций:**

```bash
# Создание merge миграции
railway run alembic merge -m "merge heads" head1 head2

# Применение merge
railway run alembic upgrade head
```

---

## 💳 PAYMENT ISSUES

### 1. CloudPayments webhook не работает

#### Симптомы:

- Платежи проходят, но статус не обновляется
- Нет уведомлений о платежах
- CloudPayments возвращает ошибки webhook

#### Диагностика:

```bash
# Проверка webhook endpoint
curl -X POST https://your-app.railway.app/webhook/payment \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Проверка логов webhook
railway logs | grep webhook
```

#### Решения:

**A. Неверный URL webhook:**

```python
# В CloudPayments настройках указать:
# Success URL: https://your-app.railway.app/webhook/payment/success
# Fail URL: https://your-app.railway.app/webhook/payment/fail

# Проверить обработчик
@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    data = await request.json()
    logger.info(f"Payment webhook received: {data}")

    # Обработка платежа
    result = await process_payment(data)
    return {"code": 0 if result else 1}
```

**B. Проблемы с SSL сертификатом:**

```bash
# Проверка SSL
curl -I https://your-app.railway.app

# Railway автоматически предоставляет SSL
# Убедиться что используется HTTPS URL в CloudPayments
```

### 2. Платежи отклоняются

#### Симптомы:

- "Transaction declined"
- "Invalid card number"
- "Insufficient funds"

#### Решения:

**A. Тестовые платежи:**

```python
# Использовать тестовые карты CloudPayments
test_cards = {
    "success": "4242424242424242",  # Успешная карта
    "decline": "4000000000000002",  # Отклонение
    "3ds": "4000000000000028"       # Требует 3DS
}

# В тестовом режиме
CLOUDPAYMENTS_PUBLIC_ID = "test_api_pk_..."  # test_ префикс
```

**B. Валидация данных:**

```python
from decimal import Decimal

def validate_payment_amount(amount: float) -> bool:
    """Валидация суммы платежа"""
    if amount <= 0:
        return False
    if amount > 1000000:  # Максимум 1 млн рублей
        return False
    if Decimal(str(amount)).as_tuple().exponent < -2:  # Больше 2 знаков
        return False
    return True
```

---

## 🔍 MONITORING ISSUES

### 1. Мониторинг не запускается

#### Симптомы:

- Кнопка "Start Monitoring" не работает
- Нет алертов в админ чате
- Dashboard показывает "Мониторинг не запущен"

#### Диагностика:

```bash
# Проверка переменных окружения
railway variables | grep ADMIN_CHAT_ID

# Тест создания мониторинга
railway run python -c "
from bot.services.production_monitoring_system import ProductionMonitoringSystem
from telegram import Bot
import os
import asyncio

async def test_monitoring():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')
    monitoring = ProductionMonitoringSystem(bot, admin_chat_id)
    print(f'✅ Monitoring system created')
    print(f'Health checks: {len(monitoring.health_checks)}')

asyncio.run(test_monitoring())
"
```

#### Решения:

**A. Неверный ADMIN_CHAT_ID:**

```bash
# Получить правильный chat_id
# 1. Добавить бота в чат
# 2. Отправить любое сообщение
# 3. Открыть: https://api.telegram.org/bot<TOKEN>/getUpdates
# 4. Найти chat.id в ответе

railway variables set ADMIN_CHAT_ID=correct_chat_id
```

**B. Проблемы с правами бота:**

```python
# Проверить права бота в чате
async def check_bot_permissions(bot, chat_id):
    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        print(f"Bot status: {chat_member.status}")
        print(f"Can send messages: {chat_member.can_send_messages}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

### 2. Алерты не приходят

#### Решения:

**A. Проверка cooldown системы:**

```python
# В production_monitoring_system.py
def _is_alert_in_cooldown(self, cooldown_key: str) -> bool:
    last_alert = self.alert_cooldown.get(cooldown_key)
    if not last_alert:
        return False

    # Временно отключить cooldown для тестирования
    return False  # Было: datetime.now() - last_alert < self.cooldown_period
```

**B. Тестовый алерт:**

```python
# Отправка тестового алерта
async def send_test_alert():
    from bot.services.production_monitoring_system import AlertLevel
    await monitoring_system._send_admin_alert(
        AlertLevel.INFO,
        "test_system",
        "🧪 Test alert - monitoring system working"
    )
```

---

## 📊 PERFORMANCE ISSUES

### 1. Высокое использование памяти

#### Симптомы:

- Memory usage > 90%
- OutOfMemory ошибки
- Медленная работа системы

#### Диагностика:

```bash
# Мониторинг памяти
railway run python -c "
import psutil
memory = psutil.virtual_memory()
print(f'Memory usage: {memory.percent}%')
print(f'Available: {memory.available / 1024 / 1024:.0f} MB')
"

# Профилирование Python
railway run python -c "
import tracemalloc
tracemalloc.start()
# ... ваш код ...
current, peak = tracemalloc.get_traced_memory()
print(f'Current memory usage: {current / 1024 / 1024:.1f} MB')
print(f'Peak memory usage: {peak / 1024 / 1024:.1f} MB')
"
```

#### Решения:

**A. Оптимизация кода:**

```python
# Использование __slots__ для экономии памяти
class OptimizedClass:
    __slots__ = ['field1', 'field2']

    def __init__(self, field1, field2):
        self.field1 = field1
        self.field2 = field2

# Очистка больших объектов
def process_large_data(data):
    result = expensive_operation(data)
    del data  # Принудительное удаление
    gc.collect()  # Принудительная сборка мусора
    return result
```

**B. Кэширование с TTL:**

```python
from functools import lru_cache
import asyncio
from datetime import datetime, timedelta

class TTLCache:
    def __init__(self, maxsize=128, ttl_seconds=300):
        self.cache = {}
        self.maxsize = maxsize
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        if len(self.cache) >= self.maxsize:
            # Удаляем самый старый элемент
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (value, datetime.now())
```

### 2. Медленная работа AI

#### Решения:

**A. Кэширование AI ответов:**

```python
import hashlib

class AIResponseCache:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl_seconds=3600)

    def get_cache_key(self, message: str, context: dict) -> str:
        """Создание ключа кэша"""
        content = f"{message}_{str(sorted(context.items()))}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get_cached_response(self, message: str, context: dict):
        cache_key = self.get_cache_key(message, context)
        return self.cache.get(cache_key)

    async def cache_response(self, message: str, context: dict, response: dict):
        cache_key = self.get_cache_key(message, context)
        self.cache.set(cache_key, response)
```

**B. Асинхронная обработка:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Для CPU-intensive операций
executor = ThreadPoolExecutor(max_workers=2)

async def process_ai_request(message: str):
    # Быстрый ответ пользователю
    await send_typing_action()

    # Тяжелая обработка в отдельном потоке
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        cpu_intensive_ai_processing,
        message
    )

    return result
```

---

## 🌐 NETWORK ISSUES

### 1. Таймауты API запросов

#### Симптомы:

- "Request timeout"
- "Connection reset by peer"
- Медленные ответы внешних API

#### Решения:

**A. Настройка таймаутов:**

```python
import aiohttp
import asyncio

async def make_api_request(url, data=None, timeout=30):
    timeout_config = aiohttp.ClientTimeout(total=timeout)

    try:
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(url, json=data) as response:
                return await response.json()
    except asyncio.TimeoutError:
        logger.error(f"Timeout for request to {url}")
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Network error for {url}: {e}")
        raise
```

**B. Retry механизм:**

```python
import random

async def retry_api_request(url, data=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await make_api_request(url, data)
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff
            delay = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s")
            await asyncio.sleep(delay)
```

### 2. SSL/TLS проблемы

#### Решения:

**A. Обновление сертификатов:**

```bash
# Railway автоматически обновляет SSL
# Для VPS:
sudo certbot renew --quiet

# Проверка сертификата
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

**B. Настройка SSL контекста:**

```python
import ssl
import aiohttp

# Создание SSL контекста
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE  # Только для тестирования!

connector = aiohttp.TCPConnector(ssl=ssl_context)
session = aiohttp.ClientSession(connector=connector)
```

---

## 🚀 DEPLOYMENT ISSUES

### 1. Railway деплой не работает

#### Симптомы:

- Build fails
- Deployment timeout
- Service не запускается

#### Диагностика:

```bash
# Логи билда
railway logs --deployment

# Статус сервиса
railway status

# Переменные окружения
railway variables
```

#### Решения:

**A. Проблемы с зависимостями:**

```bash
# Обновить requirements.txt
pip freeze > requirements.txt

# Проверить совместимость версий
pip check

# Локальный тест
pip install -r requirements.txt
python bot/main.py
```

**B. Проблемы с памятью при билде:**

```dockerfile
# В Dockerfile увеличить лимиты
FROM python:3.12-slim

# Установка с ограничением памяти
RUN pip install --no-cache-dir -r requirements.txt
```

**C. Timeout при старте:**

```python
# В railway_start.py увеличить timeout
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        timeout_keep_alive=120,  # Увеличен timeout
        access_log=False
    )
```

### 2. Environment variables не загружаются

#### Решения:

**A. Проверка и установка переменных:**

```bash
# Просмотр всех переменных
railway variables

# Установка отсутствующих
railway variables set BOT_TOKEN=your_token
railway variables set ADMIN_CHAT_ID=your_chat_id

# Удаление неиспользуемых
railway variables delete OLD_VARIABLE
```

**B. Резервные значения в коде:**

```python
import os

# С fallback значениями
BOT_TOKEN = os.getenv('BOT_TOKEN', 'default_token')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '0')

# Проверка критичных переменных
def validate_environment():
    required_vars = ['BOT_TOKEN', 'ADMIN_CHAT_ID', 'DATABASE_URL']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")

# Вызов при старте
validate_environment()
```

---

## 🚨 EMERGENCY PROCEDURES

### 1. Полный отказ системы

#### Пошаговые действия:

**1. Первичная диагностика (5 минут):**

```bash
# Проверка доступности
curl -I https://your-app.railway.app/health

# Логи Railway
railway logs --tail=100

# Статус сервисов
railway status
```

**2. Быстрое восстановление (10 минут):**

```bash
# Откат к последней рабочей версии
railway rollback

# Или перезапуск сервиса
railway up --detach
```

**3. Если не помогает (15 минут):**

```bash
# Проверка и восстановление переменных
railway variables

# Форсированная пересборка
railway up --force

# Проверка базы данных
railway connect postgresql
```

### 2. Критические алерты

#### При получении CRITICAL алерта:

**Шаг 1: Немедленная оценка (1 минута)**

- Открыть `/quick_fix` → Monitoring Dashboard
- Определить затронутые системы
- Оценить масштаб проблемы

**Шаг 2: Временные меры (5 минут)**

- Если autopost down → отключить автопостинг
- Если database down → переключиться на readonly режим
- Если payment down → уведомить пользователей

**Шаг 3: Устранение причины (15 минут)**

- Проверить логи конкретной системы
- Применить известные решения
- При необходимости откатить последние изменения

**Шаг 4: Проверка восстановления (5 минут)**

- Запустить тесты: `/production_test`
- Проверить все критичные функции
- Убедиться что алерты прекратились

### 3. Backup и восстановление

#### Создание backup:

```bash
# Backup базы данных
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup конфигурации
railway variables > env_backup_$(date +%Y%m%d).txt

# Backup кода (Git)
git tag backup_$(date +%Y%m%d_%H%M%S)
git push origin --tags
```

#### Восстановление:

```bash
# Восстановление БД
railway run psql $DATABASE_URL < backup_20240115_103000.sql

# Восстановление переменных
while IFS= read -r line; do
    railway variables set "$line"
done < env_backup_20240115.txt

# Восстановление кода
git checkout backup_20240115_103000
railway up
```

---

## 📊 MONITORING CHECKLIST

### Ежедневная проверка:

- [ ] Dashboard мониторинга: `/quick_fix` → Auto Monitoring
- [ ] Проверка алертов за последние 24 часа
- [ ] Состояние всех систем (7 health checks)
- [ ] Лог ошибок: критичные и частые проблемы
- [ ] Статистика производительности

### Еженедельная проверка:

- [ ] Полное тестирование: `/production_test`
- [ ] Анализ трендов производительности
- [ ] Проверка backup'ов
- [ ] Обновление документации при необходимости
- [ ] Планирование улучшений

### Ежемесячная проверка:

- [ ] Комплексный аудит безопасности
- [ ] Обновление зависимостей
- [ ] Анализ финансовых метрик
- [ ] Оценка удовлетворенности пользователей
- [ ] Планирование развития системы

---

## 📞 КОНТАКТЫ ПОДДЕРЖКИ

### Эскалация по уровням:

**Level 1 - Операционные проблемы:**

- Telegram: @admin_username
- Response time: 1 час

**Level 2 - Технические проблемы:**

- Telegram: @tech_admin
- Email: tech@company.com
- Response time: 4 часа

**Level 3 - Критичные инциденты:**

- Phone: +7 (XXX) XXX-XX-XX
- Telegram: @developer_username
- Response time: 30 минут

**Экстренная связь 24/7:**

- Emergency hotline: +7 (XXX) XXX-XX-XX
- Только для CRITICAL инцидентов

---

## 📚 ПОЛЕЗНЫЕ РЕСУРСЫ

### Документация:

- [Production README](PRODUCTION_README.md)
- [Admin Manual](ADMIN_MANUAL.md)
- [API Reference](API_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

### Инструменты мониторинга:

- Railway Dashboard: https://railway.app/dashboard
- Telegram Bot: @your_bot_name
- CloudPayments: https://cp.cloudpayments.ru

### Логи и метрики:

- Application logs: `railway logs`
- Database logs: Railway PostgreSQL dashboard
- Payment logs: CloudPayments dashboard
- Monitoring alerts: Telegram admin chat

---

**🛠️ Помните: лучший troubleshooting - это профилактика проблем!**
