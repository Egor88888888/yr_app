#!/usr/bin/env python3
"""
Простой локальный тест бота
"""
import os
import sys

print("🧪 Запуск локального тестирования бота...")

# Добавляем переменные окружения для тестирования
os.environ["YOUR_BOT_TOKEN"] = "7852572614:AAHx9Twf6s-5G7qzq1Vczcl6LK4CKY2zLP0"
os.environ["ADMIN_CHAT_ID"] = "343688708"
os.environ["MY_RAILWAY_PUBLIC_URL"] = "localhost:8000"

print("✅ Переменные окружения установлены:")
print(f"   TOKEN: {os.environ.get('YOUR_BOT_TOKEN', 'НЕ НАЙДЕН')[:20]}...")
print(f"   ADMIN_CHAT_ID: {os.environ.get('ADMIN_CHAT_ID', 'НЕ НАЙДЕН')}")
print(f"   PUBLIC_URL: {os.environ.get('MY_RAILWAY_PUBLIC_URL', 'НЕ НАЙДЕН')}")

# Импортируем и запускаем бота
try:
    print("🚀 Запускаем бота...")
    from bot_final import main
    main()
except KeyboardInterrupt:
    print("\n🛑 Остановлено пользователем")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
