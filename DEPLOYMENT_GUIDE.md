# 🚀 DEPLOYMENT GUIDE - Production Deployment

## 📋 Полное руководство по развертыванию системы в продакшене

---

## 🎯 ОБЗОР ДЕПЛОЯ

### Поддерживаемые платформы:

- ✅ **Railway.app** (рекомендовано) - основной деплой
- ✅ **Heroku** - альтернативный вариант
- ✅ **VPS/Dedicated Server** - для самостоятельного хостинга
- ✅ **Docker** - контейнеризация

### Требования:

- Python 3.12+
- PostgreSQL 13+
- Redis (опционально, для кэширования)
- Минимум 1GB RAM

---

## 🚀 RAILWAY DEPLOYMENT (Рекомендовано)

### 1. Подготовка проекта

#### Необходимые файлы:

```
yr_app/
├── Procfile                 # Команды запуска
├── railway.json            # Конфигурация Railway
├── requirements.txt        # Python зависимости
├── runtime.txt             # Версия Python
└── railway_start.py        # Скрипт запуска
```

#### Procfile:

```
web: python railway_start.py
worker: python bot/main.py
```

#### railway.json:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python railway_start.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 2. Пошаговый деплой

#### Шаг 1: Установка Railway CLI

```bash
# macOS/Linux
npm install -g @railway/cli

# Windows
npm install -g @railway/cli

# Или через curl
curl -fsSL https://railway.app/install.sh | sh
```

#### Шаг 2: Логин и создание проекта

```bash
# Логин
railway login

# Создание нового проекта
railway init

# Или подключение к существующему
railway link [project-id]
```

#### Шаг 3: Настройка базы данных

```bash
# Добавление PostgreSQL
railway add postgresql

# Получение DATABASE_URL
railway variables
```

#### Шаг 4: Настройка переменных окружения

```bash
# Установка переменных через CLI
railway variables set BOT_TOKEN=your_bot_token
railway variables set ADMIN_CHAT_ID=your_admin_chat_id
railway variables set TARGET_CHANNEL_ID=your_channel_id
railway variables set OPENAI_API_KEY=your_openai_key
railway variables set CLOUDPAYMENTS_PUBLIC_ID=your_public_id
railway variables set CLOUDPAYMENTS_API_SECRET=your_api_secret

# Или через .env файл (не коммитить!)
railway variables set --from-file .env
```

#### Шаг 5: Деплой

```bash
# Первичный деплой
git add .
git commit -m "Initial deployment"
git push origin main

# Railway автоматически задеплоит при push
railway up

# Проверка статуса
railway status
```

### 3. Пост-деплой настройка

#### Инициализация БД:

```bash
# Подключение к удаленной БД
railway connect postgresql

# Выполнение миграций
railway run alembic upgrade head

# Или через web interface
railway shell
python -c "from alembic import command; from alembic.config import Config; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"
```

#### Проверка работы:

```bash
# Логи
railway logs

# Статус сервисов
railway ps

# Health check
curl https://your-app.railway.app/health
```

---

## 🐳 DOCKER DEPLOYMENT

### 1. Dockerfile

```dockerfile
FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директории для логов
RUN mkdir -p logs

# Экспорт порта
EXPOSE 8000

# Команда запуска
CMD ["python", "bot/main.py"]
```

### 2. Docker Compose

```yaml
version: "3.8"

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DATABASE_URL=postgresql://postgres:password@db:5432/jurbot
      - ADMIN_CHAT_ID=${ADMIN_CHAT_ID}
      - TARGET_CHANNEL_ID=${TARGET_CHANNEL_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  web:
    build: .
    command: python railway_start.py
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/jurbot
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=jurbot
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 3. Запуск Docker

```bash
# Сборка и запуск
docker-compose up -d

# Применение миграций
docker-compose exec bot alembic upgrade head

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down
```

---

## 🖥️ VPS DEPLOYMENT

### 1. Подготовка сервера

#### Ubuntu/Debian:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python 3.12
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib

# Установка Git и другие утилиты
sudo apt install git nginx supervisor redis-server
```

#### CentOS/RHEL:

```bash
# Python 3.12
sudo yum install python3.12 python3.12-devel

# PostgreSQL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2. Настройка приложения

#### Клонирование и настройка:

```bash
# Создание пользователя
sudo adduser jurbot
sudo usermod -aG sudo jurbot
su - jurbot

# Клонирование репозитория
git clone https://github.com/yourusername/yr_app.git
cd yr_app

# Виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install gunicorn
```

#### Переменные окружения:

```bash
# Создание .env
cat > .env << EOF
BOT_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_chat_id
TARGET_CHANNEL_ID=your_channel_id
DATABASE_URL=postgresql://jurbot:password@localhost/jurbot
OPENAI_API_KEY=your_openai_key
CLOUDPAYMENTS_PUBLIC_ID=your_public_id
CLOUDPAYMENTS_API_SECRET=your_api_secret
EOF

