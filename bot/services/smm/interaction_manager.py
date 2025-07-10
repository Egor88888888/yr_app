"""
🤝 INTERACTION MANAGER  
Bridge system for comments management and audience engagement
"""

import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Типы взаимодействий"""
    COMMENT_REPLY = "comment_reply"
    DISCUSSION_START = "discussion_start"
    EXPERT_ANSWER = "expert_answer"
    COMMUNITY_MODERATION = "community_moderation"
    ENGAGEMENT_BOOST = "engagement_boost"
    VIRAL_AMPLIFICATION = "viral_amplification"


class EngagementStage(Enum):
    """Стадии вовлечения"""
    INITIAL_HOOK = "initial_hook"           # Первичный захват внимания
    ACTIVE_DISCUSSION = "active_discussion"  # Активное обсуждение
    EXPERT_PHASE = "expert_phase"          # Экспертная фаза
    CONVERSION_PUSH = "conversion_push"     # Толчок к конверсии
    RETENTION_PHASE = "retention_phase"     # Удержание аудитории


@dataclass
class EngagementSession:
    """Сессия вовлечения для поста"""
    post_id: str
    channel_id: str
    discussion_group_id: Optional[str]
    start_time: datetime
    current_stage: EngagementStage
    participants: Set[str]
    comments_count: int
    expert_responses: int
    conversion_opportunities: int
    viral_score: float
    active_until: datetime


@dataclass
class CommentTemplate:
    """Шаблон для комментариев/ответов"""
    trigger_keywords: List[str]
    response_text: str
    tone: str  # professional, friendly, authoritative, conversational
    follow_up_action: Optional[str]
    conversion_potential: float


class InteractionManager:
    """Менеджер взаимодействий и комментариев"""

    def __init__(self):
        self.active_sessions: Dict[str, EngagementSession] = {}
        self.comment_templates = self._load_comment_templates()
        self.bridge_system = BridgeSystem()
        self.engagement_analyzer = EngagementAnalyzer()

    async def start_engagement_session(
        self,
        post_id: str,
        channel_id: str,
        content_type: str,
        expected_engagement: float
    ) -> EngagementSession:
        """Запуск сессии вовлечения для поста"""

        try:
            # Создаем мост к группе обсуждений
            discussion_group_id = await self.bridge_system.setup_discussion_bridge(
                channel_id, post_id
            )

            session = EngagementSession(
                post_id=post_id,
                channel_id=channel_id,
                discussion_group_id=discussion_group_id,
                start_time=datetime.now(),
                current_stage=EngagementStage.INITIAL_HOOK,
                participants=set(),
                comments_count=0,
                expert_responses=0,
                conversion_opportunities=0,
                viral_score=0.0,
                active_until=datetime.now() + timedelta(hours=24)
            )

            self.active_sessions[post_id] = session

            # Запускаем автоматическое управление сессией
            asyncio.create_task(self._manage_engagement_session(session))

            logger.info(f"Started engagement session for post {post_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to start engagement session: {e}")
            raise

    async def _manage_engagement_session(self, session: EngagementSession):
        """Автоматическое управление сессией вовлечения"""

        try:
            while datetime.now() < session.active_until:
                # Анализируем текущее состояние
                engagement_data = await self.engagement_analyzer.analyze_session(session)

                # Определяем следующую стадию
                next_stage = await self._determine_next_stage(session, engagement_data)

                if next_stage != session.current_stage:
                    await self._transition_to_stage(session, next_stage)

                # Выполняем действия для текущей стадии
                await self._execute_stage_actions(session, engagement_data)

                # Ждем перед следующей проверкой
                await asyncio.sleep(300)  # 5 минут

        except Exception as e:
            logger.error(
                f"Error managing engagement session {session.post_id}: {e}")

    async def _determine_next_stage(
        self,
        session: EngagementSession,
        engagement_data: Dict[str, Any]
    ) -> EngagementStage:
        """Определение следующей стадии вовлечения"""

        current_time = datetime.now()
        session_age = (
            current_time - session.start_time).total_seconds() / 3600  # в часах

        if session.current_stage == EngagementStage.INITIAL_HOOK:
            # Переход к активному обсуждению через 1-2 часа или при достижении 5+ комментариев
            if session_age >= 1 or session.comments_count >= 5:
                return EngagementStage.ACTIVE_DISCUSSION

        elif session.current_stage == EngagementStage.ACTIVE_DISCUSSION:
            # Переход к экспертной фазе при высокой активности
            if session.comments_count >= 15 or engagement_data.get('engagement_rate', 0) > 0.1:
                return EngagementStage.EXPERT_PHASE
            # Или через 4 часа в любом случае
            elif session_age >= 4:
                return EngagementStage.CONVERSION_PUSH

        elif session.current_stage == EngagementStage.EXPERT_PHASE:
            # Переход к конверсии через 2 часа экспертной фазы
            if session_age >= 6:
                return EngagementStage.CONVERSION_PUSH

        elif session.current_stage == EngagementStage.CONVERSION_PUSH:
            # Переход к удержанию через 12 часов
            if session_age >= 12:
                return EngagementStage.RETENTION_PHASE

        return session.current_stage

    async def _transition_to_stage(self, session: EngagementSession, new_stage: EngagementStage):
        """Переход к новой стадии вовлечения"""

        logger.info(
            f"Session {session.post_id} transitioning from {session.current_stage.value} to {new_stage.value}")

        session.current_stage = new_stage

        # Выполняем действия перехода
        if new_stage == EngagementStage.ACTIVE_DISCUSSION:
            await self._initiate_active_discussion(session)
        elif new_stage == EngagementStage.EXPERT_PHASE:
            await self._start_expert_phase(session)
        elif new_stage == EngagementStage.CONVERSION_PUSH:
            await self._push_conversion(session)
        elif new_stage == EngagementStage.RETENTION_PHASE:
            await self._activate_retention(session)

    async def _execute_stage_actions(
        self,
        session: EngagementSession,
        engagement_data: Dict[str, Any]
    ):
        """Выполнение действий для текущей стадии"""

        if session.current_stage == EngagementStage.INITIAL_HOOK:
            await self._execute_initial_hook_actions(session)
        elif session.current_stage == EngagementStage.ACTIVE_DISCUSSION:
            await self._execute_discussion_actions(session, engagement_data)
        elif session.current_stage == EngagementStage.EXPERT_PHASE:
            await self._execute_expert_actions(session, engagement_data)
        elif session.current_stage == EngagementStage.CONVERSION_PUSH:
            await self._execute_conversion_actions(session, engagement_data)
        elif session.current_stage == EngagementStage.RETENTION_PHASE:
            await self._execute_retention_actions(session, engagement_data)

    async def _execute_initial_hook_actions(self, session: EngagementSession):
        """Действия для стадии первичного захвата"""

        # Первый комментарий от "эксперта" через 30-60 минут
        session_age = (datetime.now() -
                       session.start_time).total_seconds() / 60

        if 30 <= session_age <= 90 and session.expert_responses == 0:
            expert_comment = await self._generate_expert_hook_comment(session)
            await self.bridge_system.post_expert_comment(
                session.discussion_group_id,
                expert_comment
            )
            session.expert_responses += 1

    async def _execute_discussion_actions(
        self,
        session: EngagementSession,
        engagement_data: Dict[str, Any]
    ):
        """Действия для стадии активного обсуждения"""

        # Отвечаем на комментарии пользователей
        new_comments = await self.bridge_system.get_new_comments(
            session.discussion_group_id,
            last_check=datetime.now() - timedelta(minutes=5)
        )

        for comment in new_comments:
            if await self._should_respond_to_comment(comment, session):
                response = await self._generate_comment_response(comment, session)
                await self.bridge_system.post_response(
                    session.discussion_group_id,
                    comment['id'],
                    response
                )

    async def _initiate_active_discussion(self, session: EngagementSession):
        """Запуск активной фазы обсуждения"""

        discussion_starters = [
            "Интересно услышать ваше мнение! У кого были похожие ситуации? 🤔",
            "А что думаете по поводу такого подхода? Работает ли это на практике? 💭",
            "Поделитесь своим опытом - сталкивались с подобным? Как решали? 📝",
            "Кто-нибудь пробовал применить этот совет? Какие результаты? 🎯"
        ]

        starter = random.choice(discussion_starters)
        await self.bridge_system.post_discussion_starter(
            session.discussion_group_id,
            starter
        )

    async def _start_expert_phase(self, session: EngagementSession):
        """Запуск экспертной фазы"""

        expert_announcements = [
            "🎯 **EXPERT ONLINE** Наш ведущий юрист готов ответить на ваши вопросы! Задавайте! ⚖️",
            "⚡ **ПРЯМАЯ ЛИНИЯ С ЭКСПЕРТОМ** Следующие 2 часа отвечаем на любые правовые вопросы! 💼",
            "🔥 **AMA СЕССИЯ** Ask Me Anything - наш эксперт онлайн! Не упустите шанс! 📞"
        ]

        announcement = random.choice(expert_announcements)
        await self.bridge_system.post_expert_announcement(
            session.discussion_group_id,
            announcement
        )

    async def _push_conversion(self, session: EngagementSession):
        """Толчок к конверсии"""

        conversion_messages = [
            """🎯 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ ДЛЯ УЧАСТНИКОВ ОБСУЖДЕНИЯ!**

