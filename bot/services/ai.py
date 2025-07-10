"""AI helper using Azure OpenAI ONLY.
Functions: chat_complete, humanize, generate_content.
ТОЛЬКО AZURE OPENAI - OpenRouter полностью убран!
"""

import os
import aiohttp
import json

# Azure OpenAI Configuration - ТОЛЬКО AZURE!
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY", "Fjaj2B7pc9tXPnLT4jY8Wv4Gl9435Ifw6ymyQ68OolKP0LVxBoqjJQQJ99BEACfhMk5XJ3w3AAAAACOGrsqR")
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT", "https://divan-mb68c0s7-swedencentral.cognitiveservices.azure.com")
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")


async def generate_ai_response(messages: list[dict], model: str = "gpt-4o-mini", max_tokens: int = 800) -> str:
    """Generate AI response using ТОЛЬКО Azure OpenAI"""

    # ТОЛЬКО Azure OpenAI - без fallback на OpenRouter!
    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
        try:
            return await _azure_openai_request(messages, model, max_tokens)
        except Exception as e:
            print(f"❌ Azure OpenAI error: {e}")
            return "🤖 AI консультант временно недоступен. Проверьте настройки Azure OpenAI."

    return "🤖 Azure OpenAI не настроен. Обратитесь к администратору."


async def _azure_openai_request(messages: list[dict], model: str, max_tokens: int) -> str:
    """Make request to Azure OpenAI - ОБНОВЛЕННЫЙ MAPPING"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "api-key": AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json",
        }

        # ИСПРАВЛЕННЫЙ Azure OpenAI deployment mapping для ваших actual deployments
        deployment_map = {
            "gpt-4o-mini": "gpt-35-turbo",          # используем gpt-35-turbo
            "gpt-4o": "gpt-4.1",                   # используем gpt-4.1
            "gpt-35-turbo": "gpt-35-turbo",        # прямое соответствие
            "gpt-4.1": "gpt-4.1",                  # прямое соответствие
            "openai/gpt-4o-mini": "gpt-35-turbo",  # fallback
            "openai/gpt-4o": "gpt-4.1"             # fallback
        }

        deployment_name = deployment_map.get(
            model, "gpt-35-turbo")  # по умолчанию gpt-35-turbo

        print(
            f"🔧 Using Azure deployment: {deployment_name} for model: {model}")

        url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment_name}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

        data = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Azure OpenAI SUCCESS with {deployment_name}")
                return result["choices"][0]["message"]["content"].strip()
            else:
                error_text = await response.text()
                print(
                    f"❌ Azure OpenAI deployment {deployment_name} error {response.status}: {error_text}")
                raise Exception(
                    f"Azure OpenAI failed with status {response.status}")


async def generate_post_content(topic: str) -> str:
    """Generate post content for channel using Azure OpenAI"""
    messages = [
        {"role": "system", "content": "Ты юрист, пишешь полезные посты для Telegram канала. Используй эмодзи."},
        {"role": "user", "content": f"Напиши пост на тему: {topic}. Объем 300-400 символов."}
    ]
    return await generate_ai_response(messages)
