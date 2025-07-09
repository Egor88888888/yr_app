#!/usr/bin/env python3
"""
🔧 ENHANCED AI PRODUCTION DIAGNOSTICS
Тестирует все компоненты Enhanced AI в production
"""

import asyncio
import json
import logging
import os
import traceback
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_ai():
    """Полная диагностика Enhanced AI"""
    print("🔧 ENHANCED AI PRODUCTION DIAGNOSTICS")
    print("=" * 50)

    # 1. Environment check
    print("\n📋 1. ENVIRONMENT CHECK")
    env_vars = [
        "DATABASE_URL",
        "OPENROUTER_API_KEY",
        "BOT_TOKEN",
        "RAILWAY_ENVIRONMENT"
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(
                f"✅ {var}: {'*' * 10}{value[-4:] if len(value) > 4 else value}")
        else:
            print(f"❌ {var}: NOT SET")

    # 2. Database connectivity
    print("\n🗄️ 2. DATABASE CONNECTIVITY")
    try:
        from bot.services.db import async_sessionmaker, init_db
        from sqlalchemy import text

        await init_db()

        async with async_sessionmaker() as session:
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection: OK")
    except Exception as e:
        print(f"❌ Database connection: {e}")
        return False

    # 3. AI service test
    print("\n🤖 3. BASIC AI SERVICE TEST")
    try:
        from bot.services.ai import generate_ai_response

        messages = [
            {"role": "system", "content": "Answer briefly."},
            {"role": "user", "content": "What is 2+2?"}
        ]

        response = await generate_ai_response(messages)
        print(f"✅ Basic AI response: {response[:50]}...")
    except Exception as e:
        print(f"❌ Basic AI service: {e}")
        traceback.print_exc()

    # 4. Enhanced AI manager import test
    print("\n🚀 4. ENHANCED AI IMPORT TEST")
    try:
        from bot.services.ai_enhanced.core.ai_manager import AIEnhancedManager
        print("✅ Enhanced AI Manager import: OK")

        manager = AIEnhancedManager()
        print("✅ Enhanced AI Manager creation: OK")
    except Exception as e:
        print(f"❌ Enhanced AI Manager import: {e}")
        traceback.print_exc()
        return False

    # 5. Enhanced AI initialization test
    print("\n⚡ 5. ENHANCED AI INITIALIZATION TEST")
    try:
        await manager.initialize()
        print("✅ Enhanced AI initialization: OK")
        print(f"✅ Manager initialized state: {manager._initialized}")
    except Exception as e:
        print(f"❌ Enhanced AI initialization: {e}")
        traceback.print_exc()
        return False

    # 6. Enhanced AI components health check
    print("\n💊 6. ENHANCED AI HEALTH CHECK")
    try:
        health = await manager.health_check()
        print(f"✅ Health check status: {health.get('status')}")

        components = health.get('components', {})
        for name, status in components.items():
            component_status = status.get('status', 'unknown')
            emoji = "✅" if component_status == "ok" else "❌"
            print(f"{emoji} {name}: {component_status}")
    except Exception as e:
        print(f"❌ Enhanced AI health check: {e}")
        traceback.print_exc()

    # 7. Enhanced AI test response
    print("\n🧠 7. ENHANCED AI RESPONSE TEST")
    try:
        test_message = "Как правильно развестись в России?"
        response = await manager.generate_response(
            user_id=12345,
            message=test_message
        )
        print(f"✅ Enhanced AI response length: {len(response)} chars")
        print(f"✅ Response preview: {response[:100]}...")

        # Check if it's not fallback message
        if "временно недоступен" in response:
            print("⚠️ WARNING: Enhanced AI returned fallback message!")
            return False
        else:
            print("✅ Enhanced AI response: WORKING")

    except Exception as e:
        print(f"❌ Enhanced AI response generation: {e}")
        traceback.print_exc()
        return False

    # 8. Test fallback scenario
    print("\n🔄 8. FALLBACK TEST")
    try:
        # Create uninitialized manager to test fallback
        fallback_manager = AIEnhancedManager()
        fallback_manager._initialized = False

        # Temporarily break something to trigger fallback
        original_openrouter = os.environ.get('OPENROUTER_API_KEY')
        os.environ['OPENROUTER_API_KEY'] = 'invalid_key'

        fallback_response = await fallback_manager._fallback_response(
            "test message", "test error"
        )

        # Restore original key
        if original_openrouter:
            os.environ['OPENROUTER_API_KEY'] = original_openrouter

        print(f"✅ Fallback response: {fallback_response[:50]}...")

    except Exception as e:
        print(f"❌ Fallback test: {e}")
        traceback.print_exc()

    print("\n🎉 ENHANCED AI DIAGNOSTICS COMPLETED")
    return True


async def test_telegram_integration():
    """Test telegram bot integration"""
    print("\n📱 TELEGRAM INTEGRATION TEST")

    try:
        from bot.main import ai_enhanced_manager

        if ai_enhanced_manager is None:
            print("❌ Global ai_enhanced_manager is None")
            return False

        if not ai_enhanced_manager._initialized:
            print("❌ Global ai_enhanced_manager not initialized")
            return False

        print("✅ Global Enhanced AI manager: OK")
        return True

    except Exception as e:
        print(f"❌ Telegram integration test: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostics"""
    try:
        print("🚀 Starting Enhanced AI Production Diagnostics...")

        # Test Enhanced AI
        enhanced_ai_ok = await test_enhanced_ai()

        # Test Telegram integration
        telegram_ok = await test_telegram_integration()

        print("\n" + "=" * 50)
        print("📊 FINAL RESULTS:")
        print(f"Enhanced AI: {'✅ OK' if enhanced_ai_ok else '❌ FAILED'}")
        print(f"Telegram Integration: {'✅ OK' if telegram_ok else '❌ FAILED'}")

        if enhanced_ai_ok and telegram_ok:
            print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        else:
            print("\n⚠️ ISSUES DETECTED - CHECK LOGS ABOVE")

    except Exception as e:
        print(f"❌ Diagnostics failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
