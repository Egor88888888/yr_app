#!/usr/bin/env python3
"""
🎨 ДЕМОНСТРАЦИЯ НОВОГО ПРОФЕССИОНАЛЬНОГО ДИЗАЙНА ПОСТОВ
"""

import asyncio
from bot.services.content_intelligence.post_generator import PostGenerator

async def demo_new_design():
    """Демонстрация новых элегантных шаблонов"""
    
    generator = PostGenerator()
    
    print("=" * 80)
    print("🎨 НОВЫЙ ЭЛЕГАНТНЫЙ ДИЗАЙН ПОСТОВ")
    print("=" * 80)
    
    # 1. Банковский прецедент
    print("\n1️⃣ БАНКОВСКИЙ ПРЕЦЕДЕНТ:")
    print("-" * 50)
    banking_post = await generator.create_banking_precedent_post()
    print(banking_post)
    
    print("\n" + "=" * 80)
    
    # 2. Потребительское право
    print("\n2️⃣ ПОТРЕБИТЕЛЬСКОЕ ПРАВО:")
    print("-" * 50)
    consumer_post = await generator.generate_case_post('consumer_protection')
    print(consumer_post)
    
    print("\n" + "=" * 80)
    
    # 3. Трудовое право
    print("\n3️⃣ ТРУДОВОЕ ПРАВО:")
    print("-" * 50)
    labor_post = await generator.generate_case_post('labor_law')
    print(labor_post)
    
    print("\n" + "=" * 80)
    
    # 4. Семейное право
    print("\n4️⃣ СЕМЕЙНОЕ ПРАВО:")
    print("-" * 50)
    family_post = await generator.generate_case_post('family_law')
    print(family_post)
    
    print("\n" + "=" * 80)
    print("✨ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(demo_new_design())