За активность в комментариях - бесплатная 15-минутная консультация по вашему вопросу!

💼 Просто напишите боту /start и укажите код: DISCUSSION2024
⏰ Предложение действует только 24 часа!""",

            """💡 **ХОТИТЕ РАЗОБРАТЬ ВАШУ СИТУАЦИЮ ПОДРОБНО?**

Видим, что тема вас заинтересовала! Наши эксперты готовы:
✅ Проанализировать вашу ситуацию персонально  
✅ Дать конкретные рекомендации
✅ Помочь составить документы

🎁 Для участников обсуждения - скидка 50% на консультацию!
📞 Записаться: /start -> "Получить консультацию\""""
        ]

        message = random.choice(conversion_messages)
        await self.bridge_system.post_conversion_offer(
            session.discussion_group_id,
            message
        )
        session.conversion_opportunities += 1

    async def _activate_retention(self, session: EngagementSession):
        """Активация удержания аудитории"""

        retention_content = [
            """📚 **А ВЫ ЗНАЛИ?** 
            
Завтра в 15:00 разберем новый резонансный кейс: "Как блогер отсудил у банка 500,000₽ за незаконную блокировку карты"

🔔 Включите уведомления, чтобы не пропустить!
💬 Есть похожие вопросы? Пишите - обязательно разберем!""",

            """🎯 **СЛЕДУЮЩАЯ ТЕМА УЖЕ ГОТОВА!**
            
Завтра публикуем: "5 ошибок при покупке квартиры, которые стоят миллионы"

📝 Основано на реальных судебных делах
💰 Поможет сэкономить сотни тысяч рублей
⚖️ С комментариями практикующих юристов

🔔 Подписывайтесь, чтобы не пропустить!"""
        ]

        message = random.choice(retention_content)
        await self.bridge_system.post_retention_content(
            session.discussion_group_id,
            message
        )

    async def _generate_expert_hook_comment(self, session: EngagementSession) -> str:
        """Генерация экспертного комментария-зацепки"""

        expert_hooks = [
            "⚖️ **Юрист комментирует:** Отличный кейс! Хочу добавить важный нюанс, который многие упускают...",
            "💼 **Из практики:** Вчера был похожий случай. Клиент получил на 200,000₽ больше, зная один секрет...",
            "🎯 **Важное дополнение:** Здесь есть подводный камень, о котором не говорят...",
            "⚡ **Свежая практика:** Верховный суд недавно изменил подход к таким делам. Теперь можно..."
        ]

        return random.choice(expert_hooks)

    async def _should_respond_to_comment(
        self,
        comment: Dict[str, Any],
        session: EngagementSession
    ) -> bool:
        """Определение, нужно ли отвечать на комментарий"""

        # Отвечаем на вопросы
        if any(word in comment['text'].lower() for word in ['как', 'что', 'где', 'когда', 'почему', '?']):
            return True

        # Отвечаем на споры/сомнения
        if any(word in comment['text'].lower() for word in ['не согласен', 'сомневаюсь', 'не работает', 'ерунда']):
            return True

        # Отвечаем на истории пользователей
        if any(word in comment['text'].lower() for word in ['у меня', 'мой случай', 'была ситуация']):
            return True

        # Ограничиваем частоту ответов
        if session.expert_responses >= 10:
            return random.random() < 0.3

        return random.random() < 0.7

    async def _generate_comment_response(
        self,
        comment: Dict[str, Any],
        session: EngagementSession
    ) -> str:
        """Генерация ответа на комментарий"""

        comment_text = comment['text'].lower()

        # Ответы на вопросы
        if '?' in comment_text:
            return await self._generate_question_response(comment_text)

        # Ответы на сомнения
        if any(word in comment_text for word in ['не согласен', 'сомневаюсь', 'не работает']):
            return await self._generate_doubt_response(comment_text)

        # Ответы на истории
        if any(word in comment_text for word in ['у меня', 'мой случай', 'была ситуация']):
            return await self._generate_story_response(comment_text)

        # Общий ответ
        return await self._generate_general_response(comment_text)

    async def _generate_question_response(self, comment_text: str) -> str:
        """Ответ на вопрос"""

        responses = [
            "Отличный вопрос! 🎯 В такой ситуации важно учесть несколько моментов...",
            "Разберем по пунктам! 📝 Во-первых...",
            "Хороший кейс для разбора! ⚖️ Здесь ключевое...",
            "Интересная ситуация! 💡 Рекомендую следующий алгоритм действий..."
        ]

        return random.choice(responses)

    def _load_comment_templates(self) -> List[CommentTemplate]:
        """Загрузка шаблонов комментариев"""

        return [
            CommentTemplate(
                trigger_keywords=["спасибо", "помогло", "полезно"],
                response_text="Рады помочь! 😊 Если возникнут вопросы - обращайтесь!",
                tone="friendly",
                follow_up_action=None,
                conversion_potential=0.3
            ),
            CommentTemplate(
                trigger_keywords=["не работает", "ерунда", "бред"],
                response_text="Понимаю ваши сомнения. Давайте разберем конкретно вашу ситуацию - в чем отличия?",
                tone="professional",
                follow_up_action="offer_consultation",
                conversion_potential=0.6
            ),
            CommentTemplate(
                trigger_keywords=["сколько стоит", "цена", "деньги"],
                response_text="Стоимость зависит от сложности дела. Первичная консультация бесплатно - оценим перспективы!",
                tone="professional",
                follow_up_action="conversion_push",
                conversion_potential=0.8
            )
        ]


