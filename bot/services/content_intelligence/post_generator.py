"""
📝 ENHANCED POST GENERATOR
Генерация высококачественных постов с алгоритмами, ресурсами и решениями проблем
"""

import logging
import random
from typing import Dict, List
from ..ai import generate_ai_response
from .models import NewsItem

logger = logging.getLogger(__name__)


class PostGenerator:
    """Генератор качественных структурированных постов"""

    def __init__(self):
        # Новые улучшенные шаблоны с алгоритмами и ресурсами
        self.enhanced_templates = {
            'step_by_step_guide': """🎯 **{title}**

📋 **ПОШАГОВЫЙ АЛГОРИТМ:**
{step_algorithm}

⚠️ **ВОЗМОЖНЫЕ ПРОБЛЕМЫ:**
{potential_problems}

🔗 **ПОЛЕЗНЫЕ РЕСУРСЫ:**
{useful_resources}

📞 **НУЖНА ПОМОЩЬ?**
Получите персональную консультацию: /start""",

            'legal_analysis': """⚖️ **{title}**

🔍 **СУТЬ ИЗМЕНЕНИЙ:**
{key_changes}

📝 **ЧТО ДЕЛАТЬ ГРАЖДАНАМ:**
{citizen_actions}

🚨 **НА ЧТО ОБРАТИТЬ ВНИМАНИЕ:**
{warnings}

🌐 **ОФИЦИАЛЬНЫЕ ИСТОЧНИКИ:**
{official_sources}

💼 Консультация юриста: /start""",

            'practical_solution': """💡 **{title}**

✅ **РЕШЕНИЕ ПРОБЛЕМЫ:**
{solution_steps}

📊 **СТАТИСТИКА И ФАКТЫ:**
{statistics}

🔧 **ПРАКТИЧЕСКИЕ СОВЕТЫ:**
{practical_tips}

📚 **ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:**
{additional_info}

📞 Персональная помощь: /start""",

            'urgent_alert': """🚨 **ВАЖНО!** {title}

⏰ **СРОЧНЫЕ ДЕЙСТВИЯ:**
{urgent_actions}

📅 **КЛЮЧЕВЫЕ ДАТЫ:**
{important_dates}

🎯 **КОМУ ЭТО КАСАЕТСЯ:**
{target_audience}

📋 **ДОКУМЕНТЫ:**
{required_documents}

🆘 Срочная консультация: /start"""
        }

        # База знаний полезных ресурсов
        self.resource_database = {
            'government_sites': [
                "🏛️ Госуслуги: gosuslugi.ru",
                "📋 Росреестр: rosreestr.gov.ru",
                "💼 Налоговая: nalog.gov.ru",
                "⚖️ Консультант Плюс: consultant.ru",
                "📖 Гарант: garant.ru"
            ],
            'legal_assistance': [
                "📞 Правовая помощь: fedpal.ru",
                "🏛️ Роскадастр: kadastr.ru",
                "👥 Общественная палата: oprf.ru",
                "🔍 Судебная система: sudrf.ru"
            ],
            'consumer_protection': [
                "🛡️ Роспотребнадзор: rospotrebnadzor.ru",
                "📋 Реестр недобросовестных поставщиков: zakupki.gov.ru",
                "💳 Центробанк: cbr.ru"
            ]
        }

        # Типовые проблемы и решения
        self.common_problems = {
            'documentation': [
                "❌ Отказ в приеме документов",
                "📝 Неправильное оформление заявления",
                "⏰ Пропуск сроков подачи",
                "🔍 Отсутствие необходимых справок"
            ],
            'bureaucracy': [
                "🏢 Отказ в предоставлении услуги",
                "⏱️ Нарушение сроков рассмотрения",
                "💰 Незаконные требования доплаты",
                "📞 Отсутствие ответа от ведомства"
            ],
            'legal_procedures': [
                "⚖️ Неправильное толкование закона",
                "📋 Требование дополнительных документов",
                "🕐 Затягивание процедуры",
                "❌ Нарушение ваших прав"
            ]
        }

    async def generate_post(self, news_item: NewsItem = None) -> str:
        """Генерация качественного поста с алгоритмами и ресурсами"""

        if news_item:
            # Обработка реальной новости
            return await self._generate_news_based_post(news_item)
        else:
            # Генерация образовательного поста
            return await self._generate_educational_post()

    async def _generate_news_based_post(self, news_item: NewsItem) -> str:
        """Генерация поста на основе новости"""

        post_type = self._determine_enhanced_post_type(news_item)

        # Создаем улучшенный AI промпт
        enhanced_content = await self._create_structured_content(news_item, post_type)

        # Форматируем по новому шаблону
        return self._format_enhanced_post(enhanced_content, post_type)

    async def _generate_educational_post(self) -> str:
        """Генерация образовательного поста без привязки к новостям"""

        # Выбираем тему для образовательного поста
        educational_topics = [
            {
                'title': 'Как правильно подать жалобу в Роспотребнадзор',
                'category': 'consumer_protection',
                'type': 'step_by_step_guide'
            },
            {
                'title': 'Защита трудовых прав: пошаговая инструкция',
                'category': 'labor_law',
                'type': 'practical_solution'
            },
            {
                'title': 'Электронные услуги Росреестра: полный гид',
                'category': 'property_law',
                'type': 'step_by_step_guide'
            },
            {
                'title': 'Банкротство физлица: когда и как подавать',
                'category': 'bankruptcy',
                'type': 'legal_analysis'
            },
            {
                'title': 'Налоговые вычеты 2024: что изменилось',
                'category': 'tax_law',
                'type': 'urgent_alert'
            },
            {
                'title': 'Семейные споры: как защитить интересы детей',
                'category': 'family_law',
                'type': 'practical_solution'
            },
            {
                'title': 'Административные штрафы: новые правила обжалования',
                'category': 'administrative_law',
                'type': 'step_by_step_guide'
            },
            {
                'title': 'Жилищные права: как бороться с управляющей компанией',
                'category': 'housing_law',
                'type': 'practical_solution'
            }
        ]

        topic = random.choice(educational_topics)
        return await self._create_educational_content(topic)

    async def _create_educational_content(self, topic: Dict) -> str:
        """Создание образовательного контента с AI"""

        # Создаем продвинутый промпт для образовательного поста
        system_prompt = f"""Ты - ведущий юрист-эксперт, создающий практические гиды для обычных граждан.

ЗАДАЧА: Создать максимально полезный пост на тему "{topic['title']}"

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА:
1. ПОШАГОВЫЙ АЛГОРИТМ (4-6 конкретных шагов)
2. ВОЗМОЖНЫЕ ПРОБЛЕМЫ (3-4 типичные ситуации)
3. ПОЛЕЗНЫЕ РЕСУРСЫ (официальные сайты и телефоны)
4. ПРАКТИЧЕСКИЕ СОВЕТЫ (что делать, если что-то пошло не так)

ТРЕБОВАНИЯ:
✅ Конкретные действия с указанием сроков
✅ Реальные ссылки на госресурсы
✅ Предупреждения о подводных камнях
✅ Простые формулировки для обычных людей
✅ Эмодзи для структурирования
✅ Объем: 600-800 символов

СТИЛЬ: Экспертный, но понятный. Как будто объясняешь другу."""

        user_prompt = f"""Создай подробный практический гид: "{topic['title']}"

Включи:
- Четкий алгоритм действий по шагам
- Конкретные сроки и документы
- Официальные ссылки и контакты
- Предупреждения о возможных проблемах
- Советы при возникновении трудностей

Категория: {topic['category']}
Тип поста: {topic['type']}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            ai_response = await generate_ai_response(messages, model="openai/gpt-4o", max_tokens=1000)

            # Парсим ответ AI и структурируем
            structured_content = self._parse_educational_response(
                ai_response, topic)

            # Форматируем по шаблону
            template = self.enhanced_templates.get(
                topic['type'], self.enhanced_templates['step_by_step_guide'])

            return template.format(**structured_content)

        except Exception as e:
            logger.error(f"Failed to generate educational content: {e}")
            return await self._create_fallback_post(topic)

    def _parse_educational_response(self, ai_response: str, topic: Dict) -> Dict[str, str]:
        """Парсинг образовательного ответа AI в структурированный формат"""

        # Базовая структура
        result = {
            'title': topic['title'],
            'step_algorithm': '',
            'potential_problems': '',
            'useful_resources': '',
            'key_changes': '',
            'citizen_actions': '',
            'warnings': '',
            'official_sources': '',
            'solution_steps': '',
            'statistics': '',
            'practical_tips': '',
            'additional_info': '',
            'urgent_actions': '',
            'important_dates': '',
            'target_audience': '',
            'required_documents': ''
        }

        # Разбиваем ответ на секции
        lines = ai_response.split('\n')
        current_section = 'step_algorithm'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Определяем секцию по ключевым словам
            line_lower = line.lower()

            if any(word in line_lower for word in ['шаг', 'алгоритм', 'действия', 'порядок']):
                current_section = 'step_algorithm'
            elif any(word in line_lower for word in ['проблем', 'трудност', 'ошибк', 'подводн']):
                current_section = 'potential_problems'
            elif any(word in line_lower for word in ['ресурс', 'сайт', 'ссылк', 'контакт']):
                current_section = 'useful_resources'
            elif any(word in line_lower for word in ['совет', 'рекоменд', 'tip']):
                current_section = 'practical_tips'
            elif any(word in line_lower for word in ['документ', 'справк', 'заявлен']):
                current_section = 'required_documents'
            elif any(word in line_lower for word in ['срок', 'дата', 'время']):
                current_section = 'important_dates'

            # Добавляем контент в нужную секцию
            if result[current_section]:
                result[current_section] += f"\n{line}"
            else:
                result[current_section] = line

        # Дополняем ресурсами из базы знаний
        if not result['useful_resources']:
            result['useful_resources'] = self._get_relevant_resources(
                topic['category'])

        # Дополняем типовыми проблемами
        if not result['potential_problems']:
            result['potential_problems'] = self._get_relevant_problems(
                topic['category'])

        return result

    def _get_relevant_resources(self, category: str) -> str:
        """Получение релевантных ресурсов из базы знаний"""

        # Выбираем подходящие ресурсы по категории
        if 'consumer' in category or 'protection' in category:
            resources = self.resource_database['consumer_protection']
        elif 'government' in category or 'tax' in category:
            resources = self.resource_database['government_sites']
        else:
            resources = self.resource_database['legal_assistance']

        return '\n'.join(random.sample(resources, min(3, len(resources))))

    def _get_relevant_problems(self, category: str) -> str:
        """Получение релевантных проблем из базы знаний"""

        if 'procedure' in category or 'legal' in category:
            problems = self.common_problems['legal_procedures']
        elif 'documentation' in category:
            problems = self.common_problems['documentation']
        else:
            problems = self.common_problems['bureaucracy']

        return '\n'.join(random.sample(problems, min(3, len(problems))))

    async def _create_fallback_post(self, topic: Dict) -> str:
        """Создание резервного поста при ошибке AI"""

        return f"""🎯 **{topic['title']}**

