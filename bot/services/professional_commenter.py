#!/usr/bin/env python3
"""
📝 PROFESSIONAL LEGAL COMMENTER
Система профессионального комментирования юридических постов
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from bot.services.legal_expert_ai import world_class_legal_ai
from bot.services.legal_knowledge_base import legal_knowledge
from bot.services.ai_unified import unified_ai_service, AIModel

logger = logging.getLogger(__name__)

class PostType(Enum):
    """Типы постов"""
    NEWS = "news"                    # Новости права
    EDUCATIONAL = "educational"      # Обучающий контент
    CASE_STUDY = "case_study"       # Разбор дела
    LEGISLATION = "legislation"      # Изменения в законах
    COURT_DECISION = "court"        # Судебные решения
    ADVICE = "advice"               # Советы
    DISCUSSION = "discussion"       # Дискуссия
    OTHER = "other"

class CommentTone(Enum):
    """Тон комментария"""
    AUTHORITATIVE = "authoritative"  # Авторитетный
    EDUCATIONAL = "educational"      # Обучающий
    CONSTRUCTIVE = "constructive"    # Конструктивный
    CORRECTIVE = "corrective"       # Корректирующий
    SUPPORTIVE = "supportive"       # Поддерживающий

@dataclass
class PostAnalysis:
    """Анализ поста"""
    post_content: str
    post_type: PostType
    legal_category: str
    key_points: List[str]
    legal_accuracy: str
    missing_info: List[str]
    target_audience: str
    comment_opportunities: List[str]

@dataclass
class ProfessionalComment:
    """Профессиональный комментарий"""
    content: str
    tone: CommentTone
    legal_references: List[str]
    value_added: str
    sales_message: str
    engagement_level: str

class ProfessionalCommenter:
    """Профессиональная система комментирования"""
    
    def __init__(self):
        self.comment_templates = self._initialize_templates()
        self.legal_phrases = self._initialize_legal_phrases()
        self.sales_messages = self._initialize_sales_messages()
    
    def _initialize_templates(self) -> Dict:
        """Инициализация шаблонов комментариев"""
        return {
            "expert_opening": [
                "🏛️ Как практикующий юрист хочу отметить",
                "⚖️ С профессиональной точки зрения",  
                "📚 Основываясь на многолетней практике",
                "🎯 Важно понимать правовые аспекты",
                "💼 В юридической практике сталкиваемся"
            ],
            "legal_clarification": [
                "Согласно действующему законодательству",
                "Важно учитывать нормы",
                "Судебная практика показывает",
                "В соответствии с позицией ВС РФ",
                "Актуальные изменения в законе"
            ],
            "practical_advice": [
                "На практике рекомендую",
                "Из опыта ведения подобных дел",
                "Важно предпринять следующие шаги",
                "Для защиты ваших интересов",
                "Чтобы избежать правовых рисков"
            ],
            "sales_closure": [
                "При необходимости готов проконсультировать",
                "Для детального разбора ситуации",
                "Если требуется профессиональная помощь",
                "Сложные случаи требуют индивидуального подхода",
                "Каждая ситуация уникальна"
            ]
        }
    
    def _initialize_legal_phrases(self) -> Dict:
        """Инициализация юридических фраз"""
        return {
            "civil_law": [
                "согласно ст. 15 ГК РФ о возмещении убытков",
                "в рамках обязательственного права",
                "применительно к договорным отношениям",
                "с учетом принципа добросовестности"
            ],
            "criminal_law": [
                "в контексте уголовно-правовой квалификации", 
                "согласно принципам уголовного права",
                "с учетом судебной практики ВС РФ",
                "применительно к составу преступления"
            ],
            "family_law": [
                "согласно принципам семейного права",
                "в интересах несовершеннолетних детей",
                "с учетом равенства прав супругов",
                "согласно СК РФ"
            ],
            "labor_law": [
                "в соответствии с ТК РФ",
                "с учетом трудовых прав работника",
                "согласно позиции Роструда",
                "применительно к трудовым отношениям"
            ]
        }
    
    def _initialize_sales_messages(self) -> Dict:
        """Инициализация продающих сообщений"""
        return {
            "soft_sell": [
                "📞 При возникновении подобных вопросов всегда готов помочь",
                "💼 15+ лет практики в данной сфере",
                "⚖️ Успешно решаем сложные правовые вопросы",
                "🎯 Индивидуальный подход к каждому случаю"
            ],
            "urgency": [
                "⏰ Важно действовать в установленные сроки",
                "🚨 Промедление может повлечь негативные последствия", 
                "📅 Соблюдение процессуальных сроков критично",
                "⚡ Быстрое реагирование - залог успеха"
            ],
            "expertise": [
                "🏆 Практический опыт в разрешении подобных споров",
                "📊 98% успешно решенных дел в данной категории",
                "🎖️ Признанный эксперт в области права",
                "💡 Авторские стратегии решения сложных вопросов"
            ]
        }
    
    async def analyze_post(self, post_content: str, post_topic: str = "") -> PostAnalysis:
        """Анализ поста для комментирования"""
        logger.info("📊 Analyzing post for professional commenting")
        
        # Определяем тип поста
        post_type = self._determine_post_type(post_content, post_topic)
        
        # Определяем правовую категорию
        legal_category = self._determine_legal_category(post_content)
        
        # Извлекаем ключевые моменты
        key_points = self._extract_key_points(post_content)
        
        # Оцениваем юридическую точность
        legal_accuracy = await self._assess_legal_accuracy(post_content, legal_category)
        
        # Находим пропущенную информацию
        missing_info = self._find_missing_info(post_content, legal_category)
        
        # Определяем целевую аудиторию
        target_audience = self._determine_target_audience(post_content)
        
        # Находим возможности для комментирования
        comment_opportunities = self._find_comment_opportunities(post_content, legal_category)
        
        return PostAnalysis(
            post_content=post_content,
            post_type=post_type,
            legal_category=legal_category,
            key_points=key_points,
            legal_accuracy=legal_accuracy,
            missing_info=missing_info,
            target_audience=target_audience,
            comment_opportunities=comment_opportunities
        )
    
    async def generate_professional_comment(self, post_analysis: PostAnalysis) -> ProfessionalComment:
        """Генерация профессионального комментария"""
        logger.info(f"💬 Generating professional comment for {post_analysis.post_type.value}")
        
        # Определяем тон комментария
        comment_tone = self._determine_comment_tone(post_analysis)
        
        # Генерируем основной контент комментария
        comment_content = await self._generate_comment_content(post_analysis, comment_tone)
        
        # Добавляем правовые ссылки
        legal_references = self._add_legal_references(post_analysis)
        
        # Определяем добавленную ценность
        value_added = self._determine_value_added(post_analysis, comment_content)
        
        # Добавляем продающее сообщение
        sales_message = self._craft_sales_message(post_analysis, comment_tone)
        
        # Оцениваем уровень вовлеченности
        engagement_level = self._assess_engagement_level(comment_content)
        
        return ProfessionalComment(
            content=comment_content,
            tone=comment_tone,
            legal_references=legal_references,
            value_added=value_added,
            sales_message=sales_message,
            engagement_level=engagement_level
        )
    
    def _determine_post_type(self, content: str, topic: str) -> PostType:
        """Определение типа поста"""
        content_lower = (content + " " + topic).lower()
        
        if any(word in content_lower for word in ["новость", "новые", "изменения", "вступил в силу"]):
            return PostType.NEWS
        elif any(word in content_lower for word in ["как", "инструкция", "пошагово", "совет"]):
            return PostType.EDUCATIONAL
        elif any(word in content_lower for word in ["дело", "случай", "практика", "разбор"]):
            return PostType.CASE_STUDY
        elif any(word in content_lower for word in ["закон", "статья", "кодекс", "норма"]):
            return PostType.LEGISLATION
        elif any(word in content_lower for word in ["суд", "решение", "постановление", "определение"]):
            return PostType.COURT_DECISION
        elif any(word in content_lower for word in ["совет", "рекомендация", "что делать"]):
            return PostType.ADVICE
        elif "?" in content or any(word in content_lower for word in ["мнение", "считаете", "думаете"]):
            return PostType.DISCUSSION
        else:
            return PostType.OTHER
    
    def _determine_legal_category(self, content: str) -> str:
        """Определение правовой категории"""
        content_lower = content.lower()
        
        categories = {
            "семейное": ["развод", "алименты", "брак", "семья", "опека"],
            "трудовое": ["работ", "увольн", "зарплат", "отпуск", "трудов"],
            "гражданское": ["договор", "сделка", "обязательств", "собственност"],
            "уголовное": ["преступлен", "уголовн", "наказан", "состав"],
            "налоговое": ["налог", "ндс", "ндфл", "декларац", "фнс"],
            "административное": ["административн", "штраф", "нарушен", "коап"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category
        
        return "общее"
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Извлечение ключевых моментов"""
        # Простое извлечение предложений с ключевыми словами
        sentences = content.split('.')
        key_words = ["важно", "необходимо", "следует", "можно", "нельзя", "должен", "право", "обязанность"]
        
        key_points = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in key_words) and len(sentence.strip()) > 20:
                key_points.append(sentence.strip())
        
        return key_points[:3]  # Максимум 3 ключевых момента
    
    async def _assess_legal_accuracy(self, content: str, category: str) -> str:
        """Оценка юридической точности"""
        # Базовая оценка на основе ключевых слов
        accuracy_indicators = {
            "высокая": ["согласно", "статья", "кодекс", "закон", "постановление"],
            "средняя": ["обычно", "как правило", "чаще всего"],
            "низкая": ["возможно", "вероятно", "иногда", "может быть"]
        }
        
        content_lower = content.lower()
        
        for level, indicators in accuracy_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return level
        
        return "требует проверки"
    
    def _find_missing_info(self, content: str, category: str) -> List[str]:
        """Поиск пропущенной информации"""
        missing_info = []
        
        # Общие пропуски
        if "срок" not in content.lower():
            missing_info.append("Временные рамки")
        if "стоимость" not in content.lower() and "цена" not in content.lower():
            missing_info.append("Ориентировочная стоимость")
        if "документ" not in content.lower():
            missing_info.append("Необходимые документы")
        
        # Категориальные пропуски
        if category == "семейное" and "алименты" in content.lower():
            if "размер" not in content.lower():
                missing_info.append("Размер алиментов")
        
        return missing_info[:3]
    
    def _determine_target_audience(self, content: str) -> str:
        """Определение целевой аудитории"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["юрист", "коллег", "практик"]):
            return "профессионалы"
        elif any(word in content_lower for word in ["предприниматель", "бизнес", "ип"]):
            return "бизнес"
        else:
            return "широкая публика"
    
    def _find_comment_opportunities(self, content: str, category: str) -> List[str]:
        """Поиск возможностей для комментирования"""
        opportunities = []
        
        # Общие возможности
        if "?" in content:
            opportunities.append("Ответить на вопрос")
        if any(word in content.lower() for word in ["неточност", "ошибк", "неправильн"]):
            opportunities.append("Корректировка информации")
        if len(content) < 200:
            opportunities.append("Дополнить информацией")
        
        # Добавить экспертное мнение
        opportunities.append("Поделиться практическим опытом")
        
        return opportunities
    
    def _determine_comment_tone(self, post_analysis: PostAnalysis) -> CommentTone:
        """Определение тона комментария"""
        if post_analysis.legal_accuracy == "низкая":
            return CommentTone.CORRECTIVE
        elif post_analysis.post_type == PostType.EDUCATIONAL:
            return CommentTone.EDUCATIONAL
        elif post_analysis.post_type == PostType.DISCUSSION:
            return CommentTone.CONSTRUCTIVE
        elif "вопрос" in post_analysis.post_content.lower():
            return CommentTone.SUPPORTIVE
        else:
            return CommentTone.AUTHORITATIVE
    
    async def _generate_comment_content(self, post_analysis: PostAnalysis, tone: CommentTone) -> str:
        """Генерация содержания комментария"""
        
        # Формируем запрос для AI
        ai_prompt = f"""
