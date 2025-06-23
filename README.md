# Юридический Центр - Telegram Bot

Полнофункциональный Telegram бот для юридических услуг с веб-приложением, онлайн оплатой и CRM интеграцией.

## 🚀 Возможности

- **12 категорий юридических услуг**: семейное право, наследство, трудовые споры, жилищные вопросы, банкротство, налоги, административные дела, арбитраж, защита прав потребителей, миграция, уголовные дела
- **Telegram Mini App** для подачи заявок с многошаговой формой
- **AI консультант** на базе OpenRouter (GPT-4)
- **Онлайн оплата** через CloudPayments
- **CRM интеграция** с Google Sheets
- **Админ панель** для управления заявками
- **Автопостинг** юридического контента в канал

## 📦 Установка

### 1. Клонирование репозитория

```bash
git clone <repository>
cd yr_app
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env и заполните все переменные
```

### 5. Инициализация базы данных

```bash
python3 manage.py init_db
```

## 🔧 Конфигурация

### Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен и добавьте в `BOT_TOKEN`
3. Узнайте свой chat_id и добавьте в `ADMIN_CHAT_ID`

### Railway PostgreSQL

1. Создайте проект на [Railway](https://railway.app)
2. Добавьте PostgreSQL
3. Скопируйте `DATABASE_URL` в переменные окружения

### Google Sheets

1. Создайте сервисный аккаунт в Google Cloud Console
2. Включите Google Sheets API
3. Скачайте JSON ключ и добавьте в `GOOGLE_SHEETS_CREDS_JSON`
4. Создайте таблицу и добавьте ID в `GOOGLE_SHEET_ID`

### CloudPayments

1. Зарегистрируйтесь на [CloudPayments](https://cloudpayments.ru)
2. Получите Public ID и Secret Key
3. Добавьте в соответствующие переменные

### OpenRouter (опционально)

1. Получите API ключ на [OpenRouter](https://openrouter.ai)
2. Добавьте в `OPENROUTER_API_KEY`

## 🚀 Запуск

### Локально

```bash
python3 -m bot.main
```

### На Railway

```bash
git push
# Railway автоматически развернет приложение
```

## 📱 Использование

### Для пользователей

1. Откройте бота в Telegram
2. Нажмите /start
3. Используйте кнопку меню для подачи заявки
4. Или задайте вопрос прямо в чате

### Для администраторов

1. Используйте команду /admin
2. Управляйте заявками, просматривайте статистику
3. Настраивайте автопостинг

## 📂 Структура проекта

```
yr_app/
├── bot/
│   ├── handlers/      # Обработчики команд
│   ├── services/      # Сервисы (БД, AI, оплата)
│   ├── jobs/          # Фоновые задачи
│   └── main.py        # Точка входа
├── webapp/            # Telegram Mini App
│   ├── index.html
│   ├── main.js
│   └── styles.css
├── alembic/           # Миграции БД
├── manage.py          # Утилиты управления
└── requirements.txt   # Зависимости
```

## 🛠 Команды управления

```bash
# Инициализация БД
python3 manage.py init_db

# Создание миграции
alembic revision --autogenerate -m "description"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

## 📊 База данных

### Основные модели:

- **User** - пользователи бота
- **Category** - категории юридических услуг
- **Application** - заявки клиентов
- **Payment** - платежи
- **Admin** - администраторы системы
- **Log** - логи действий

## 🔐 Безопасность

- Все чувствительные данные хранятся в переменных окружения
- Используется HTTPS для webhook
- Платежи обрабатываются через защищенный API CloudPayments
- Доступ к админ панели ограничен по chat_id

## 📈 Мониторинг

- Логи доступны в Railway Dashboard
- Статистика заявок в админ панели
- Google Sheets для внешней аналитики

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи в Railway
2. Убедитесь, что все переменные окружения установлены
3. Проверьте доступность внешних сервисов (Google, CloudPayments)

## 📝 Лицензия

Proprietary - Все права защищены
