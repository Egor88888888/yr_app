# 🚀 PRODUCTION ENVIRONMENT SETUP

## 🎯 КРИТИЧЕСКИ ВАЖНО: Настройка переменных окружения

Перед деплоем необходимо настроить следующие переменные в Railway Dashboard:

### ================ ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ================

```bash
# Telegram Bot Configuration
BOT_TOKEN=YOUR_REAL_PRODUCTION_BOT_TOKEN_HERE
ADMIN_CHAT_ID=YOUR_ADMIN_CHAT_ID_HERE
TARGET_CHANNEL_ID=@your_channel_id_here

# Database (автоматически заполнится Railway PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Web App (автоматически заполнится Railway)
RAILWAY_PUBLIC_DOMAIN=your-app.railway.app
PORT=8080

# AI Integration
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
```

### ================ ДОПОЛНИТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ================

```bash
# Payment System (для онлайн-платежей)
CLOUDPAYMENTS_PUBLIC_ID=YOUR_CLOUDPAYMENTS_PUBLIC_ID
CLOUDPAYMENTS_API_SECRET=YOUR_CLOUDPAYMENTS_SECRET_KEY

# Google Sheets Integration (для CRM)
GOOGLE_SHEETS_CREDS_JSON={"type":"service_account","project_id":"..."}
GOOGLE_SHEET_ID=your_google_sheet_id_here

# Notifications (опционально)
MAILGUN_API_KEY=your_mailgun_api_key_here
MAILGUN_DOMAIN=mg.yourdomain.com
SMS_RU_API_KEY=your_sms_ru_api_key_here
```

### ================ RAILWAY SYSTEM ================

```bash
# System Variables (автоматически)
PYTHONPATH=.
PYTHONUNBUFFERED=1
```

## 🔧 Как настроить в Railway:

1. **Откройте Railway Dashboard**
2. **Выберите ваш проект**
3. **Перейдите в Variables**
4. **Добавьте каждую переменную из списка выше**

## ✅ Проверка готовности:

После настройки переменных запустите:

```bash
python final_production_verification.py
```

Должно быть **0 критических ошибок** для успешного деплоя.