Создайте профессиональный юридический комментарий к посту.

ПОСТ: {post_analysis.post_content[:300]}
ТИП ПОСТА: {post_analysis.post_type.value}
ПРАВОВАЯ ОБЛАСТЬ: {post_analysis.legal_category}
ТОН: {tone.value}

ТРЕБОВАНИЯ:
✅ Профессиональная экспертиза
✅ Ссылки на законодательство
✅ Практические рекомендации
✅ Добавленная ценность
✅ Конструктивность

СТРУКТУРА:
🏛️ [Экспертное мнение]
⚖️ [Правовая основа]
💡 [Практические советы]

ДЛИНА: 100-150 слов
СТИЛЬ: Профессиональный, авторитетный
"""
        
        try:
            response = await world_class_legal_ai.generate_professional_comment(
                post_analysis.post_content, 
                f"{post_analysis.post_type.value} - {post_analysis.legal_category}"
            )
            return response
        except Exception as e:
            logger.error(f"AI comment generation failed: {e}")
            return self._generate_fallback_comment(post_analysis, tone)
    
    def _generate_fallback_comment(self, post_analysis: PostAnalysis, tone: CommentTone) -> str:
        """Генерация резервного комментария"""
        import random
        
        opening = random.choice(self.comment_templates["expert_opening"])
        legal_phrase = random.choice(self.legal_phrases.get(post_analysis.legal_category, ["что в данном вопросе"]))
        practical = random.choice(self.comment_templates["practical_advice"])
        
        return f"""{opening}, {legal_phrase} важно учитывать все нюансы.

