"""
🧠 ADVANCED CONTENT ENGINE
AI-powered content generation with trends, personalization and viral mechanics
"""

import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Типы контента для максимального разнообразия"""
    VIRAL_CASE_STUDY = "viral_case_study"           # Вирусные кейсы
    TRENDING_LEGAL_NEWS = "trending_legal_news"     # Актуальные новости права
    INTERACTIVE_QUIZ = "interactive_quiz"           # Интерактивные опросы
    EXPERT_OPINION = "expert_opinion"               # Экспертные мнения
    CLIENT_SUCCESS_STORY = "client_success_story"   # Истории успеха
    LEGAL_LIFE_HACK = "legal_life_hack"            # Лайфхаки
    CONTROVERSIAL_TOPIC = "controversial_topic"     # Провокационные темы
    BEHIND_SCENES = "behind_scenes"                 # Закулисье работы
    MYTH_BUSTING = "myth_busting"                  # Развенчание мифов
    SEASONAL_CONTENT = "seasonal_content"           # Сезонный контент


class EngagementMechanic(Enum):
    """Механики вовлечения"""
    QUESTION_WITH_POLL = "question_with_poll"
    CASE_DISCUSSION = "case_discussion"
    LEGAL_CHALLENGE = "legal_challenge"
    EXPERT_AMA = "expert_ama"
    PREDICTION_GAME = "prediction_game"
    BEFORE_AFTER = "before_after"
    COMMUNITY_VOTE = "community_vote"


@dataclass
class ContentPiece:
    """Структура контента"""
    content_type: ContentType
    text: str
    engagement_mechanics: List[EngagementMechanic]
    target_segments: List[str]
    hashtags: List[str]
    optimal_publish_time: datetime
    expected_engagement: float
    viral_potential: float
    conversion_potential: float
    discussion_triggers: List[str]
    ab_test_variant: Optional[str] = None


@dataclass
class TrendData:
    """Данные о трендах"""
    trending_keywords: List[str]
    hot_topics: List[str]
    viral_formats: List[str]
    seasonal_events: List[str]
    competitor_analysis: Dict[str, Any]


class AdvancedContentEngine:
    """Продвинутый движок создания контента"""

    def __init__(self):
        self.content_templates = self._load_content_templates()
        self.trend_tracker = TrendTracker()
        self.personalization_engine = PersonalizationEngine()
        self.viral_optimizer = ViralOptimizer()

    async def generate_optimized_content(
        self,
        audience_insights: Dict[str, Any],
        force_type: Optional[ContentType] = None
    ) -> ContentPiece:
        """Генерация оптимизированного контента с учетом аудитории и трендов"""

        try:
            # 1. Анализ трендов
            trends = await self.trend_tracker.get_current_trends()

            # 2. Выбор типа контента
            content_type = force_type or await self._select_optimal_content_type(
                audience_insights, trends
            )

            # 3. Генерация контента
            content = await self._generate_content_by_type(content_type, trends, audience_insights)

            # 4. Оптимизация для вирусности
            content = await self.viral_optimizer.optimize_for_virality(content)

            # 5. Добавление интерактивных элементов
            content = await self._add_engagement_mechanics(content, audience_insights)

            logger.info(
                f"Generated {content_type.value} content with {content.viral_potential:.2f} viral potential")

            return content

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return await self._generate_fallback_content()

    async def _select_optimal_content_type(
        self,
        audience_insights: Dict[str, Any],
        trends: TrendData
    ) -> ContentType:
        """Выбор оптимального типа контента на основе данных"""

        # Веса для разных типов контента
        content_weights = {
            ContentType.VIRAL_CASE_STUDY: 25,       # Высокое вовлечение
            ContentType.TRENDING_LEGAL_NEWS: 20,    # Актуальность
            ContentType.INTERACTIVE_QUIZ: 15,       # Интерактивность
            ContentType.LEGAL_LIFE_HACK: 15,        # Практичность
            ContentType.CONTROVERSIAL_TOPIC: 10,    # Вирусность
            ContentType.CLIENT_SUCCESS_STORY: 5,    # Социальное доказательство
            ContentType.EXPERT_OPINION: 5,          # Экспертность
            ContentType.BEHIND_SCENES: 3,           # Человечность
            ContentType.MYTH_BUSTING: 2,            # Образование
        }

        # Корректировка весов на основе аудитории
        hour = datetime.now().hour
        if 9 <= hour <= 18:  # Рабочее время - больше практического контента
            content_weights[ContentType.LEGAL_LIFE_HACK] *= 1.5
            content_weights[ContentType.TRENDING_LEGAL_NEWS] *= 1.3
        elif 18 <= hour <= 22:  # Вечер - больше развлекательного
            content_weights[ContentType.VIRAL_CASE_STUDY] *= 1.4
            content_weights[ContentType.INTERACTIVE_QUIZ] *= 1.3

        # Учет дня недели
        weekday = datetime.now().weekday()
        if weekday in [5, 6]:  # Выходные
            content_weights[ContentType.BEHIND_SCENES] *= 2
            content_weights[ContentType.CONTROVERSIAL_TOPIC] *= 1.5

        # Выбор с учетом весов
        content_types = list(content_weights.keys())
        weights = list(content_weights.values())

        return random.choices(content_types, weights=weights)[0]

    async def _generate_content_by_type(
        self,
        content_type: ContentType,
        trends: TrendData,
        audience_insights: Dict[str, Any]
    ) -> ContentPiece:
        """Генерация контента по типу"""

        if content_type == ContentType.VIRAL_CASE_STUDY:
            return await self._generate_viral_case_study(trends)
        elif content_type == ContentType.TRENDING_LEGAL_NEWS:
            return await self._generate_trending_news(trends)
        elif content_type == ContentType.INTERACTIVE_QUIZ:
            return await self._generate_interactive_quiz(trends)
        elif content_type == ContentType.LEGAL_LIFE_HACK:
            return await self._generate_legal_lifehack(trends)
        elif content_type == ContentType.CONTROVERSIAL_TOPIC:
            return await self._generate_controversial_topic(trends)
        elif content_type == ContentType.CLIENT_SUCCESS_STORY:
            return await self._generate_success_story(trends)
        elif content_type == ContentType.EXPERT_OPINION:
            return await self._generate_expert_opinion(trends)
        elif content_type == ContentType.BEHIND_SCENES:
            return await self._generate_behind_scenes(trends)
        elif content_type == ContentType.MYTH_BUSTING:
            return await self._generate_myth_busting(trends)
        else:
            return await self._generate_viral_case_study(trends)

    async def _generate_viral_case_study(self, trends: TrendData) -> ContentPiece:
        """Генерация вирусного кейса"""

        viral_cases = [
            {
                "title": "Блогер отсудил 2 млн за использование фото без разрешения",
                "story": """📸 **ВИРУСНАЯ ИСТОРИЯ:**
                
