#!/usr/bin/env python3
"""
Скрипт для генерации Telethon StringSession для пользователя.
Используйте этот скрипт локально, чтобы сгенерировать сессию для доступа к внешним каналам.

1. Установите: pip install telethon
2. Запустите: python session_gen.py
3. Введите номер телефона и код подтверждения
4. Скопируйте полученную STRING_SESSION в переменную окружения TELETHON_USER_SESSION в Railway
"""

import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Читаем из переменных окружения или используем значения по умолчанию
API_ID = int(os.getenv("API_ID", 15185317))
API_HASH = os.getenv("API_HASH", "e2f465afb7dd25919332fe6bea1812c4")

print("🔐 Генерация пользовательской сессии Telethon")
print("Это нужно сделать ОДИН РАЗ локально, затем добавить в Railway Variables")
print()

try:
    with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        print("✅ Сессия успешно создана!")
        print()
        print("🔑 TELETHON_USER_SESSION =", client.session.save())
        print()
        print("📋 Скопируйте эту строку и добавьте как переменную TELETHON_USER_SESSION в Railway")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    print("Убедитесь что API_ID и API_HASH корректные")
