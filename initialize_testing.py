"""
🧪 PRODUCTION TESTING INITIALIZATION
Инициализация хэндлеров продакшн тестирования
"""

from bot.handlers.production_testing import register_production_testing_handlers


def initialize_production_testing(application):
    """Инициализация хэндлеров продакшн тестирования"""
    try:
        register_production_testing_handlers(application)
        print("✅ Production testing handlers registered")
        return True
    except Exception as e:
        print(f"⚠️ Could not register production testing handlers: {e}")
        return False


if __name__ == "__main__":
    print("This module should be imported, not run directly")