Блогер Анна (500К подписчиков) обнаружила свои фотографии в рекламе косметики без разрешения. Компания заработала на них 10 млн₽.

🔥 **ЧТО СДЕЛАЛА АННА:**
• Зафиксировала все использования через скриншоты и нотариуса
• Потребовала компенсацию 5 млн₽ за нарушение авторских прав
• Подала иск о защите изображения гражданина
• Доказала размер ущерба через экспертизу по доходам

⚖️ **РЕЗУЛЬТАТ:**
Суд взыскал 2 млн₽ + расходы на юристов + моральный вред. Прецедент для всех блогеров!""",
                "legal_aspect": """📚 **ПРАВОВАЯ БАЗА:**
• Статья 152.1 ГК РФ - охрана изображения гражданина
• Статья 1301 ГК РФ - авторские права на фото
• Постановление Пленума ВС №10 - размер компенсации""",
                "action_plan": """💡 **ЧТО ДЕЛАТЬ, ЕСЛИ ЭТО ВАША СИТУАЦИЯ:**
1. 📸 Немедленно фиксируйте нарушение (скриншоты + нотариус)
2. 📧 Направьте досудебную претензию с требованием компенсации
3. 💰 Рассчитайте размер ущерба через доходы нарушителя
4. ⚖️ При отказе - сразу в суд, не теряя время
5. 📊 Требуйте максимальную компенсацию (до 5 млн₽)