{practical} обратиться за профессиональной консультацией для получения персонализированных рекомендаций.

💼 Готов предоставить детальную консультацию по данному вопросу."""
    
    def _add_legal_references(self, post_analysis: PostAnalysis) -> List[str]:
        """Добавление правовых ссылок"""
        references = []
        
        # Поиск в базе знаний
        related_norms = legal_knowledge.search_norms(
            post_analysis.post_content[:100], 
            post_analysis.legal_category
        )
        
        for norm in related_norms[:2]:
            references.append(f"{norm.code} ст. {norm.article}")
        
        return references
    
    def _determine_value_added(self, post_analysis: PostAnalysis, comment: str) -> str:
        """Определение добавленной ценности"""
        if post_analysis.legal_accuracy == "низкая":
            return "Корректировка неточностей"
        elif len(post_analysis.missing_info) > 0:
            return "Дополнение важной информации"
        elif post_analysis.post_type == PostType.DISCUSSION:
            return "Экспертное мнение"
        else:
            return "Практические рекомендации"
    
    def _craft_sales_message(self, post_analysis: PostAnalysis, tone: CommentTone) -> str:
        """Создание продающего сообщения"""
        import random
        
        if post_analysis.target_audience == "бизнес":
            return "💼 Специализируюсь на корпоративном праве и защите интересов бизнеса"
        elif "срочн" in post_analysis.post_content.lower():
            return random.choice(self.sales_messages["urgency"])
        else:
            return random.choice(self.sales_messages["soft_sell"])
    
    def _assess_engagement_level(self, comment: str) -> str:
        """Оценка уровня вовлеченности"""
        engagement_indicators = len([
            "?" in comment,
            "❓" in comment or "❗" in comment,
            len(comment) > 200,
            comment.lower().count("важно") > 0,
            comment.lower().count("рекомендую") > 0
        ])
        
        if engagement_indicators >= 3:
            return "высокий"
        elif engagement_indicators >= 2:
            return "средний"
        else:
            return "базовый"

# Глобальный экземпляр комментатора
professional_commenter = ProfessionalCommenter()