#!/usr/bin/env python3
"""
Тест генерации элегантного контента через SMM систему
"""

import asyncio
from bot.services.smm.content_engine import AdvancedContentEngine, ContentType


async def demo_new_design():
    """Демонстрация новых элегантных шаблонов"""

    generator = AdvancedContentEngine()

    print("=" * 80)
    print("🎨 НОВЫЙ ЭЛЕГАНТНЫЙ ДИЗАЙН ПОСТОВ")
    print("=" * 80)

    # 1. Банковский прецедент (вирусный кейс)
    print("\n1️⃣ БАНКОВСКИЙ ПРЕЦЕДЕНТ:")
    print("-" * 50)
    banking_post = await generator.generate_optimized_content(
        audience_insights={},
        force_type=ContentType.VIRAL_CASE_STUDY
    )
    print(banking_post.text)

    print("\n" + "=" * 80)

    # 2. Потребительское право (история успеха)
    print("\n2️⃣ ПОТРЕБИТЕЛЬСКОЕ ПРАВО:")
    print("-" * 50)
    consumer_post = await generator.generate_optimized_content(
        audience_insights={},
        force_type=ContentType.CLIENT_SUCCESS_STORY
    )
    print(consumer_post.text)

    print("\n" + "=" * 80)

    # 3. Трудовое право (лайфхак)
    print("\n3️⃣ ТРУДОВОЕ ПРАВО:")
    print("-" * 50)
    labor_post = await generator.generate_optimized_content(
        audience_insights={},
        force_type=ContentType.LEGAL_LIFE_HACK
    )
    print(labor_post.text)

    print("\n" + "=" * 80)

    # 4. Провокационная тема
    print("\n4️⃣ ПРОВОКАЦИОННАЯ ТЕМА:")
    print("-" * 50)
    controversial_post = await generator.generate_optimized_content(
        audience_insights={},
        force_type=ContentType.CONTROVERSIAL_TOPIC
    )
    print(controversial_post.text)

    print("\n" + "=" * 80)
    print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_new_design())