🎯 **ВАЖНО:** Срок исковой давности - 3 года с момента нарушения!"""
            },
            {
                "title": "Курьер выиграл суд против Delivery Club на 300,000₽",
                "story": """🛵 **РЕЗОНАНСНОЕ ДЕЛО:**
                
Курьер Михаил работал в Delivery Club как "самозанятый", но суд признал его обычным работником со всеми правами.

🔥 **КЛЮЧЕВЫЕ ФАКТЫ:**
• Жесткий график работы (как у штатных сотрудников)
• Обязательная форма и оборудование от компании  
• Штрафы за отказ от заказов
• Контроль времени доставки через приложение

⚖️ **РЕШЕНИЕ СУДА:**
Признали трудовые отношения + взыскали:
• Доплату до МРОТ за 2 года: 180,000₽
• Отпускные: 50,000₽  
• Компенсацию сверхурочных: 70,000₽
• Моральный вред: 30,000₽""",
                "legal_aspect": """📚 **ПРАВОВАЯ РЕВОЛЮЦИЯ:**
Это решение меняет всю gig-экономику России!

• Uber, Яндекс.Такси, Delivery теперь под ударом
• Суды будут смотреть на факты, а не на договоры
• Миллионы курьеров и водителей получили защиту""",
                "action_plan": """💡 **ИНСТРУКЦИЯ ДЛЯ КУРЬЕРОВ/ВОДИТЕЛЕЙ:**
1. 📊 Ведите учет всех заказов и времени работы
2. 📱 Сохраняйте переписку с диспетчерами/поддержкой
3. 📸 Фиксируйте требования носить форму/использовать оборудование
4. 💰 Рассчитайте недоплаченную сумму до МРОТ
5. ⚖️ Обращайтесь в суд для признания трудовых отношений

🎯 **ШАНС:** У каждого курьера есть право на доплату за прошлые годы!"""
            }
        ]

        selected_case = random.choice(viral_cases)

        content_text = f"""🔥 **{selected_case['title'].upper()}**

{selected_case['story']}

{selected_case['legal_aspect']}

{selected_case['action_plan']}

💼 **ПОПАЛИ В ПОХОЖУЮ СИТУАЦИЮ?**
Не знаете, как защитить свои права?

🎯 Наши юристы специализируются на резонансных делах:
✅ Анализируем перспективы вашего дела БЕСПЛАТНО
✅ Разрабатываем стратегию с учетом актуальной практики  
✅ Ведем дело до победного результата
✅ Работаем по принципу "нет результата - нет оплаты"

💬 Получить план действий: /start
📞 Экстренная консультация: свяжемся за 15 минут!

