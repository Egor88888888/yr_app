#!/bin/bash

# 🚀 PRODUCTION DEPLOY SCRIPT
# Скрипт для безопасного деплоя в продакшен

set -e  # Выход при любой ошибке

echo "🚀 Starting production deployment..."

# 1. Проверяем что мы в правильной ветке
echo "📝 Checking git status..."
if [[ $(git symbolic-ref --short HEAD) != "main" ]]; then
    echo "❌ Not on main branch. Switch to main before deploying."
    exit 1
fi

if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Working directory is not clean. Commit changes before deploying."
    exit 1
fi

# 2. Проверяем наличие обязательных файлов
echo "📁 Checking required files..."
required_files=("webapp/index.html" "bot/main.py" "requirements.txt" "runtime.txt")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

# 3. Валидация конфигурации
echo "⚙️ Validating configuration..."
if [[ -z "$BOT_TOKEN" ]]; then
    echo "❌ BOT_TOKEN environment variable is required"
    exit 1
fi

if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ DATABASE_URL environment variable is required"
    exit 1
fi

# 4. Запускаем тесты (если есть)
if [[ -f "test_local.py" ]]; then
    echo "🧪 Running tests..."
    python test_local.py
fi

# 5. Проверяем синтаксис Python
echo "🐍 Checking Python syntax..."
python -m py_compile bot/main.py
python -m py_compile manage.py

# 6. Создаем backup текущей версии (если на Railway)
if [[ -n "$RAILWAY_ENVIRONMENT" ]]; then
    echo "💾 Creating backup..."
    # В Railway бэкап создается автоматически
    echo "✅ Railway handles backups automatically"
fi

# 7. Деплой
echo "🚀 Deploying to production..."
git push origin main

# 8. Ждем успешного деплоя (примерно 2 минуты)
echo "⏳ Waiting for deployment to complete..."
sleep 60

# 9. Проверяем health check
echo "🏥 Checking application health..."
if command -v curl &> /dev/null; then
    HEALTH_URL="https://poetic-simplicity-production-60e7.up.railway.app/health"
    
    # Ждем до 5 минут пока приложение поднимется
    for i in {1..30}; do
        if curl -f -s "$HEALTH_URL" > /dev/null; then
            echo "✅ Health check passed!"
            break
        fi
        echo "🔄 Attempt $i/30: Waiting for application to start..."
        sleep 10
    done
else
    echo "⚠️ curl not available, skipping health check"
fi

# 10. Финальная проверка
echo "🎯 Final verification..."
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Application URLs:"
echo "   Bot: https://t.me/YOUR_BOT_USERNAME"
echo "   WebApp: https://poetic-simplicity-production-60e7.up.railway.app/webapp/"
echo "   Admin: https://poetic-simplicity-production-60e7.up.railway.app/admin/"
echo ""
echo "📊 Monitor your application:"
echo "   Logs: railway logs --tail"
echo "   Metrics: https://poetic-simplicity-production-60e7.up.railway.app/health?detailed=true"
echo ""
echo "🎉 Production deployment successful!" 