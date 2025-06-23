# 🚀 Настройка Юридического Центра - Telegram Bot

## Быстрый старт

### 1. Создание бота в Telegram

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Выберите имя и username для бота
4. Сохраните полученный **BOT_TOKEN**

### 2. Настройка Railway

1. Зайдите на [railway.app](https://railway.app)
2. Подключите GitHub репозиторий
3. Добавьте PostgreSQL сервис
4. Настройте переменные окружения:

#### Обязательные переменные:

```
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_CHAT_ID=ваш_chat_id (получить можно у @userinfobot)
RAILWAY_PUBLIC_DOMAIN=автоматически_заполнится
DATABASE_URL=автоматически_заполнится_от_PostgreSQL
PORT=8080
```

#### Опциональные переменные:

```
OPENROUTER_API_KEY=ключ_для_AI_консультаций
CLOUDPAYMENTS_PUBLIC_ID=для_онлайн_оплаты
CLOUDPAYMENTS_SECRET_KEY=для_онлайн_оплаты
GOOGLE_SHEETS_CREDS_JSON=для_CRM_интеграции
GOOGLE_SHEET_ID=ID_таблицы_для_лидов
MAILGUN_API_KEY=для_email_уведомлений
SMS_RU_API_KEY=для_SMS_уведомлений
CHANNEL_ID=@ваш_канал_для_автопостинга
```

### 3. Настройка Google Sheets (опционально)

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com)
2. Создайте новый проект
3. Включите Google Sheets API
4. Создайте сервисный аккаунт
5. Скачайте JSON ключ
6. Добавьте JSON в переменную `GOOGLE_SHEETS_CREDS_JSON`
7. Создайте Google Sheet и добавьте ID в `GOOGLE_SHEET_ID`

### 4. Настройка платежей (опционально)

1. Зарегистрируйтесь на [CloudPayments](https://cloudpayments.ru)
2. Получите Public ID и Secret Key
3. Добавьте в переменные окружения

### 5. Запуск

После настройки переменных бот автоматически развернется на Railway.

## Проверка работы

### WebApp (Mini-App)

URL: `https://your-app.railway.app/webapp/`

Должен открываться красивый интерфейс из 4 экранов:

1. ✅ Выбор категории (12 блоков с прокруткой)
2. ✅ Описание проблемы + загрузка файлов
3. ✅ Контакты + способ связи
4. ✅ Проверка данных + отправка

### Telegram Bot

1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Проверьте кнопку меню "📝 Подать заявку"
4. Отправьте любой текст для AI консультации

### Админ панель

1. Отправьте боту `/admin`
2. Должны появиться кнопки управления
3. Проверьте просмотр заявок и статистику

## Устранение проблем

### Бот не отвечает

- ✅ Проверьте BOT_TOKEN
- ✅ Убедитесь что Railway приложение запущено
- ✅ Проверьте логи в Railway Dashboard

### WebApp не открывается

- ✅ Проверьте RAILWAY_PUBLIC_DOMAIN
- ✅ Убедитесь что /webapp/ доступен по HTTPS
- ✅ Проверьте, что файлы webapp/\* загружены

### База данных

- ✅ PostgreSQL должен быть подключен в Railway
- ✅ DATABASE_URL должен быть автоматически установлен
- ✅ Таблицы создаются автоматически при первом запуске

### Файлы не загружаются

- ✅ Проверьте размер файлов (макс. 10MB)
- ✅ Форматы: PDF, DOC, JPG, PNG
- ✅ Максимум 5 файлов

## Локальное тестирование

```bash
# Клонировать репозиторий
git clone https://github.com/your-repo/yr_app.git
cd yr_app

# Установить зависимости
pip install -r requirements.txt

# Запустить локальный тест
python3 test_local.py
```

Откройте http://localhost:8080/webapp/ для проверки интерфейса.

## Архитектура

```
yr_app/
├── bot/
│   ├── main.py              # Основной файл бота
│   ├── services/
│   │   ├── db.py           # Модели базы данных
│   │   ├── sheets.py       # Google Sheets интеграция
│   │   ├── pay.py          # CloudPayments
│   │   ├── ai.py           # OpenRouter AI
│   │   └── notifications.py # Email/SMS уведомления
├── webapp/
│   ├── index.html          # WebApp интерфейс
│   ├── main.js             # Логика формы
│   └── styles.css          # Стили
├── alembic/                # Миграции БД
└── requirements.txt        # Зависимости Python
```

## Возможности

✅ **12 категорий юридических услуг**
✅ **4-шаговая форма с загрузкой файлов**
✅ **AI консультант (OpenRouter)**
✅ **Онлайн оплата (CloudPayments)**
✅ **CRM интеграция (Google Sheets)**
✅ **Email/SMS уведомления**
✅ **UTM отслеживание**
✅ **Роли админов (оператор/юрист/суперадмин)**
✅ **Автопостинг в канал**
✅ **Детальная статистика**

Система готова к продакшену! 🎉
