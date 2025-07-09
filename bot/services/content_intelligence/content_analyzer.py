"""
🔍 CONTENT ANALYZER
NLP анализ релевантности и качества контента
"""

import re
from typing import Dict
from .models import NewsItem

class ContentAnalyzer:
    """Анализатор контента с NLP"""
    
    def __init__(self):
        self.legal_keywords = {
            'high_relevance': [
                'федеральный закон', 'постановление', 'приказ', 'решение суда',
                'конституционный суд', 'верховный суд', 'арбитражный суд',
                'налоговый кодекс', 'гражданский кодекс', 'трудовой кодекс'
            ],
            'medium_relevance': [
                'права граждан', 'юридические услуги', 'правовая помощь',
                'судебная практика', 'изменения в законодательстве',
                'новые правила', 'штрафы', 'компенсации'
            ],
            'legal_entities': [
                'минюст', 'роскомнадзор', 'фас', 'фнс', 'цб рф',
                'росреестр', 'пфр', 'фсс', 'роспотребнадзор'
            ]
        }
    
    async def analyze_relevance(self, news_item: NewsItem) -> float:
        """Анализ релевантности новости"""
        
        text = f"{news_item.title} {news_item.content}".lower()
        score = 0.0
        
        # Базовая оценка по ключевым словам
        for keyword in self.legal_keywords['high_relevance']:
            if keyword in text:
                score += 0.3
        
        for keyword in self.legal_keywords['medium_relevance']:
            if keyword in text:
                score += 0.2
        
        for keyword in self.legal_keywords['legal_entities']:
            if keyword in text:
                score += 0.1
        
        # Дополнительные факторы
        if news_item.source in ['pravo_gov', 'ksrf']:
            score += 0.4  # Официальные источники важнее
        
        if any(word in text for word in ['новый', 'изменения', 'вступил в силу']):
            score += 0.2  # Актуальность
        
        # Нормализуем к диапазону 0-1
        return min(score, 1.0)
    
    async def analyze_content_quality(self, news_item: NewsItem) -> Dict[str, float]:
        """Анализ качества контента"""
        
        content_len = len(news_item.content)
        
        quality_metrics = {
            'title_quality': self._score_title_quality(news_item.title),
            'content_length': min(content_len / 500, 1.0),
            'informativeness': self._score_informativeness(news_item.content),
            'readability': self._score_readability(news_item.content)
        }
        
        return quality_metrics
    
    def _score_title_quality(self, title: str) -> float:
        """Оценка качества заголовка"""
        score = 0.5
        
        # Длина заголовка
        if 30 <= len(title) <= 100:
            score += 0.2
        
        # Наличие ключевых слов
        if any(word in title.lower() for word in ['закон', 'права', 'суд', 'новые']):
            score += 0.2
        
        # Избегаем clickbait
        if not any(word in title.lower() for word in ['шок', 'сенсация', '!!!']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_informativeness(self, content: str) -> float:
        """Оценка информативности"""
        score = 0.3
        
        # Наличие дат
        if re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', content):
            score += 0.2
        
        # Наличие цифр
        if re.search(r'\d+', content):
            score += 0.1
        
        # Упоминание статей закона
        if re.search(r'стать[яие] \d+', content.lower()):
            score += 0.2
        
        # Ссылки на документы
        if any(word in content.lower() for word in ['№', 'федеральный закон']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_readability(self, content: str) -> float:
        """Оценка читаемости"""
        sentences = content.split('.')
        if not sentences:
            return 0.3
        
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Оптимальная длина предложения 10-20 слов
        if 10 <= avg_sentence_length <= 20:
            return 0.8
        elif 5 <= avg_sentence_length <= 30:
            return 0.6
        else:
            return 0.4
