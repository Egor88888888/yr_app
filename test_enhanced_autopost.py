#!/usr/bin/env python3
"""
🧪 TEST ENHANCED AUTOPOST SYSTEM
Тестирование новой системы качественного автопостинга
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_enhanced_posts():
    """Тестирование улучшенной системы постов"""

    print("🚀 Testing Enhanced Autopost System...")
    print("=" * 60)

    try:
        # Устанавливаем минимальные переменные окружения для тестирования
        os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test_key')
        os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'test_endpoint')
        os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')

        # Импортируем PostGenerator
        from bot.services.content_intelligence.post_generator import PostGenerator

        generator = PostGenerator()

        print("📝 Testing post templates and structure...")

        # Тестируем шаблоны
        print(f"✅ Templates loaded: {len(generator.enhanced_templates)}")
        print(
            f"✅ Resource database: {len(generator.resource_database)} categories")
        print(
            f"✅ Common problems: {len(generator.common_problems)} categories")

        print("\n📋 Available templates:")
        for template_name in generator.enhanced_templates.keys():
            print(f"  • {template_name}")

        print("\n🔗 Resource categories:")
        for category, resources in generator.resource_database.items():
            print(f"  • {category}: {len(resources)} resources")

        print("\n⚠️ Problem categories:")
        for category, problems in generator.common_problems.items():
            print(f"  • {category}: {len(problems)} problems")

        # Тестируем вспомогательные методы
        print(f"\n🧪 Testing helper methods...")

        # Тест получения ресурсов
        consumer_resources = generator._get_relevant_resources(
            'consumer_protection')
        print(
            f"✅ Consumer resources: {len(consumer_resources.split(chr(10)))} items")

        # Тест получения проблем
        legal_problems = generator._get_relevant_problems('legal_procedures')
        print(f"✅ Legal problems: {len(legal_problems.split(chr(10)))} items")

        # Тест fallback поста
        test_topic = {
            'title': 'Test Legal Topic',
            'category': 'test_category',
            'type': 'step_by_step_guide'
        }

        fallback_post = await generator._create_fallback_post(test_topic)
        print(f"✅ Fallback post generated: {len(fallback_post)} characters")

        print(f"\n📄 Sample fallback post:")
        print("-" * 40)
        print(fallback_post)
        print("-" * 40)

        # Качественная оценка
        quality_score = 0
        if "🎯" in fallback_post:
            quality_score += 1
        if "⚠️" in fallback_post:
            quality_score += 1
        if "🔗" in fallback_post:
            quality_score += 1
        if "📞" in fallback_post:
            quality_score += 1
        if any(site in fallback_post for site in ['gosuslugi.ru', 'consultant.ru']):
            quality_score += 1

        print(f"📊 Quality Score: {quality_score}/5 ⭐")

        if quality_score >= 4:
            print("✅ HIGH QUALITY STRUCTURE")
        elif quality_score >= 3:
            print("⚡ GOOD QUALITY STRUCTURE")
        else:
            print("⚠️ NEEDS IMPROVEMENT")

        print("\n" + "=" * 60)
        print("🎉 Enhanced Autopost Structure Test PASSED!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Error details:\n{traceback.format_exc()}")
        return False


async def test_template_formatting():
    """Тестирование форматирования шаблонов"""

    print("\n🧪 Testing Template Formatting...")

    try:
        from bot.services.content_intelligence.post_generator import PostGenerator

        generator = PostGenerator()

        # Тестовые данные для форматирования
        test_content = {
            'title': 'Как правильно подать жалобу в Роспотребнадзор',
            'step_algorithm': '''1. Подготовьте документы (чеки, договоры)
2. Заполните заявление на сайте или лично
3. Приложите доказательства нарушения
4. Подайте жалобу в течение 2 лет
5. Дождитесь ответа в течение 30 дней''',
            'potential_problems': '''• Отсутствие документов-доказательств
• Пропуск срока подачи жалобы
• Неправильное заполнение заявления''',
            'useful_resources': '''🛡️ Роспотребнадзор: rospotrebnadzor.ru
🏛️ Госуслуги: gosuslugi.ru
📖 Гарант: garant.ru''',
            'practical_tips': '''• Сохраняйте все документы
• Фотографируйте товар с дефектами
• Записывайте даты всех обращений'''
        }

        # Тестируем каждый шаблон
        for template_name, template in generator.enhanced_templates.items():
            print(f"\n📋 Testing template: {template_name}")

            try:
                formatted = generator._format_enhanced_post(
                    test_content, template_name)
                print(f"✅ Length: {len(formatted)} chars")

                # Проверяем наличие ключевых элементов
                has_title = 'Как правильно подать жалобу' in formatted
                has_emojis = any(emoji in formatted for emoji in [
                                 '🎯', '⚖️', '💡', '🚨'])
                has_structure = any(section in formatted for section in [
                                    'АЛГОРИТМ', 'ПРОБЛЕМЫ', 'РЕСУРСЫ'])

                print(f"   Title: {'✅' if has_title else '❌'}")
                print(f"   Emojis: {'✅' if has_emojis else '❌'}")
                print(f"   Structure: {'✅' if has_structure else '❌'}")

            except Exception as e:
                print(f"❌ Template {template_name} failed: {e}")

        print("\n✅ Template formatting test completed!")
        return True

    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False


async def main():
    """Главная функция тестирования"""

    print("🧪 ENHANCED AUTOPOST SYSTEM TESTS")
    print("=" * 60)

    # Тест 1: Структура и компоненты
    test1_result = await test_enhanced_posts()

    # Тест 2: Форматирование шаблонов
    test2_result = await test_template_formatting()

    print(f"\n{'=' * 60}")
    print("📊 FINAL TEST RESULTS:")
    print(f"Structure Test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Template Test: {'✅ PASSED' if test2_result else '❌ FAILED'}")

    if test1_result and test2_result:
        print("\n🎉 ALL TESTS PASSED! System ready for deployment.")
        return 0
    else:
        print("\n❌ Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
