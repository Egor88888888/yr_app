"""AI helper using Azure OpenAI.
Functions: chat_complete, humanize, generate_content.
"""

import os
import aiohttp
import json

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY", "Fjaj2B7pc9tXPnLT4jY8Wv4Gl9435Ifw6ymyQ68OolKP0LVxBoqjJQQJ99BEACfhMk5XJ3w3AAAAACOGrsqR")
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT", "https://divan-mb68c0s7-swedencentral.cognitiveservices.azure.com")
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Fallback to legacy OpenRouter if Azure not configured
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


async def generate_ai_response(messages: list[dict], model: str = "gpt-4o-mini", max_tokens: int = 800) -> str:
    """Generate AI response using Azure OpenAI (primary) or OpenRouter (fallback)"""

    # Try Azure OpenAI first
    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
        try:
            return await _azure_openai_request(messages, model, max_tokens)
        except Exception as e:
            print(f"Azure OpenAI error: {e}")
            # Fallback to OpenRouter if Azure fails

    # Fallback to OpenRouter
    if OPENROUTER_API_KEY:
        try:
            return await _openrouter_request(messages, model, max_tokens)
        except Exception as e:
            print(f"OpenRouter error: {e}")

    return "🤖 AI консультант временно недоступен. Обратитесь к администратору."


async def _azure_openai_request(messages: list[dict], model: str, max_tokens: int) -> str:
    """Make request to Azure OpenAI"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "api-key": AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json",
        }

        # Azure OpenAI deployment name mapping
        deployment_map = {
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4o": "gpt-4o",
            "openai/gpt-4o-mini": "gpt-4o-mini",
            "openai/gpt-4o": "gpt-4o"
        }

        deployment_name = deployment_map.get(model, "gpt-4o-mini")

        url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment_name}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

        data = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                error_text = await response.text()
                print(
                    f"Azure OpenAI API error {response.status}: {error_text}")
                raise Exception(
                    f"Azure OpenAI failed with status {response.status}")


async def _openrouter_request(messages: list[dict], model: str, max_tokens: int) -> str:
    """Fallback request to OpenRouter"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": model if model.startswith("openai/") else f"openai/{model}",
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
                print(f"⚠️ OpenRouter Payment Required (402) - баланс исчерпан")
                raise Exception("OpenRouter payment required")
            elif response.status == 429:
                print(f"⚠️ OpenRouter Rate Limit (429)")
                raise Exception("OpenRouter rate limit exceeded")
            else:
                error_text = await response.text()
                print(
                    f"⚠️ OpenRouter API error {response.status}: {error_text}")
                raise Exception(
                    f"OpenRouter failed with status {response.status}")


async def generate_post_content(topic: str) -> str:
    """Generate post content for channel"""
    messages = [
        {"role": "system", "content": "Ты юрист, пишешь полезные посты для Telegram канала. Используй эмодзи."},
        {"role": "user", "content": f"Напиши пост на тему: {topic}. Объем 300-400 символов."}
    ]
    return await generate_ai_response(messages)
