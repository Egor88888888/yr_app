#!/usr/bin/env python3
"""
🏛️ WORLD-CLASS LEGAL AI CONSULTANT
Профессиональная система юридических консультаций мирового уровня
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import re
from datetime import datetime

from bot.services.ai_unified import unified_ai_service, AIModel, AIResponse

logger = logging.getLogger(__name__)

class LegalCategory(Enum):
    """Категории юридических консультаций"""
    FAMILY_LAW = "family_law"
    CIVIL_LAW = "civil_law"
    CRIMINAL_LAW = "criminal_law"
    LABOR_LAW = "labor_law"
    REAL_ESTATE = "real_estate"
    BUSINESS_LAW = "business_law"
    TAX_LAW = "tax_law"
    ADMINISTRATIVE = "administrative"
    INHERITANCE = "inheritance"
    BANKRUPTCY = "bankruptcy"
    INTELLECTUAL_PROPERTY = "ip"
    MIGRATION = "migration"
    OTHER = "other"

class ConsultationType(Enum):
    """Типы консультаций"""
    EXPRESS = "express"        # Быстрая консультация
    DETAILED = "detailed"      # Подробная консультация
    DOCUMENT_REVIEW = "document"  # Анализ документов
    STRATEGY = "strategy"      # Стратегическое планирование
    EMERGENCY = "emergency"    # Экстренная консультация

@dataclass
class LegalCase:
    """Юридическое дело/ситуация"""
    user_id: int
    category: LegalCategory
    consultation_type: ConsultationType
    description: str
    urgency: str = "medium"
    location: str = "РФ"
    budget_range: Optional[str] = None
    case_complexity: str = "medium"
    documents_available: bool = False

@dataclass 
class LegalAdvice:
    """Юридическая консультация"""
    case: LegalCase
    legal_analysis: str
    recommended_actions: List[str]
    legal_references: List[str]
    risks_assessment: str
    timeline: str
    estimated_cost: str
    next_steps: List[str]
    sales_offer: str
    follow_up_questions: List[str]

class WorldClassLegalAI:
    """Мировой класс AI юриста"""
    
    def __init__(self):
        self.legal_knowledge_base = self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self) -> Dict:
        """Инициализация базы юридических знаний"""
        return {
            "current_legislation": {
                "civil_code": "Гражданский кодекс РФ (актуальная редакция)",
                "criminal_code": "Уголовный кодекс РФ (актуальная редакция)",
                "labor_code": "Трудовой кодекс РФ (актуальная редакция)",
                "family_code": "Семейный кодекс РФ (актуальная редакция)",
                "tax_code": "Налоговый кодекс РФ (актуальная редакция)",
                "administrative_code": "КоАП РФ (актуальная редакция)",
                "housing_code": "Жилищный кодекс РФ (актуальная редакция)"
            },
            "court_practice": {
                "supreme_court": "Практика Верховного Суда РФ",
                "constitutional_court": "Практика Конституционного Суда РФ",
                "arbitrage_courts": "Практика арбитражных судов",
                "regional_courts": "Практика региональных судов"
            },
            "legal_procedures": {
                "civil_procedure": "Гражданский процессуальный кодекс РФ",
                "criminal_procedure": "Уголовно-процессуальный кодекс РФ",
                "arbitrage_procedure": "Арбитражный процессуальный кодекс РФ",
                "administrative_procedure": "КАС РФ"
            }
        }
    
    
    
    async def analyze_legal_case(self, case: LegalCase) -> LegalAdvice:
        """Анализ юридического дела"""
        logger.info(f"🏛️ Analyzing legal case for user {case.user_id}")
        
        # Определяем специализированный промпт
        system_prompt = self._build_specialized_prompt(case)
        
        # Формируем запрос для AI
        consultation_request = self._build_consultation_request(case)
        
        # Получаем консультацию от AI с нашим профессиональным промптом
        ai_response = await unified_ai_service.generate_world_class_consultation(
            user_message=consultation_request,
            system_prompt=system_prompt,
            category=case.category.value,
            model=AIModel.GPT_4O  # Используем лучшую модель
        )
        
        if not ai_response.success:
            logger.error(f"❌ AI consultation failed: {ai_response.error}")
            return self._generate_fallback_advice(case)
        
        # Парсим и структурируем ответ
        structured_advice = await self._structure_advice(case, ai_response.content)
        
        logger.info(f"✅ Legal advice generated for user {case.user_id}")
        return structured_advice
    
    def _build_specialized_prompt(self, case: LegalCase) -> str:
        """Построение специализированного промпта"""
        base_prompt = self.consultation_templates["system_prompts"]["world_class_lawyer"]
        
        category_expertise = {
            LegalCategory.FAMILY_LAW: "Специализация: СЕМЕЙНОЕ ПРАВО - развод, алименты, опека, раздел имущества, брачные договоры.",
            LegalCategory.CIVIL_LAW: "Специализация: ГРАЖДАНСКОЕ ПРАВО - договоры, возмещение ущерба, защита прав потребителей.",
            LegalCategory.CRIMINAL_LAW: "Специализация: УГОЛОВНОЕ ПРАВО - защита по уголовным делам, обжалование приговоров.",
            LegalCategory.LABOR_LAW: "Специализация: ТРУДОВОЕ ПРАВО - увольнения, трудовые споры, взыскание зарплаты.",
            LegalCategory.REAL_ESTATE: "Специализация: НЕДВИЖИМОСТЬ - сделки, споры с застройщиками, приватизация.",
            LegalCategory.BUSINESS_LAW: "Специализация: КОРПОРАТИВНОЕ ПРАВО - регистрация бизнеса, договоры, споры.",
            LegalCategory.TAX_LAW: "Специализация: НАЛОГОВОЕ ПРАВО - налоговые споры, оптимизация, проверки.",
            LegalCategory.INHERITANCE: "Специализация: НАСЛЕДСТВЕННОЕ ПРАВО - вступление в наследство, споры между наследниками.",
            LegalCategory.BANKRUPTCY: "Специализация: БАНКРОТСТВО - процедуры банкротства физлиц и юрлиц."
        }
        
        specialization = category_expertise.get(case.category, "Универсальная юридическая практика")
        
        return f"{base_prompt}\n\n{specialization}\n\nУРОВЕН�ь СЛОЖНОСТИ ДЕЛА: {case.case_complexity.upper()}\nМЕСТО: {case.location}"
    
    def _build_consultation_request(self, case: LegalCase) -> str:
        """Построение запроса для консультации"""
        urgency_text = {
            "low": "Обычная ситуация",
            "medium": "Требует внимания", 
            "high": "Срочная ситуация",
            "emergency": "ЭКСТРЕННАЯ СИТУАЦИЯ"
        }
        
        request = f"""
