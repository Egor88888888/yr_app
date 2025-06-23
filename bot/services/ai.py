"""AI helper using OpenRouter.
Functions: chat_complete, humanize, generate_content.
"""

import os
import openai

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY:
    openai.api_key = OPENROUTER_API_KEY
    openai.api_base = "https://openrouter.ai/api/v1"


async def generate_ai_response(messages: list[dict], model: str = "gpt-3.5-turbo", max_tokens: int = 800) -> str:
    """Generate AI response using OpenRouter"""
    if not OPENROUTER_API_KEY:
        return "AI временно недоступен"

    try:
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка AI: {str(e)}"


async def generate_post_content(topic: str) -> str:
    """Generate post content for channel"""
    messages = [
        {"role": "system", "content": "Ты юрист, пишешь полезные посты для Telegram канала. Используй эмодзи."},
        {"role": "user", "content": f"Напиши пост на тему: {topic}. Объем 300-400 символов."}
    ]
    return await generate_ai_response(messages)
