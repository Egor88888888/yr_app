"""AI helper using OpenRouter.
Functions: chat_complete, humanize, generate_content.
"""

import os
import aiohttp
import json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


async def generate_ai_response(messages: list[dict], model: str = "openai/gpt-4o-mini", max_tokens: int = 800) -> str:
    """Generate AI response using OpenRouter"""
    if not OPENROUTER_API_KEY:
        return "🤖 AI консультант временно недоступен. Обратитесь к администратору."

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            }

            data = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }

            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                elif response.status == 402:
                    # Payment Required - специальная обработка
                    print(f"⚠️ OpenRouter Payment Required (402) - баланс исчерпан")
                    return "🏠 🤖 AI временно недоступен (код 402) 💼 Для детальной консультации нажмите /start и заполните заявку."
                elif response.status == 429:
                    # Rate limit exceeded
                    print(f"⚠️ OpenRouter Rate Limit (429)")
                    return "🤖 AI временно перегружен. Попробуйте через несколько минут."
                else:
                    error_text = await response.text()
                    print(
                        f"⚠️ OpenRouter API error {response.status}: {error_text}")
                    return f"🤖 AI временно недоступен (код {response.status}) 💼 Для детальной консультации нажмите /start и заполните заявку."

    except Exception as e:
        print(f"AI Error: {e}")
        return "🤖 Произошла ошибка при обращении к AI консультанту. Попробуйте позже."


async def generate_post_content(topic: str) -> str:
    """Generate post content for channel"""
    messages = [
        {"role": "system", "content": "Ты юрист, пишешь полезные посты для Telegram канала. Используй эмодзи."},
        {"role": "user", "content": f"Напиши пост на тему: {topic}. Объем 300-400 символов."}
    ]
    return await generate_ai_response(messages)
