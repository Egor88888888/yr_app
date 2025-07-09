"""
📝 POST GENERATOR
Интеллектуальная генерация постов с AI
"""

import logging
from typing import Dict
from ..ai import generate_ai_response
from .models import NewsItem

logger = logging.getLogger(__name__)

class PostGenerator:
    """Генератор умных постов"""
    
    def __init__(self):
        self.post_templates = {
            'new_law': """🆕 **НОВЫЙ ЗАКОН**

{title}

🔍 **Что это значит:**
{implications}

📅 Вступает в силу: {effective_date}

💼 Для консультации: /start""",
            
            'court_decision': """⚖️ **РЕШЕНИЕ СУДА**

{title}

🏛️ **Суть решения:**
{summary}

📊 **Практическое значение:**
{implications}

💼 Для консультации: /start""",
            
            'regulatory_change': """�� **ИЗМЕНЕНИЯ В РЕГУЛИРОВАНИИ**

{title}

📈 **Основные изменения:**
{changes}

⏰ **Сроки:** {timeline}

💼 Для консультации: /start""",
            
            'practical_guide': """💡 **ПРАКТИЧЕСКИЙ СОВЕТ**

{title}

📝 **Рекомендации:**
{recommendations}

💼 Для консультации: /start"""
        }
    
    async def generate_post(self, news_item: NewsItem) -> str:
        """Генерация поста на основе новости"""
        
        # Определяем тип поста
        post_type = self._determine_post_type(news_item)
        
        # Используем AI для обработки
        enhanced_content = await self._enhance_with_ai(news_item, post_type)
        
        # Форматируем пост
        formatted_post = self._format_post(enhanced_content, post_type)
        
        return formatted_post
    
    def _determine_post_type(self, news_item: NewsItem) -> str:
        """Определение типа поста"""
        
        title_content = f"{news_item.title} {news_item.content}".lower()
        
        if any(word in title_content for word in ['федеральный закон', 'новый закон']):
            return 'new_law'
        elif any(word in title_content for word in ['решение суда', 'постановление суда']):
            return 'court_decision'
        elif any(word in title_content for word in ['изменения', 'новые правила']):
            return 'regulatory_change'
        else:
            return 'practical_guide'
    
    async def _enhance_with_ai(self, news_item: NewsItem, post_type: str) -> Dict[str, str]:
        """Улучшение контента с помощью AI"""
        
        system_prompt = f"""Ты - опытный юрист, создающий понятные посты для Telegram.

Тип поста: {post_type}
Исходная новость: {news_item.title}
Контент: {news_item.content}

Создай полезный пост для обычных граждан:
1. Объясни простыми словами
2. Покажи практическое значение  
3. Дай конкретные рекомендации
4. Используй эмодзи
5. Объем: до 400 символов"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Создай пост: {news_item.title}\n\n{news_item.content}"}
        ]
        
        try:
            ai_response = await generate_ai_response(messages, model="openai/gpt-4o-mini", max_tokens=500)
            enhanced_content = self._parse_ai_response(ai_response, news_item)
            return enhanced_content
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            
            # Fallback
            return {
                'title': news_item.title,
                'summary': news_item.content[:200] + "...",
                'implications': "Подробную консультацию можно получить у наших юристов.",
                'recommendations': "Обратитесь к юристу для индивидуальной консультации.",
                'changes': "Подробности в источнике.",
                'timeline': "Уточняйте актуальные сроки.",
                'effective_date': "Уточняйте дату вступления в силу."
            }
    
    def _parse_ai_response(self, ai_response: str, news_item: NewsItem) -> Dict[str, str]:
        """Парсинг ответа AI"""
        
        result = {
            'title': news_item.title,
            'summary': ai_response[:200] + "...",
            'implications': "",
            'recommendations': "",
            'changes': "",
            'timeline': "",
            'effective_date': ""
        }
        
        # Простое извлечение секций
        lines = ai_response.split('\n')
        current_section = 'summary'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Определяем секцию по ключевым словам
            if any(word in line.lower() for word in ['значение', 'означает']):
                current_section = 'implications'
            elif any(word in line.lower() for word in ['рекомендации', 'советы']):
                current_section = 'recommendations'
            elif any(word in line.lower() for word in ['изменения', 'новое']):
                current_section = 'changes'
            elif any(word in line.lower() for word in ['срок', 'дата']):
                current_section = 'effective_date'
            
            # Добавляем контент
            if result[current_section]:
                result[current_section] += " " + line
            else:
                result[current_section] = line
        
        return result
    
    def _format_post(self, content: Dict[str, str], post_type: str) -> str:
        """Форматирование поста"""
        
        template = self.post_templates.get(post_type, self.post_templates['practical_guide'])
        
        try:
            formatted_post = template.format(**content)
            
            # Ограничиваем длину
            if len(formatted_post) > 800:
                content['summary'] = content['summary'][:100] + "..."
                formatted_post = template.format(**content)
            
            return formatted_post
            
        except KeyError as e:
            logger.warning(f"Missing template key {e}")
            
            # Простой fallback
            return f"""📰 **{content['title']}**

{content['summary']}

💼 Для консультации: /start"""
