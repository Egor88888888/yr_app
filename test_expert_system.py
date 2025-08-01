#!/usr/bin/env python3
"""
🧪 ТЕСТИРОВАНИЕ ЭКСПЕРТНОЙ СИСТЕМЫ
Проверка работы мирового уровня юридического AI
"""

import asyncio
import logging
from bot.services.legal_expert_ai import world_class_legal_ai, LegalCase, LegalCategory, ConsultationType
from bot.services.professional_commenter import professional_commenter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_legal_consultation():
    """Тест юридической консультации"""
    print("🧪 ТЕСТИРОВАНИЕ ЮРИДИЧЕСКОЙ КОНСУЛЬТАЦИИ")
    print("=" * 60)
    
    test_cases = [
        {
            "description": "Меня незаконно уволили с работы без объяснения причин. Что делать?",
            "category": LegalCategory.LABOR_LAW,
            "consultation_type": ConsultationType.EXPRESS,
            "urgency": "high"
        },
        {
            "description": "Хочу подать на развод, есть ребенок и совместная квартира. Как правильно разделить имущество?",
            "category": LegalCategory.FAMILY_LAW,
            "consultation_type": ConsultationType.DETAILED,
            "urgency": "medium"
        },
        {
            "description": "СРОЧНО! Завтра суд по уголовному делу, нужна помощь адвоката!",
            "category": LegalCategory.CRIMINAL_LAW,
            "consultation_type": ConsultationType.EMERGENCY,
            "urgency": "emergency"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 ТЕСТ {i}: {test_case['category'].value.upper()}")
        print(f"📝 Вопрос: {test_case['description']}")
        
        # Создаем дело
        legal_case = LegalCase(
            user_id=12345,
            category=test_case["category"],
            consultation_type=test_case["consultation_type"],
            description=test_case["description"],
            urgency=test_case["urgency"],
            location="РФ",
            case_complexity="medium",
            documents_available=False
        )
        
        try:
            # Получаем консультацию
            advice = await world_class_legal_ai.analyze_legal_case(legal_case)
            
            print(f"\n✅ УСПЕШНО ПОЛУЧЕНА КОНСУЛЬТАЦИЯ:")
            print(f"📊 Правовой анализ: {advice.legal_analysis[:100]}...")
            print(f"⚖️ Правовые ссылки: {len(advice.legal_references)}")
            print(f"📋 Рекомендации: {len(advice.recommended_actions)}")
            print(f"💰 Стоимость: {advice.estimated_cost}")
            print(f"⏰ Сроки: {advice.timeline}")
            print(f"🎯 Продажи: {'Есть предложение' if advice.sales_offer else 'Нет предложения'}")
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 40)

async def test_professional_comments():
    """Тест профессиональных комментариев"""
    print("\n📝 ТЕСТИРОВАНИЕ ПРОФЕССИОНАЛЬНЫХ КОММЕНТАРИЕВ")
    print("=" * 60)
    
    test_posts = [
        {
            "content": "Можно ли уволить беременную сотрудницу за прогулы?",
            "topic": "Трудовое право"
        },
        {
            "content": "Новый закон о семейном насилии вступил в силу. Теперь можно получить защитный ордер за 24 часа.",
            "topic": "Семейное право - новости"
        },
        {
            "content": "Разбираем дело: предприниматель не заплатил налоги и получил штраф 1 млн рублей. Правомерно ли это?",
            "topic": "Налоговое право - разбор случая"
        },
        {
            "content": "Как правильно составить договор купли-продажи квартиры? Какие пункты обязательны?",
            "topic": "Недвижимость - инструкция"
        }
    ]
    
    for i, post in enumerate(test_posts, 1):
        print(f"\n🔍 ТЕСТ КОММЕНТАРИЯ {i}")
        print(f"📋 Пост: {post['content']}")
        print(f"🏷️ Тема: {post['topic']}")
        
        try:
            # Анализируем пост
            analysis = await professional_commenter.analyze_post(
                post["content"], 
                post["topic"]
            )
            
            print(f"\n📊 АНАЛИЗ ПОСТА:")
            print(f"   Тип: {analysis.post_type.value}")
            print(f"   Категория: {analysis.legal_category}")
            print(f"   Аудитория: {analysis.target_audience}")
            print(f"   Точность: {analysis.legal_accuracy}")
            print(f"   Пропуски: {len(analysis.missing_info)}")
            
            # Генерируем комментарий
            comment = await professional_commenter.generate_professional_comment(analysis)
            
            print(f"\n💬 ПРОФЕССИОНАЛЬНЫЙ КОММЕНТАРИЙ:")
            print(f"   Тон: {comment.tone.value}")
            print(f"   Ценность: {comment.value_added}")
            print(f"   Вовлеченность: {comment.engagement_level}")
            print(f"\n📝 ТЕКСТ КОММЕНТАРИЯ:")
            print(f"   {comment.content}")
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 40)

async def test_knowledge_base():
    """Тест базы знаний"""
    print("\n📚 ТЕСТИРОВАНИЕ БАЗЫ ЗНАНИЙ")
    print("=" * 60)
    
    from bot.services.legal_knowledge_base import legal_knowledge
    
    search_queries = [
        "договор",
        "алименты", 
        "увольнение",
        "мошенничество",
        "недвижимость"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Поиск: '{query}'")
        
        results = legal_knowledge.search_norms(query)
        print(f"   Найдено: {len(results)} норм")
        
        for result in results[:2]:
            print(f"   - {result.code} ст.{result.article}: {result.title}")
        
        if not results:
            print("   ❌ Ничего не найдено")

async def test_sales_integration():
    """Тест интеграции продаж"""
    print("\n💰 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ ПРОДАЖ")
    print("=" * 60)
    
    # Проверяем, что все консультации содержат продающие элементы
    test_case = LegalCase(
        user_id=12345,
        category=LegalCategory.BUSINESS_LAW,
        consultation_type=ConsultationType.STRATEGY,
        description="Как защитить бизнес от недобросовестных конкурентов?",
        urgency="medium",
        location="РФ"
    )
    
    try:
        advice = await world_class_legal_ai.analyze_legal_case(test_case)
        
        print("✅ ПРОВЕРКА ПРОДАЮЩИХ ЭЛЕМЕНТОВ:")
        print(f"   Есть предложение услуг: {'✅' if 'консультация' in advice.sales_offer.lower() else '❌'}")
        print(f"   Указаны цены: {'✅' if any(c.isdigit() for c in advice.sales_offer) else '❌'}")
        print(f"   Есть call-to-action: {'✅' if 'записаться' in advice.sales_offer.lower() or 'звоните' in advice.sales_offer.lower() else '❌'}")
        print(f"   Указаны преимущества: {'✅' if 'опыт' in advice.sales_offer.lower() or 'эксперт' in advice.sales_offer.lower() else '❌'}")
        
        print(f"\n💬 ПРОДАЮЩЕЕ ПРЕДЛОЖЕНИЕ:")
        print(f"   {advice.sales_offer}")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")

async def main():
    """Главная функция тестирования"""
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ ЭКСПЕРТНОЙ СИСТЕМЫ")
    print("=" * 80)
    
    try:
        await test_legal_consultation()
        await test_professional_comments()
        await test_knowledge_base()
        await test_sales_integration()
        
        print("\n🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())