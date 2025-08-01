#!/usr/bin/env python3
"""
Unified AI Service - consolidates all AI functionality.
Replaces duplicate AI services with a single, comprehensive interface.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from bot.config.settings import (
    OPENAI_API_KEY, OPENROUTER_API_KEY, AZURE_OPENAI_API_KEY, 
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION
)

logger = logging.getLogger(__name__)

class AIProvider(Enum):
    """Available AI providers"""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    AZURE_OPENAI = "azure_openai"

class AIModel(Enum):
    """Available AI models"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_35_TURBO = "gpt-35-turbo"

@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: AIProvider
    model: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

@dataclass
class AIRequest:
    """Standardized AI request"""
    messages: List[Dict[str, str]]
    model: AIModel = AIModel.GPT_4O_MINI
    max_tokens: int = 800
    temperature: float = 0.7
    system_prompt: Optional[str] = None

class BaseAIProvider(ABC):
    """Base class for AI providers"""
    
    @abstractmethod
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass

class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT API provider - PRIMARY"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return bool(self.api_key)
    
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate response using OpenAI API"""
        import aiohttp
        import time
        
        if not self.is_available():
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=request.model.value,
                success=False,
                error="OpenAI API key not configured"
            )
        
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)
            
            # API request payload
            payload = {
                "model": request.model.value,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    response_time = time.time() - start_time
                    result = await response.json()
                    
                    if response.status == 200:
                        content = result["choices"][0]["message"]["content"].strip()
                        tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        
                        return AIResponse(
                            content=content,
                            provider=AIProvider.OPENAI,
                            model=request.model.value,
                            tokens_used=tokens_used,
                            response_time=response_time,
                            success=True
                        )
                    else:
                        error_msg = result.get("error", {}).get("message", f"HTTP {response.status}")
                        logger.error(f"OpenAI API error: {error_msg}")
                        
                        return AIResponse(
                            content="",
                            provider=AIProvider.OPENAI,
                            model=request.model.value,
                            response_time=response_time,
                            success=False,
                            error=error_msg
                        )
        
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"OpenAI API exception: {e}")
            
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=request.model.value,
                response_time=response_time,
                success=False,
                error=str(e)
            )

class AzureOpenAIProvider(BaseAIProvider):
    """Azure OpenAI provider"""
    
    def __init__(self):
        self.api_key = AZURE_OPENAI_API_KEY
        self.endpoint = AZURE_OPENAI_ENDPOINT
        self.api_version = AZURE_OPENAI_API_VERSION
        
        # Deployment mapping for Azure
        self.deployment_map = {
            AIModel.GPT_4O_MINI: "gpt-35-turbo",
            AIModel.GPT_4O: "gpt-35-turbo", 
            AIModel.GPT_35_TURBO: "gpt-35-turbo"
        }
    
    def is_available(self) -> bool:
        """Check if Azure OpenAI is available"""
        return bool(self.api_key and self.endpoint)
    
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate response using Azure OpenAI"""
        import aiohttp
        import time
        
        if not self.is_available():
            return AIResponse(
                content="",
                provider=AIProvider.AZURE_OPENAI,
                model=request.model.value,
                success=False,
                error="Azure OpenAI not configured"
            )
        
        start_time = time.time()
        
        try:
            deployment = self.deployment_map.get(request.model, "gpt-35-turbo")
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json",
            }
            
            url = f"{self.endpoint}/openai/deployments/{deployment}/chat/completions?api-version={self.api_version}"
            
            # Add system prompt if provided
            messages = request.messages.copy()
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            data = {
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        
                        response_time = time.time() - start_time
                        
                        return AIResponse(
                            content=content,
                            provider=AIProvider.AZURE_OPENAI,
                            model=deployment,
                            tokens_used=result.get("usage", {}).get("total_tokens"),
                            response_time=response_time,
                            success=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Azure OpenAI error {response.status}: {error_text}")
                        
                        return AIResponse(
                            content="",
                            provider=AIProvider.AZURE_OPENAI,
                            model=deployment,
                            response_time=time.time() - start_time,
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Azure OpenAI exception: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.AZURE_OPENAI,
                model=request.model.value,
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

class OpenRouterProvider(BaseAIProvider):
    """OpenRouter provider"""
    
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
    
    def is_available(self) -> bool:
        """Check if OpenRouter is available"""
        return bool(self.api_key)
    
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate response using OpenRouter"""
        import aiohttp
        import time
        
        if not self.is_available():
            return AIResponse(
                content="",
                provider=AIProvider.OPENROUTER,
                model=request.model.value,
                success=False,
                error="OpenRouter not configured"
            )
        
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            url = f"{self.base_url}/chat/completions"
            
            # Add system prompt if provided
            messages = request.messages.copy()
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            # Map model to OpenRouter format
            model_map = {
                AIModel.GPT_4O: "openai/gpt-4o",
                AIModel.GPT_4O_MINI: "openai/gpt-4o-mini",
                AIModel.GPT_35_TURBO: "openai/gpt-3.5-turbo"
            }
            
            data = {
                "model": model_map.get(request.model, "openai/gpt-4o-mini"),
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        
                        response_time = time.time() - start_time
                        
                        return AIResponse(
                            content=content,
                            provider=AIProvider.OPENROUTER,
                            model=data["model"],
                            tokens_used=result.get("usage", {}).get("total_tokens"),
                            response_time=response_time,
                            success=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter error {response.status}: {error_text}")
                        
                        return AIResponse(
                            content="",
                            provider=AIProvider.OPENROUTER,
                            model=data["model"],
                            response_time=time.time() - start_time,
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"OpenRouter exception: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.OPENROUTER,
                model=request.model.value,
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

class UnifiedAIService:
    """Unified AI service that manages multiple providers"""
    
    def __init__(self):
        self.providers = {
            AIProvider.OPENAI: OpenAIProvider(),
            AIProvider.OPENROUTER: OpenRouterProvider(),
            AIProvider.AZURE_OPENAI: AzureOpenAIProvider()
        }
        # Primary: OpenAI, Fallbacks: OpenRouter, Azure (temporary fallback mode)
        self.fallback_order = [AIProvider.OPENAI, AIProvider.OPENROUTER, AIProvider.AZURE_OPENAI]
        
        # Legal system prompts
        self.system_prompts = {
            "legal_expert": """Вы - опытный юрист, специализирующийся на российском праве. 
Отвечайте профессионально, точно и по существу. 
Приводите ссылки на нормативные акты, когда это уместно.
В конце ответа всегда предлагайте подать заявку для детальной консультации.""",
            
            "legal_consultation": """Вы - юридический консультант с большим опытом.
Анализируйте ситуацию клиента и давайте практические рекомендации.
Объясняйте сложные юридические концепции простым языком.
Всегда указывайте на важность профессиональной консультации для конкретного случая.""",
            
            "content_generator": """Вы - эксперт по созданию юридического контента.
Создавайте информативные, профессиональные и полезные материалы.
Используйте актуальную информацию и четкую структуру.
Материал должен быть понятен широкой аудитории."""
        }
    
    async def generate_legal_consultation(
        self, 
        user_message: str, 
        category: Optional[str] = None,
        model: AIModel = AIModel.GPT_4O_MINI
    ) -> AIResponse:
        """Generate legal consultation response"""
        
        system_prompt = self.system_prompts["legal_consultation"]
        
        if category:
            system_prompt += f"\n\nОсобое внимание уделите вопросам категории: {category}"
        
        messages = [{"role": "user", "content": user_message}]
        
        request = AIRequest(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        
        return await self._generate_with_fallback(request)
    
    async def generate_expert_response(
        self, 
        user_message: str,
        model: AIModel = AIModel.GPT_4O
    ) -> AIResponse:
        """Generate expert legal response"""
        
        messages = [{"role": "user", "content": user_message}]
        
        request = AIRequest(
            messages=messages,
            model=model,
            system_prompt=self.system_prompts["legal_expert"],
            max_tokens=1200,
            temperature=0.6
        )
        
        return await self._generate_with_fallback(request)
    
    async def generate_content(
        self, 
        topic: str, 
        content_type: str = "article",
        model: AIModel = AIModel.GPT_4O_MINI
    ) -> AIResponse:
        """Generate legal content for posts/articles"""
        
        content_prompts = {
            "article": f"Напишите информативную статью на тему: {topic}",
            "post": f"Создайте пост для социальных сетей на тему: {topic}",
            "news": f"Напишите новостную сводку по теме: {topic}"
        }
        
        user_message = content_prompts.get(content_type, content_prompts["article"])
        messages = [{"role": "user", "content": user_message}]
        
        request = AIRequest(
            messages=messages,
            model=model,
            system_prompt=self.system_prompts["content_generator"],
            max_tokens=800,
            temperature=0.8
        )
        
        return await self._generate_with_fallback(request)
    
    async def generate_simple_response(
        self, 
        messages: List[Dict[str, str]], 
        model: AIModel = AIModel.GPT_4O_MINI,
        max_tokens: int = 800
    ) -> AIResponse:
        """Generate simple AI response (backward compatibility)"""
        
        request = AIRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return await self._generate_with_fallback(request)
    
    async def _generate_with_fallback(self, request: AIRequest) -> AIResponse:
        """Generate response with provider fallback"""
        
        for provider_type in self.fallback_order:
            provider = self.providers[provider_type]
            
            if not provider.is_available():
                logger.debug(f"Provider {provider_type.value} not available, trying next")
                continue
            
            logger.info(f"Attempting generation with {provider_type.value}")
            response = await provider.generate_response(request)
            
            if response.success:
                logger.info(f"✅ Success with {provider_type.value}")
                return response
            else:
                logger.warning(f"❌ Failed with {provider_type.value}: {response.error}")
        
        # All providers failed
        return AIResponse(
            content="⚠️ AI консультант временно недоступен из-за неправильных API ключей.\n\n📞 Пожалуйста, свяжитесь с администратором для обновления конфигурации API ключей:\n- OpenAI API ключ недействителен\n- OpenRouter API ключ не настроен\n- Azure OpenAI не настроен\n\n🔧 Для решения проблемы администратору нужно:\n1. Проверить правильность OpenAI API ключа\n2. Установить корректные переменные окружения\n3. Перезапустить сервис",
            provider=AIProvider.OPENAI,  # Primary provider
            model=request.model.value,
            success=False,
            error="All AI providers failed - invalid API keys"
        )
    
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        return [
            provider_type for provider_type, provider in self.providers.items()
            if provider.is_available()
        ]
    
    def get_provider_status(self) -> Dict[str, bool]:
        """Get status of all providers"""
        return {
            provider_type.value: provider.is_available()
            for provider_type, provider in self.providers.items()
        }

# Global unified AI service instance
unified_ai_service = UnifiedAIService()

# ================ LEGACY COMPATIBILITY FUNCTIONS ================

async def generate_ai_response(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o-mini", 
    max_tokens: int = 800
) -> str:
    """Legacy compatibility function for generate_ai_response"""
    
    # Map string model to enum
    model_map = {
        "gpt-4o": AIModel.GPT_4O,
        "gpt-4o-mini": AIModel.GPT_4O_MINI,
        "gpt-35-turbo": AIModel.GPT_35_TURBO,
        "openai/gpt-4o": AIModel.GPT_4O,
        "openai/gpt-4o-mini": AIModel.GPT_4O_MINI
    }
    
    ai_model = model_map.get(model, AIModel.GPT_4O_MINI)
    
    response = await unified_ai_service.generate_simple_response(
        messages=messages,
        model=ai_model,
        max_tokens=max_tokens
    )
    
    return response.content

async def generate_post_content(topic: str) -> str:
    """Legacy compatibility function for post content generation"""
    response = await unified_ai_service.generate_content(
        topic=topic,
        content_type="post"
    )
    return response.content

async def generate_expert_content(user_message: str, category: str = None) -> str:
    """Legacy compatibility function for expert content"""
    response = await unified_ai_service.generate_legal_consultation(
        user_message=user_message,
        category=category,
        model=AIModel.GPT_4O
    )
    return response.content

# ================ HEALTH CHECK ================

async def ai_health_check() -> Dict[str, Any]:
    """Comprehensive AI service health check"""
    status = unified_ai_service.get_provider_status()
    available = unified_ai_service.get_available_providers()
    
    return {
        "status": "healthy" if available else "unavailable",
        "available_providers": [p.value for p in available],
        "provider_status": status,
        "total_providers": len(unified_ai_service.providers),
        "active_providers": len(available)
    }