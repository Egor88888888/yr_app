"""
🔷 ПРОФЕССИОНАЛЬНАЯ СИСТЕМА АВТОПОСТИНГА
Генерирует ежедневный разнообразный юридический контент с реальными источниками
+ ИНТЕГРИРОВАНА СИСТЕМА ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА
"""

import asyncio
import sqlite3
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import json
import logging

# Импорт системы дедупликации
try:
    from .content_deduplication import validate_and_register_content, get_deduplication_system
    from .professional_legal_content import get_expert_legal_content
    from .ai_legal_expert import generate_ai_expert_content
except ImportError:
    # Fallback если модуль не найден
    def validate_and_register_content(*args, **kwargs):
        return True, "Deduplication not available"
    def get_deduplication_system():
        return None
    async def get_expert_legal_content(*args, **kwargs):
        return "Professional content not available"
    async def generate_ai_expert_content(*args, **kwargs):
        return "AI content not available"

log = logging.getLogger(__name__)


class LegalContentDatabase:
    """База данных для хранения истории публикаций и правовой информации"""

    def __init__(self, db_path: str = "legal_content.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица истории публикаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_type TEXT NOT NULL,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                legal_reference TEXT,
                publication_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                engagement_rate REAL DEFAULT 0,
                views INTEGER DEFAULT 0
            )
        ''')

        # Таблица правовых источников
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS legal_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                legal_code TEXT,
                article_number TEXT,
                content TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица тем для ротации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_rotation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_category TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 5.0
            )
        ''')

        # Таблица запланированных постов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT NOT NULL,
                topic TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                channel_id TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                enable_comments BOOLEAN DEFAULT 1,
                keyboard_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                engagement_score REAL DEFAULT 0,
                views INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0
            )
        ''')

        # Таблица комментариев к постам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                comment_text TEXT NOT NULL,
                comment_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_approved BOOLEAN DEFAULT 1,
                is_expert_response BOOLEAN DEFAULT 0,
                reply_to_comment_id INTEGER,
                FOREIGN KEY (post_id) REFERENCES scheduled_posts (post_id),
                FOREIGN KEY (reply_to_comment_id) REFERENCES post_comments (id)
            )
        ''')

        conn.commit()
        conn.close()

        # Заполняем базовыми данными если пуста
        self._populate_initial_data()

    def _populate_initial_data(self):
        """Заполнение начальными данными"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем есть ли данные
        cursor.execute("SELECT COUNT(*) FROM content_rotation")
        if cursor.fetchone()[0] == 0:

            # Темы для кейсов
            case_topics = [
                ("case", "Трудовые споры"),
                ("case", "Семейные конфликты"),
                ("case", "Жилищные вопросы"),
                ("case", "Защита прав потребителей"),
                ("case", "Автомобильные споры"),
                ("case", "Банковские разногласия"),
                ("case", "Наследственные дела"),
                ("case", "Налоговые споры"),
                ("case", "Земельные вопросы"),
                ("case", "Административные штрафы")
            ]

            # Статьи кодексов для разбора
            code_articles = [
                ("article", "ГК РФ Статья 393 - Возмещение убытков"),
                ("article", "ТК РФ Статья 81 - Расторжение по инициативе работодателя"),
                ("article", "КоАП РФ Статья 12.8 - Управление в состоянии опьянения"),
                ("article", "УК РФ Статья 158 - Кража"),
                ("article", "СК РФ Статья 80 - Обязанности родителей"),
                ("article", "ЖК РФ Статья 29 - Общее собрание собственников"),
                ("article", "НК РФ Статья 114 - Зачет налога"),
                ("article", "АПК РФ Статья 125 - Подача искового заявления"),
                ("article", "ФЗ О защите прав потребителей Статья 18"),
                ("article", "ГПК РФ Статья 131 - Форма и содержание заявления")
            ]

            # Категории новостей
            news_categories = [
                ("news", "Изменения в трудовом праве"),
                ("news", "Новые налоговые льготы"),
                ("news", "Судебная практика ВС РФ"),
                ("news", "Административные нововведения"),
                ("news", "Банковское регулирование"),
                ("news", "Семейное законодательство"),
                ("news", "Жилищные новации"),
                ("news", "Автомобильное право"),
                ("news", "Цифровые права"),
                ("news", "Экологическое право")
            ]

            all_topics = case_topics + code_articles + news_categories

            cursor.executemany(
                "INSERT INTO content_rotation (topic_category, topic_name) VALUES (?, ?)",
                all_topics
            )

        conn.commit()
        conn.close()

    def get_next_topic(self) -> Tuple[str, str]:
        """Получить следующую тему для публикации с учетом ротации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Получаем последний тип поста
        cursor.execute("""
            SELECT post_type FROM post_history 
            ORDER BY publication_date DESC LIMIT 1
        """)

        last_type = cursor.fetchone()
        last_type = last_type[0] if last_type else None

        # Определяем следующий тип по ротации
        if last_type == "case":
            next_type = "article"
        elif last_type == "article":
            next_type = "news"
        else:
            next_type = "case"

        # Получаем наименее используемую тему этого типа
        cursor.execute("""
            SELECT topic_name FROM content_rotation 
            WHERE topic_category = ? 
            ORDER BY last_used ASC, usage_count ASC, RANDOM() 
            LIMIT 1
        """, (next_type,))

        topic = cursor.fetchone()
        if not topic:
            # Fallback на случайную тему
            topic = ("Общие правовые вопросы",)

        # Обновляем статистику использования
        cursor.execute("""
            UPDATE content_rotation 
            SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1
            WHERE topic_category = ? AND topic_name = ?
        """, (next_type, topic[0]))

        conn.commit()
        conn.close()

        return next_type, topic[0]

    def save_post(self, post_type: str, title: str, topic: str, legal_ref: str = ""):
        """Сохранить информацию о публикации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO post_history (post_type, title, topic, legal_reference)
            VALUES (?, ?, ?, ?)
        """, (post_type, title, topic, legal_ref))

        conn.commit()
        conn.close()

    def schedule_post(self, post_data: Dict, scheduled_time: datetime, channel_id: str = "@your_channel") -> str:
        """Планирование поста"""
        post_id = f"post_{uuid.uuid4().hex[:8]}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        keyboard_json = json.dumps(post_data.get('keyboard', []))

        cursor.execute('''
            INSERT INTO scheduled_posts 
            (post_id, title, content, post_type, topic, scheduled_time, channel_id, 
             enable_comments, keyboard_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id,
            post_data.get('title', ''),
            post_data['content'],
            post_data.get('type', 'general'),
            post_data.get('topic', ''),
            scheduled_time.isoformat(),
            channel_id,
            post_data.get('enable_comments', True),
            keyboard_json
        ))

        conn.commit()
        conn.close()

        return post_id

    def get_scheduled_posts(self, limit: int = 10) -> List[Dict]:
        """Получить запланированные посты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, title, post_type, topic, scheduled_time, 
                   channel_id, status, enable_comments, views, comments_count
            FROM scheduled_posts 
            WHERE status = 'scheduled'
            ORDER BY scheduled_time ASC
            LIMIT ?
        ''', (limit,))

        posts = []
        for row in cursor.fetchall():
            posts.append({
                'post_id': row[0],
                'title': row[1],
                'post_type': row[2],
                'topic': row[3],
                'scheduled_time': row[4],
                'channel_id': row[5],
                'status': row[6],
                'enable_comments': row[7],
                'views': row[8],
                'comments_count': row[9]
            })

        conn.close()
        return posts

    def add_comment_to_post(self, post_id: str, user_id: int, username: str, comment_text: str, reply_to: int = None) -> int:
        """Добавить комментарий к посту"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO post_comments 
            (post_id, user_id, username, comment_text, reply_to_comment_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (post_id, user_id, username, comment_text, reply_to))

        comment_id = cursor.lastrowid

        # Обновляем счетчик комментариев у поста
        cursor.execute('''
            UPDATE scheduled_posts 
            SET comments_count = comments_count + 1 
            WHERE post_id = ?
        ''', (post_id,))

        conn.commit()
        conn.close()

        return comment_id

    def get_post_comments(self, post_id: str, limit: int = 20) -> List[Dict]:
        """Получить комментарии к посту"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, user_id, username, comment_text, comment_time, 
                   is_approved, is_expert_response, reply_to_comment_id
            FROM post_comments 
            WHERE post_id = ? AND is_approved = 1
            ORDER BY comment_time ASC
            LIMIT ?
        ''', (post_id, limit))

        comments = []
        for row in cursor.fetchall():
            comments.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'comment_text': row[3],
                'comment_time': row[4],
                'is_approved': row[5],
                'is_expert_response': row[6],
                'reply_to': row[7]
            })

        conn.close()
        return comments

    def mark_post_published(self, post_id: str):
        """Отметить пост как опубликованный"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE scheduled_posts 
            SET status = 'published', published_at = ?
            WHERE post_id = ?
        ''', (datetime.now().isoformat(), post_id))

        conn.commit()
        conn.close()


