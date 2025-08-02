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
        self.consultation_templates = self._initialize_consultation_templates()
    
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
    
    def _initialize_consultation_templates(self) -> Dict:
        """Инициализация естественных промптов для диалога"""
        return {
            "system_prompts": {
                "natural_lawyer": """Вы - опытный юрист с глубокими знаниями российского права. Ведите естественный профессиональный диалог.

Принципы работы:
- Анализируйте конкретную ситуацию клиента индивидуально
- Демонстрируйте экспертизу через конкретные правовые знания
- Объясняйте сложные моменты доступно
- Предлагайте персональную помощь естественно в ходе разговора

Важно: НЕ используйте структурированные форматы, шаблоны, эмодзи или стандартные фразы. Отвечайте как настоящий юрист в живой беседе."""
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
        try:
            ai_response = await unified_ai_service.generate_world_class_consultation(
                user_message=consultation_request,
                system_prompt=system_prompt,
                category=case.category.value,
                model=AIModel.GPT_4O_MINI  # Используем более доступную модель
            )
            
            if not ai_response.success:
                logger.warning(f"⚠️ Primary AI consultation failed: {ai_response.error}")
                # Пробуем с более простым промптом
                fallback_response = await unified_ai_service.generate_legal_consultation(
                    user_message=case.description,
                    category=case.category.value,
                    model=AIModel.GPT_4O_MINI
                )
                
                if fallback_response.success:
                    ai_response = fallback_response
                else:
                    logger.error(f"❌ All AI consultation attempts failed: {fallback_response.error}")
                    return await self._generate_fallback_advice(case)
        except Exception as e:
            logger.error(f"❌ AI consultation exception: {e}")
            return await self._generate_fallback_advice(case)
        
        # Парсим и структурируем ответ
        structured_advice = await self._structure_advice(case, ai_response.content)
        
        logger.info(f"✅ Legal advice generated for user {case.user_id}")
        return structured_advice
    
    def _build_specialized_prompt(self, case: LegalCase) -> str:
        """Построение специализированного промпта"""
        base_prompt = self.consultation_templates["system_prompts"]["natural_lawyer"]
        
        # Убираем шаблонные специализации - естественный диалог
        area_focus = ""
        if case.category != LegalCategory.OTHER:
            area_focus = f"Ситуация клиента относится к области: {case.category.value.replace('_', ' ')}"
        
        return f"{base_prompt}\n\n{area_focus}"
    
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
        sales_offer = self._generate_sales_offer(case)
        
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
            next_steps=self._generate_next_steps(case),
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
        """NO SALES OFFERS - Return empty string for natural conversation"""
        return ""
    
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
        """Генерация консультации без AI - использует шаблоны и базу знаний"""
        
        logger.info(f"🔄 Generating fallback advice for category {case.category.value}")
        
        # Генерируем базовую консультацию на основе категории
        legal_analysis = self._get_category_analysis(case)
        recommended_actions = self._get_category_actions(case)
        legal_references = self._get_category_references(case)
        risks_assessment = self._get_category_risks(case)
        timeline = self._get_category_timeline(case)
        
        return LegalAdvice(
            case=case,
            legal_analysis=legal_analysis,
            recommended_actions=recommended_actions,
            legal_references=legal_references,
            risks_assessment=risks_assessment,
            timeline=timeline,
            estimated_cost=self._get_category_cost_estimate(case),
            next_steps=self._get_category_next_steps(case),
            sales_offer=self._generate_sales_offer(case),
            follow_up_questions=self._get_category_follow_up_questions(case)
        )
    
    def _get_category_analysis(self, case: LegalCase) -> str:
        """Базовый анализ по категории - естественный разговорный стиль"""
        category_analysis = {
            LegalCategory.FAMILY_LAW: "В семейных вопросах важно учитывать множество нюансов. Каждая ситуация уникальна и требует индивидуального подхода. Семейное право защищает интересы всех членов семьи, особенно детей.",
            
            LegalCategory.CIVIL_LAW: "В гражданских делах ключевую роль играют договорные отношения и принцип равенства сторон. Важно правильно оценить все обстоятельства и выбрать наиболее эффективный способ защиты ваших прав.",
            
            LegalCategory.LABOR_LAW: "Трудовые споры требуют знания не только законодательства, но и судебной практики. Важно соблюдать процедуры и сроки, чтобы защитить свои права как работника или работодателя.",
            
            LegalCategory.REAL_ESTATE: "Операции с недвижимостью всегда связаны с рисками. Тщательная проверка документов и соблюдение процедур регистрации помогут избежать проблем в будущем.",
            
            LegalCategory.BUSINESS_LAW: "Предпринимательская деятельность требует соблюдения множества требований. Правильное оформление и ведение бизнеса поможет избежать штрафов и других неприятностей."
        }
        
        return category_analysis.get(case.category, "Каждая правовая ситуация уникальна и требует внимательного изучения. Важно собрать все документы, соблюсти сроки и выбрать правильную стратегию действий.")
    
    def _get_category_actions(self, case: LegalCase) -> List[str]:
        """Рекомендуемые действия по категории"""
        category_actions = {
            LegalCategory.FAMILY_LAW: [
                "Собрать все документы, подтверждающие семейные отношения",
                "Получить справки о доходах всех участников процесса",
                "Составить опись совместно нажитого имущества",
                "Обратиться за консультацией к семейному психологу (при необходимости)",
                "Подготовить документы для обращения в суд"
            ],
            LegalCategory.CIVIL_LAW: [
                "Проанализировать все договоры и соглашения",
                "Собрать доказательства нарушения обязательств",
                "Рассчитать размер причиненного ущерба",
                "Направить претензию нарушителю",
                "Подготовить исковое заявление в суд"
            ],
            LegalCategory.LABOR_LAW: [
                "Зафиксировать все нарушения работодателя документально",
                "Обратиться с жалобой в трудовую инспекцию",
                "Получить справку о заработной плате",
                "Подготовить копии всех трудовых документов",
                "Рассмотреть возможность досудебного урегулирования"
            ],
            LegalCategory.REAL_ESTATE: [
                "Заказать выписку из ЕГРН на объект недвижимости",
                "Проверить техническую документацию",
                "Получить справки об отсутствии задолженностей",
                "Провести независимую оценку объекта",
                "Оформить страхование сделки"
            ]
        }
        
        return category_actions.get(case.category, [
            "Провести детальный анализ ситуации",
            "Собрать все необходимые документы",
            "Определить правовую стратегию",
            "Подготовить документы для обращения в компетентные органы",
            "Рассмотреть возможности досудебного урегулирования"
        ])
    
    def _get_category_references(self, case: LegalCase) -> List[str]:
        """Применимые нормы права по категории"""
        category_refs = {
            LegalCategory.FAMILY_LAW: [
                "Семейный кодекс РФ",
                "ГПК РФ (особенности семейных дел)",
                "ФЗ «Об актах гражданского состояния»",
                "Постановления Пленума ВС РФ по семейным делам"
            ],
            LegalCategory.CIVIL_LAW: [
                "Гражданский кодекс РФ (части 1-4)",
                "ГПК РФ (гражданский процесс)",
                "ФЗ «О защите прав потребителей»",
                "Постановления Пленума ВС РФ по гражданским делам"
            ],
            LegalCategory.LABOR_LAW: [
                "Трудовой кодекс РФ",
                "ФЗ «О профессиональных союзах»",
                "ГПК РФ (трудовые споры)",
                "Постановления Правительства РФ по трудовым отношениям"
            ],
            LegalCategory.REAL_ESTATE: [
                "Гражданский кодекс РФ (сделки с недвижимостью)",
                "ФЗ «О государственной регистрации недвижимости»",
                "Жилищный кодекс РФ",
                "ФЗ «Об участии в долевом строительстве»"
            ]
        }
        
        return category_refs.get(case.category, [
            "Гражданский кодекс РФ",
            "Применимые федеральные законы",
            "Постановления Правительства РФ",
            "Судебная практика по аналогичным делам"
        ])
    
    def _get_category_risks(self, case: LegalCase) -> str:
        """Оценка рисков по категории"""
        category_risks = {
            LegalCategory.FAMILY_LAW: """⚠️ **ОСНОВНЫЕ РИСКИ:**
• Затягивание процесса при несогласии сторон
• Сложности с определением долей в имуществе
• Эмоциональные факторы, влияющие на принятие решений
• Возможные изменения в финансовом положении сторон""",
            
            LegalCategory.CIVIL_LAW: """⚠️ **ОСНОВНЫЕ РИСКИ:**
• Недостаточность доказательств нарушения
• Сложности с взысканием присужденных сумм
• Длительность судебного разбирательства
• Возможность встречных исков""",
            
            LegalCategory.LABOR_LAW: """⚠️ **ОСНОВНЫЕ РИСКИ:**
• Ухудшение отношений с работодателем
• Сложности с дальнейшим трудоустройством
• Длительность рассмотрения споров
• Необходимость доказывания нарушений""",
            
            LegalCategory.REAL_ESTATE: """⚠️ **ОСНОВНЫЕ РИСКИ:**
• Мошеннические схемы в сфере недвижимости
• Скрытые обременения на объект
• Изменения в градостроительном законодательстве
• Колебания цен на рынке недвижимости"""
        }
        
        return category_risks.get(case.category, """⚠️ **ОБЩИЕ РИСКИ:**
• Неправильная правовая оценка ситуации
• Пропуск процессуальных сроков
• Недостаточность доказательной базы
• Непредвиденные процессуальные сложности""")
    
    def _get_category_timeline(self, case: LegalCase) -> str:
        """Временные рамки по категории"""
        category_timelines = {
            LegalCategory.FAMILY_LAW: "Семейные дела: 1-6 месяцев (в зависимости от сложности)",
            LegalCategory.CIVIL_LAW: "Гражданские споры: 2-12 месяцев",
            LegalCategory.LABOR_LAW: "Трудовые споры: 1-3 месяца",
            LegalCategory.REAL_ESTATE: "Сделки с недвижимостью: 1-3 месяца"
        }
        
        return category_timelines.get(case.category, "Зависит от сложности дела: от 1 до 12 месяцев")
    
    def _get_category_cost_estimate(self, case: LegalCase) -> str:
        """Оценка стоимости по категории"""
        return "Стоимость услуг определяется индивидуально на консультации"
    
    def _get_category_follow_up_questions(self, case: LegalCase) -> List[str]:
        """Вопросы для продолжения диалога по категории"""
        category_questions = {
            LegalCategory.FAMILY_LAW: [
                "Есть ли несовершеннолетние дети, интересы которых нужно учесть?",
                "Какое имущество было приобретено в браке?",
                "Пытались ли вы решить вопрос мирным путем?"
            ],
            LegalCategory.CIVIL_LAW: [
                "Какие документы у вас есть, подтверждающие ваши требования?",
                "Пытались ли вы урегулировать спор в досудебном порядке?",
                "Какой ущерб был причинен вашим правам и интересам?"
            ],
            LegalCategory.LABOR_LAW: [
                "Как долго длятся трудовые отношения с работодателем?",
                "Есть ли письменные доказательства нарушений?",
                "Обращались ли вы к работодателю с претензиями ранее?"
            ]
        }
        
        return category_questions.get(case.category, [
            "Какие документы у вас есть по данному вопросу?",
            "Какие действия вы уже предпринимали?",
            "Каковы ваши ожидания от решения данной ситуации?"
        ])
    

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