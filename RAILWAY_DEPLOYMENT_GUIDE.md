# 🚀 RAILWAY DEPLOYMENT GUIDE - OpenAI GPT Integration

## ✅ **ИЗМЕНЕНИЯ ВЫПОЛНЕНЫ:**

### 🔄 **ПЕРЕХОД НА OPENAI GPT API:**
- **Основной API:** OpenAI GPT (переменная `API_GPT`)
- **Fallback:** OpenRouter → Azure OpenAI (в таком порядке)
- **Интеграция:** https://api.openai.com/v1/chat/completions

### 🔴 **АВТОПОСТИНГ ОТКЛЮЧЕН ПО УМОЛЧАНИЮ:**
- Требует ручного включения через админ панель
- `/admin` → "⚡ Автопостинг" → "🟢 Запустить"

---

## 📦 **ДЕПЛОЙ ПАКЕТ:** `railway_deploy_openai.zip`

### 🔧 **ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ДЛЯ RAILWAY:**

**ОБЯЗАТЕЛЬНЫЕ:**
```bash
# Bot Token
BOT_TOKEN=ваш_telegram_bot_token

# Admin
ADMIN_CHAT_ID=123456789

# PRIMARY AI API - OPENAI GPT
API_GPT=sk-ваш-openai-api-ключ

# Database (Railway PostgreSQL addon)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Channel
TARGET_CHANNEL_ID=-1001234567890
TARGET_CHANNEL_USERNAME=@your_channel
```

**ОПЦИОНАЛЬНЫЕ:**
```bash
# Fallback AI APIs
OPENROUTER_API_KEY=ваш_openrouter_ключ
AZURE_OPENAI_API_KEY=ваш_azure_ключ

# Autopost (disabled by default)
ENABLE_AUTOPOST=false
POST_INTERVAL_HOURS=10

# Production
RAILWAY_ENVIRONMENT=production
```

---

## 🚀 **ИНСТРУКЦИИ ДЕПЛОЯ:**

### **1. Подготовка Railway:**
1. Зайдите на [Railway.app](https://railway.app)
2. Создайте новый проект
3. Добавьте PostgreSQL addon
4. Загрузите `railway_deploy_openai.zip`

### **2. Настройка переменных:**
1. В Railway Dashboard → Variables
2. Добавьте все переменные выше
3. **ВАЖНО:** `API_GPT` - ваш OpenAI API ключ

### **3. Деплой:**
1. Railway автоматически развернет из zip
2. Установит зависимости из `requirements.txt`
3. Запустит `bot/main.py`

### **4. Проверка работы:**
1. Найдите бота в Telegram
2. Напишите `/start`
3. Админ: `/admin` → проверьте все функции
4. **Автопостинг:** включите вручную если нужно

---

## 🎯 **ОСОБЕННОСТИ ДЕПЛОЯ:**

### ✅ **ПРЕИМУЩЕСТВА OpenAI:**
- **Стабильность:** Прямой API без промежуточных сервисов
- **Скорость:** Быстрые ответы
- **Качество:** Лучшая производительность GPT моделей
- **Простота:** Одна переменная `API_GPT`

### 🔄 **Fallback система:**
1. **OpenAI** (основной) - если есть `API_GPT`
2. **OpenRouter** (резерв) - если OpenAI недоступен
3. **Azure OpenAI** (legacy) - последний резерв

### 🔴 **Автопостинг отключен:**
- **По умолчанию:** OFF
- **Включение:** Только через админ панель
- **Причина:** Безопасность и контроль

---

## 🧪 **ТЕСТИРОВАНИЕ ПОСЛЕ ДЕПЛОЯ:**

### **1. Основные функции:**
```
/start - запуск бота
/admin - админ панель (только для админов)
```

### **2. AI консультации:**
- Напишите любой юридический вопрос
- Проверьте качество ответов OpenAI
- Fallback сработает автоматически при ошибках

### **3. Админ панель:**
```
/admin → "📊 Статистика" - проверка метрик
/admin → "📝 Создать пост" - тест AI генерации
/admin → "⚡ Автопостинг" - управление постами
/admin → "🔧 Система" - системная информация
```

### **4. Автопостинг (если включить):**
- Создает юридические посты через AI
- Проверяет дубли
- Публикует в канал

---

## 🚨 **TROUBLESHOOTING:**

### **Проблема: AI не отвечает**
**Решение:** Проверьте `API_GPT` переменную, должна начинаться с `sk-`

### **Проблема: Bot не запускается**
**Решение:** 
1. Проверьте `BOT_TOKEN`
2. Проверьте `ADMIN_CHAT_ID`
3. Проверьте `DATABASE_URL`

### **Проблема: Админ панель недоступна**
**Решение:** Убедитесь что ваш Telegram ID указан в `ADMIN_CHAT_ID`

### **Проблема: Автопостинг не работает**
**Решение:** 
1. Включите вручную через `/admin` → "⚡ Автопостинг"
2. Проверьте `TARGET_CHANNEL_ID`
3. Убедитесь что бот админ в канале

---

## 📈 **МОНИТОРИНГ:**

После деплоя следите за:
- **Railway Logs** - ошибки и предупреждения
- **Bot /admin** - статистика использования
- **AI API Usage** - расход токенов OpenAI
- **Database** - размер и производительность

---

**ГОТОВО К PRODUCTION ДЕПЛОЮ! 🎉**

*Создано Claude Code для стабильной работы на Railway*