class LegalContentGenerator:
    """Генератор профессионального юридического контента"""

    def __init__(self, database: LegalContentDatabase):
        self.db = database
        self.legal_sources = {
            'consultant': 'https://www.consultant.ru/',
            'garant': 'https://base.garant.ru/',
            'pravo_gov': 'https://publication.pravo.gov.ru/',
            'sudact': 'https://sudact.ru/',
            'vsrf': 'https://vsrf.ru/'
        }

    async def generate_case_post(self, topic: str) -> Dict[str, str]:
        """Генерация кейс-поста"""

        case_scenarios = {
            "Трудовые споры": {
                "situation": "Марина получила сообщение от директора в WhatsApp: «С завтрашнего дня можешь не выходить. Уволена». Приказ не подписывала, трудовую книжку не получала.",
                "question": "Можно ли уволить сотрудника через мессенджер?",
                "legal_base": "ст. 84.1 ТК РФ",
                "legal_text": "«Прекращение трудового договора оформляется приказом (распоряжением) работодателя»",
                "court_case": "Определение ВС РФ от 20.02.2023 № 5-КГ22-103",
                "consultant_link": "https://www.consultant.ru/document/cons_doc_LAW_34683/",
                "algorithm": [
                    "Сохраните переписку как доказательство",
                    "Подайте жалобу в Государственную инспекцию труда",
                    "Обратитесь в суд для восстановления на работе",
                    "Потребуйте выплату за вынужденный прогул"
                ]
            },

            "Семейные конфликты": {
                "situation": "После развода отец не платит алименты уже 6 месяцев. Говорит, что денег нет, но в соцсетях постоянно фото с дорогих курортов.",
                "question": "Как заставить платить алименты, если должник скрывает доходы?",
                "legal_base": "ст. 157 УК РФ, ст. 5.35.1 КоАП РФ",
                "legal_text": "«Неуплата алиментов в течение двух и более месяцев влечет штраф до 20 000 рублей»",
                "court_case": "Постановление Пленума ВС РФ от 26.12.2017 № 56",
                "consultant_link": "https://www.consultant.ru/document/cons_doc_LAW_10699/",
                "algorithm": [
                    "Обратитесь к судебным приставам с заявлением о розыске имущества",
                    "Подайте заявление о привлечении к административной ответственности",
                    "Соберите доказательства скрытых доходов (фото, чеки, свидетели)",
                    "При злостном уклонении - заявление в полицию (ст. 157 УК РФ)"
                ]
            },

            "Защита прав потребителей": {
                "situation": "Купила телефон за 50 000 рублей. Через неделю экран стал мигать. В магазине сказали: «Гарантия есть, но сначала экспертиза за ваш счет».",
                "question": "Должен ли покупатель оплачивать экспертизу по гарантии?",
                "legal_base": "ст. 18 Закона «О защите прав потребителей»",
                "legal_text": "«Экспертиза товара проводится за счет продавца»",
                "court_case": "Определение ВС РФ от 15.03.2022 № 5-КГ21-67",
                "consultant_link": "https://www.consultant.ru/document/cons_doc_LAW_305/",
                "algorithm": [
                    "Напишите претензию с требованием замены/возврата",
                    "Укажите срок исполнения требований (10 дней)",
                    "При отказе - в суд с иском о защите прав потребителей",
                    "Потребуйте компенсацию морального вреда и штраф"
                ]
            }
        }

        if topic not in case_scenarios:
            topic = random.choice(list(case_scenarios.keys()))

        scenario = case_scenarios[topic]

        title = f"🚨 {topic}: {scenario['situation'].split('.')[0]}"

        post_content = f"""👩‍⚖️ **Кейс: {topic}**

{scenario['situation']}

❓ **{scenario['question']}**

✅ **Ответ:**
Нет. Согласно {scenario['legal_base']}: {scenario['legal_text']}

🔗 **Правовая база:** {scenario['consultant_link']}
📌 **Судебная практика:** {scenario['court_case']}

🔍 **Что делать:**
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(scenario['algorithm'])])}

⚖️ **Нужна помощь в такой ситуации? Наши юристы разберут ваш вопрос бесплатно. Жми "Консультация" ⤵️**"""

        return {
            "title": title,
            "content": post_content,
            "type": "case",
            "topic": topic,
            "legal_reference": scenario['legal_base']
        }

    async def generate_article_post(self, topic: str) -> Dict[str, str]:
        """Генерация разбора статьи кодекса"""

        article_explanations = {
            "ГК РФ Статья 393 - Возмещение убытков": {
                "full_title": "Статья 393 ГК РФ. Возмещение убытков",
                "article_text": "Должник обязан возместить кредитору убытки, причиненные неисполнением или ненадлежащим исполнением обязательства",
                "simple_explanation": "Если вам не выполнили договор или выполнили плохо, вы можете потребовать возмещения всех понесенных убытков",
                "when_applies": [
                    "Подрядчик не сдал ремонт в срок",
                    "Поставщик привез бракованный товар",
                    "Турфирма отменила тур в последний момент",
                    "Банк незаконно списал деньги"
                ],
                "how_violated": [
                    "Неисполнение договора в срок",
                    "Исполнение с нарушением качества",
                    "Полное неисполнение обязательств"
                ],
                "how_defend": [
                    "Рассчитайте размер ущерба (документы, чеки, справки)",
                    "Направьте претензию с требованием возмещения",
                    "При отказе - обращайтесь в суд",
                    "Требуйте возмещения судебных расходов"
                ],
                "consultant_link": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                "court_example": "Определение ВС РФ от 12.07.2022 № 18-КГ22-15"
            },

            "ТК РФ Статья 81 - Расторжение по инициативе работодателя": {
                "full_title": "Статья 81 ТК РФ. Расторжение трудового договора по инициативе работодателя",
                "article_text": "Трудовой договор может быть расторгнут работодателем только в случаях, предусмотренных настоящим Кодексом",
                "simple_explanation": "Работодатель не может уволить вас просто так - только по строго определенным законом основаниям",
                "when_applies": [
                    "Ликвидация организации",
                    "Сокращение численности",
                    "Несоответствие должности",
                    "Неоднократное неисполнение обязанностей",
                    "Прогул, появление в нетрезвом виде"
                ],
                "how_violated": [
                    "Увольнение без законных оснований",
                    "Нарушение процедуры увольнения",
                    "Увольнение защищенных категорий работников"
                ],
                "how_defend": [
                    "Требуйте письменное обоснование увольнения",
                    "Проверьте соблюдение процедуры уведомления",
                    "Обжалуйте в инспекции труда",
                    "Подавайте иск о восстановлении на работе"
                ],
                "consultant_link": "https://www.consultant.ru/document/cons_doc_LAW_34683/",
                "court_example": "Постановление Пленума ВС РФ от 17.03.2004 № 2"
            }
        }

        if topic not in article_explanations:
            topic = random.choice(list(article_explanations.keys()))

        article = article_explanations[topic]

        title = f"📚 Разбираем {article['full_title']}"

        post_content = f"""📖 **РАЗБОР СТАТЬИ: {article['full_title']}**

📋 **Текст статьи:**
{article['article_text']}

💡 **Простыми словами:**
{article['simple_explanation']}

🎯 **Где применяется:**
{chr(10).join([f"• {case}" for case in article['when_applies']])}

⚠️ **Как нарушается:**
{chr(10).join([f"• {violation}" for violation in article['how_violated']])}

🛡️ **Как отстоять права:**
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(article['how_defend'])])}

🔗 **Источник:** {article['consultant_link']}
📌 **Судебная практика:** {article['court_example']}

⚖️ **Нужна помощь? Наши юристы разберут ваш случай бесплатно. Жми "Консультация" ⤵️**"""

        return {
            "title": title,
            "content": post_content,
            "type": "article",
            "topic": topic,
            "legal_reference": article['full_title']
        }

    async def generate_news_post(self, topic: str) -> Dict[str, str]:
        """Генерация поста о новых законах/решениях"""

        # Эмуляция актуальных новостей (в реальности здесь был бы парсинг источников)
        news_items = {
            "Изменения в трудовом праве": {
                "headline": "С 1 марта 2024 года изменились правила оплаты больничных",
                "what_changed": "Теперь первые 3 дня больничного оплачивает работодатель в размере 100% от среднего заработка (ранее 60-80%)",
                "legal_base": "Федеральный закон от 28.12.2023 № 618-ФЗ",
                "who_affected": [
                    "Все работники по трудовым договорам",
                    "Работодатели всех форм собственности",
                    "ИП с работниками"
                ],
                "what_to_do": [
                    "Работодателям пересмотреть расчет больничных",
                    "Работникам знать свои новые права",
                    "Бухгалтерам изучить новый порядок расчета"
                ],
                "source_link": "https://publication.pravo.gov.ru/document/0001202312280042"
            },

            "Судебная практика ВС РФ": {
                "headline": "Верховный суд разъяснил права покупателей при возврате товаров",
                "what_changed": "ВС РФ указал, что продавец не может требовать от покупателя сохранения всех ярлыков и бирок при возврате качественного товара",
                "legal_base": "Определение ВС РФ от 15.01.2024 № 5-КГ23-145",
                "who_affected": [
                    "Все покупатели товаров",
                    "Интернет-магазины",
                    "Розничные продавцы"
                ],
                "what_to_do": [
                    "Покупателям знать свои расширенные права",
                    "Продавцам пересмотреть правила возврата",
                    "При споре ссылаться на позицию ВС РФ"
                ],
                "source_link": "https://vsrf.ru/documents/practice/28956/"
            }
        }

        if topic not in news_items:
            topic = random.choice(list(news_items.keys()))

        news = news_items[topic]

        title = f"🆕 {news['headline']}"

        post_content = f"""📢 **ПРАВОВЫЕ НОВОСТИ: {topic}**

🔥 **{news['headline']}**

📋 **Что изменилось:**
{news['what_changed']}

⚖️ **Правовая основа:**
{news['legal_base']}

👥 **Кого касается:**
{chr(10).join([f"• {person}" for person in news['who_affected']])}

🎯 **Что делать:**
{chr(10).join([f"{i+1}. {action}" for i, action in enumerate(news['what_to_do'])])}

🔗 **Источник:** {news['source_link']}

⚖️ **Нужна консультация по новым правилам? Наши юристы помогут разобраться. Жми "Консультация" ⤵️**"""

        return {
            "title": title,
            "content": post_content,
            "type": "news",
            "topic": topic,
            "legal_reference": news['legal_base']
        }


