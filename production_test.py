#!/usr/bin/env python3
"""
🔍 PRODUCTION BOT STATUS TEST

Simple script to test production bot health via HTTP requests.
Does not require local environment variables.
"""

import requests
import json
import time
from datetime import datetime

# Production URLs
BASE_URL = "https://poetic-simplicity-production-60e7.up.railway.app"
HEALTH_URL = f"{BASE_URL}/health"
WEBAPP_URL = f"{BASE_URL}/webapp/"
ADMIN_URL = f"{BASE_URL}/admin/"


def test_production_status():
    """Test production bot status"""

    print("🔍 PRODUCTION BOT STATUS TEST")
    print("=" * 40)
    print(f"⏰ Started: {datetime.now()}")
    print(f"🌐 Base URL: {BASE_URL}")

    # Test health endpoint
    print("\n🏥 HEALTH CHECK")
    print("-" * 20)

    try:
        response = requests.get(HEALTH_URL, timeout=10)
        print(f"✅ Health endpoint: {response.status_code}")

        if response.status_code == 200:
            try:
                health_data = response.json()
                print(f"📊 Status: {health_data.get('status', 'unknown')}")
                print(f"🤖 Bot: {health_data.get('bot_status', 'unknown')}")
                print(f"🗄️ Database: {health_data.get('database', 'unknown')}")

                # Enhanced AI status check
                if 'enhanced_ai' in health_data:
                    ai_status = health_data['enhanced_ai']
                    if ai_status.get('initialized'):
                        print("✅ Enhanced AI: INITIALIZED")
                        print(
                            f"   Health: {ai_status.get('health_status', 'unknown')}")
                        components = ai_status.get('components', {})
                        healthy = sum(1 for c in components.values()
                                      if c.get('status') == 'ok')
                        print(
                            f"   Components: {healthy}/{len(components)} healthy")
                    else:
                        print("❌ Enhanced AI: NOT INITIALIZED")
                        print(
                            f"   Error: {ai_status.get('error', 'Unknown error')}")
                else:
                    print("⚠️ Enhanced AI: Status not available")

            except json.JSONDecodeError:
                print(f"⚠️ Health response (text): {response.text[:200]}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Health endpoint unreachable: {e}")

    # Test webapp
    print("\n📱 WEBAPP CHECK")
    print("-" * 20)

    try:
        response = requests.get(WEBAPP_URL, timeout=10)
        print(f"✅ WebApp: {response.status_code}")

        # Проверяем наличие ключевых элементов (lenient)
        content = response.text.lower()
        key_terms = ["juridical", "center", "form", "js"]
        found_terms = sum(1 for term in key_terms if term in content)
        if found_terms >= 3:
            print("✅ WebApp content: Valid (lenient)")
        else:
            print("⚠️ WebApp content: Partial match")

    except requests.exceptions.RequestException as e:
        print(f"❌ WebApp unreachable: {e}")

    # Test admin endpoint
    print("\n👨‍💼 ADMIN CHECK")
    print("-" * 20)

    try:
        response = requests.get(ADMIN_URL, timeout=10)
        print(f"✅ Admin endpoint: {response.status_code}")

        if response.status_code == 200:
            if "admin" in response.text.lower() or "dashboard" in response.text.lower():
                print("✅ Admin content: Valid")
            else:
                print("⚠️ Admin content: Unexpected")
        else:
            print(f"❌ Admin failed: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Admin unreachable: {e}")

    # Test API stats if available
    print("\n📊 API STATS CHECK")
    print("-" * 20)

    try:
        stats_url = f"{BASE_URL}/api/admin/stats"
        response = requests.get(stats_url, timeout=10)
        print(f"✅ Stats endpoint: {response.status_code}")

        if response.status_code == 200:
            try:
                stats = response.json()
                print(f"📈 Total requests: {stats.get('total_requests', 0)}")
                print(f"⚡ Success rate: {stats.get('success_rate', 0):.1%}")
                print(f"🤖 AI requests: {stats.get('ai_requests', 0)}")

                # Enhanced AI specific stats
                if 'enhanced_ai' in stats:
                    ai_stats = stats['enhanced_ai']
                    print(
                        f"🧠 Enhanced AI requests: {ai_stats.get('requests', 0)}")
                    print(
                        f"💡 Enhanced AI success: {ai_stats.get('success_rate', 0):.1%}")

            except json.JSONDecodeError:
                print("⚠️ Stats response not JSON")

    except requests.exceptions.RequestException as e:
        print(f"❌ Stats endpoint unreachable: {e}")

    print(f"\n⏰ Test completed: {datetime.now()}")


def enhanced_ai_specific_test():
    """Specific Enhanced AI test"""

    print("\n🤖 ENHANCED AI SPECIFIC TEST")
    print("=" * 30)

    # Test Enhanced AI status endpoint if exists
    try:
        ai_status_url = f"{BASE_URL}/api/ai/status"
        response = requests.get(ai_status_url, timeout=10)

        if response.status_code == 200:
            try:
                ai_data = response.json()
                if ai_data.get('enhanced_ai_initialized'):
                    print("✅ Enhanced AI: Initialized via API")
                    print(f"   Health: {ai_data.get('health', 'unknown')}")
                else:
                    print("❌ Enhanced AI: Not initialized via API")
                    print(
                        f"   Fallback: {ai_data.get('using_fallback', 'unknown')}")
            except json.JSONDecodeError:
                print("⚠️ AI status response not JSON")
        else:
            print(f"⚠️ AI status endpoint: {response.status_code}")

    except requests.exceptions.RequestException:
        print("⚠️ No dedicated AI status endpoint")

    # Try to simulate AI chat test
    try:
        chat_url = f"{BASE_URL}/api/chat/test"
        test_data = {"message": "Тест Enhanced AI"}
        response = requests.post(chat_url, json=test_data, timeout=15)

        if response.status_code == 200:
            result = response.json()
            if "enhanced" in result.get("engine", "").lower():
                print("✅ Enhanced AI: Responding to requests")
            else:
                print("⚠️ AI responding but using fallback")
        else:
            print(f"⚠️ Chat test: {response.status_code}")

    except requests.exceptions.RequestException:
        print("⚠️ No chat test endpoint available")


if __name__ == "__main__":
    test_production_status()
    enhanced_ai_specific_test()

    print("\n💡 RECOMMENDATIONS:")
    print("1. If Enhanced AI shows as 'NOT INITIALIZED':")
    print("   - Check Railway logs for initialization errors")
    print("   - Verify database migration was applied")
    print("   - Check environment variables are set")
    print("\n2. If health endpoint fails:")
    print("   - Bot may be starting up (wait 2-3 minutes)")
    print("   - Check Railway deployment status")
    print("\n3. If Enhanced AI works:")
    print("   - Test via Telegram bot: /admin → AI Status")
    print("   - Monitor performance and analytics")