КАТЕГОРИЯ: {case.category.value.upper()}
ТИП КОНСУЛЬТАЦИИ: {case.consultation_type.value.upper()}
СРОЧНОСТЬ: {urgency_text.get(case.urgency, 'Обычная')}

ОПИСАНИЕ СИТУАЦИИ:
{case.description}

ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:
- Регион: {case.location}
- Сложность дела: {case.case_complexity}
- Наличие документов: {'Да' if case.documents_available else 'Нет'}
- Бюджет: {case.budget_range or 'Не указан'}

ТРЕБОВАНИЯ К КОНСУЛЬТАЦИИ:
🧠 ОБУЧАЮЩИЙ ХАРАКТЕР - объясните клиенту ВСЕ правовые тонкости
📚 ПЕРЕДАЧА ЗНАНИЙ - поделитесь профессиональными секретами
🎯 АЛГОРИТМ МЫШЛЕНИЯ - научите клиента самостоятельно анализировать подобные ситуации
💡 МАКСИМУМ ИНСАЙТОВ - расскажите то, что знают только практикующие юристы
🔄 ПРОДОЛЖЕНИЕ ДИАЛОГА - заинтересуйте клиента в дальнейшем общении
🤝 ПРОДАЖА ЧЕРЕЗ ЭКСПЕРТНОСТЬ - покажите ценность профессиональной помощи БЕЗ упоминания цен

СТРУКТУРА ОТВЕТА:
📖 ПРАВОВОЕ ОБРАЗОВАНИЕ: Объясните основные понятия простыми словами
🔍 ГЛУБОКИЙ АНАЛИЗ: Детальный разбор с пояснениями каждого аспекта
⚖️ ЗАКОНОДАТЕЛЬНАЯ БАЗА: Конкретные статьи с объяснением их практического применения
📊 СУДЕБНАЯ ПРАКТИКА: Примеры из реальных дел с выводами
🛡️ ОЦЕНКА РИСКОВ: Научите клиента видеть правовые подводные камни
📋 АЛГОРИТМ ДЕЙСТВИЙ: Подробная инструкция с обоснованием каждого шага
⏰ ВРЕМЕННЫЕ НЮАНСЫ: Все сроки с объяснением их критичности
💼 ПРОФЕССИОНАЛЬНЫЕ СЕКРЕТЫ: Практические хитрости из опыта
❓ ВОПРОСЫ ДЛЯ РАЗМЫШЛЕНИЯ: Подтолкните к дальнейшему диалогу
🤝 ЦЕННОСТЬ ЭКСПЕРТА: Покажите важность профессиональной помощи