#ВирусныеДела #ЗащитаПрав #СудебнаяПрактика #ЮридическаяПомощь"""

        return ContentPiece(
            content_type=ContentType.VIRAL_CASE_STUDY,
            text=content_text,
            engagement_mechanics=[
                EngagementMechanic.CASE_DISCUSSION,
                EngagementMechanic.COMMUNITY_VOTE
            ],
            target_segments=["все_сегменты"],
            hashtags=["#ВирусныеДела", "#ЗащитаПрав", "#СудебнаяПрактика"],
            optimal_publish_time=datetime.now() + timedelta(hours=1),
            expected_engagement=0.85,
            viral_potential=0.9,
            conversion_potential=0.7,
            discussion_triggers=[
                "А у вас были похожие случаи?",
                "Поделитесь своим опытом в комментариях",
                "Как думаете, справедливое решение?"
            ]
        )

    async def _generate_trending_news(self, trends: TrendData) -> ContentPiece:
        """Генерация актуальных новостей права"""

        trending_news = [
            {
                "title": "Госдума приняла закон о криптовалютах: что изменится",
                "news": """⚡ **BREAKING NEWS:**
                
С 1 февраля 2025 года в России легализованы операции с криптовалютами для физлиц!

🆕 **ЧТО РАЗРЕШИЛИ:**
• Покупка и продажа криптовалют через российские биржи
• Уплата налогов с прибыли (13% для резидентов)
• Наследование криптоактивов по завещанию
• Использование в качестве средства платежа (лимит 600,000₽/год)

🚫 **ЧТО ЗАПРЕЩЕНО:**
• Майнинг без регистрации ИП (штраф до 500,000₽)
• Операции через зарубежные биржи (штраф до 1 млн₽)
• Сокрытие доходов от ФНС (уголовная ответственность)""",
                "impact": """📈 **КАК ЭТО ВЛИЯЕТ НА ВАС:**

👥 **ДЛЯ ФИЗЛИЦ:**
✅ Легальная торговля криптой без страха санкций
✅ Защита инвестиций государством  
✅ Возможность получить налоговые вычеты
⚠️ Обязательная декларация доходов

👨‍💼 **ДЛЯ БИЗНЕСА:**
✅ Новые возможности привлечения инвестиций
✅ Интеграция блокчейн-технологий
⚠️ Строгое регулирование и лицензирование

💰 **ДЛЯ ИНВЕСТОРОВ:**
✅ Рост доверия к российской криптоиндустрии
✅ Снижение рисков заморозки активов
⚠️ Необходимость пересмотра налоговых стратегий""",
                "action": """💡 **ЧТО ДЕЛАТЬ ПРЯМО СЕЙЧАС:**

📋 **ЕСЛИ У ВАС ЕСТЬ КРИПТОВАЛЮТЫ:**
1. Подготовьте отчет обо всех операциях с 2021 года
2. Рассчитайте налоговые обязательства  
3. Подайте уточненные декларации до 31 марта
4. Переведите активы на российские площадки

🚀 **ЕСЛИ ПЛАНИРУЕТЕ ИНВЕСТИРОВАТЬ:**
1. Дождитесь запуска лицензированных российских бирж
2. Изучите налоговые последствия операций
3. Рассмотрите открытие ИИС для льгот по налогам

⚖️ **ЕСЛИ НУЖНА ЮРИДИЧЕСКАЯ ПОМОЩЬ:**
• Консультация по легализации криптоактивов
• Подготовка документов для налоговой
• Защита при налоговых проверках"""
            }
        ]

        selected_news = random.choice(trending_news)

        content_text = f"""⚡ **СРОЧНЫЕ НОВОСТИ: {selected_news['title'].upper()}**

{selected_news['news']}

{selected_news['impact']}

{selected_news['action']}

💼 **НУЖНА ПОМОЩЬ С НОВЫМ ЗАКОНОМ?**
Запутались в нововведениях? Не знаете, как действовать?

🎯 Наши эксперты по финансовому праву помогут:
✅ Разобраться во всех тонкостях нового закона
✅ Оценить влияние на вашу ситуацию  
✅ Подготовить все необходимые документы
✅ Обеспечить полное соответствие требованиям

💬 Срочная консультация: /start
📞 Горячая линия по новому закону!

#НовыйЗакон #Криптовалюты #ФинансовоеПраво #НалоговоеПраво"""

        return ContentPiece(
            content_type=ContentType.TRENDING_LEGAL_NEWS,
            text=content_text,
            engagement_mechanics=[
                EngagementMechanic.EXPERT_AMA,
                EngagementMechanic.QUESTION_WITH_POLL
            ],
            target_segments=["инвесторы", "бизнес", "молодежь"],
            hashtags=["#НовыйЗакон", "#Криптовалюты", "#ФинансовоеПраво"],
            optimal_publish_time=datetime.now() + timedelta(hours=1),
            expected_engagement=0.7,
            viral_potential=0.8,
            conversion_potential=0.6,
            discussion_triggers=[
                "Как думаете, это хорошо или плохо?",
                "У кого есть криптовалюты? Поделитесь планами",
                "Какие вопросы по новому закону?"
            ]
        )

    async def _generate_interactive_quiz(self, trends: TrendData) -> ContentPiece:
        """Генерация интерактивного опроса"""

        quiz_topics = [
            {
                "title": "Тест: Знаете ли вы свои права потребителя?",
                "intro": """🧠 **ПРОВЕРЬТЕ СВОИ ЗНАНИЯ!**
                
Ответьте на 5 вопросов и узнайте, насколько хорошо вы знаете права потребителя. В комментариях пишите свои ответы!""",
                "questions": [
                    "❓ **Вопрос 1:** Можно ли вернуть товар надлежащего качества в интернет-магазин?\nА) Нет, только бракованный\nБ) Да, в течение 7 дней\nВ) Да, в течение 14 дней\nГ) Да, в течение 30 дней",

                    "❓ **Вопрос 2:** Кто должен доказывать, что поломка произошла не по вине покупателя?\nА) Покупатель\nБ) Продавец  \nВ) Независимый эксперт\nГ) Производитель",

                    "❓ **Вопрос 3:** Максимальный размер морального вреда в потребительских спорах:\nА) 1,000₽\nБ) 10,000₽\nВ) 50,000₽\nГ) Не ограничен",

                    "❓ **Вопрос 4:** Срок рассмотрения претензии продавцом:\nА) 3 дня\nБ) 10 дней\nВ) 30 дней\nГ) Зависит от товара",

                    "❓ **Вопрос 5:** Можно ли требовать возврата денег за некачественную услугу?\nА) Нет, только повторное оказание\nБ) Да, но только частично\nВ) Да, полностью\nГ) Только через суд"
                ],
                "answers": """✅ **ПРАВИЛЬНЫЕ ОТВЕТЫ:**
1. В) 14 дней (для интернет-покупок)
2. Б) Продавец (если товар на гарантии)  
3. Г) Не ограничен (суды присуждают и 100,000₽+)
4. Б) 10 дней (для товаров)
5. В) Да, полностью + компенсация расходов

🏆 **РЕЗУЛЬТАТЫ:**
• 5 правильных - Вы эксперт по защите прав! 👨‍⚖️
• 3-4 правильных - Хорошие знания, но есть пробелы 📚  
• 1-2 правильных - Срочно изучайте свои права! ⚠️
• 0 правильных - Вас легко обмануть, нужна помощь юриста! 🆘"""
            }
        ]

        selected_quiz = random.choice(quiz_topics)

        questions_text = "\n\n".join(selected_quiz["questions"])

        content_text = f"""🎯 **{selected_quiz['title'].upper()}**

{selected_quiz['intro']}

{questions_text}

💭 **КАК УЧАСТВОВАТЬ:**
1. Ответьте на вопросы в комментариях (например: 1-В, 2-Б, 3-А...)
2. Через час опубликуем правильные ответы
3. Лучшие знатоки получат бесплатную консультацию! 🎁

{selected_quiz['answers']}

💼 **ХОТИТЕ ЗНАТЬ БОЛЬШЕ?**
Изучите все тонкости защиты прав потребителей!

🎯 Наша программа "Права потребителя от А до Я":
✅ Все актуальные законы простым языком
✅ Готовые шаблоны претензий и исков
✅ Разбор реальных кейсов и судебной практики
✅ Персональные консультации по вашим вопросам

💬 Узнать подробности: /start
📚 Станьте экспертом по защите своих прав!

#ТестПоПравам #ЗащитаПотребителей #ПравоваяГрамотность #ИнтерактивОбучение"""

        return ContentPiece(
            content_type=ContentType.INTERACTIVE_QUIZ,
            text=content_text,
            engagement_mechanics=[
                EngagementMechanic.COMMUNITY_VOTE,
                EngagementMechanic.PREDICTION_GAME
            ],
            target_segments=["все_сегменты"],
            hashtags=["#ТестПоПравам", "#ЗащитаПотребителей", "#Обучение"],
            optimal_publish_time=datetime.now() + timedelta(hours=1),
            expected_engagement=0.9,
            viral_potential=0.75,
            conversion_potential=0.5,
            discussion_triggers=[
                "Отвечайте в комментариях!",
                "Кто наберет 5 из 5?",
                "Поделитесь своими результатами"
            ]
        )

    async def _generate_legal_lifehack(self, trends: TrendData) -> ContentPiece:
        """Генерация правового лайфхака"""

        lifehacks = [
            {
                "title": "Лайфхак: Как получить скидку на штрафы ГИБДД до 50%",
                "hack": """💰 **СЕКРЕТ, КОТОРЫЙ СКРЫВАЮТ ГИБДДШНИКИ:**
                
Вы можете ЗАКОННО уменьшить любой штраф ГИБДД в 2 раза! Но мало кто знает, как это работает.

🎯 **МАГИЧЕСКАЯ ФОРМУЛА:**
**50% скидка** = оплата в течение 20 дней + правильное основание

📋 **ПОШАГОВЫЙ АЛГОРИТМ:**
1. Получили постановление? Не спешите платить!
2. Внимательно изучите дату вынесения (не вручения!)
3. У вас есть 20 дней с даты ВЫНЕСЕНИЯ для скидки
4. Оплачивайте через госуслуги (там автоматически применяется скидка)
5. Сохраните чек - это защита от двойного штрафа""",
                "exceptions": """⚠️ **ВАЖНЫЕ ИСКЛЮЧЕНИЯ:**
Скидка НЕ действует на штрафы за:
• Повторные нарушения в течение года  
• Вождение в нетрезвом виде
• Причинение вреда здоровью
• Отказ от медосвидетельствования
• Превышение скорости на 40+ км/ч""",
                "bonus": """🎁 **БОНУС-ЛАЙФХАК:**
Если вы не успели оплатить в 20 дней, но прошло меньше 70 дней - подавайте жалобу! 

📝 **Текст жалобы:**
"Прошу отменить постановление в связи с отсутствием состава правонарушения" + любое формальное обоснование.

🎯 **Результат:** 
• Жалобу рассматривают 10 дней
• За это время 20-дневный срок восстанавливается  
• Платите со скидкой 50% даже через месяц!

💡 **Работает в 90% случаев!**"""
            }
        ]

        selected_hack = random.choice(lifehacks)

        content_text = f"""💡 **{selected_hack['title'].upper()}**

{selected_hack['hack']}

{selected_hack['exceptions']}

{selected_hack['bonus']}

💼 **ПОПАЛИ В СЛОЖНУЮ СИТУАЦИЮ С ГИБДД?**
Незаконный штраф? Лишение прав? Спорная ситуация?

🎯 Наши автоюристы помогут:
✅ Обжаловать любые постановления ГИБДД
✅ Вернуть права после лишения досрочно
✅ Доказать невиновность в ДТП
✅ Сэкономить десятки тысяч рублей на штрафах

💬 Бесплатная консультация: /start  
🚗 Защитим ваши права на дороге!

💾 **СОХРАНИТЕ ЭТОТ ПОСТ** - пригодится каждому водителю!

#ЛайфхакиГИБДД #Штрафы #АвтоЮрист #ЗащитаПрав #Автомобилисты"""

        return ContentPiece(
            content_type=ContentType.LEGAL_LIFE_HACK,
            text=content_text,
            engagement_mechanics=[
                EngagementMechanic.BEFORE_AFTER,
                EngagementMechanic.CASE_DISCUSSION
            ],
            target_segments=["автомобилисты", "все_сегменты"],
            hashtags=["#ЛайфхакиГИБДД", "#Штрафы", "#АвтоЮрист"],
            optimal_publish_time=datetime.now() + timedelta(hours=1),
            expected_engagement=0.8,
            viral_potential=0.85,
            conversion_potential=0.6,
            discussion_triggers=[
                "Сохраняйте, пригодится!",
                "У кого получилось сэкономить таким способом?",
                "Поделитесь своими историями со штрафами"
            ]
        )

    async def _add_engagement_mechanics(
        self,
        content: ContentPiece,
        audience_insights: Dict[str, Any]
    ) -> ContentPiece:
        """Добавление механик вовлечения"""

        # Добавляем интерактивные элементы в зависимости от типа контента
        if ContentType.INTERACTIVE_QUIZ in [content.content_type]:
            content.text += "\n\n💬 **ОБСУЖДЕНИЕ В КОММЕНТАРИЯХ:** Напишите ваши ответы!"

        if ContentType.CONTROVERSIAL_TOPIC in [content.content_type]:
            content.text += "\n\n🔥 **ВАШ ГОЛОС:** Согласны с таким решением? Да/Нет в комментариях!"

        # Добавляем призыв к действию
        discussion_trigger = random.choice(content.discussion_triggers)
        content.text += f"\n\n💭 {discussion_trigger}"

        return content

    async def _generate_fallback_content(self) -> ContentPiece:
        """Резервный контент при ошибках"""

        fallback_text = """⚖️ **ЗНАЕТЕ ЛИ ВЫ?**

В России каждый день нарушаются права 2.5 миллионов граждан. Но только 3% обращаются за защитой к юристам.

🎯 **САМЫЕ ЧАСТЫЕ НАРУШЕНИЯ:**
• Работодатели не выплачивают зарплату в срок - 40%
• Продавцы отказываются менять бракованный товар - 25%  
• УК завышают тарифы без согласования - 20%
• Банки блокируют карты без объяснений - 10%
• Страховые отказывают в выплатах - 5%

💡 **ПРАВДА В ТОМ, что знание своих прав - это:**
✅ Экономия денег (в среднем 50,000₽ в год)
✅ Экономия времени (решение вопросов в 3 раза быстрее)
✅ Уверенность в любых ситуациях
✅ Защита от мошенников

💼 **ХОТИТЕ ИЗМЕНИТЬ СТАТИСТИКУ?**
Станьте одним из 3% тех, кто знает и защищает свои права!

🎯 Получите бесплатную консультацию и узнайте:
✅ Какие права у вас нарушают прямо сейчас
✅ Как получить компенсацию за прошлые нарушения  
✅ Как защитить себя в будущем

💬 Начать защиту прав: /start
⚖️ Не дайте себя обмануть!

#ЗащитаПрав #ЮридическаяПомощь #ЗнайСвоиПрава"""

        return ContentPiece(
            content_type=ContentType.LEGAL_LIFE_HACK,
            text=fallback_text,
            engagement_mechanics=[EngagementMechanic.CASE_DISCUSSION],
            target_segments=["все_сегменты"],
            hashtags=["#ЗащитаПрав", "#ЮридическаяПомощь"],
            optimal_publish_time=datetime.now() + timedelta(hours=1),
            expected_engagement=0.6,
            viral_potential=0.5,
            conversion_potential=0.7,
            discussion_triggers=["Поделитесь своим опытом в комментариях!"]
        )

    def _load_content_templates(self) -> Dict[ContentType, List[str]]:
        """Загрузка шаблонов контента"""
        # В будущем можно вынести в отдельные файлы или БД
        return {}


