"""
🚀 ПРОСТАЯ И НАДЕЖНАЯ СИСТЕМА АВТОПОСТИНГА
Работает БЕЗ сложных зависимостей - только базовый python + telegram
+ ИНТЕГРИРОВАНА СИСТЕМА ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

# Импорт системы дедупликации - PostgreSQL версия для production
try:
    from .content_deduplication_pg import validate_and_register_content
    DEDUPLICATION_TYPE = "PostgreSQL"
except ImportError:
    # Fallback на SQLite версию для локальной разработки
    from .content_deduplication import validate_and_register_content, get_deduplication_system
    DEDUPLICATION_TYPE = "SQLite"
# Импорт профессионального контента
from .professional_legal_content import get_expert_legal_content
from .ai_legal_expert import generate_ai_expert_content

logger = logging.getLogger(__name__)


class SimpleAutopost:
    """Простая система автопостинга без сложных зависимостей"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.last_post_time = None
        self.last_deploy_post_time = None
        self.autopost_interval_minutes = 60  # 1 час по умолчанию
        self.posts_created_today = 0
        self.daily_post_limit = 24  # Максимум 24 поста в день

        # Получаем channel_id из environment
        self.channel_id = (
            os.getenv('TARGET_CHANNEL_ID') or
            os.getenv('CHANNEL_ID') or
            '@test_legal_channel'
        )

        logger.info(
            f"🔧 SimpleAutopost initialized for channel: {self.channel_id}")
        logger.info(f"🔍 Deduplication system: {DEDUPLICATION_TYPE}")

    async def start_autopost_system(self):
        """Запуск простой системы автопостинга"""
        if self.is_running:
            logger.warning("Autopost system already running")
            return

        self.is_running = True
        logger.info("🚀 Starting simple autopost system...")

        # Запускаем основные задачи в фоне
        asyncio.create_task(self._deploy_autopost_timer())
        asyncio.create_task(self._regular_autopost_loop())
        asyncio.create_task(self._daily_reset_timer())

        logger.info("✅ Simple autopost system started - all tasks running in background")

    async def _deploy_autopost_timer(self):
        """Создание поста через 5 минут после запуска (deploy post)"""
        try:
            logger.info("🔧 Deploy autopost timer started")
            
            # Проверяем не создавали ли мы уже deploy post недавно
            if self.last_deploy_post_time:
                time_since_deploy = datetime.now() - self.last_deploy_post_time
                if time_since_deploy < timedelta(hours=1):
                    logger.info(
                        "Deploy post already created recently, skipping")
                    return

            logger.info("⏰ Deploy autopost: waiting 5 minutes...")
            await asyncio.sleep(300)  # 5 минут
            logger.info("⏰ Deploy autopost: 5 minutes passed, creating post...")

            if self.is_running:
                await self._create_deploy_post()
                self.last_deploy_post_time = datetime.now()
                logger.info("✅ Deploy autopost completed successfully")
            else:
                logger.warning("⚠️ Deploy autopost skipped - system not running")

        except Exception as e:
            logger.error(f"❌ Deploy autopost error: {e}")
            import traceback
            logger.error(f"Deploy autopost traceback: {traceback.format_exc()}")

    async def _regular_autopost_loop(self):
        """Регулярный автопостинг каждый час"""
        try:
            logger.info("🔧 Regular autopost loop started")
            # Ждем 10 минут после старта перед первым регулярным постом
            logger.info("⏰ Regular autopost: waiting 10 minutes before first post...")
            await asyncio.sleep(600)
            logger.info("⏰ Regular autopost: 10 minutes passed, starting loop...")

            while self.is_running:
                try:
                    # Проверяем лимиты
                    if self.posts_created_today >= self.daily_post_limit:
                        logger.info(
                            f"Daily post limit reached ({self.posts_created_today}/{self.daily_post_limit}), waiting for reset")
                        await asyncio.sleep(3600)  # Ждем час
                        continue

                    logger.info(f"📝 Creating regular post ({self.posts_created_today + 1}/{self.daily_post_limit} for today)")
                    
                    # Создаем регулярный пост
                    await self._create_regular_post()
                    self.last_post_time = datetime.now()
                    self.posts_created_today += 1
                    
                    logger.info(f"✅ Regular post created successfully ({self.posts_created_today}/{self.daily_post_limit})")

                    # Ждем до следующего поста
                    logger.info(
                        f"⏰ Next regular post in {self.autopost_interval_minutes} minutes")
                    await asyncio.sleep(self.autopost_interval_minutes * 60)

                except Exception as e:
                    logger.error(f"❌ Regular autopost error: {e}")
                    import traceback
                    logger.error(f"Regular autopost traceback: {traceback.format_exc()}")
                    await asyncio.sleep(300)  # Ждем 5 минут при ошибке

        except Exception as e:
            logger.error(f"Regular autopost loop error: {e}")

    async def _daily_reset_timer(self):
        """Сброс счетчика постов каждый день"""
        while self.is_running:
            try:
                # Ждем до следующей полуночи
                now = datetime.now()
                tomorrow = now.replace(
                    hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                seconds_until_midnight = (tomorrow - now).total_seconds()

                await asyncio.sleep(seconds_until_midnight)

                # Сбрасываем счетчик
                self.posts_created_today = 0
                logger.info("Daily post counter reset")

            except Exception as e:
                logger.error(f"Daily reset error: {e}")
                await asyncio.sleep(3600)

    async def _create_deploy_post(self):
        """Создание поста после деплоя"""
        try:
            logger.info("🚀 Creating deploy autopost...")

            post_text = f"""🚀 **СИСТЕМА ОБНОВЛЕНА И ГОТОВА К РАБОТЕ!**

✅ **Что нового:**
• Улучшенная обработка заявок
• Более быстрые ответы AI-консультанта  
• Расширенная база юридических знаний
• Оптимизированная работа с документами

🎯 **Готов помочь вам с:**
• Консультации по любым правовым вопросам
• Составление документов и заявлений
• Анализ договоров и соглашений
• Защита прав потребителей
• Семейное и трудовое право
• Вопросы недвижимости и наследства

📱 **Получить консультацию прямо сейчас!**

*Обновлено: {datetime.now().strftime('%d.%m.%Y в %H:%M')}*"""

            # Создаем кнопку
            keyboard = [[
                InlineKeyboardButton(
                    "📱 Получить консультацию",
                    url=f"https://t.me/{self.bot.username.replace('@', '')}"
                )
            ]]

            # Отправляем пост
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=post_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            logger.info(f"✅ Deploy autopost created: {message.message_id}")
            return {"success": True, "message_id": message.message_id}

        except Exception as e:
            logger.error(f"Failed to create deploy post: {e}")
            return {"success": False, "error": str(e)}

    async def _create_regular_post(self):
        """Создание регулярного поста с проверкой уникальности"""
        max_attempts = 10  # Максимум попыток генерации уникального контента
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"📝 Creating regular autopost (attempt {attempt + 1}/{max_attempts})...")

                # Выбираем тип контента
                post_types = [
                    "legal_case",
                    "legal_tip", 
                    "legal_news",
                    "legal_fact"
                ]

                post_type = random.choice(post_types)

                # НОВАЯ СИСТЕМА: Генерация профессионального контента
                if post_type == "legal_case":
                    # 80% профессиональный контент, 20% базовый
                    if random.random() < 0.8:
                        post_text = await get_expert_legal_content("case")
                    else:
                        post_text = await self._generate_legal_case()
                elif post_type == "legal_tip":
                    if random.random() < 0.8:
                        post_text = await get_expert_legal_content("guide")
                    else:
                        post_text = await self._generate_legal_tip()
                elif post_type == "legal_news":
                    if random.random() < 0.8:
                        post_text = await get_expert_legal_content("update")
                    else:
                        post_text = await self._generate_legal_news()
                else:
                    if random.random() < 0.8:
                        post_text = await get_expert_legal_content("practice")
                    else:
                        post_text = await self._generate_legal_fact()

                # ПРОВЕРКА УНИКАЛЬНОСТИ КОНТЕНТА
                title = post_text.split('\n')[0][:100]  # Первая строка как заголовок
                is_valid, message = validate_and_register_content(
                    title=title,
                    content=post_text,
                    content_type="simple_autopost",
                    source_system="simple_autopost"
                )

                if not is_valid:
                    logger.warning(f"❌ Post not unique (attempt {attempt + 1}): {message}")
                    # Блокируем использованную тему на 2 часа
                    dedup_system = get_deduplication_system()
                    dedup_system.block_topic_temporarily(title, f"SimpleAutopost duplicate on attempt {attempt + 1}", hours=2)
                    continue

                # Добавляем кнопку консультации
                keyboard = [[
                    InlineKeyboardButton(
                        "📱 Получить консультацию",
                        url=f"https://t.me/{self.bot.username.replace('@', '')}"
                    )
                ]]

                # Отправляем пост
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=post_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

                logger.info(f"✅ Unique regular autopost created: {message.message_id} (type: {post_type}) after {attempt + 1} attempts")
                return {
                    "success": True, 
                    "message_id": message.message_id, 
                    "type": post_type,
                    "attempts_needed": attempt + 1,
                    "uniqueness_validated": True
                }

            except Exception as e:
                logger.error(f"Failed to create regular post (attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    return {"success": False, "error": str(e), "max_attempts_reached": True}
                continue

        # Если все попытки исчерпаны
        logger.error(f"❌ Failed to generate unique content after {max_attempts} attempts")
        return {
            "success": False, 
            "error": f"Could not generate unique content after {max_attempts} attempts",
            "max_attempts_reached": True
        }

    async def _generate_legal_case(self) -> str:
        """Генерация юридического кейса"""
        cases = [
            {
                "title": "Возврат товара без чека",
                "situation": "Покупатель хочет вернуть товар, но потерял чек",
                "solution": "По закону чек не является единственным доказательством покупки",
                "law": "ст. 18 Закона 'О защите прав потребителей'"
            },
            {
                "title": "Увольнение во время отпуска",
                "situation": "Работника пытаются уволить, пока он в отпуске",
                "solution": "Увольнение во время отпуска возможно только по инициативе работника",
                "law": "ст. 81 ТК РФ"
            },
            {
                "title": "Задержка зарплаты",
                "situation": "Работодатель задерживает выплату заработной платы",
                "solution": "За каждый день просрочки полагается компенсация",
                "law": "ст. 236 ТК РФ"
            }
        ]

        case = random.choice(cases)

        return f"""⚖️ **ЮРИДИЧЕСКИЙ КЕЙС: {case['title'].upper()}**

🔍 **Ситуация:**
{case['situation']}

✅ **Решение:**
{case['solution']}

📋 **Правовая основа:**
{case['law']}

💡 **Помните:** Незнание закона не освобождает от ответственности, но знание защищает ваши права!

❓ **Есть похожая ситуация? Получите персональную консультацию!**"""

    async def _generate_legal_tip(self) -> str:
        """Генерация правового совета"""
        tips = [
            {
                "title": "Как правильно составить претензию",
                "content": "1. Укажите адресата и свои данные\n2. Опишите суть нарушения\n3. Сошлитесь на закон\n4. Укажите требования\n5. Поставьте дату и подпись"
            },
            {
                "title": "Права потребителя при покупке",
                "content": "• Право на качественный товар\n• Право на полную информацию\n• Право на безопасность\n• Право на возврат в течение 14 дней\n• Право на гарантийное обслуживание"
            },
            {
                "title": "Что делать при ДТП",
                "content": "1. Остановитесь и включите аварийку\n2. Выставите знак аварийной остановки\n3. Вызовите ГИБДД или оформите европротокол\n4. Сфотографируйте место происшествия\n5. Обменяйтесь данными с другим водителем"
            }
        ]

        tip = random.choice(tips)

        return f"""💡 **ПРАВОВОЙ СОВЕТ: {tip['title'].upper()}**

📝 **Пошаговая инструкция:**
{tip['content']}

✅ **Следуя этим правилам, вы защитите свои интересы и избежите проблем!**

🔗 **Нужна помощь с вашей конкретной ситуацией?**"""

    async def _generate_legal_news(self) -> str:
        """Генерация правовых новостей"""
        news = [
            "С 2024 года изменились правила возврата товаров купленных онлайн",
            "Новые штрафы за нарушение трудового законодательства вступили в силу",
            "Упрощена процедура подачи исков в суд через Госуслуги",
            "Изменились правила расчета алиментов на детей",
            "Новые льготы для многодетных семей при покупке жилья"
        ]

        selected_news = random.choice(news)

        return f"""📰 **ПРАВОВЫЕ НОВОСТИ**

🆕 **{selected_news}**

📋 Эти изменения могут затронуть ваши права и обязанности. 

❓ **Хотите узнать подробности и как это влияет на вашу ситуацию?**

💬 **Получите персональную консультацию по новым законам!**"""

    async def _generate_legal_fact(self) -> str:
        """Генерация правового факта"""
        facts = [
            "Срок исковой давности по большинству гражданских дел составляет 3 года",
            "Работодатель обязан предупредить об увольнении по сокращению за 2 месяца",
            "Потребитель имеет право вернуть качественный товар в течение 14 дней",
            "Алименты можно взыскать за прошедший период, но не более чем за 3 года",
            "Банк не имеет права требовать досрочный возврат кредита без веских оснований"
        ]

        fact = random.choice(facts)

        return f"""🧠 **А ВЫ ЗНАЛИ?**

💡 **Правовой факт:**
{fact}

📚 **Знание своих прав поможет вам:**
• Избежать нарушений
• Защитить свои интересы  
• Не стать жертвой мошенников
• Получить положенные компенсации

❓ **Хотите узнать больше о своих правах в конкретной ситуации?**"""

    async def set_interval(self, minutes: int):
        """Установка интервала автопостинга"""
        self.autopost_interval_minutes = minutes
        logger.info(f"Autopost interval set to {minutes} minutes")

    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса автопостинга"""
        return {
            "running": self.is_running,
            "interval_minutes": self.autopost_interval_minutes,
            "posts_today": self.posts_created_today,
            "daily_limit": self.daily_post_limit,
            "last_post_time": self.last_post_time.isoformat() if self.last_post_time else None,
            "last_deploy_post": self.last_deploy_post_time.isoformat() if self.last_deploy_post_time else None,
            "channel_id": self.channel_id
        }

    async def create_immediate_post(self, post_type: str = "regular") -> Dict[str, Any]:
        """Создание немедленного поста для тестирования"""
        if post_type == "deploy":
            return await self._create_deploy_post()
        else:
            return await self._create_regular_post()

    async def stop_autopost(self):
        """Остановка автопостинга"""
        self.is_running = False
        logger.info("Simple autopost system stopped")


# Глобальная переменная для хранения экземпляра
_simple_autopost_instance = None


async def init_simple_autopost(bot: Bot) -> SimpleAutopost:
    """Инициализация простой системы автопостинга"""
    global _simple_autopost_instance

    try:
        if _simple_autopost_instance is None:
            _simple_autopost_instance = SimpleAutopost(bot)

        # Запускаем систему автопостинга
        await _simple_autopost_instance.start_autopost_system()

        logger.info("✅ Simple autopost system initialized and started")
        return _simple_autopost_instance

    except Exception as e:
        logger.error(f"Failed to initialize simple autopost: {e}")
        raise


def get_simple_autopost() -> Optional[SimpleAutopost]:
    """Получение экземпляра простой системы автопостинга"""
    return _simple_autopost_instance