ЦЕЛЬ: Максимально повысить правовую грамотность клиента и создать желание продолжить общение
"""
        
        return request
    
    async def _structure_advice(self, case: LegalCase, ai_content: str) -> LegalAdvice:
        """Структурирование совета от AI"""
        
        # Извлекаем ключевые компоненты из ответа AI
        legal_analysis = self._extract_section(ai_content, "ПРАВОВОЙ АНАЛИЗ", "ПРИМЕНИМЫЕ НОРМЫ")
        legal_references = self._extract_legal_references(ai_content)
        risks_assessment = self._extract_section(ai_content, "АНАЛИЗ РИСКОВ", "ПЛАН ДЕЙСТВИЙ")
        recommended_actions = self._extract_action_plan(ai_content)
        timeline = self._extract_timeline(ai_content)
        estimated_cost = self._extract_cost_estimate(ai_content)
        
        # Генерируем персонализированное торговое предложение
        sales_offer = await self._generate_sales_offer(case)
        
        # Генерируем вопросы для уточнения
        follow_up_questions = await self._generate_follow_up_questions(case)
        
        return LegalAdvice(
            case=case,
            legal_analysis=legal_analysis or ai_content[:500] + "...",
            recommended_actions=recommended_actions,
            legal_references=legal_references,
            risks_assessment=risks_assessment or "Требуется дополнительный анализ",
            timeline=timeline or "Зависит от обстоятельств дела",
            estimated_cost=estimated_cost or "Требуется персональная оценка",
            next_steps=await self._generate_next_steps(case),
            sales_offer=sales_offer,
            follow_up_questions=follow_up_questions
        )
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """Извлечение секции из текста"""
        start_pattern = rf"{start_marker}[:\s]*"
        end_pattern = rf"{end_marker}[:\s]*"
        
        start_match = re.search(start_pattern, text, re.IGNORECASE)
        if not start_match:
            return ""
        
        start_pos = start_match.end()
        end_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
        
        if end_match:
            end_pos = start_pos + end_match.start()
            return text[start_pos:end_pos].strip()
        else:
            # Берем до конца или до следующего заголовка
            next_section = re.search(r'\n[🔍⚖️⚠️📋💰⏰]', text[start_pos:])
            if next_section:
                end_pos = start_pos + next_section.start()
                return text[start_pos:end_pos].strip()
            return text[start_pos:start_pos+300].strip()
    
    def _extract_legal_references(self, text: str) -> List[str]:
        """Извлечение ссылок на законы"""
        patterns = [
            r'ст\.\s*\d+[.\d]*\s+[А-Я][а-я\s]+кодекс[а-я\s]*',
            r'статья\s+\d+[.\d]*\s+[А-Я][а-я\s]+кодекс[а-я\s]*',
            r'п\.\s*\d+[.\d]*\s+ст\.\s*\d+[.\d]*\s+[А-Я][а-я\s]+',
            r'Федеральный закон[а-я\s]*№\s*\d+-[А-Я]{2}',
            r'ГК РФ[,\s]*ст\.\s*\d+',
            r'УК РФ[,\s]*ст\.\s*\d+',
            r'ТК РФ[,\s]*ст\.\s*\d+'
        ]
        
        references = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))[:5]  # Максимум 5 ссылок
    
    def _extract_action_plan(self, text: str) -> List[str]:
        """Извлечение плана действий"""
        action_section = self._extract_section(text, "ПЛАН ДЕЙСТВИЙ", "ОРИЕНТИРОВОЧНАЯ СТОИМОСТЬ")
        
        if not action_section:
            return ["Требуется персональная консультация для составления плана"]
        
        # Извлекаем пронумерованные пункты
        actions = []
        lines = action_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line) or line.startswith('-') or line.startswith('•'):
                clean_line = re.sub(r'^\d+\.\s*', '', line)
                clean_line = re.sub(r'^[-•]\s*', '', clean_line)
                if clean_line:
                    actions.append(clean_line)
        
        return actions[:7]  # Максимум 7 действий
    
    def _extract_timeline(self, text: str) -> str:
        """Извлечение временных рамок"""
        timeline_section = self._extract_section(text, "ВРЕМЕННЫЕ РАМКИ", "")
        
        if timeline_section:
            return timeline_section
        
        # Ищем упоминания времени в тексте
        time_patterns = [
            r'\d+[-–]\d+\s*дней?',
            r'\d+[-–]\d+\s*месяц[а-я]*',
            r'в течение\s+\d+\s*[дней|месяц][а-я]*',
            r'срок[и]?\s*[-–:]\s*\d+\s*[дней|месяц][а-я]*'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return "Зависит от сложности дела (обычно 1-3 месяца)"
    
    def _extract_cost_estimate(self, text: str) -> str:
        """Извлечение оценки стоимости"""
        cost_section = self._extract_section(text, "ОРИЕНТИРОВОЧНАЯ СТОИМОСТЬ", "")
        
        if cost_section:
            return cost_section
        
        # Ищем упоминания стоимости
        cost_patterns = [
            r'\d+\s*[-–]\s*\d+\s*(?:тыс\.?|000)\s*руб',
            r'от\s+\d+\s*(?:тыс\.?|000)\s*руб',
            r'около\s+\d+\s*(?:тыс\.?|000)\s*руб'
        ]
        
        for pattern in cost_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return "Требуется индивидуальная оценка"
    
    def _generate_sales_offer(self, case: LegalCase) -> str:
        """Генерация продающего предложения через ценность и экспертность (БЕЗ ЦЕН)"""
        
        expertise_messages = {
            LegalCategory.FAMILY_LAW: "🏠 Защищаю семейные интересы уже 15+ лет. Знаю все нюансы семейного права.",
            LegalCategory.CRIMINAL_LAW: "⚖️ Специализируюсь на уголовной защите. Каждое дело - это чья-то жизнь.",
            LegalCategory.LABOR_LAW: "💼 Восстанавливаю трудовые права. За плечами сотни выигранных дел.",
            LegalCategory.REAL_ESTATE: "🏘️ Эксперт по недвижимости. Защищаю от мошенничества в сделках.",
            LegalCategory.BUSINESS_LAW: "🏢 Помогаю бизнесу работать в правовом поле и избегать рисков."
        }
        
        expertise = expertise_messages.get(case.category, "⚖️ Опытный юрист широкого профиля с глубокими знаниями права.")
        
        value_proposition = {
            "emergency": "🚨 В экстренных ситуациях каждая минута критична. Готов подключиться немедленно.",
            "high": "⚡ Понимаю важность быстрого решения. Приоритетное рассмотрение вашего дела.",
            "medium": "📋 Проведу комплексный анализ и разработаю стратегию решения.",
            "low": "💡 Помогу быстро разобраться в ситуации и наметить план действий."
        }
        
        urgency_value = value_proposition.get(case.urgency, value_proposition["medium"])
        
        return f"""{expertise}

