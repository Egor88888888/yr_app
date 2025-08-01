#!/usr/bin/env python3
"""
AI System Status Checker
Проверяет состояние всех AI провайдеров
"""
import os
import asyncio
from bot.services.ai_unified import unified_ai_service

async def main():
    print("🔍 ПРОВЕРКА СТАТУСА AI СИСТЕМЫ")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Переменные окружения:")
    api_keys = {
        "API_GPT (OpenAI)": os.getenv("API_GPT", "НЕ УСТАНОВЛЕН"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "НЕ УСТАНОВЛЕН"),
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY", "НЕ УСТАНОВЛЕН"),
    }
    
    for key, value in api_keys.items():
        if value != "НЕ УСТАНОВЛЕН":
            masked = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {key}: {masked}")
        else:
            print(f"❌ {key}: {value}")
    
    # Check provider status
    print(f"\n🤖 Статус провайдеров:")
    status = unified_ai_service.get_provider_status()
    for provider, available in status.items():
        icon = "✅" if available else "❌"
        print(f"{icon} {provider.upper()}: {'Доступен' if available else 'Недоступен'}")
    
    # Test AI functionality
    print(f"\n🧪 Тестирование AI функциональности:")
    try:
        response = await unified_ai_service.generate_legal_consultation(
            "Тестовый вопрос по трудовому праву",
            category="Трудовое право"
        )
        
        print(f"📊 Результат: {'Успешно' if response.success else 'Неудачно'}")
        print(f"🔧 Провайдер: {response.provider.value}")
        
        if response.success:
            print(f"📝 Ответ: {response.content[:100]}...")
            print("🎉 AI СИСТЕМА РАБОТАЕТ!")
        else:
            print(f"❌ Ошибка: {response.error}")
            print("🚨 AI СИСТЕМА НЕ РАБОТАЕТ!")
            
    except Exception as e:
        print(f"💥 Исключение при тестировании: {e}")
        print("🚨 AI СИСТЕМА НЕ РАБОТАЕТ!")
    
    print("\n" + "=" * 50)
    print("📞 Для исправления проблем:")
    print("1. Получите корректный OpenAI API ключ")
    print("2. Установите: export API_GPT='ваш_ключ'")
    print("3. Перезапустите сервис")

if __name__ == "__main__":
    asyncio.run(main())