#!/usr/bin/env python3
"""
Локальный тест AI ассистента перед деплоем в Railway
"""

import asyncio
import os
import sys
import logging

# Set environment variable BEFORE any imports
if not os.getenv("API_GPT"):
    os.environ["API_GPT"] = "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"

# Add bot directory to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.services.ai_unified import unified_ai_service

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ai_assistant():
    """Тест AI ассистента"""
    print("🔧 Тестирование AI ассистента...")
    
    # Check environment variables
    api_key = os.getenv("API_GPT")
    if not api_key:
        print("❌ Переменная API_GPT не найдена")
        return False
    
    print(f"✅ OpenAI API ключ найден: {api_key[:20]}...")
    
    # Test questions
    test_questions = [
        "Как подать на развод?",
        "Что такое наследство?", 
        "Как защитить права потребителя?"
    ]
    
    all_tests_passed = True
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🧪 Тест {i}: {question}")
        
        try:
            ai_response = await unified_ai_service.generate_legal_consultation(
                user_message=question,
                category="Общие вопросы"
            )
            response = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
            
            if response and len(response) > 50:
                print(f"✅ Тест {i} УСПЕШЕН")
                print(f"📝 Ответ (первые 100 символов): {response[:100]}...")
            else:
                print(f"❌ Тест {i} ПРОВАЛЕН - короткий ответ: {response}")
                all_tests_passed = False
                
        except Exception as e:
            print(f"❌ Тест {i} ПРОВАЛЕН - ошибка: {e}")
            all_tests_passed = False
    
    return all_tests_passed

async def main():
    """Main test function"""
    print("🤖 Локальное тестирование AI ассистента")
    print("=" * 50)
    
    # Environment variable already set before imports
    
    # Test AI
    success = await test_ai_assistant()
    
    if success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! AI ассистент готов к деплою.")
        return True
    else:
        print("\n💥 ТЕСТЫ ПРОВАЛЕНЫ! НЕ ДЕПЛОИТЬ!")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)