{urgency_value}

🎯 **ЧТО ПОЛУЧИТЕ ОТ ПЕРСОНАЛЬНОЙ КОНСУЛЬТАЦИИ:**
✅ Индивидуальная стратегия решения именно вашей ситуации
✅ Все документы и их правильное оформление
✅ Пошаговый план действий с временными рамками
✅ Постоянная поддержка до решения вопроса
✅ Гарантия профессионального результата

💼 **МОЙ ОПЫТ - ВАША УВЕРЕННОСТЬ:**
🏆 20+ лет успешной юридической практики
📊 Сотни выигранных дел в данной сфере
🎓 Постоянное повышение квалификации
🤝 Индивидуальный подход к каждому клиенту

📞 Готов обсудить детали вашей ситуации лично!"""
    
    def _generate_next_steps(self, case: LegalCase) -> List[str]:
        """Генерация следующих шагов"""
        base_steps = [
            "Записаться на персональную консультацию",
            "Подготовить все имеющиеся документы",
            "Зафиксировать важные обстоятельства дела"
        ]
        
        category_steps = {
            LegalCategory.FAMILY_LAW: [
                "Собрать документы о семейном положении",
                "Оценить совместно нажитое имущество",
                "Подготовить справки о доходах"
            ],
            LegalCategory.LABOR_LAW: [
                "Сохранить все документы с работы",
                "Зафиксировать нарушения работодателя",
                "Получить справку о заработной плате"
            ],
            LegalCategory.REAL_ESTATE: [
                "Проверить документы на недвижимость",
                "Заказать выписку из ЕГРН",
                "Получить техническую документацию"
            ]
        }
        
        specific_steps = category_steps.get(case.category, [])
        return base_steps + specific_steps[:3]
    
    async def _generate_follow_up_questions(self, case: LegalCase) -> List[str]:
        """Генерация вопросов для продолжения диалога через AI"""
        
        questions_prompt = f"""Составьте 3-4 интересных вопроса для клиента, чтобы продолжить диалог.