class TrendTracker:
    """Отслеживание трендов и актуальных тем"""

    async def get_current_trends(self) -> TrendData:
        """Получение текущих трендов"""

        # Базовые тренды (в будущем можно интегрировать с внешними API)
        return TrendData(
            trending_keywords=["криптовалюты", "штрафы ГИБДД",
                               "права потребителей", "самозанятые"],
            hot_topics=["новые законы",
                        "судебная практика", "налоговые льготы"],
            viral_formats=["кейсы из жизни",
                           "лайфхаки", "тесты", "спорные темы"],
            seasonal_events=[],
            competitor_analysis={}
        )


class PersonalizationEngine:
    """Движок персонализации контента"""

    async def personalize_content(
        self,
        content: ContentPiece,
        user_segment: str
    ) -> ContentPiece:
        """Персонализация контента под сегмент аудитории"""
        # Пока заглушка, в будущем - ML персонализация
        return content


class ViralOptimizer:
    """Оптимизатор вирусного потенциала"""

    async def optimize_for_virality(self, content: ContentPiece) -> ContentPiece:
        """Оптимизация контента для вирусности"""

        # Добавляем элементы вирусности
        if content.viral_potential > 0.8:
            # Добавляем эмоциональные хуки
            if "🔥" not in content.text:
                content.text = content.text.replace("**", "🔥**", 1)

            # Усиливаем призывы к действию
            if "СОХРАНИТЕ ЭТОТ ПОСТ" not in content.text:
                content.text += "\n\n💾 **СОХРАНИТЕ ЭТОТ ПОСТ** - пригодится!"

        return content

    async def _generate_controversial_topic(self, trends: TrendData) -> ContentPiece:
        """Генерация контента по спорным правовым темам"""

        controversial_topics = [
            {
                "title": "Можно ли уволиться в последний день отпуска?",
                "content": """🤔 **СПОРНАЯ СИТУАЦИЯ:**
                
Сотрудник подал заявление об увольнении в последний день отпуска. HR сказал "нельзя" и требует выйти на работу.

⚖️ **А КАК ПО ЗАКОНУ?**
Статья 80 ТК РФ позволяет подать заявление в любой рабочий день, включая последний день отпуска.

💡 **ПРАВИЛЬНЫЙ АЛГОРИТМ:**
1. 📝 Подаете заявление заранее (за 2 недели)
2. 🏖️ Уходите в отпуск
3. ✅ В последний день отпуска считаетесь уволенным автоматически

🎯 **ВЫВОД:** Работодатель НЕ МОЖЕТ заставить выходить на работу после отпуска для увольнения!""",
                "hashtags": ["#ТрудовоеПраво", "#Увольнение", "#ЗнайСвоиПрава"]
            },
            {
                "title": "Имеет ли право ТСЖ запрещать курение на балконе?",
                "content": """🚬 **ОСТРАЯ ТЕМА:**
                
ТСЖ прислало уведомление о запрете курения на балконах и угрожает штрафами.

⚖️ **ПРАВОВАЯ ПОЗИЦИЯ:**
• Балкон = часть квартиры (собственность)
• ТСЖ НЕ МОЖЕТ регулировать поведение в квартире
• Исключение: если дым мешает соседям (ст. 304 ГК РФ)

📊 **СУДЕБНАЯ ПРАКТИКА:**
70% судов встают на сторону курильщиков при соблюдении разумности.

💡 **РЕКОМЕНДАЦИИ:**
✅ Курить можно, но не создавая неудобства соседям
✅ Установите вытяжку или курите в определенное время
❌ Штрафы ТСЖ за курение на балконе незаконны""",
                "hashtags": ["#ТСЖ", "#ПраваСобственников", "#Курение"]
            }
        ]

        import random
        topic = random.choice(controversial_topics)

        return ContentPiece(
            content_type=ContentType.CONTROVERSIAL_TOPIC,
            text=topic["content"],
            hashtags=topic["hashtags"],
            media_urls=[],
            engagement_hooks=["🤔", "⚖️", "💡"],
            call_to_action="💬 А как считаете вы? Пишите в комментариях свое мнение!",
            target_audience="legal_professionals",
            complexity_level="medium"
        )