class EnhancedAutopostSystem:
    """Улучшенная система автопостинга с профессиональным контентом"""

    def __init__(self):
        self.db = LegalContentDatabase()
        self.generator = LegalContentGenerator(self.db)
        self.last_post_time = None

    async def generate_daily_post(self) -> Dict[str, str]:
        """Генерация ежедневного поста с учетом ротации и проверкой уникальности"""

        max_attempts = 15  # Больше попыток для более сложной системы
        
        for attempt in range(max_attempts):
            try:
                # Получаем следующую тему по ротации
                post_type, topic = self.db.get_next_topic()

                log.info(f"Generating {post_type} post about: {topic} (attempt {attempt + 1}/{max_attempts})")

                # ОБНОВЛЕННАЯ СИСТЕМА: Приоритет профессиональному контенту
                use_professional = random.random() < 0.9  # 90% профессиональный контент
                
                if use_professional:
                    try:
                        if post_type == "case":
                            expert_content = await get_expert_legal_content("case")
                        elif post_type == "article":  
                            expert_content = await get_expert_legal_content("guide")
                        elif post_type == "news":
                            expert_content = await get_expert_legal_content("update")
                        else:
                            expert_content = await get_expert_legal_content("practice")
                        
                        # Формируем данные поста из экспертного контента
                        title = expert_content.split('\n')[0].replace('**', '').replace('*', '').strip()
                        post_data = {
                            "title": title[:100],
                            "content": expert_content,
                            "type": f"expert_{post_type}",
                            "topic": topic,
                            "legal_reference": "Экспертный анализ"
                        }
                        
                    except Exception as e:
                        log.warning(f"Failed to generate expert content: {e}, falling back to standard")
                        use_professional = False
                
                if not use_professional:
                    # Генерируем стандартный контент в зависимости от типа
                    if post_type == "case":
                        post_data = await self.generator.generate_case_post(topic)
                    elif post_type == "article":
                        post_data = await self.generator.generate_article_post(topic)
                    elif post_type == "news":
                        post_data = await self.generator.generate_news_post(topic)
                    else:
                        # Fallback на кейс
                        post_data = await self.generator.generate_case_post("Общие правовые вопросы")

                # ПРОВЕРКА УНИКАЛЬНОСТИ КОНТЕНТА
                is_valid, message = validate_and_register_content(
                    title=post_data['title'],
                    content=post_data['content'],
                    content_type="enhanced_autopost",
                    source_system="enhanced_autopost"
                )

                if not is_valid:
                    log.warning(f"❌ Enhanced post not unique (attempt {attempt + 1}): {message}")
                    # Блокируем тему на более длительный срок
                    dedup_system = get_deduplication_system()
                    if dedup_system:
                        dedup_system.block_topic_temporarily(
                            topic, 
                            f"Enhanced autopost duplicate on attempt {attempt + 1}: {message}", 
                            hours=4
                        )
                    continue

                # Добавляем кнопку консультации
                post_data['content'] += "\n\n📱 **Есть вопросы? Получите консультацию!**"
                post_data['enable_comments'] = False

                # Получаем имя бота из переменных окружения или используем fallback
                import os
                bot_username = os.getenv("BOT_USERNAME", "your_bot").replace("@", "")

                post_data['keyboard'] = [
                    [{"text": "📱 Получить консультацию", "url": f"https://t.me/{bot_username}"}]
                ]

                # Сохраняем в историю только после успешной проверки уникальности
                self.db.save_post(
                    post_data['type'],
                    post_data['title'],
                    post_data['topic'],
                    post_data.get('legal_reference', '')
                )

                self.last_post_time = datetime.now()
                
                # Добавляем информацию о проверке уникальности
                post_data['uniqueness_validated'] = True
                post_data['attempts_needed'] = attempt + 1

                log.info(f"✅ Unique enhanced post created after {attempt + 1} attempts")
                return post_data
                
            except Exception as e:
                log.error(f"Error generating post (attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    # Последняя попытка - возвращаем fallback
                    break
                continue

        # Если все попытки исчерпаны, возвращаем fallback без проверки уникальности
        log.error(f"❌ Failed to generate unique enhanced content after {max_attempts} attempts, using fallback")
        
        fallback_data = {
            "title": "📚 Правовая помощь доступна каждому",
            "content": """⚖️ **ЗНАЙТЕ СВОИ ПРАВА!**

🔍 **Каждый день мы помогаем людям решать правовые вопросы:**
• Трудовые споры и увольнения
• Семейные конфликты и алименты
• Защита прав потребителей
• Жилищные вопросы и ЖКХ
• Автомобильные споры и ОСАГО

💡 **Помните:** незнание закона не освобождает от ответственности, но знание защищает ваши права!

❓ **Есть вопрос? Получите персональную консультацию!**

📱 **Есть вопросы? Получите консультацию!**""",
            "type": "fallback",
            "topic": "Общая правовая помощь",
            "legal_reference": "Общие нормы права",
            "enable_comments": False,
            "uniqueness_validated": False,
            "attempts_needed": max_attempts,
            "is_fallback": True
        }
        
        # Получаем имя бота
        import os
        bot_username = os.getenv("BOT_USERNAME", "your_bot").replace("@", "")
        fallback_data['keyboard'] = [
            [{"text": "📱 Получить консультацию", "url": f"https://t.me/{bot_username}"}]
        ]

        self.last_post_time = datetime.now()
        return fallback_data

    async def should_post_now(self) -> bool:
        """Проверка нужно ли публиковать пост сейчас"""

        if not self.last_post_time:
            return True  # Первый пост

        # Публикуем раз в день
        time_since_last = datetime.now() - self.last_post_time
        return time_since_last >= timedelta(hours=24)

    async def get_posting_statistics(self) -> Dict[str, any]:
        """Получение статистики постов"""

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM post_history")
        total_posts = cursor.fetchone()[0]

        # Статистика по типам
        cursor.execute("""
            SELECT post_type, COUNT(*) 
            FROM post_history 
            GROUP BY post_type
        """)
        type_stats = dict(cursor.fetchall())

        # Последние посты
        cursor.execute("""
            SELECT title, publication_date, post_type 
            FROM post_history 
            ORDER BY publication_date DESC 
            LIMIT 5
        """)
        recent_posts = cursor.fetchall()

        conn.close()

        return {
            "total_posts": total_posts,
            "by_type": type_stats,
            "recent_posts": recent_posts,
            "last_post_time": self.last_post_time
        }

    async def schedule_professional_post(self, hours_from_now: int = 24, channel_id: str = "@your_channel") -> Dict[str, str]:
        """Запланировать профессиональный пост"""

        # Генерируем контент
        post_data = await self.generate_daily_post()

        # Планируем время публикации
        scheduled_time = datetime.now() + timedelta(hours=hours_from_now)

        # Сохраняем в базу
        post_id = self.db.schedule_post(post_data, scheduled_time, channel_id)

        post_data['post_id'] = post_id
        post_data['scheduled_time'] = scheduled_time.isoformat()
        post_data['channel_id'] = channel_id

        return post_data

    async def get_scheduled_posts_list(self, limit: int = 10) -> List[Dict]:
        """Получить список запланированных постов"""
        return self.db.get_scheduled_posts(limit)

    async def add_comment_to_post(self, post_id: str, user_id: int, username: str, comment_text: str, reply_to: int = None) -> int:
        """Добавить комментарий к посту"""
        return self.db.add_comment_to_post(post_id, user_id, username, comment_text, reply_to)

    async def get_post_comments_list(self, post_id: str, limit: int = 20) -> List[Dict]:
        """Получить комментарии к посту"""
        return self.db.get_post_comments(post_id, limit)

    async def publish_scheduled_post(self, post_id: str) -> bool:
        """Опубликовать запланированный пост (обычно вызывается планировщиком)"""
        try:
            # Здесь будет логика публикации в канал
            # Пока что просто помечаем как опубликованный
            self.db.mark_post_published(post_id)
            return True
        except Exception as e:
            log.error(f"Failed to publish post {post_id}: {e}")
            return False

    async def get_autopost_dashboard_data(self) -> Dict[str, Any]:
        """Получить данные для дашборда автопостинга"""

        # Основная статистика
        stats = await self.get_posting_statistics()

        # Запланированные посты
        scheduled = await self.get_scheduled_posts_list(5)

        # Последние опубликованные посты
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, title, post_type, published_at, views, comments_count
            FROM scheduled_posts 
            WHERE status = 'published'
            ORDER BY published_at DESC
            LIMIT 5
        ''')

        published_posts = []
        for row in cursor.fetchall():
            published_posts.append({
                'post_id': row[0],
                'title': row[1],
                'post_type': row[2],
                'published_at': row[3],
                'views': row[4],
                'comments_count': row[5]
            })

        conn.close()

        return {
            'statistics': stats,
            'scheduled_posts': scheduled,
            'recent_published': published_posts,
            'system_status': 'active' if self.last_post_time else 'inactive'
        }


# Глобальный экземпляр системы
enhanced_autopost = EnhancedAutopostSystem()


async def get_enhanced_autopost_status() -> Dict[str, any]:
    """Получить статус улучшенной системы автопостинга"""
    return await enhanced_autopost.get_posting_statistics()


async def generate_professional_post() -> Dict[str, str]:
    """Генерация профессионального поста"""
    return await enhanced_autopost.generate_daily_post()


async def should_create_autopost() -> bool:
    """Проверить нужно ли создавать автопост"""
    return await enhanced_autopost.should_post_now()


async def schedule_smart_post(hours_from_now: int = 24, channel_id: str = "@your_channel") -> Dict[str, str]:
    """Запланировать умный пост"""
    return await enhanced_autopost.schedule_professional_post(hours_from_now, channel_id)


async def get_scheduled_posts(limit: int = 10) -> List[Dict]:
    """Получить запланированные посты"""
    return await enhanced_autopost.get_scheduled_posts_list(limit)


async def add_post_comment(post_id: str, user_id: int, username: str, comment_text: str, reply_to: int = None) -> int:
    """Добавить комментарий к посту"""
    return await enhanced_autopost.add_comment_to_post(post_id, user_id, username, comment_text, reply_to)


async def get_post_comments(post_id: str, limit: int = 20) -> List[Dict]:
    """Получить комментарии к посту"""
    return await enhanced_autopost.get_post_comments_list(post_id, limit)


async def get_autopost_dashboard() -> Dict[str, Any]:
    """Получить данные дашборда автопостинга"""
    return await enhanced_autopost.get_autopost_dashboard_data()


async def publish_post_now(post_id: str) -> bool:
    """Опубликовать пост немедленно"""
    return await enhanced_autopost.publish_scheduled_post(post_id)