📋 **ВАЖНАЯ ИНФОРМАЦИЯ:**
Данная тема требует индивидуального подхода и детального изучения всех обстоятельств.

⚠️ **РЕКОМЕНДАЦИИ:**
• Обратитесь за персональной консультацией
• Подготовьте все имеющиеся документы
• Не откладывайте решение вопроса

🔗 **ПОЛЕЗНЫЕ РЕСУРСЫ:**
{self._get_relevant_resources(topic['category'])}

📞 **ПОЛУЧИТЬ ПОМОЩЬ:**
Персональная консультация юриста: /start"""

    def _determine_enhanced_post_type(self, news_item: NewsItem) -> str:
        """Определение типа поста для новости"""

        title_content = f"{news_item.title} {news_item.content}".lower()

        if any(word in title_content for word in ['срочно', 'важно', 'внимание', 'до']):
            return 'urgent_alert'
        elif any(word in title_content for word in ['как', 'инструкция', 'порядок', 'шаг']):
            return 'step_by_step_guide'
        elif any(word in title_content for word in ['решение', 'проблема', 'способ']):
            return 'practical_solution'
        else:
            return 'legal_analysis'

    async def _create_structured_content(self, news_item: NewsItem, post_type: str) -> Dict[str, str]:
        """Создание структурированного контента для новости"""

        enhanced_prompt = f"""Ты - ведущий юрист-аналитик, создающий структурированные посты для граждан.