class BridgeSystem:
    """Система мостов для обхода ограничений Telegram API"""

    async def setup_discussion_bridge(self, channel_id: str, post_id: str) -> Optional[str]:
        """Настройка моста для обсуждений"""
        # В реальной реализации создаем/находим связанную группу обсуждений
        # Пока возвращаем заглушку
        return f"discussion_group_{channel_id}"

    async def get_new_comments(
        self,
        discussion_group_id: str,
        last_check: datetime
    ) -> List[Dict[str, Any]]:
        """Получение новых комментариев"""
        # Заглушка - в реальности парсим сообщения из группы обсуждений
        return []

    async def post_expert_comment(self, group_id: str, comment: str):
        """Публикация комментария эксперта"""
        logger.info(f"Posting expert comment to {group_id}: {comment[:50]}...")

    async def post_response(self, group_id: str, comment_id: str, response: str):
        """Публикация ответа на комментарий"""
        logger.info(
            f"Posting response to comment {comment_id}: {response[:50]}...")

    async def post_discussion_starter(self, group_id: str, message: str):
        """Публикация стартера обсуждения"""
        logger.info(f"Posting discussion starter: {message[:50]}...")

    async def post_expert_announcement(self, group_id: str, announcement: str):
        """Публикация объявления эксперта"""
        logger.info(f"Posting expert announcement: {announcement[:50]}...")

    async def post_conversion_offer(self, group_id: str, offer: str):
        """Публикация конверсионного предложения"""
        logger.info(f"Posting conversion offer: {offer[:50]}...")

    async def post_retention_content(self, group_id: str, content: str):
        """Публикация контента для удержания"""
        logger.info(f"Posting retention content: {content[:50]}...")


class EngagementAnalyzer:
    """Анализатор вовлеченности"""

    async def analyze_session(self, session: EngagementSession) -> Dict[str, Any]:
        """Анализ сессии вовлечения"""

        session_age_hours = (
            datetime.now() - session.start_time).total_seconds() / 3600

        # Базовые метрики
        engagement_rate = session.comments_count / max(session_age_hours, 0.1)
        viral_score = session.comments_count * 0.1 + session.participants.__len__() * \
            0.2

        return {
            'session_age_hours': session_age_hours,
            'engagement_rate': engagement_rate,
            'viral_score': viral_score,
            'conversion_readiness': session.conversion_opportunities > 0,
            'activity_trend': 'growing' if engagement_rate > 2 else 'stable'
        }