Проблема клиента: "{case.description[:100]}..."
Категория: {case.category.value}

Вопросы должны:
- Углублять понимание ситуации
- Показывать экспертность юриста
- Вовлекать в дальнейший разговор

Формат: Простой список вопросов без нумерации."""
        
        response = await unified_ai_service.generate_simple_response(
            messages=[{"role": "user", "content": questions_prompt}],
            model=AIModel.GPT_4O_MINI,
            max_tokens=200
        )
        
        if response.success:
            questions = []
            for line in response.content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '?' in line:
                    # Очищаем от маркировки
                    for prefix in ['-', '•', '1.', '2.', '3.', '4.']:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                            break
                    if line:
                        questions.append(line)
            return questions[:4]
        
        # Fallback
        return [
            "Какие документы у вас есть по этому вопросу?",
            "Каковы ваши основные опасения в данной ситуации?",
            "Есть ли сроки, которые нас ограничивают?"
        ]
    
    async def _generate_fallback_advice(self, case: LegalCase) -> LegalAdvice:
        """Генерация консультации через AI при сбое основного провайдера"""
        
        # Создаем упрощенный промпт для fallback-консультации
        fallback_prompt = f"""
Вы - опытный юрист. Клиент обратился с вопросом: "{case.description}"

Дайте профессиональную консультацию включающую:
1. Анализ правовой ситуации
2. Применимые нормы права
3. Рекомендации по действиям
4. Оценку рисков
5. Примерные сроки решения

Отвечайте как живой человек-юрист, без шаблонов.
"""
        
        # Пытаемся получить ответ от AI с упрощенным промптом
        response = await unified_ai_service.generate_legal_consultation(
            user_message=fallback_prompt,
            category=case.category.value,
            model=AIModel.GPT_4O_MINI
        )
        
        if response.success:
            # Если AI ответил, парсим его ответ
            return await self._structure_advice(case, response.content)
        
        # Если и fallback AI не работает, возвращаем минимальную консультацию
        return LegalAdvice(
            case=case,
            legal_analysis="Для получения полной консультации необходимо личное обращение к юристу.",
            recommended_actions=["Записаться на консультацию", "Подготовить документы"],
            legal_references=["Применимое законодательство будет определено при консультации"],
            risks_assessment="Требуется индивидуальная оценка",
            timeline="Зависит от конкретных обстоятельств",
            estimated_cost="Определяется индивидуально",
            next_steps=["Обратиться за персональной консультацией"],
            sales_offer=self._generate_sales_offer(case),
            follow_up_questions=["Готовы обсудить детали лично?"]
        )
    

    async def generate_professional_comment(self, post_content: str, post_topic: str) -> str:
        """Генерация профессионального комментария к посту"""
        logger.info("📝 Generating professional legal comment")
        
        comment_prompt = f"""
Вы - ведущий юрист-эксперт. Прокомментируйте пост ПРОФЕССИОНАЛЬНО и ЭКСПЕРТНО.

ПОСТ: {post_topic}
СОДЕРЖАНИЕ: {post_content}

ТРЕБОВАНИЯ К КОММЕНТАРИЮ:
✅ Экспертная оценка с позиции права
✅ Ссылки на актуальное законодательство  
✅ Практические рекомендации
✅ Профессиональная терминология
✅ Конструктивная критика (если нужно)
✅ Добавить ценность для читателей

ФОРМАТ:
🏛️ [Экспертное мнение]
⚖️ [Правовая основа] 
💡 [Практические советы]
📞 [Мягкое предложение консультации]

СТИЛЬ: Профессиональный, авторитетный, полезный
ДЛИНА: 100-200 слов
"""
        
        response = await unified_ai_service.generate_expert_response(
            user_message=comment_prompt,
            model=AIModel.GPT_4O
        )
        
        if response.success:
            return response.content
        else:
            return self._generate_fallback_comment(post_topic)
    
    def _generate_fallback_comment(self, topic: str) -> str:
        """Резервный комментарий при сбое AI"""
        return f"""🏛️ Как практикующий юрист могу отметить, что данная тема требует профессионального подхода.

⚖️ В подобных вопросах важно учитывать актуальные изменения в законодательстве и судебную практику.

💡 Рекомендую не полагаться только на общую информацию - каждая ситуация индивидуальна.

📞 При необходимости готов предоставить персональную консультацию по данному вопросу."""

# Глобальный экземпляр экспертной системы
world_class_legal_ai = WorldClassLegalAI()