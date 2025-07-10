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

        # Создаем ЧЕТКИЙ промпт для избежания дублирования
        system_prompt = f"""Ты - ведущий юрист-эксперт. Создай СТРОГО СТРУКТУРИРОВАННЫЙ пост.

ТЕМА: {topic['title']}

ВАЖНО! Отвечай ТОЛЬКО содержимым разделов, без повторения заголовков!

ФОРМАТ ОТВЕТА:
АЛГОРИТМ:
[здесь 4-5 четких шагов с номерами]

ПРОБЛЕМЫ:
[здесь 3-4 проблемы с символом •]

РЕСУРСЫ:
[здесь 3 ресурса с эмодзи и ссылками]

СОВЕТЫ:
[здесь 2-3 практических совета]

ТРЕБОВАНИЯ:
- НЕ дублируй названия разделов
- НЕ повторяй заголовок темы
- Используй четкую нумерацию 1., 2., 3.
- Каждая проблема начинается с •
- Ресурсы в формате: 🏛️ Название: ссылка
- Объем каждого раздела: 100-150 символов
- Простые формулировки для граждан"""

        user_prompt = f"""Создай содержимое разделов для темы: {topic['title']}

Категория: {topic['category']}
Тип: {topic['type']}

НЕ повторяй заголовки! Только содержимое разделов!"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            ai_response = await generate_ai_response(messages, model="openai/gpt-4o", max_tokens=800)

            # УЛУЧШЕННЫЙ парсинг для избежания дублирования
            structured_content = self._parse_clean_response(ai_response, topic)

            # Форматируем по шаблону
            template = self.enhanced_templates.get(
                topic['type'], self.enhanced_templates['step_by_step_guide'])

            return template.format(**structured_content)

        except Exception as e:
            logger.error(f"Failed to generate educational content: {e}")
            return await self._create_fallback_post(topic)

    def _parse_clean_response(self, ai_response: str, topic: Dict) -> Dict[str, str]:
        """УЛУЧШЕННЫЙ парсинг AI ответа без дублирования"""

        # Базовая структура
        result = {
            'title': topic['title'],
            'step_algorithm': '',
            'potential_problems': '',
            'useful_resources': '',
            'practical_tips': '',
            'key_changes': '',
            'citizen_actions': '',
            'warnings': '',
            'official_sources': '',
            'solution_steps': '',
            'statistics': '',
            'additional_info': '',
            'urgent_actions': '',
            'important_dates': '',
            'target_audience': '',
            'required_documents': ''
        }

        # Очищаем ответ от мусора
        cleaned_response = ai_response.strip()

        # Удаляем дублирование заголовка темы
        title_variations = [
            topic['title'],
            topic['title'].lower(),
            topic['title'].upper()
        ]

        for title_var in title_variations:
            cleaned_response = cleaned_response.replace(title_var, '').strip()

        # Разбиваем по четким маркерам
        sections = {}
        current_section = None
        current_content = []

        lines = cleaned_response.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Определяем начало новой секции
            line_upper = line.upper()

            if any(marker in line_upper for marker in ['АЛГОРИТМ:', 'ДЕЙСТВИЯ:', 'ШАГИ:']):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'algorithm'
                current_content = []
                continue

            elif any(marker in line_upper for marker in ['ПРОБЛЕМЫ:', 'ТРУДНОСТИ:', 'ОШИБКИ:']):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'problems'
                current_content = []
                continue

            elif any(marker in line_upper for marker in ['РЕСУРСЫ:', 'ССЫЛКИ:', 'САЙТЫ:']):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'resources'
                current_content = []
                continue

            elif any(marker in line_upper for marker in ['СОВЕТЫ:', 'РЕКОМЕНДАЦИИ:', 'TIPS:']):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'tips'
                current_content = []
                continue

            # Добавляем контент в текущую секцию
            if current_section:
                # Очищаем от лишних символов
                clean_line = line.replace('**', '').replace('*', '').strip()
                if clean_line and not clean_line.startswith('#'):
                    current_content.append(clean_line)

        # Добавляем последнюю секцию
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)

        # Заполняем результат
        if 'algorithm' in sections:
            result['step_algorithm'] = self._clean_algorithm(
                sections['algorithm'])
            result['solution_steps'] = result['step_algorithm']
            result['urgent_actions'] = result['step_algorithm']

        if 'problems' in sections:
            result['potential_problems'] = self._clean_problems(
                sections['problems'])
            result['warnings'] = result['potential_problems']

        if 'resources' in sections:
            result['useful_resources'] = self._clean_resources(
                sections['resources'])
            result['official_sources'] = result['useful_resources']

        if 'tips' in sections:
            result['practical_tips'] = self._clean_tips(sections['tips'])
            result['citizen_actions'] = result['practical_tips']
            result['additional_info'] = result['practical_tips']

        # Дополняем пустые поля качественным контентом
        if not result['step_algorithm']:
            result['step_algorithm'] = self._generate_default_algorithm(topic)

        if not result['potential_problems']:
            result['potential_problems'] = self._get_relevant_problems(
                topic['category'])

        if not result['useful_resources']:
            result['useful_resources'] = self._get_relevant_resources(
                topic['category'])

        return result

    def _clean_algorithm(self, text: str) -> str:
        """Очистка алгоритма"""
        lines = text.split('\n')
        cleaned_lines = []

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # Убираем лишние номера и символы
            line = line.replace('**', '').replace('*', '').strip()

            # Добавляем номер если его нет
            if not line[0].isdigit():
                line = f"{i}. {line}"

            cleaned_lines.append(line)

            # Ограничиваем количество шагов
            if len(cleaned_lines) >= 5:
                break

        return '\n'.join(cleaned_lines)

    def _clean_problems(self, text: str) -> str:
        """Очистка проблем"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Убираем лишние символы
            line = line.replace('**', '').replace('*', '').strip()

            # Добавляем маркер если его нет
            if not line.startswith('•') and not line.startswith('-'):
                line = f"• {line}"
            elif line.startswith('-'):
                line = line.replace('-', '•', 1)

            cleaned_lines.append(line)

            # Ограничиваем количество проблем
            if len(cleaned_lines) >= 4:
                break

        return '\n'.join(cleaned_lines)

    def _clean_resources(self, text: str) -> str:
        """Очистка ресурсов"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Убираем лишние символы
            line = line.replace('**', '').replace('*', '').strip()

            # Если нет эмодзи, добавляем
            if not any(char in line for char in ['🏛️', '📋', '💼', '🛡️', '📞']):
                if 'госуслуги' in line.lower():
                    line = f"🏛️ {line}"
                elif 'роспотребнадзор' in line.lower():
                    line = f"🛡️ {line}"
                elif 'росреестр' in line.lower():
                    line = f"📋 {line}"
                else:
                    line = f"💼 {line}"

            cleaned_lines.append(line)

            # Ограничиваем количество ресурсов
            if len(cleaned_lines) >= 3:
                break

        return '\n'.join(cleaned_lines)

    def _clean_tips(self, text: str) -> str:
        """Очистка советов"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Убираем лишние символы
            line = line.replace('**', '').replace('*', '').strip()

            # Добавляем маркер если его нет
            if not line.startswith('•') and not line.startswith('-'):
                line = f"• {line}"
            elif line.startswith('-'):
                line = line.replace('-', '•', 1)

            cleaned_lines.append(line)

            # Ограничиваем количество советов
            if len(cleaned_lines) >= 3:
                break

        return '\n'.join(cleaned_lines)

    def _generate_default_algorithm(self, topic: Dict) -> str:
        """Генерация алгоритма по умолчанию"""

        default_algorithms = {
            'consumer_protection': '''1. Соберите документы (чеки, договоры)
2. Зафиксируйте нарушение (фото, видео)
3. Обратитесь к продавцу с претензией
4. Подайте жалобу в Роспотребнадзор
5. Дождитесь решения в течение 30 дней''',

            'labor_law': '''1. Изучите трудовой договор и законы
2. Соберите доказательства нарушения
3. Обратитесь к работодателю письменно
4. Подайте жалобу в трудовую инспекцию
5. При необходимости - в суд''',

            'housing_law': '''1. Изучите управляющий договор
2. Зафиксируйте проблему документально
3. Подайте заявление в УК
4. Обратитесь в жилищную инспекцию
5. Подайте иск в суд при необходимости'''
        }

        category = topic.get('category', 'general')

        for key, algorithm in default_algorithms.items():
            if key in category:
                return algorithm

        return '''1. Изучите применимое законодательство
2. Соберите необходимые документы
3. Обратитесь в компетентный орган
4. Подайте официальное заявление
5. Отслеживайте рассмотрение вопроса'''

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
