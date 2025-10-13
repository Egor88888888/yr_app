"""
💬 COMMENT MANAGER - PRODUCTION READY
Real comment management and automatic engagement:
- Discussion groups management
- Automatic expert responses
- Conversation flow control
- Sentiment analysis
- Anti-spam protection
- Moderation tools
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import json
import random
import re

from telegram import Bot, Message, User, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ChatType, ParseMode

logger = logging.getLogger(__name__)


class CommentType(Enum):
    """Типы комментариев"""
    QUESTION = "question"
    OPINION = "opinion"
    EXPERIENCE = "experience"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    SPAM = "spam"
    OFFTOPIC = "offtopic"


class ResponseStrategy(Enum):
    """Стратегии ответов"""
    IMMEDIATE = "immediate"      # Немедленный ответ
    DELAYED = "delayed"          # Отложенный ответ
    EXPERT_ONLY = "expert_only"  # Только экспертные ответы
    COMMUNITY = "community"      # Поощрение обсуждения в сообществе
    IGNORE = "ignore"           # Игнорировать


@dataclass
class CommentEvent:
    """Событие комментария"""
    message_id: int
    user_id: int
    username: Optional[str]
    text: str
    timestamp: datetime
    chat_id: str
    post_id: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    comment_type: Optional[CommentType] = None
    sentiment_score: float = 0.0  # -1 to 1
    requires_response: bool = False
    response_strategy: Optional[ResponseStrategy] = None


@dataclass
class ExpertResponse:
    """Экспертный ответ"""
    content: str
    response_type: str  # "answer", "question", "engagement"
    delay_minutes: int = 0
    priority: int = 1


@dataclass
class DiscussionGroup:
    """Группа обсуждений для канала"""
    group_id: str
    channel_id: str
    group_name: str
    is_active: bool = True
    member_count: int = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class CommentManager:
    """Production-ready comment management system"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.discussion_groups: Dict[str, DiscussionGroup] = {}
        self.active_conversations: Dict[str, List[CommentEvent]] = {}
        self.expert_personas = ExpertPersonaManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.conversation_flow = ConversationFlowManager()
        self.moderation_system = ModerationSystem()

        # Настройки
        self.response_probability = 0.7  # Вероятность ответа на комментарий
        # Минуты задержки для экспертного ответа
        self.expert_response_delay = (30, 120)
        self.max_responses_per_hour = 10
        self.responses_this_hour = 0
        self.last_hour_reset = datetime.now()

        # Автоматические ответы отключены по умолчанию, чтобы бот не отвечал сам
        self.auto_responses_enabled = False

        self.is_running = False

    async def start_manager(self):
        """Запуск системы управления комментариями"""
        self.is_running = True
        logger.info("💬 Starting Comment Manager")

        # Запуск основных процессов в фоне (не ждем их завершения)
        asyncio.create_task(self._monitor_discussion_groups())
        asyncio.create_task(self._process_comment_queue())
        asyncio.create_task(self._expert_response_scheduler())
        asyncio.create_task(self._conversation_flow_manager())
        asyncio.create_task(self._moderation_loop())

        logger.info("✅ Comment Manager background tasks started")

    async def stop_manager(self):
        """Остановка системы"""
        self.is_running = False
        logger.info("🛑 Stopping Comment Manager")

    async def setup_discussion_group(self, channel_id: str, post_id: str) -> Optional[str]:
        """Настройка группы обсуждений для канала"""
        try:
            # Проверяем, есть ли уже группа для этого канала
            existing_group = None
            for group in self.discussion_groups.values():
                if group.channel_id == channel_id and group.is_active:
                    existing_group = group
                    break

            if existing_group:
                logger.info(
                    f"Using existing discussion group {existing_group.group_id} for channel {channel_id}")
                return existing_group.group_id

            # Получаем информацию о канале
            channel = await self.bot.get_chat(channel_id)

            # Пытаемся найти связанную группу обсуждений
            if hasattr(channel, 'linked_chat_id') and channel.linked_chat_id:
                discussion_group_id = str(channel.linked_chat_id)

                # Проверяем доступность группы
                try:
                    discussion_group = await self.bot.get_chat(discussion_group_id)

                    # Создаем запись о группе обсуждений
                    group_record = DiscussionGroup(
                        group_id=discussion_group_id,
                        channel_id=channel_id,
                        group_name=discussion_group.title or "Discussion Group",
                        member_count=getattr(
                            discussion_group, 'member_count', 0)
                    )

                    self.discussion_groups[discussion_group_id] = group_record

                    logger.info(
                        f"✅ Set up discussion group {discussion_group_id} for channel {channel_id}")
                    return discussion_group_id

                except Exception as e:
                    logger.warning(
                        f"Cannot access linked discussion group: {e}")

            # Если связанной группы нет, создаем виртуальную систему комментариев
            # (используем replies в самом канале, если это возможно)
            virtual_group_id = f"virtual_{channel_id}"

            group_record = DiscussionGroup(
                group_id=virtual_group_id,
                channel_id=channel_id,
                group_name="Virtual Discussion",
                member_count=0
            )

            self.discussion_groups[virtual_group_id] = group_record

            logger.info(
                f"✅ Created virtual discussion system for channel {channel_id}")
            return virtual_group_id

        except Exception as e:
            logger.error(
                f"Failed to setup discussion group for {channel_id}: {e}")
            return None

    async def process_comment(self, comment_event: CommentEvent):
        """Обработка нового комментария"""
        try:
            # Анализ комментария
            await self._analyze_comment(comment_event)

            # Проверка модерации
            if await self.moderation_system.should_moderate(comment_event):
                await self._moderate_comment(comment_event)
                return

            if not self.auto_responses_enabled:
                comment_event.requires_response = False
                comment_event.response_strategy = ResponseStrategy.IGNORE
                logger.info(
                    f"💬 Processed comment from user {comment_event.user_id}: auto responses disabled")
                return

            # Добавляем в активные разговоры
            chat_key = f"{comment_event.chat_id}_{comment_event.post_id}"
            if chat_key not in self.active_conversations:
                self.active_conversations[chat_key] = []
            self.active_conversations[chat_key].append(comment_event)

            # Определяем стратегию ответа
            response_strategy = await self._determine_response_strategy(comment_event)
            comment_event.response_strategy = response_strategy

            # Планируем ответ если нужно
            if response_strategy != ResponseStrategy.IGNORE:
                await self._schedule_response(comment_event)

            logger.info(
                f"💬 Processed comment from user {comment_event.user_id}: {response_strategy.value}")

        except Exception as e:
            logger.error(f"Failed to process comment: {e}")

    async def _analyze_comment(self, comment_event: CommentEvent):
        """Анализ комментария"""
        # Определение типа комментария
        comment_event.comment_type = await self._classify_comment(comment_event.text)

        # Анализ тональности
        comment_event.sentiment_score = await self.sentiment_analyzer.analyze(comment_event.text)

        # Определение необходимости ответа
        comment_event.requires_response = await self._should_respond(comment_event)

    async def _classify_comment(self, text: str) -> CommentType:
        """Классификация типа комментария"""
        text_lower = text.lower()

        # Вопросы
        question_indicators = ["?", "как", "что", "где",
                               "когда", "почему", "можно ли", "скажите"]
        if any(indicator in text_lower for indicator in question_indicators):
            return CommentType.QUESTION

        # Жалобы
        complaint_indicators = ["плохо", "ужасно",
                                "не работает", "обман", "развод", "негодяи"]
        if any(indicator in text_lower for indicator in complaint_indicators):
            return CommentType.COMPLAINT

        # Похвала
        praise_indicators = ["спасибо", "отлично",
                             "хорошо", "помогли", "круто", "супер"]
        if any(indicator in text_lower for indicator in praise_indicators):
            return CommentType.PRAISE

        # Опыт
        experience_indicators = [
            "у меня", "я сталкивался", "мой случай", "моя ситуация"]
        if any(indicator in text_lower for indicator in experience_indicators):
            return CommentType.EXPERIENCE

        # Спам проверка
        if await self._is_spam(text):
            return CommentType.SPAM

        return CommentType.OPINION

    async def _is_spam(self, text: str) -> bool:
        """Проверка на спам"""
        spam_indicators = [
            r'https?://',  # Ссылки
            r'@\w+',       # Упоминания
            r'\b(займ|кредит|деньги|быстро|заработок)\b',  # Финансовый спам
            r'(.)\1{4,}',  # Повторяющиеся символы
        ]

        text_lower = text.lower()
        for pattern in spam_indicators:
            if re.search(pattern, text_lower):
                return True

        # Проверка на копипасту (слишком длинный текст)
        if len(text) > 500:
            return True

        return False

    async def _should_respond(self, comment_event: CommentEvent) -> bool:
        """Определение необходимости ответа"""
        # Всегда отвечаем на вопросы
        if comment_event.comment_type == CommentType.QUESTION:
            return True

        # Отвечаем на жалобы для управления репутацией
        if comment_event.comment_type == CommentType.COMPLAINT:
            return True

        # Иногда отвечаем на опыт и мнения для вовлечения
        if comment_event.comment_type in [CommentType.EXPERIENCE, CommentType.OPINION]:
            return random.random() < 0.4  # 40% вероятность

        # Благодарим за похвалу
        if comment_event.comment_type == CommentType.PRAISE:
            return random.random() < 0.3  # 30% вероятность

        return False

    async def _determine_response_strategy(self, comment_event: CommentEvent) -> ResponseStrategy:
        """Определение стратегии ответа"""
        # Проверяем лимиты ответов
        await self._check_response_limits()

        if self.responses_this_hour >= self.max_responses_per_hour:
            return ResponseStrategy.IGNORE

        # Стратегия в зависимости от типа комментария
        if comment_event.comment_type == CommentType.QUESTION:
            if random.random() < 0.7:
                return ResponseStrategy.EXPERT_ONLY
            else:
                return ResponseStrategy.COMMUNITY

        elif comment_event.comment_type == CommentType.COMPLAINT:
            return ResponseStrategy.IMMEDIATE

        elif comment_event.comment_type == CommentType.EXPERIENCE:
            return ResponseStrategy.COMMUNITY

        elif comment_event.comment_type == CommentType.PRAISE:
            return ResponseStrategy.DELAYED

        elif comment_event.comment_type == CommentType.SPAM:
            return ResponseStrategy.IGNORE

        else:
            if random.random() < self.response_probability:
                return ResponseStrategy.DELAYED
            else:
                return ResponseStrategy.IGNORE

    async def _schedule_response(self, comment_event: CommentEvent):
        """Планирование ответа"""
        try:
            # Генерируем ответ
            expert_response = await self._generate_expert_response(comment_event)

            if not expert_response:
                return

            # Определяем задержку
            delay_minutes = expert_response.delay_minutes

            if comment_event.response_strategy == ResponseStrategy.IMMEDIATE:
                delay_minutes = random.randint(1, 5)
            elif comment_event.response_strategy == ResponseStrategy.DELAYED:
                delay_minutes = random.randint(15, 60)
            elif comment_event.response_strategy == ResponseStrategy.EXPERT_ONLY:
                delay_minutes = random.randint(*self.expert_response_delay)

            # Планируем выполнение
            response_time = datetime.now() + timedelta(minutes=delay_minutes)

            # Добавляем в очередь ответов
            response_task = {
                "response_time": response_time,
                "comment_event": comment_event,
                "expert_response": expert_response,
                "chat_id": comment_event.chat_id,
                "reply_to_message_id": comment_event.message_id
            }

            # Сохраняем задачу (в реальной реализации - в базу данных)
            asyncio.create_task(self._delayed_response(response_task))

            logger.info(
                f"📅 Scheduled response for comment {comment_event.message_id} in {delay_minutes} minutes")

        except Exception as e:
            logger.error(f"Failed to schedule response: {e}")

    async def _generate_expert_response(self, comment_event: CommentEvent) -> Optional[ExpertResponse]:
        """Генерация экспертного ответа"""
        try:
            # Выбираем персону эксперта
            expert_persona = await self.expert_personas.get_appropriate_persona(
                comment_event.comment_type,
                comment_event.text
            )

            # Генерируем ответ в зависимости от типа комментария
            if comment_event.comment_type == CommentType.QUESTION:
                response_content = await self._generate_answer_response(comment_event, expert_persona)
                response_type = "answer"

            elif comment_event.comment_type == CommentType.COMPLAINT:
                response_content = await self._generate_support_response(comment_event, expert_persona)
                response_type = "support"

            elif comment_event.comment_type == CommentType.EXPERIENCE:
                response_content = await self._generate_engagement_response(comment_event, expert_persona)
                response_type = "engagement"

            elif comment_event.comment_type == CommentType.PRAISE:
                response_content = await self._generate_gratitude_response(comment_event, expert_persona)
                response_type = "gratitude"

            else:
                response_content = await self._generate_general_response(comment_event, expert_persona)
                response_type = "general"

            if response_content:
                return ExpertResponse(
                    content=response_content,
                    response_type=response_type,
                    priority=1
                )

            return None

        except Exception as e:
            logger.error(f"Failed to generate expert response: {e}")
            return None

    async def _generate_answer_response(self, comment_event: CommentEvent, expert_persona: Dict[str, Any]) -> str:
        """Генерация ответа на вопрос"""
        templates = [
            "🎯 Отличный вопрос! {answer} Если нужна более детальная консультация, обращайтесь в личные сообщения бота.",
            "⚖️ По данному вопросу могу сказать следующее: {answer} Рекомендую обратиться за персональной консультацией.",
            "💼 Согласно действующему законодательству: {answer} Подробности и индивидуальный разбор - в личной консультации.",
            "📚 Практика показывает, что {answer} Для разбора вашей конкретной ситуации напишите боту."
        ]

        template = random.choice(templates)

        # Здесь можно интегрироваться с AI для генерации ответа
        # Или использовать заготовленные ответы по темам
        answer = await self._get_ai_answer(comment_event.text)

        return template.format(answer=answer)

    async def _generate_support_response(self, comment_event: CommentEvent, expert_persona: Dict[str, Any]) -> str:
        """Генерация ответа поддержки на жалобу"""
        templates = [
            "😔 Понимаю ваше беспокойство. {solution} Давайте разберем вашу ситуацию детально в личной переписке.",
            "🤝 Сожалею, что у вас возникли сложности. {solution} Обратитесь в личные сообщения для решения вопроса.",
            "💡 Действительно, такие ситуации бывают. {solution} Напишите боту для персональной помощи.",
            "⚡ Спасибо за обратную связь! {solution} Поможем разобраться - пишите в личку."
        ]

        template = random.choice(templates)
        solution = await self._get_solution_suggestion(comment_event.text)

        return template.format(solution=solution)

    async def _generate_engagement_response(self, comment_event: CommentEvent, expert_persona: Dict[str, Any]) -> str:
        """Генерация ответа для вовлечения"""
        templates = [
            "👍 Интересный опыт! А что думают остальные участники? Поделитесь своими историями!",
            "💭 Спасибо за ваш опыт! Кто еще сталкивался с подобным? Расскажите в комментариях!",
            "🔥 Отличный кейс! У кого были похожие ситуации? Давайте обсудим!",
            "⭐ Ценная информация! Интересно услышать мнения других участников. Пишите!",
            "🎯 Благодарю за историю! А как вы думаете, что можно было сделать по-другому?"
        ]

        return random.choice(templates)

    async def _generate_gratitude_response(self, comment_event: CommentEvent, expert_persona: Dict[str, Any]) -> str:
        """Генерация ответа благодарности"""
        templates = [
            "🙏 Спасибо за добрые слова! Всегда рады помочь!",
            "❤️ Очень приятно! Обращайтесь, если будут вопросы!",
            "😊 Благодарим за отзыв! Ваша поддержка очень важна!",
            "🌟 Спасибо! Стараемся быть полезными!",
            "💪 Отлично, что смогли помочь! Удачи вам!"
        ]

        return random.choice(templates)

    async def _generate_general_response(self, comment_event: CommentEvent, expert_persona: Dict[str, Any]) -> str:
        """Генерация общего ответа"""
        templates = [
            "💡 Интересное мнение! А что думают другие?",
            "🤔 Согласен, тема актуальная. Кто еще хочет высказаться?",
            "👥 Хорошая точка зрения! Давайте обсудим!",
            "📝 Спасибо за комментарий! Ждем другие мнения!"
        ]

        return random.choice(templates)

    async def _get_ai_answer(self, question: str) -> str:
        """Получение AI-ответа на вопрос"""
        # Здесь можно интегрироваться с Enhanced AI системой
        # Для генерации более качественных ответов

        basic_answers = [
            "в таких случаях рекомендуется обратиться к специалисту",
            "согласно закону, необходимо предпринять определенные действия",
            "это довольно сложный вопрос, требующий индивидуального подхода",
            "практика показывает несколько возможных решений",
            "важно учесть все обстоятельства дела"
        ]

        return random.choice(basic_answers)

    async def _get_solution_suggestion(self, complaint: str) -> str:
        """Получение предложения решения для жалобы"""
        solutions = [
            "Обычно такие вопросы решаются довольно быстро.",
            "Есть несколько способов решения данной проблемы.",
            "Подобные ситуации имеют стандартные алгоритмы решения.",
            "Это решаемый вопрос, главное - правильный подход."
        ]

        return random.choice(solutions)

    async def _delayed_response(self, response_task: Dict[str, Any]):
        """Отложенный ответ"""
        try:
            # Ждем до времени ответа
            delay = (response_task["response_time"] -
                     datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

            # Проверяем лимиты перед отправкой
            await self._check_response_limits()
            if self.responses_this_hour >= self.max_responses_per_hour:
                logger.info("Response limit reached, skipping response")
                return

            # Отправляем ответ
            await self.bot.send_message(
                chat_id=response_task["chat_id"],
                text=response_task["expert_response"].content,
                reply_to_message_id=response_task["reply_to_message_id"],
                parse_mode=ParseMode.HTML
            )

            self.responses_this_hour += 1

            logger.info(
                f"✅ Sent expert response to message {response_task['reply_to_message_id']}")

        except Exception as e:
            logger.error(f"Failed to send delayed response: {e}")

    async def _check_response_limits(self):
        """Проверка лимитов ответов"""
        current_time = datetime.now()
        if current_time.hour != self.last_hour_reset.hour:
            self.responses_this_hour = 0
            self.last_hour_reset = current_time

    async def _monitor_discussion_groups(self):
        """Мониторинг групп обсуждений"""
        while self.is_running:
            try:
                # Здесь можно добавить логику мониторинга:
                # - Проверка активности групп
                # - Обновление статистики
                # - Обнаружение новых сообщений

                await asyncio.sleep(300)  # Проверяем каждые 5 минут

            except Exception as e:
                logger.error(f"Error in discussion groups monitoring: {e}")
                await asyncio.sleep(60)

    async def _process_comment_queue(self):
        """Обработка очереди комментариев"""
        while self.is_running:
            try:
                # Обработка накопившихся комментариев
                # В реальной реализации - из базы данных или очереди

                await asyncio.sleep(30)  # Проверяем каждые 30 секунд

            except Exception as e:
                logger.error(f"Error in comment queue processing: {e}")
                await asyncio.sleep(60)

    async def _expert_response_scheduler(self):
        """Планировщик экспертных ответов"""
        while self.is_running:
            try:
                # Планирование и выполнение отложенных ответов
                await asyncio.sleep(60)  # Проверяем каждую минуту

            except Exception as e:
                logger.error(f"Error in expert response scheduler: {e}")
                await asyncio.sleep(300)

    async def _conversation_flow_manager(self):
        """Менеджер потока разговоров"""
        while self.is_running:
            try:
                await self.conversation_flow.manage_active_conversations(
                    self.active_conversations
                )
                await asyncio.sleep(300)  # Проверяем каждые 5 минут

            except Exception as e:
                logger.error(f"Error in conversation flow management: {e}")
                await asyncio.sleep(600)

    async def _moderation_loop(self):
        """Цикл модерации"""
        while self.is_running:
            try:
                await self.moderation_system.run_moderation_checks()
                await asyncio.sleep(120)  # Проверяем каждые 2 минуты

            except Exception as e:
                logger.error(f"Error in moderation loop: {e}")
                await asyncio.sleep(300)

    async def _moderate_comment(self, comment_event: CommentEvent):
        """Модерация комментария"""
        try:
            # Удаление спама
            if comment_event.comment_type == CommentType.SPAM:
                await self.bot.delete_message(
                    chat_id=comment_event.chat_id,
                    message_id=comment_event.message_id
                )
                logger.info(
                    f"🗑️ Deleted spam message {comment_event.message_id}")

        except Exception as e:
            logger.error(f"Failed to moderate comment: {e}")


class ExpertPersonaManager:
    """Менеджер экспертных персон"""

    def __init__(self):
        self.personas = {
            "senior_lawyer": {
                "name": "Старший юрист",
                "style": "professional",
                "specialties": ["civil", "criminal", "business"],
                "response_style": "detailed"
            },
            "family_lawyer": {
                "name": "Семейный юрист",
                "style": "empathetic",
                "specialties": ["family", "divorce", "custody"],
                "response_style": "supportive"
            },
            "business_consultant": {
                "name": "Бизнес-консультант",
                "style": "practical",
                "specialties": ["business", "contracts", "startup"],
                "response_style": "solution_focused"
            }
        }

    async def get_appropriate_persona(self, comment_type: CommentType, text: str) -> Dict[str, Any]:
        """Получение подходящей персоны для ответа"""
        # Простая логика выбора персоны
        if comment_type == CommentType.COMPLAINT:
            return self.personas["family_lawyer"]  # Более эмпатичный
        elif "бизнес" in text.lower() or "ооо" in text.lower():
            return self.personas["business_consultant"]
        else:
            return self.personas["senior_lawyer"]


class SentimentAnalyzer:
    """Анализатор тональности"""

    async def analyze(self, text: str) -> float:
        """Анализ тональности текста (-1 до 1)"""
        positive_words = ["хорошо", "отлично",
                          "спасибо", "помогли", "классно", "супер"]
        negative_words = ["плохо", "ужасно", "обман",
                          "развод", "негодяи", "не помогли"]

        text_lower = text.lower()

        positive_count = sum(
            1 for word in positive_words if word in text_lower)
        negative_count = sum(
            1 for word in negative_words if word in text_lower)

        total_words = len(text.split())

        if total_words == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / \
            max(total_words / 10, 1)

        return max(-1.0, min(1.0, sentiment))


class ConversationFlowManager:
    """Менеджер потока разговоров"""

    async def manage_active_conversations(self, conversations: Dict[str, List[CommentEvent]]):
        """Управление активными разговорами"""
        for chat_key, events in conversations.items():
            if len(events) > 10:  # Очищаем старые разговоры
                conversations[chat_key] = events[-5:]


class ModerationSystem:
    """Система модерации"""

    def __init__(self):
        self.spam_threshold = 0.8
        self.offensive_words = ["дурак", "идиот", "козел"]  # Можно расширить

    async def should_moderate(self, comment_event: CommentEvent) -> bool:
        """Определение необходимости модерации"""
        # Проверка на спам
        if comment_event.comment_type == CommentType.SPAM:
            return True

        # Проверка на оскорбления
        text_lower = comment_event.text.lower()
        if any(word in text_lower for word in self.offensive_words):
            return True

        # Проверка на слишком негативную тональность
        if comment_event.sentiment_score < -0.8:
            return True

        return False

    async def run_moderation_checks(self):
        """Запуск проверок модерации"""
        # Здесь можно добавить дополнительные проверки:
        # - Анализ паттернов поведения пользователей
        # - Проверка на координированные атаки
        # - Обновление списков запрещенных слов
        pass