ИСХОДНАЯ НОВОСТЬ: {news_item.title}
КОНТЕНТ: {news_item.content}
ТИП ПОСТА: {post_type}

ЗАДАЧА: Создать максимально полезный пост с практической ценностью.

ОБЯЗАТЕЛЬНЫЕ ЭЛЕМЕНТЫ:
✅ Конкретные пошаговые действия
✅ Предупреждения о возможных проблемах  
✅ Ссылки на официальные ресурсы
✅ Практические советы для граждан
✅ Четкие сроки и требования

СТИЛЬ: Экспертный, структурированный, максимально полезный.
ОБЪЕМ: 600-800 символов.
"""

        messages = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": f"Проанализируй новость и создай структурированный пост: {news_item.title}"}
        ]

        try:
            ai_response = await generate_ai_response(messages, model="openai/gpt-4o", max_tokens=1000)
            return self._parse_news_response(ai_response, news_item)

        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return self._create_basic_news_content(news_item)

    def _parse_news_response(self, ai_response: str, news_item: NewsItem) -> Dict[str, str]:
        """Парсинг ответа AI для новостных постов"""

        # Используем тот же метод парсинга, что и для образовательных постов
        return self._parse_educational_response(ai_response, {
            'title': news_item.title,
            'category': news_item.category,
            'type': 'news_analysis'
        })

    def _create_basic_news_content(self, news_item: NewsItem) -> Dict[str, str]:
        """Создание базового контента при ошибке AI"""

        return {
            'title': news_item.title,
            'step_algorithm': "1. Изучите изменения в законодательстве\n2. Оцените влияние на вашу ситуацию\n3. При необходимости обратитесь к юристу",
            'potential_problems': "• Неправильная трактовка изменений\n• Пропуск важных деталей\n• Несвоевременная реакция",
            'useful_resources': self._get_relevant_resources('general'),
            'key_changes': news_item.content[:200] + "...",
            'citizen_actions': "Рекомендуется получить персональную консультацию для оценки влияния изменений на вашу ситуацию.",
            'warnings': "Не принимайте решений без консультации с квалифицированным юристом.",
            'official_sources': "Официальную информацию уточняйте на сайтах государственных органов."
        }

    def _format_enhanced_post(self, content: Dict[str, str], post_type: str) -> str:
        """Форматирование поста по улучшенному шаблону"""

        template = self.enhanced_templates.get(
            post_type, self.enhanced_templates['step_by_step_guide'])

        try:
            formatted_post = template.format(**content)

            # Проверяем длину и при необходимости сокращаем
            if len(formatted_post) > 1000:
                # Сокращаем самые длинные секции
                for key in ['step_algorithm', 'solution_steps', 'key_changes']:
                    if key in content and len(content[key]) > 150:
                        content[key] = content[key][:150] + "..."

                formatted_post = template.format(**content)

            return formatted_post

        except KeyError as e:
            logger.warning(f"Missing template key {e}")
            return self._create_emergency_fallback(content)

    def _create_emergency_fallback(self, content: Dict[str, str]) -> str:
        """Экстренный fallback при ошибках форматирования"""

        title = content.get('title', 'Важная юридическая информация')

        return f"""🎯 **{title}**

📋 **ОСНОВНАЯ ИНФОРМАЦИЯ:**
{content.get('step_algorithm', content.get('key_changes', 'Подробности в консультации'))}

⚠️ **ВАЖНО ЗНАТЬ:**
{content.get('potential_problems', content.get('warnings', 'Требует индивидуального рассмотрения'))}

🔗 **ПОЛЕЗНЫЕ РЕСУРСЫ:**
{content.get('useful_resources', '🏛️ Госуслуги: gosuslugi.ru')}

📞 **ПОЛУЧИТЬ ПОМОЩЬ:**
Персональная консультация: /start"""
