"""AI helper using OpenAI GPT API as primary with Azure fallback.
Functions: chat_complete, humanize, generate_content.
PRIMARY: OpenAI GPT API, FALLBACK: Azure OpenAI
"""

import os
import aiohttp
import json

# OpenAI Configuration - PRIMARY
OPENAI_API_KEY = os.getenv("API_GPT")

# Azure OpenAI Configuration - FALLBACK
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")


async def generate_ai_response(messages: list[dict], model: str = "gpt-4o-mini", max_tokens: int = 800) -> str:
    """Generate AI response using OpenAI as primary, Azure as fallback"""

    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            return await _openai_request(messages, model, max_tokens)
        except Exception as e:
            print(f"❌ OpenAI error: {e}")
    
    # Fallback to Azure OpenAI
    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
        try:
            return await _azure_openai_request(messages, model, max_tokens)
        except Exception as e:
            print(f"❌ Azure OpenAI error: {e}")
            return "🤖 AI консультант временно недоступен. Проверьте настройки OpenAI API."

    return "🤖 OpenAI API не настроен. Обратитесь к администратору."


async def _openai_request(messages: list[dict], model: str, max_tokens: int) -> str:
    """Make request to OpenAI API"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                error_text = await response.text()
                print(f"❌ OpenAI API error {response.status}: {error_text}")
                raise Exception(f"OpenAI API error: {response.status}")


async def _azure_openai_request(messages: list[dict], model: str, max_tokens: int) -> str:
    """Make request to Azure OpenAI - ОБНОВЛЕННЫЙ MAPPING"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "api-key": AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json",
        }

        # ОБНОВЛЕННЫЙ Azure OpenAI deployment mapping - используем доступные deployments
        deployment_map = {
            "gpt-4o-mini": "gpt-35-turbo",          # используем gpt-35-turbo  
            "gpt-4o": "gpt-35-turbo",              # fallback на gpt-35-turbo
            "gpt-35-turbo": "gpt-35-turbo",        # прямое соответствие
            "gpt-4.1": "gpt-35-turbo",             # fallback на gpt-35-turbo
            "openai/gpt-4o-mini": "gpt-35-turbo",  # fallback
            "openai/gpt-4o": "gpt-35-turbo"        # fallback
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