# Установка прав
chmod 600 .env
```

### 3. Настройка базы данных

```bash
# Создание пользователя и БД
sudo -u postgres psql
CREATE USER jurbot WITH PASSWORD 'strong_password';
CREATE DATABASE jurbot OWNER jurbot;
GRANT ALL PRIVILEGES ON DATABASE jurbot TO jurbot;
\q

# Применение миграций
source .venv/bin/activate
alembic upgrade head
```

### 4. Настройка Systemd

#### Bot Service:

```bash
sudo tee /etc/systemd/system/jurbot.service << EOF
[Unit]
Description=Juridical Bot
After=network.target postgresql.service

[Service]
Type=simple
User=jurbot
WorkingDirectory=/home/jurbot/yr_app
Environment=PATH=/home/jurbot/yr_app/.venv/bin
ExecStart=/home/jurbot/yr_app/.venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### Web Service:

```bash
sudo tee /etc/systemd/system/jurbot-web.service << EOF
[Unit]
Description=Juridical Bot Web
After=network.target

[Service]
Type=simple
User=jurbot
WorkingDirectory=/home/jurbot/yr_app
Environment=PATH=/home/jurbot/yr_app/.venv/bin
ExecStart=/home/jurbot/yr_app/.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 3 railway_start:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

#### Запуск сервисов:

```bash
sudo systemctl daemon-reload
sudo systemctl enable jurbot jurbot-web
sudo systemctl start jurbot jurbot-web

# Проверка статуса
sudo systemctl status jurbot
sudo systemctl status jurbot-web
```

### 5. Настройка Nginx

```bash
sudo tee /etc/nginx/sites-available/jurbot << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
EOF

# Активация сайта
sudo ln -s /etc/nginx/sites-available/jurbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔐 SSL/HTTPS SETUP

### Использование Certbot:

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 📊 МОНИТОРИНГ И ЛОГИ

### 1. Система логирования

#### Логротация:

```bash
sudo tee /etc/logrotate.d/jurbot << EOF
/home/jurbot/yr_app/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 jurbot jurbot
    postrotate
        systemctl reload jurbot
    endscript
}
EOF
```

### 2. Мониторинг ресурсов

#### Prometheus + Grafana (опционально):

```bash
# Установка Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
sudo mv prometheus-2.40.0.linux-amd64 /opt/prometheus

# Конфигурация
sudo tee /opt/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'jurbot'
    static_configs:
      - targets: ['localhost:8000']
EOF
```

---

## 🚨 EMERGENCY PROCEDURES

### 1. Быстрое восстановление

#### Rollback:

```bash
# Railway
railway rollback

# VPS
cd /home/jurbot/yr_app
git checkout previous-working-commit
sudo systemctl restart jurbot jurbot-web
```

### 2. Backup и восстановление

#### Backup БД:

```bash
# Создание backup
pg_dump -h hostname -U jurbot -d jurbot > backup_$(date +%Y%m%d).sql

# Восстановление
psql -h hostname -U jurbot -d jurbot < backup_20240101.sql
```

### 3. Проверка работоспособности

#### Health Check Script:

```bash
#!/bin/bash
# health_check.sh

echo "🔍 Checking system health..."

# Bot process
if pgrep -f "python.*bot/main.py" > /dev/null; then
    echo "✅ Bot is running"
else
    echo "❌ Bot is not running"
    sudo systemctl restart jurbot
fi

# Web service
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Web service is healthy"
else
    echo "❌ Web service is down"
    sudo systemctl restart jurbot-web
fi

# Database
if pg_isready -h localhost -U jurbot > /dev/null 2>&1; then
    echo "✅ Database is accessible"
else
    echo "❌ Database connection failed"
fi

echo "Health check completed"
```

---

## 📞 SUPPORT & TROUBLESHOOTING

### Основные команды диагностики:

```bash
# Логи системы
sudo journalctl -u jurbot -f
sudo journalctl -u jurbot-web -f

# Логи приложения
tail -f /home/jurbot/yr_app/logs/bot.log

# Статус сервисов
sudo systemctl status jurbot jurbot-web nginx postgresql

# Мониторинг ресурсов
htop
df -h
free -h
```

### Частые проблемы и решения:

1. **Bot не отвечает**: Проверить BOT_TOKEN и network connectivity
2. **DB connection error**: Проверить DATABASE_URL и PostgreSQL service
3. **High memory usage**: Увеличить память или оптимизировать код
4. **SSL certificate expired**: Обновить через certbot

---

**🚀 Deployment готов! Система в продакшене.**
