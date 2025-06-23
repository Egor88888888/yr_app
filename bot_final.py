#!/usr/bin/env python3
"""
Telegram bot with Mini-App launched via a single MenuButtonWebApp.
Works on Railway automatically: no manual steps after deploy.
– aiohttp web-server handles both Telegram webhook POST /<TOKEN>
  and POST /submit from the mini-app.
– /submit parses payload, notifies admin, answers WebAppQuery to
  close the mini-app.
"""
import asyncio
import json
import logging
import os
import uuid
import random
from aiohttp import web
from telegram import (
    Update,
    WebAppInfo,
    MenuButtonWebApp,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile,
)
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import timedelta, datetime
import openai
from typing import Optional
from telegram.constants import ChatAction
import aiohttp
import io
# === Analytics & External parsing ===
from db import init_models, async_sessionmaker
from jobs import collect_subscribers_job, scan_external_channels_job, scan_rss_sources_job, get_rss_stats_job, EXTERNAL_CHANNELS
from telethon import TelegramClient
from telethon.sessions import StringSession
from collections import deque

########################### CONFIG ###########################
TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # string
# e.g. poetic-simplicity-production-xxx.up.railway.app
PUBLIC_HOST = os.getenv("MY_RAILWAY_PUBLIC_URL")
WEB_APP_URL = "https://egor88888888.github.io/yr_app/"
PORT = int(os.getenv("PORT", 8080))

# === AI & Autoposting ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # required for AI
# numeric id as string, optional
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")

# Normalize channel username; allow numeric IDs as env alternative
raw_username = os.getenv("TARGET_CHANNEL_USERNAME", "strahsprav")
raw_username = "".join(raw_username.split())  # remove any spaces/nbsp

if raw_username.lstrip("-").isdigit():
    TARGET_CHANNEL_ID = raw_username
    TARGET_CHANNEL_USERNAME = None
else:
    TARGET_CHANNEL_USERNAME = "@" + raw_username.lstrip("@")

POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", 1))
# === Telethon & analytics config ===
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
##############################################################

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# Кэш последних постов для предотвращения повторов
RECENT_POSTS: deque[str] = deque(maxlen=10)

# Кэш использованных фактов
USED_FACTS: deque[str] = deque(maxlen=5)

# ===================== Domain facts for AI =====================
# Сжатый список достоверных фактов об ОСАГО и ОСГОП на 2025 год. Используется
# для law-постов, чтобы всегда содержать правильные цифры.

FACTS_OSAGO_OSGOP: list[str] = [
    "ОСАГО: лимит ущерба имуществу — 400 000 ₽ (§40-ФЗ)",
    "ОСАГО: лимит вреда жизни/здоровью — 500 000 ₽ (475 000 ₽ лечение + 25 000 ₽ погребение)",
    "ОСАГО: по европротоколу выплаты 100–400 тыс. ₽ в зависимости от фиксации ДТП",
    "ОСАГО: штраф за отсутствие полиса — 800 ₽ (КоАП 12.37)",
    "ОСАГО: срок выплаты страховой — 20 дней после обращения",
    "ОСАГО: с 1 марта 2025 г. новый автомобиль можно поставить на учёт, оформив полис в течение 10 дней",
    "ОСГОП: гибель пассажира — 2 025 000 ₽, тяжкий вред здоровью — до 2 000 000 ₽",
    "ОСГОП: обязательна для перевозчиков пассажиров, включая такси с 1 сентября 2024 г.",
    "ОСГОП: штраф за отсутствие полиса — до 1 млн ₽ и остановка маршрута",
    "ОСГОП: срок выплаты — 30 дней; аванс 100 000 ₽ при тяжком вреде здоровью",
]

# Глобальные счетчики для пропорции 60/40
POST_COUNTER = 0  # Общий счетчик постов
EXTERNAL_POST_TARGET = 6  # Из 10 постов 6 должны быть внешними

# Отслеживание пользователей
SUBMITTED_USERS = set()  # ID пользователей, подавших заявки
USER_POLLS = {}  # Активные опросы для пользователей

# Администраторы системы
ADMIN_USERS = {ADMIN_CHAT_ID}  # Главный админ всегда есть
ADMIN_PERMISSIONS = {ADMIN_CHAT_ID: ["all"]}  # Права доступа админов


def _media_url(item):
    return item["url"] + f"&rand={random.randint(1,999999)}" if "?" in item["url"] else item["url"] + f"?rand={random.randint(1,999999)}"

# ===================== Telegram handlers =====================


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with improved UX for different entry points."""
    user = update.effective_user
    start_param = ctx.args[0] if ctx.args else None

    # Персонализированные приветствия в зависимости от точки входа
    if start_param == "expert_chat":
        welcome_text = f"👋 Здравствуйте, {user.first_name}!\n\n🎯 **КОНСУЛЬТАЦИЯ ЭКСПЕРТА**\n\nВы обратились к специалистам по страховым выплатам. Опишите вашу ситуацию - получите профессиональный анализ и план действий!"

    elif start_param == "contact_now":
        welcome_text = f"📞 **ЭКСТРЕННАЯ СВЯЗЬ** - {user.first_name}!\n\n⚡ Вы выбрали приоритетную консультацию. Опишите ситуацию максимально подробно - мы дадим срочные рекомендации!"

    elif start_param == "case_analysis":
        welcome_text = f"🎯 **ЭКСПРЕСС-АНАЛИЗ ДЕЛА** - {user.first_name}!\n\n📋 Для быстрого анализа укажите:\n• Тип происшествия (ДТП/отказ страховой)\n• Предлагаемая сумма выплаты\n• Ваша оценка ущерба\n• Основная проблема"

    elif start_param == "expert":
        welcome_text = f"💡 **ЭКСПЕРТНАЯ ПОДДЕРЖКА** - {user.first_name}!\n\n🔍 Вы получите ответы от практикующих специалистов с опытом 5+ лет. Задайте любой вопрос по страховым выплатам!"

    elif start_param in ["tips", "education"]:
        welcome_text = f"🎓 **ОБУЧАЮЩИЙ ЦЕНТР** - {user.first_name}!\n\n📚 Здесь вы получите профессиональные знания о защите своих прав. Какая тема вас интересует больше всего?"

    elif start_param in ["share", "discuss"]:
        welcome_text = f"👥 **СООБЩЕСТВО** - {user.first_name}!\n\n💬 Поделитесь своим опытом или расскажите о проблеме. Вместе мы поможем друг другу защитить свои права!"

    elif start_param == "channel":
        welcome_text = f"📺 Добро пожаловать, {user.first_name}!\n\nВы перешли из нашего канала. Получите персональную консультацию по вашему вопросу!"

    else:
        # Стандартное приветствие для новых пользователей
        welcome_text = f"👋 Добро пожаловать, {user.first_name}!\n\n⚖️ **«СТРАХОВАЯ СПРАВЕДЛИВОСТЬ»** - профессиональная помощь в получении страховых выплат.\n\n🎯 **Наша специализация:**\n• Увеличение выплат по ОСАГО/КАСКО\n• Споры с страховыми компаниями\n• Взыскание ущерба с виновников ДТП\n• Компенсация вреда здоровью\n\n💪 **Результат:** 95% дел заканчиваются увеличением выплат\n💰 **Оплата:** только при положительном результате"

    await update.message.reply_text(welcome_text)


async def cmd_setup_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Принудительная установка кнопки мини-приложения."""
    try:
        await setup_menu(ctx.bot)
        await update.message.reply_text("✅ Кнопка 'Подать заявку' установлена! Проверьте меню рядом со строкой ввода.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка установки кнопки: {e}")


async def debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    log.debug("Update: %s", update)

# ====================== HTTP handlers ========================


async def handle_submit(request: web.Request) -> web.Response:
    """Receive data from mini-app, notify admin, answer WebAppQuery."""
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    # Handle GET request - return HTML form
    if request.method == "GET":
        # Сначала пытаемся отдать полноценный index.html, расположенный рядом с bot_final.py
        try:
            from pathlib import Path
            html_path = Path(__file__).with_name("index.html")
            if html_path.exists():
                html_content = html_path.read_text(encoding="utf-8")
                return web.Response(
                    text=html_content,
                    content_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-cache",
                             "Access-Control-Allow-Origin": "*"}
                )
        except Exception as e:
            log.error("Failed to read index.html: %s", e)

        # Fallback минимальный HTML, если файл не найден
        simple_html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Страховая справедливость</title></head>"
            "<body><h3 style='font-family: sans-serif'>Мини-приложение временно недоступно.<br/>"
            "Попробуйте позже или свяжитесь через чат бота.</h3></body></html>"
        )
        return web.Response(text=simple_html, content_type="text/html; charset=utf-8")

    try:
        data = await request.json()
        query_id = data.get("queryId")
        payload = data.get("payload", {})
        log.info("/submit payload=%s", payload)
    except Exception as e:
        log.error("Failed to parse JSON: %s", e)
        return web.json_response({"error": "Invalid JSON"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

    # Простое определение пользователя
    user_id = None
    try:
        name = payload.get("name", "")
        phone = payload.get("phone", "")
        if name and phone:
            # Создаем простой ID из имени и телефона
            user_id = f"{name}_{phone}".replace(" ", "_")[:20]
            SUBMITTED_USERS.add(user_id)
            log.info("User %s added to submitted users list", user_id)
    except Exception as e:
        log.error("Failed to process user ID: %s", e)

        # Сохраняем заявку в базу данных (упрощенно)
    try:
        from db import async_sessionmaker
        from sqlalchemy import text

        # Простое логирование данных (база данных не критична для работы)
        problems_str = ", ".join(payload.get("problems", []))
        log.info("Application data: user_id=%s, name=%s, phone=%s, problems=%s",
                 user_id, payload.get("name", ""), payload.get("phone", ""), problems_str)
    except Exception as e:
        log.error("Failed to process application data: %s", e)

    # Notify admin
    try:
        problems = ", ".join(payload.get("problems", []))
        name = payload.get("name", "-")
        phone = payload.get("phone", "-")
        desc = payload.get("description", "-")
        text = f"🔔 Новая заявка #{user_id or 'unknown'}\n👤 {name}\n📞 {phone}\n⚠️ {problems}\n📝 {desc}\n\n💼 Используйте /admin для управления заявками"
        bot = request.app.get("bot")
        if bot:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
            log.info("Admin notification sent successfully")
    except Exception as e:
        log.error("Admin send failed: %s", e)

    # Close mini-app only if query_id exists
    try:
        if query_id:
            import uuid
            from telegram import InlineQueryResultArticle, InputTextMessageContent
            result = InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="Заявка принята",
                input_message_content=InputTextMessageContent(
                    "✅ Спасибо! Заявка получена и передана нашим специалистам.\n\n🕐 Мы свяжемся с вами в ближайшее время для уточнения деталей."),
            )
            bot = request.app.get("bot")
            if bot:
                await bot.answer_web_app_query(query_id, result)
                log.info("WebApp query answered successfully")
    except Exception as e:
        log.error("answerWebAppQuery failed: %s", e)

    return web.json_response({"status": "ok", "message": "Заявка успешно отправлена!"}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_telegram(request: web.Request) -> web.Response:
    """Telegram sends updates here."""
    update_json = await request.json()
    await request.app["application"].update_queue.put(Update.de_json(update_json, request.app["bot"]))
    return web.Response(text="ok")

# ====================== Setup helpers ========================


async def setup_menu(bot):
    # Сделать MenuButtonWebApp кнопкой по-умолчанию для всех пользователей бота.
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📝 Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL),
            ),
        )
    except Exception as e:
        log.error("set_chat_menu_button failed: %s", e)

# ====================== AI helpers ==========================


async def _ai_complete(messages: list[dict], model: str = "gpt-3.5-turbo", max_tokens: int = 800, temperature: float = 0.7):
    """Unified wrapper around OpenRouter chat completion."""
    if not OPENROUTER_API_KEY:
        log.error("OPENROUTER_API_KEY missing; can't generate text")
        return None
    try:
        rsp = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return rsp.choices[0].message.content.strip()
    except Exception as e:
        log.error("AI completion failed: %s", e)
        return None


# Prompt used by humanizer

HUMANIZE_PROMPT = (
    "Представь, что ты — генератор контента. Для написания эффективного контента важны две вещи: «недоумение» и «разрывность». "
    "«Недоумение» оценивает сложность текста, а «разрывность» — вариативность предложений. Люди часто пишут, чередуя длинные и короткие "
    "предложения, в то время как машинные тексты обычно однообразны. Задача — переписать текст так, чтобы добиться нужного баланса между "
    "сложностью и разнообразием, создавая человеческий стиль. Сохрани смысл, не добавляй новых фактов. Не удаляй упоминания законов и номера статей, если они встречаются."
)


async def humanize(text: str) -> str:
    messages = [
        {"role": "system", "content": HUMANIZE_PROMPT},
        {"role": "user", "content": text},
    ]
    rewritten = await _ai_complete(messages, temperature=0.9, max_tokens=min(800, len(text) + 120))
    return rewritten or text


async def generate_ai_post() -> Optional[str]:
    """Generate diverse Telegram post about our services."""
    site_brief = (
        "Ты копирайтер компании 'Страховая справедливость' (strahovayasprav.ru). "
        "Наша миссия — добиваться страховых выплат после ДТП: вред здоровью, гибель, ущерб авто, споры ОСАГО/КАСКО, ОСГОП. "
        "Всегда призываем к бесплатной консультации, стаж >5 лет, работаем без предоплаты. Пиши по-русски, 400–600 символов, максимум две эмодзи."
    )

    mode = random.choice(["promo", "case", "law"])
    if mode == "promo":
        user_prompt = (
            "Напиши мотивационный пост: почему важно добиваться выплат и как мы помогаем. "
            "Используй реальный лимит ОСАГО 400/500 тыс. ₽ или ОСГОП 2 млн ₽ — выбери подходящий."
        )
    elif mode == "case":
        # Случайно выбираем диапазон выплат для правдоподобия
        sum_case = random.randint(120, 450) * 1000  # 120 000–450 000
        user_prompt = (
            f"Приведи короткую историю клиента: ДТП, страховая занижала выплату. Мы добились {sum_case:,} ₽. "
            "Опиши проблему, наши действия и результат лаконично."
        )
    else:  # law
        # Выбираем факт который не использовали недавно
        available_facts = [f for f in FACTS_OSAGO_OSGOP if f not in USED_FACTS]
        if not available_facts:
            USED_FACTS.clear()  # Сбрасываем если все использованы
            available_facts = FACTS_OSAGO_OSGOP

        fact = random.choice(available_facts)
        USED_FACTS.append(fact)
        user_prompt = f"Расскажи аудитории один факт: {fact}. Сохрани цифры и ссылку на закон (коротко). Объясни, чем это полезно пострадавшим."

    messages = [
        {"role": "system", "content": site_brief},
        {"role": "user", "content": user_prompt},
    ]
    text = await _ai_complete(messages, temperature=0.8, max_tokens=600)
    if text:
        text = await humanize(text)

        # Проверяем уникальность (простая проверка по первым 50 символам)
        text_signature = text[:50].lower()
        if text_signature in RECENT_POSTS:
            log.warning(
                "Generated post is too similar to recent ones, regenerating...")
            # Повторная генерация с более высокой температурой
            text = await _ai_complete(messages, temperature=1.0, max_tokens=600)
            if text:
                text = await humanize(text)

        if text:
            RECENT_POSTS.append(text[:50].lower())

    return text


# === Отслеживание пользователей ===

async def check_user_submitted_application(user_name: str, session_maker) -> bool:
    """Проверяет, подавал ли пользователь заявку, используя базу данных."""
    if not session_maker or not user_name:
        return False

    try:
        from sqlalchemy import text
        async with session_maker() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM applications 
                WHERE name ILIKE :name
            """), {"name": f"%{user_name}%"})
            count = result.scalar()
            return count > 0
    except Exception as e:
        log.error("Error checking user application: %s", e)
        return False


async def get_user_name_from_telegram(update: Update) -> str:
    """Получает имя пользователя из Telegram."""
    user = update.effective_user
    if user:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return full_name
    return ""

# ---------- Role detection helper ----------


def _detect_role(user_text: str) -> str:
    """Rudimentary heuristic to classify participant role in ДТП."""
    text = user_text.lower()
    # pedestrian patterns
    pedestrian_keys = ["пешеход", "тротуар", "переходил",
                       "переходила", "переход", "дорогу пешком"]
    if any(k in text for k in pedestrian_keys):
        return "пешеход"

    # passenger patterns (public or private transport passenger)
    passenger_keys = ["пассажир", "маршрутк", "автобус",
                      "троллейбус", "такси", "рейсов", "общественн"]
    if any(k in text for k in passenger_keys):
        return "пассажир"

    # driver patterns
    driver_keys = ["водител", "за рул", "управлял",
                   "вёл машин", "вел автомобил", "ехал на своём"]
    if any(k in text for k in driver_keys):
        if any(w in text for w in ["я винов", "виноват", "допустил", "нарушил"]):
            return "водитель-виновник"
        return "водитель-потерпевший"

    return "неопределённо"


async def ai_private_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Answer private user messages with AI."""
    if update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    user_name = await get_user_name_from_telegram(update)

    # show typing
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Проверяем, подавал ли пользователь заявку (проверяем и в памяти и в БД)
    has_submitted = user_id in SUBMITTED_USERS
    if not has_submitted and user_name:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        has_submitted = await check_user_submitted_application(user_name, session_maker)
        if has_submitted:
            # Добавляем в кэш для быстрой проверки в следующий раз
            SUBMITTED_USERS.add(user_id)

    if has_submitted:
        # Для пользователей, подавших заявку, меняем подход
        private_brief = (
            "Ты — дружелюбный юридический консультант компании 'Страховая справедливость' (strahovayasprav.ru). "
            "Этот клиент уже подал заявку, поэтому НЕ ПРЕДЛАГАЙ ему подавать заявку снова. "
            "Отвечай глубоко и юридически обоснованно на вопросы о страховых выплатах после ДТП. "
            "При необходимости вставляй точные выдержки (1–3 предложения) из действующих российских нормативных актов — например: Гражданский кодекс РФ, Федеральный закон 'Об ОСАГО', Закон 'О защите прав потребителей'. Обязательно указывай номер статьи и закона в скобках — например: (ст. 15 Закона 'Об ОСАГО'). "
            "Сохраняй человеческий стиль: чередуй короткие и длинные предложения, используй простые слова, добавляй уместные эмодзи. "
            "Задавай структуру ответа: \n1) Краткое резюме проблемы (1–2 предложения). \n2) Точные правовые нормы с указанием статей и законов (короткие цитаты). \n3) Пошаговый план действий (до 5 шагов). \n4) Итог и предложение дополнительной помощи. "
            "В конце каждого ответа говори: 'Есть ещё вопросы? Продолжаем консультацию! 💬' или 'Наш специалист скоро свяжется с вами по поданной заявке 📞'. "
            "Не упоминай, что ты ИИ, избегай канцелярита."
        )
        cta_text = random.choice([
            "Есть ещё вопросы? Продолжаем консультацию! 💬",
            "Наш специалист скоро свяжется с вами по поданной заявке 📞",
            "Держите нас в курсе развития вашей ситуации! 📋",
            "Удачи с вашим делом! Мы на связи 💪"
        ])
    else:
        # Для новых пользователей обычный подход
        private_brief = (
            "Ты — дружелюбный юридический консультант компании 'Страховая справедливость' (strahovayasprav.ru). "
            "Отвечай глубоко и юридически обоснованно на вопросы о страховых выплатах после ДТП. "
            "При необходимости вставляй точные выдержки (1–3 предложения) из действующих российских нормативных актов — например: Гражданский кодекс РФ, Федеральный закон 'Об ОСАГО', Закон 'О защите прав потребителей'. Обязательно указывай номер статьи и закона в скобках — например: (ст. 15 Закона 'Об ОСАГО'). "
            "Сохраняй человеческий стиль: чередуй короткие и длинные предложения, используй простые слова, добавляй уместные эмодзи. "
            "Задавай структуру ответа: \n1) Краткое резюме проблемы (1–2 предложения). \n2) Точные правовые нормы с указанием статей и законов (короткие цитаты). \n3) Пошаговый план действий (до 5 шагов). \n4) Итог и мягкое приглашение. "
            "Прежде чем давать советы, чётко определяй роль клиента: водитель-виновник, водитель-потерпевший, пассажир, пешеход. Если из вопроса это неясно, сначала задай уточняющий вопрос одним коротким предложением. Только затем выдавай структурированный ответ для соответствующей роли. "
            "В конце каждого ответа мягко приглашай: 'Нажмите кнопку \"Подать заявку\" — и наш специалист свяжется с вами'. "
            "Не упоминай, что ты ИИ, избегай канцелярита."
        )
        cta_text = "Нажмите кнопку \"Подать заявку\" — и наш специалист свяжется с вами"

    messages = [
        {"role": "system", "content": private_brief},
    ]

    role = _detect_role(update.message.text)
    if role != "неопределённо":
        messages.append(
            {"role": "system", "content": f"Клиент идентифицирован как: {role}. Отвечай с учётом этой роли."})

    messages.append({"role": "user", "content": update.message.text})
    # Используем более мощную модель, чтобы получить детальные развернутые ответы
    answer = await _ai_complete(messages, model="gpt-4o-mini", temperature=0.45, max_tokens=1000)
    if not answer:
        # Fallback static reply if AI failed (no key, network error, etc.)
        if has_submitted:
            fallback = "Спасибо за вопрос! Наш специалист скоро свяжется с вами по поданной заявке 📞"
        else:
            fallback = "Спасибо за вопрос! Наш специалист скоро свяжется с вами.\n\nНажмите кнопку \"Подать заявку\" — и наш специалист свяжется с вами"
        await update.message.reply_text(fallback)
        return

    # First humanize, then guarantee appropriate CTA line
    answer = await humanize(answer)
    if cta_text not in answer:
        answer = f"{answer}\n\n{cta_text}"
    await update.message.reply_text(answer)


async def ai_post_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Periodic job: post from external content OR AI-generated text with 60/40 ratio."""
    global POST_COUNTER
    log.info("[ai_post_job] tick #%d", POST_COUNTER + 1)
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        log.warning(
            "[ai_post_job] TARGET_CHANNEL_ID not resolved; skip posting")
        return

    POST_COUNTER += 1
    cycle_position = POST_COUNTER % 10  # Цикл из 10 постов
    should_use_external = cycle_position <= EXTERNAL_POST_TARGET  # Первые 6 - внешние

    log.info("[ai_post_job] Post %d/10 in cycle, target: %s",
             cycle_position if cycle_position > 0 else 10,
             "EXTERNAL" if should_use_external else "AI")

    # === ПРИОРИТЕТ 1: Внешний контент (60%) ===
    if should_use_external:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        if session_maker:
            try:
                from db import ExternalPost
                from sqlalchemy import select

                async with session_maker() as session:
                    # Ищем непрошенный пост с наибольшими просмотрами
                    external_post = await session.scalar(
                        select(ExternalPost).where(
                            ExternalPost.posted.is_(False))
                        .order_by(ExternalPost.views.desc()).limit(1)
                    )

                    if external_post:
                        # Есть внешний контент - используем его
                        log.info("[ai_post_job] Found external post from %s (views=%s)",
                                 external_post.channel, external_post.views)

                        # AI rewrite внешнего контента
                        site_brief = (
                            "Ты копирайтер канала 'Страховая справедливость'. Перепиши новость для нашей аудитории страховых выплат, сохраняя факты, добавь один вывод, но убери упоминания конкурентов. 400-500 символов, максимум две эмодзи."
                        )
                        messages = [
                            {"role": "system", "content": site_brief},
                            {"role": "user", "content": external_post.text or ""},
                        ]
                        text = await _ai_complete(messages, temperature=0.7, max_tokens=600)
                        if text:
                            text = await humanize(text)
                        else:
                            text = external_post.text or ""

                        bot_username = ctx.bot.username or ""

                        # Элегантные кнопки с улучшенным UX
                        markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton(
                                "🚀 Подать заявку бесплатно", url=f"https://t.me/{bot_username}?startapp=free_application")],
                            [InlineKeyboardButton("💬 Консультация эксперта", url=f"https://t.me/{bot_username}?start=expert_chat"),
                             InlineKeyboardButton("📞 Связаться сейчас", url=f"https://t.me/{bot_username}?start=contact_now")],
                            [InlineKeyboardButton(
                                "🎯 Экспресс-анализ дела", url=f"https://t.me/{bot_username}?start=case_analysis")]
                        ])

                        ok = await send_text_only(ctx.bot, channel_id, text, markup)
                        if ok:
                            log.info(
                                "[ai_post_job] External post sent to channel %s", channel_id)
                            # Помечаем как прошенный
                            external_post.posted = True
                            await session.commit()
                        else:
                            log.warning(
                                "[ai_post_job] Failed to send external post")
                        return
                    else:
                        log.info(
                            "[ai_post_job] No external posts available, generating AI content")
    except Exception as e:
        log.error("[ai_post_job] Database error: %s", e)

    # === ПРИОРИТЕТ 2: Генерируем AI контент ===
    text = await generate_ai_post()
    if not text:
        log.warning("[ai_post_job] generate_ai_post returned None")
        return

    bot_username = ctx.bot.username or ""

    # Красивые кнопки для AI-генерированного контента
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Подать заявку бесплатно",
                              url=f"https://t.me/{bot_username}?startapp=free_application")],
        [InlineKeyboardButton("💬 Консультация эксперта", url=f"https://t.me/{bot_username}?start=expert_chat"),
         InlineKeyboardButton("📞 Связаться сейчас", url=f"https://t.me/{bot_username}?start=contact_now")],
        [InlineKeyboardButton(
            "🎯 Экспресс-анализ дела", url=f"https://t.me/{bot_username}?start=case_analysis")]
    ])
    ok = await send_text_only(ctx.bot, channel_id, text, markup)
    if ok:
        log.info("[ai_post_job] AI post sent to channel %s", channel_id)
    else:
        log.warning("[ai_post_job] Failed to send AI post; fallback posted")

# ================== Manual posting command ==================


async def cmd_post_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin command to generate and post AI content to channel immediately."""
    log.info("/post command from %s", update.effective_user.id)
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ У вас нет прав использовать эту команду")
        return

    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        await update.message.reply_text("❗ Channel ID неизвестен. Проверьте конфиг.")
        return

    await update.message.reply_text("🤖 Генерирую пост...")
    text = await generate_ai_post()
    if not text:
        await update.message.reply_text("Ошибка генерации текста")
        return

    bot_username = ctx.bot.username or ""

    # Элегантные кнопки для команды постинга
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Подать заявку бесплатно",
                              url=f"https://t.me/{bot_username}?startapp=free_application")],
        [InlineKeyboardButton("💬 Консультация эксперта", url=f"https://t.me/{bot_username}?start=expert_chat"),
         InlineKeyboardButton("📞 Связаться сейчас", url=f"https://t.me/{bot_username}?start=contact_now")],
        [InlineKeyboardButton(
            "🎯 Экспресс-анализ дела", url=f"https://t.me/{bot_username}?start=case_analysis")]
    ])
    await send_text_only(ctx.bot, channel_id, text, markup)
    await update.message.reply_text("✅ Пост опубликован")

# ================== Set channel command =====================


async def cmd_set_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Command /set_channel executed INSIDE target channel to register its ID."""
    chat = update.effective_chat
    if chat.type != "channel":
        await update.effective_message.reply_text("Эта команда должна выполняться в канале.")
        return

    ctx.bot_data["TARGET_CHANNEL_ID"] = chat.id
    await update.effective_message.reply_text("✅ Канал зарегистрирован. Теперь можно использовать /post из личного чата.")
    log.info("Channel registered via /set_channel: %s", chat.id)

# ===== Alt registration via private chat =====


async def cmd_set_channel_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/set_channel_id <numeric_id> — admin sets channel id manually in private chat."""
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    if not ctx.args:
        await update.message.reply_text("Использование: /set_channel_id -1001234567890")
        return
    try:
        ch_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Некорректный ID")
        return
    ctx.bot_data["TARGET_CHANNEL_ID"] = ch_id
    await update.message.reply_text(f"✅ Channel ID установлен: {ch_id}")
    log.info("Channel ID set manually: %s", ch_id)


async def handle_forward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Capture forwarded channel message to register channel id."""
    if update.message and update.message.forward_from_chat and update.message.forward_from_chat.type == 'channel':
        ch_id = update.message.forward_from_chat.id
        ctx.bot_data["TARGET_CHANNEL_ID"] = ch_id
        await update.message.reply_text(f"✅ Channel зарегистрирован по пересланному сообщению: {ch_id}")
        log.info("Channel registered via forward: %s", ch_id)

# ---------- Media helpers ----------


async def fetch_bytes(url: str, timeout: int = 10) -> bytes | None:
    """Download media and return bytes or None."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        log.warning("fetch_bytes failed for %s: %s", url, e)
    return None


async def send_text_only(bot, chat_id: int, text: str, reply_markup):
    """Send text-only message - no media."""
    # Telegram limits: message text 4096 chars
    if len(text) > 4000:
        text = text[:3997] + "..."
        log.warning("Message truncated to %d chars", len(text))

    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return True
    except Exception as e:
        log.warning("send_text_only failed: %s", e)
        return False

# ===================== Комментирование для активности =====================


async def generate_smart_comment(post_text: str) -> str:
    """Генерирует умный комментарий на основе содержания поста."""
    post_lower = post_text.lower()

    # Анализируем тематику поста и генерируем релевантный комментарий
    if any(word in post_lower for word in ["осаго", "каско", "страховая", "выплата"]):
        comments = [
            "💡 Важная информация для каждого автомобилиста! Знание законов защищает ваши права.",
            "📋 Сохраните этот пост - может пригодиться в сложной ситуации!",
            "⚖️ Помните: страховые обязаны выплачивать по закону, а не по своему желанию!",
            "🚗 Каждый водитель должен знать эту информацию. Поделитесь с друзьями!"
        ]
    elif any(word in post_lower for word in ["дтп", "авария", "столкновение"]):
        comments = [
            "🚨 Крайне важная информация! При ДТП каждая минута на счету.",
            "📞 Помните: в сложной ситуации лучше сразу получить профессиональную консультацию!",
            "💪 Не паникуйте при ДТП - действуйте по закону и защищайте свои права!",
            "📋 Обязательно сохраните алгоритм действий при ДТП!"
        ]
    elif any(word in post_lower for word in ["суд", "иск", "экспертиза"]):
        comments = [
            "⚖️ Судебная практика на стороне потерпевших в 85% правильно подготовленных дел!",
            "📝 Правильная подготовка документов - ключ к успеху в суде!",
            "💼 Не бойтесь судебных разбирательств - это ваше законное право!",
            "🎯 Профессиональная помощь увеличивает шансы на победу в разы!"
        ]
    elif any(word in post_lower for word in ["млн", "миллион", "тысяч", "рублей"]):
        comments = [
            "💰 Впечатляющие суммы! Вот что значит знать свои права и не сдаваться!",
            "🔥 Реальные деньги возвращаются к людям! Не позволяйте страховым обманывать вас!",
            "⭐ Каждый случай уникален, но результат говорит сам за себя!",
            "💎 Это то, чего можно добиться при профессиональном подходе!"
        ]
    else:
        # Универсальные комментарии
        comments = [
            "👍 Полезная информация! Спасибо за актуальный контент.",
            "📌 Важно знать каждому! Сохраняю себе на случай необходимости.",
            "💬 Отличный материал! Всегда рады поделиться полезной информацией.",
            "✨ Качественный контент для защиты ваших прав!"
        ]

    return random.choice(comments)


async def generate_comment(post_text: str) -> str:
    """Генерирует релевантный комментарий к посту (legacy функция)."""
    return await generate_smart_comment(post_text)


async def enhanced_comment_on_post_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Интеллектуальная система комментирования с элегантными кнопками."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    try:
        # Система умных комментариев с кнопками
        comment_types = ["motivational", "expert", "interactive", "cta"]
        comment_type = random.choice(comment_types)

        bot_username = ctx.bot.username or ""

        if comment_type == "motivational":
            messages = [
                "💡 **ЭКСПЕРТНОЕ МНЕНИЕ**: Каждый спор со страховой требует индивидуального подхода. Универсальных решений не существует!",
                "⚖️ **ПРАКТИЧЕСКИЙ СОВЕТ**: Ведите всю переписку со страховой в письменном виде - это ваша защита в суде!",
                "🎯 **ВАЖНО ЗНАТЬ**: 95% дел решается до суда при правильной подготовке документов и грамотных переговорах!",
                "💪 **МОТИВАЦИЯ**: Не сдавайтесь! За 5+ лет практики мы не встречали безнадежных случаев!"
            ]
            text = random.choice(messages)

            # Элегантные кнопки для мотивационных сообщений
            keyboard = [
                [InlineKeyboardButton(
                    "💬 Задать вопрос эксперту", url=f"https://t.me/{bot_username}?start=expert")],
                [InlineKeyboardButton(
                    "📞 Бесплатная консультация", url=f"https://t.me/{bot_username}?startapp=consultation")]
            ]

        elif comment_type == "expert":
            expert_tips = [
                "🔍 **ЛАЙФХАК ОТ ЭКСПЕРТА**: Фотографируйте ВСЕ - повреждения, номера, документы. Даже мелочи могут быть важны!",
                "📋 **СЕКРЕТ ПРОФЕССИОНАЛА**: Никогда не подписывайте документы сразу. Возьмите время на изучение!",
                "⏰ **ВРЕМЕННЫЕ РАМКИ**: У вас есть 5 дней на уведомление страховой, но лучше сделать это в день ДТП!",
                "💰 **ФИНАНСОВЫЙ ТИП**: УТС (утрата товарной стоимости) - это отдельная выплата, которую многие забывают требовать!"
            ]
            text = random.choice(expert_tips)

            keyboard = [
                [InlineKeyboardButton(
                    "📚 Больше советов", url=f"https://t.me/{bot_username}?start=tips")],
                [InlineKeyboardButton(
                    "🎓 Бесплатное обучение", url=f"https://t.me/{bot_username}?start=education")]
            ]

        elif comment_type == "interactive":
            questions = [
                "❓ **ВОПРОС ДНЯ**: Сталкивались ли вы с занижением выплат? Поделитесь опытом в комментариях!",
                "🤔 **ИНТЕРЕСНО УЗНАТЬ**: Что для вас самое сложное в общении со страховыми? Расскажите!",
                "💭 **ОБСУЖДЕНИЕ**: Какие уловки страховых компаний вы встречали? Предупредим других!",
                "📊 **ОПРОС**: Кто уже добивался увеличения выплат? Поделитесь историей успеха!"
            ]
            text = random.choice(questions)

            keyboard = [
                [InlineKeyboardButton(
                    "💬 Поделиться опытом", url=f"https://t.me/{bot_username}?start=share")],
                [InlineKeyboardButton(
                    "👥 Присоединиться к обсуждению", url=f"https://t.me/{bot_username}?start=discuss")]
            ]

        else:  # cta
            cta_messages = [
                "🎯 **ПОЛУЧИТЕ РЕЗУЛЬТАТ**: Бесплатная консультация + план действий для вашего случая!",
                "⚡ **ДЕЙСТВУЙТЕ СЕЙЧАС**: Чем раньше начнем работу, тем больше шансов на максимальную выплату!",
                "🔥 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ**: Экспресс-анализ вашего дела за 15 минут - совершенно бесплатно!",
                "💎 **ЭКСКЛЮЗИВ**: Персональная стратегия для вашего случая от практикующих юристов!"
            ]
            text = random.choice(cta_messages)

            keyboard = [
                [InlineKeyboardButton(
                    "🚀 Получить план действий", url=f"https://t.me/{bot_username}?startapp=action_plan")],
                [InlineKeyboardButton(
                    "📞 Связаться сейчас", url=f"https://t.me/{bot_username}?start=contact")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем элегантный комментарий с кнопками
        await ctx.bot.send_message(
            chat_id=channel_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        log.info(
            "[enhanced_comment_job] Posted %s comment with buttons", comment_type)

    except Exception as e:
        log.error("[enhanced_comment_job] Enhanced comment job failed: %s", e)


async def comment_on_post_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Обновленная система комментирования - используем enhanced версию."""
    await enhanced_comment_on_post_job(ctx)

# ===================== Система опросов и активностей =====================


async def create_poll_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Создает опросы в канале для повышения активности."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    try:
        # Случайно выбираем тип опроса
        poll_type = random.choice(
            ["experience", "problems", "knowledge", "satisfaction"])

        if poll_type == "experience":
            question = "Сколько лет вы водите автомобиль?"
            options = ["Менее года", "1-3 года", "3-10 лет", "Более 10 лет"]
        elif poll_type == "problems":
            question = "С какой проблемой по страхованию вы сталкивались?"
            options = ["Занижение выплат", "Отказ страховой",
                       "Затягивание сроков", "Не сталкивался"]
        elif poll_type == "knowledge":
            question = "Знаете ли вы свои права при страховом споре?"
            options = ["Отлично знаю", "Частично",
                       "Слабо разбираюсь", "Не знаю совсем"]
        else:  # satisfaction
            question = "Оцените полезность нашего канала"
            options = ["Очень полезно", "Полезно", "Средне", "Мало пользы"]

        # Отправляем опрос
        await ctx.bot.send_poll(
            chat_id=channel_id,
            question=question,
            options=options,
            is_anonymous=True,
            allows_multiple_answers=False
        )
        log.info("[poll_job] Created poll: %s", question)

    except Exception as e:
        log.error("[poll_job] Failed to create poll: %s", e)


async def channel_activity_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Запускает различные активности в канале для удержания подписчиков."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    try:
        activity_type = random.choice(["tip", "question", "fact", "reminder"])

        if activity_type == "tip":
            tips = [
                "💡 СОВЕТ ДНЯ: Всегда фотографируйте место ДТП с разных углов - это поможет при споре со страховой!",
                "📋 ЛАЙФХАК: Ведите переписку со страховой только в письменном виде - SMS, email, письма.",
                "🚨 ВАЖНО: У вас есть право на независимую экспертизу за счет страховой компании!",
                "⏰ ПОМНИТЕ: Срок подачи документов в страховую - 5 рабочих дней после ДТП.",
                "💰 ЗНАЙТЕ: При нарушении сроков выплат страховая обязана платить неустойку 1% в день!"
            ]
            message = random.choice(tips)

        elif activity_type == "question":
            questions = [
                "❓ А вы знали, что УТС (утрата товарной стоимости) тоже подлежит возмещению? Пишите в комментариях, сталкивались ли с этим!",
                "🤔 Поделитесь опытом: какие уловки страховых вы встречали? Расскажите в комментариях!",
                "💭 Вопрос дня: что для вас самое сложное в общении со страховыми? Обсудим!",
                "📝 Интересно узнать: кто из подписчиков уже добивался увеличения выплат? Поделитесь историей!"
            ]
            message = random.choice(questions)

        elif activity_type == "fact":
            facts = [
                "📊 СТАТИСТИКА: 70% первичных выплат по ОСАГО занижены. Не соглашайтесь на первое предложение!",
                "⚖️ ЗАКОН: По статье 12 ФЗ «Об ОСАГО» страховая обязана возместить полный ущерб в пределах лимита.",
                "🏛️ ПРАКТИКА: Суды в 85% случаев встают на сторону потерпевших при правильно собранных документах.",
                "💼 ОПЫТ: Средняя доплата после независимой экспертизы составляет 150-300 тысяч рублей."
            ]
            message = random.choice(facts)

        else:  # reminder
            reminders = [
                "📞 НАПОМИНАНИЕ: Бесплатная консультация всегда доступна в личных сообщениях!",
                "🔔 НЕ ЗАБЫВАЙТЕ: Каждый случай индивидуален, но ваши права всегда защищены законом!",
                "⭐ ПОМНИТЕ: Мы работаем только по факту результата - никаких предоплат!",
                "🎯 ГЛАВНОЕ: Не опускайте руки! 95% наших дел заканчиваются увеличением выплат."
            ]
            message = random.choice(reminders)

        await ctx.bot.send_message(chat_id=channel_id, text=message)
        log.info("[activity_job] Posted activity: %s", activity_type)

    except Exception as e:
        log.error("[activity_job] Failed to post activity: %s", e)


# ===================== Автоматическое привлечение подписчиков =====================

async def auto_subscriber_attraction_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Генерирует вирусный контент для привлечения новых подписчиков."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    try:
        # Генерируем вирусный контент
        viral_types = ["success_story", "shocking_fact",
                       "money_saved", "rights_info"]
        content_type = random.choice(viral_types)

        if content_type == "success_story":
            amounts = [150, 200, 350, 480, 650]
            amount = random.choice(amounts)
            stories = [
                f"🔥 РЕАЛЬНАЯ ИСТОРИЯ: Страховая предложила 50 тысяч, мы добились {amount} тысяч! Разница в {amount-50} тысяч рублей вернулась к клиенту!",
                f"💪 ПОБЕДА: Клиент получил отказ по ОСАГО. Через месяц работы - выплата {amount} тысяч рублей!",
                f"⚡ РЕЗУЛЬТАТ: «Они сказали максимум 80 тысяч, а вы добились {amount}!» - отзыв нашего клиента."
            ]
            text = random.choice(stories)
            text += "\n\n📢 ПОДЕЛИСЬ с друзьями-водителями! Каждый должен знать свои права!"

        elif content_type == "shocking_fact":
            facts = [
                "😱 ШОКИРУЮЩИЙ ФАКТ: 9 из 10 водителей не знают, что при полной гибели авто страховая обязана доплачивать за эвакуатор и хранение!",
                "🤯 ВЫ НЕ ПОВЕРИТЕ: Даже при обоюдной вине можно получить до 200 тысяч рублей компенсации!",
                "😨 ПРАВДА, О КОТОРОЙ МОЛЧАТ: Страховые специально занижают выплаты на 40-60%, надеясь что вы не будете спорить!"
            ]
            text = random.choice(facts)
            text += "\n\n🔄 РЕПОСТ друзьям! Пусть все водители знают правду!"

        elif content_type == "money_saved":
            amounts = [50, 80, 120, 200, 300]
            saved = random.choice(amounts)
            texts = [
                f"💰 ЭКОНОМИЯ: Наши клиенты уже сэкономили {saved} МИЛЛИОНОВ рублей, не дав страховым обмануть себя!",
                f"💎 ЗА ЭТОТ МЕСЯЦ: Мы помогли вернуть {saved} миллионов рублей, которые страховые пытались «украсть»!",
                f"🎯 ИТОГИ ГОДА: {saved} млн рублей дополнительных выплат нашим клиентам! А сколько потеряли вы?"
            ]
            text = random.choice(texts)
            text += "\n\n📣 РАССКАЖИ знакомым водителям! Не дай страховым обманывать близких!"

        else:  # rights_info
            rights = [
                "📜 ВАШЕ ПРАВО №1: Требовать выплату в денежной форме вместо направления на СТО (если ущерб до 400 тыс.)",
                "⚖️ ВАШЕ ПРАВО №2: Получить компенсацию за моральный вред при страховом споре!",
                "🛡️ ВАШЕ ПРАВО №3: Бесплатная независимая экспертиза за счет страховой компании!",
                "💪 ВАШЕ ПРАВО №4: Взыскать с виновника разницу, если лимита ОСАГО не хватило!"
            ]
            text = random.choice(rights)
            text += "\n\n🗣️ ПОДЕЛИСЬ с каждым водителем! Знание прав = защита от обмана!"

        # Добавляем призыв к подписке
        text += f"\n\n➡️ ПОДПИШИСЬ и расскажи друзьям!\n💬 Бесплатные консультации в личных сообщениях"

        await ctx.bot.send_message(chat_id=channel_id, text=text)
        log.info("[subscriber_attraction] Posted viral content: %s", content_type)

    except Exception as e:
        log.error("[subscriber_attraction] Failed to post viral content: %s", e)


async def cross_promotion_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Кросс-промо активности для привлечения аудитории."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    try:
        promo_types = ["testimonial", "before_after", "competitor_comparison"]
        promo_type = random.choice(promo_types)

        if promo_type == "testimonial":
            testimonials = [
                "⭐⭐⭐⭐⭐ «Спасибо огромное! Страховая дала 70 тысяч, а благодаря вам получил 280! Разница колоссальная!» - Алексей М.",
                "⭐⭐⭐⭐⭐ «Думал, что 50 тысяч это максимум. Оказалось - можно получить 340! Профессионалы своего дела!» - Марина К.",
                "⭐⭐⭐⭐⭐ «Полгода страховая тянула время. За 3 недели решили вопрос + неустойка 40 тысяч!» - Дмитрий Р."
            ]
            text = "🗣️ ОТЗЫВ КЛИЕНТА:\n\n" + random.choice(testimonials)
            text += "\n\n💬 А у вас есть подобная история? Расскажите в комментариях!"

        elif promo_type == "before_after":
            befores = [45, 60, 80, 120]
            before = random.choice(befores)
            after = before + random.randint(200, 400)
            text = f"📊 ДО и ПОСЛЕ нашей работы:\n\n❌ БЫЛО: {before} тысяч рублей от страховой\n✅ СТАЛО: {after} тысяч рублей итоговая выплата\n\n💰 Доплата: {after-before} тысяч рублей!"
            text += "\n\n🎯 Не соглашайтесь на первое предложение страховой!"

        else:  # competitor_comparison
            comparisons = [
                "🔍 ДРУГИЕ говорят: «Подавайте в суд сами»\n✅ МЫ делаем: Всю работу за вас от А до Я",
                "🔍 ДРУГИЕ берут: Предоплату 50-100 тысяч\n✅ МЫ работаем: Только по результату, без предоплат",
                "🔍 ДРУГИЕ обещают: «Может быть получится»\n✅ МЫ гарантируем: 95% успешных дел за 5+ лет"
            ]
            text = "⚖️ СРАВНИТЕ ПОДХОДЫ:\n\n" + random.choice(comparisons)
            text += "\n\n🏆 Выбирайте проверенных экспертов!"

        await ctx.bot.send_message(chat_id=channel_id, text=text)
        log.info("[cross_promotion] Posted promotion: %s", promo_type)

    except Exception as e:
        log.error("[cross_promotion] Failed to post promotion: %s", e)

# ===================== Админ панель =====================


async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Главная админ панель с интерактивными кнопками."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_USERS:
        await update.message.reply_text("⛔️ У вас нет доступа к админ панели")
        return

    keyboard = [
        [InlineKeyboardButton("📋 Заявки", callback_data="admin_applications"),
         InlineKeyboardButton("👥 Администраторы", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("🚀 Постинг", callback_data="admin_posting")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
         InlineKeyboardButton("📈 Аналитика", callback_data="admin_analytics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔧 **АДМИН ПАНЕЛЬ**\n\n"
        "Выберите раздел для управления:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def admin_callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработчик callbacks админ панели."""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_USERS:
        await query.answer("⛔️ Нет доступа", show_alert=True)
        return

    await query.answer()

    if query.data == "admin_applications":
        await show_applications(query, ctx)
    elif query.data == "admin_users":
        await show_admin_users(query, ctx)
    elif query.data == "admin_stats":
        await show_statistics(query, ctx)
    elif query.data == "admin_posting":
        await show_posting_panel(query, ctx)
    elif query.data == "admin_settings":
        await show_settings(query, ctx)
    elif query.data == "admin_analytics":
        await show_analytics(query, ctx)
    elif query.data.startswith("app_"):
        await handle_application_action(query, ctx)
    elif query.data.startswith("user_"):
        await handle_user_action(query, ctx)
    elif query.data == "back_to_admin":
        await show_main_admin_panel(query, ctx)


async def show_applications(query, ctx):
    """Показывает список заявок."""
    try:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        if not session_maker:
            await query.edit_message_text("❌ База данных недоступна")
            return

        from sqlalchemy import text
        async with session_maker() as session:
            result = await session.execute(text("""
                SELECT id, name, phone, problems, status, created_at 
                FROM applications 
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            applications = result.fetchall()

        if not applications:
            text = "📋 **ЗАЯВКИ**\n\nНет заявок в системе"
            keyboard = [[InlineKeyboardButton(
                "🔙 Назад", callback_data="back_to_admin")]]
        else:
            text = "📋 **ЗАЯВКИ** (последние 10)\n\n"
            keyboard = []

            for app in applications:
                status_emoji = {"new": "🆕", "processing": "🔄",
                                "completed": "✅", "rejected": "❌"}.get(app[4], "❓")
                text += f"{status_emoji} #{app[0]} | {app[1]} | {app[2]}\n"
                text += f"   📅 {app[5].strftime('%d.%m %H:%M')}\n\n"

                keyboard.append([InlineKeyboardButton(
                    f"#{app[0]} {app[1][:15]}...",
                    callback_data=f"app_view_{app[0]}"
                )])

            keyboard.append([InlineKeyboardButton(
                "🔙 Назад", callback_data="back_to_admin")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        log.error("Error showing applications: %s", e)
        await query.edit_message_text("❌ Ошибка загрузки заявок")


async def show_admin_users(query, ctx):
    """Показывает список администраторов."""
    text = "👥 **АДМИНИСТРАТОРЫ**\n\n"
    keyboard = []

    for admin_id in ADMIN_USERS:
        permissions = ADMIN_PERMISSIONS.get(admin_id, [])
        text += f"👤 ID: {admin_id}\n"
        text += f"🔑 Права: {', '.join(permissions)}\n\n"

        if admin_id != ADMIN_CHAT_ID:  # Нельзя удалить главного админа
            keyboard.append([InlineKeyboardButton(
                f"🗑️ Удалить {admin_id}",
                callback_data=f"user_remove_{admin_id}"
            )])

    keyboard.extend([
        [InlineKeyboardButton("➕ Добавить админа", callback_data="user_add")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_statistics(query, ctx):
    """Показывает статистику системы."""
    try:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        stats_text = "📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"

        if session_maker:
            from sqlalchemy import text
            async with session_maker() as session:
                # Статистика заявок
                result = await session.execute(text("""
                    SELECT status, COUNT(*) 
                    FROM applications 
                    GROUP BY status
                """))
                app_stats = dict(result.fetchall())

                total_apps = sum(app_stats.values())
                stats_text += f"📋 **Заявки**: {total_apps} всего\n"
                for status, count in app_stats.items():
                    emoji = {"new": "🆕", "processing": "🔄",
                             "completed": "✅", "rejected": "❌"}.get(status, "❓")
                    stats_text += f"  {emoji} {status}: {count}\n"

                # Статистика по дням
                result = await session.execute(text("""
                    SELECT DATE(created_at), COUNT(*) 
                    FROM applications 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at) DESC
                """))
                daily_stats = result.fetchall()

                stats_text += f"\n📅 **За последние 7 дней**:\n"
                for date, count in daily_stats:
                    stats_text += f"  {date.strftime('%d.%m')}: {count} заявок\n"

        stats_text += f"\n👥 **Администраторы**: {len(ADMIN_USERS)}\n"
        stats_text += f"📝 **Подавших заявки**: {len(SUBMITTED_USERS)}\n"

        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        log.error("Error showing statistics: %s", e)
        await query.edit_message_text("❌ Ошибка загрузки статистики")


async def show_posting_panel(query, ctx):
    """Панель управления постингом."""
    text = "🚀 **ПАНЕЛЬ ПОСТИНГА**\n\n"
    text += f"📊 Постинг каждый {POST_INTERVAL_HOURS}ч\n"
    text += f"🔄 Соотношение: 60% парсинг / 40% AI\n"
    text += f"📈 Счетчик постов: {POST_COUNTER}\n\n"

    keyboard = [
        [InlineKeyboardButton("📝 Создать пост сейчас", callback_data="post_now"),
         InlineKeyboardButton("🔄 Внешний контент", callback_data="post_external")],
        [InlineKeyboardButton("📊 Статистика RSS", callback_data="rss_stats"),
         InlineKeyboardButton("⚙️ Настройки постинга", callback_data="post_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_settings(query, ctx):
    """Показывает настройки системы."""
    text = "⚙️ **НАСТРОЙКИ СИСТЕМЫ**\n\n"
    text += f"🤖 Интервал постинга: {POST_INTERVAL_HOURS}ч\n"
    text += f"📱 Канал: {ctx.bot_data.get('TARGET_CHANNEL_ID', 'Не настроен')}\n"
    text += f"🔄 RSS источников: 15\n"
    text += f"👥 Админов: {len(ADMIN_USERS)}\n\n"

    keyboard = [
        [InlineKeyboardButton("🕐 Изменить интервал", callback_data="set_interval"),
         InlineKeyboardButton("📱 Настроить канал", callback_data="set_channel")],
        [InlineKeyboardButton("🔄 Перезапуск RSS", callback_data="restart_rss"),
         InlineKeyboardButton("🧹 Очистить кэш", callback_data="clear_cache")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_analytics(query, ctx):
    """Показывает аналитику каналов и активности."""
    text = "📈 **АНАЛИТИКА**\n\n"

    try:
        # Аналитика RSS
        text += "🔄 **RSS Источники**:\n"
        from jobs import RSS_SOURCES
        text += f"  📡 Всего источников: {len(RSS_SOURCES)}\n"

        # Аналитика активности
        text += f"\n🎯 **Активность**:\n"
        text += f"  💬 Комментарии: каждые 20 мин\n"
        text += f"  🗳️ Опросы: каждые 12 часов\n"
        text += f"  🔥 Вирусный контент: каждые 6 часов\n"
        text += f"  ⭐ Промо: каждые 8 часов\n"

    except Exception as e:
        log.error("Error in analytics: %s", e)
        text += "❌ Ошибка загрузки данных\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_analytics"),
         InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_main_admin_panel(query, ctx):
    """Возвращает к главной админ панели."""
    keyboard = [
        [InlineKeyboardButton("📋 Заявки", callback_data="admin_applications"),
         InlineKeyboardButton("👥 Администраторы", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("🚀 Постинг", callback_data="admin_posting")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
         InlineKeyboardButton("📈 Аналитика", callback_data="admin_analytics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🔧 **АДМИН ПАНЕЛЬ**\n\n"
        "Выберите раздел для управления:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_application_action(query, ctx):
    """Обработка действий с заявками."""
    action_data = query.data.split("_")
    if len(action_data) >= 3:
        action = action_data[1]  # view, take, reject, note
        app_id = action_data[2]

        if action == "view":
            await show_application_details(query, ctx, app_id)
        elif action == "take":
            await take_application(query, ctx, app_id)
        elif action == "reject":
            await reject_application(query, ctx, app_id)
        elif action == "note":
            await add_note_to_application(query, ctx, app_id)


async def take_application(query, ctx, app_id):
    """Берет заявку в работу."""
    try:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        if not session_maker:
            await query.answer("❌ База данных недоступна", show_alert=True)
            return

        admin_username = query.from_user.username or f"ID:{query.from_user.id}"

        from sqlalchemy import text
        async with session_maker() as session:
            # Обновляем статус заявки
            await session.execute(text("""
                UPDATE applications 
                SET status = 'processing', assigned_admin = :admin
                WHERE id = :app_id
            """), {"admin": admin_username, "app_id": app_id})
            await session.commit()

        await query.answer("✅ Заявка взята в работу", show_alert=True)
        await show_application_details(query, ctx, app_id)

    except Exception as e:
        log.error("Error taking application: %s", e)
        await query.answer("❌ Ошибка обновления заявки", show_alert=True)


async def reject_application(query, ctx, app_id):
    """Отклоняет заявку."""
    try:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        if not session_maker:
            await query.answer("❌ База данных недоступна", show_alert=True)
            return

        from sqlalchemy import text
        async with session_maker() as session:
            # Обновляем статус заявки
            await session.execute(text("""
                UPDATE applications 
                SET status = 'rejected'
                WHERE id = :app_id
            """), {"app_id": app_id})
            await session.commit()

        await query.answer("❌ Заявка отклонена", show_alert=True)
        await show_application_details(query, ctx, app_id)

    except Exception as e:
        log.error("Error rejecting application: %s", e)
        await query.answer("❌ Ошибка обновления заявки", show_alert=True)


async def add_note_to_application(query, ctx, app_id):
    """Добавляет заметку к заявке."""
    text = "📝 **ДОБАВЛЕНИЕ ЗАМЕТКИ**\n\n"
    text += f"Заявка #{app_id}\n\n"
    text += "Отправьте текст заметки следующим сообщением."

    keyboard = [[InlineKeyboardButton(
        "🔙 К заявке", callback_data=f"app_view_{app_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # Устанавливаем состояние ожидания заметки
    ctx.user_data["awaiting_note_for_app"] = app_id


async def handle_user_action(query, ctx):
    """Обработка действий с пользователями."""
    action_data = query.data.split("_")
    if len(action_data) >= 3:
        action = action_data[1]  # add, remove
        if action == "add":
            await start_add_admin_process(query, ctx)
        elif action == "remove":
            user_id = int(action_data[2])
            await remove_admin(query, ctx, user_id)


async def show_application_details(query, ctx, app_id):
    """Показывает детали заявки."""
    try:
        session_maker = ctx.bot_data.get("db_sessionmaker")
        if not session_maker:
            await query.edit_message_text("❌ База данных недоступна")
            return

        from sqlalchemy import text
        async with session_maker() as session:
            result = await session.execute(text("""
                SELECT * FROM applications WHERE id = :app_id
            """), {"app_id": app_id})
            app = result.fetchone()

        if not app:
            await query.edit_message_text("❌ Заявка не найдена")
            return

        status_emoji = {"new": "🆕", "processing": "🔄",
                        "completed": "✅", "rejected": "❌"}.get(app[6], "❓")

        text = f"📋 **ЗАЯВКА #{app[0]}** {status_emoji}\n\n"
        text += f"👤 **Имя**: {app[2]}\n"
        text += f"📞 **Телефон**: {app[3]}\n"
        text += f"⚠️ **Проблемы**: {app[4]}\n"
        text += f"📝 **Описание**: {app[5]}\n"
        text += f"📅 **Дата**: {app[7].strftime('%d.%m.%Y %H:%M')}\n"
        if app[8]:
            text += f"👨‍💼 **Ответственный**: {app[8]}\n"
        if app[9]:
            text += f"📋 **Заметки**: {app[9]}\n"

        keyboard = [
            [InlineKeyboardButton("✅ Взять в работу", callback_data=f"app_take_{app[0]}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app[0]}")],
            [InlineKeyboardButton("📝 Добавить заметку", callback_data=f"app_note_{app[0]}"),
             InlineKeyboardButton("📞 Связаться", url=f"tel:{app[3]}")],
            [InlineKeyboardButton(
                "🔙 К заявкам", callback_data="admin_applications")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        log.error("Error showing application details: %s", e)
        await query.edit_message_text("❌ Ошибка загрузки заявки")


async def start_add_admin_process(query, ctx):
    """Начинает процесс добавления админа."""
    text = "➕ **ДОБАВЛЕНИЕ АДМИНИСТРАТОРА**\n\n"
    text += "Отправьте ID пользователя или перешлите сообщение от него.\n\n"
    text += "ℹ️ ID можно узнать через @userinfobot"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # Устанавливаем состояние ожидания ID
    ctx.user_data["awaiting_admin_id"] = True


async def remove_admin(query, ctx, user_id):
    """Удаляет администратора."""
    if user_id == ADMIN_CHAT_ID:
        await query.answer("❌ Нельзя удалить главного админа", show_alert=True)
        return

    if user_id in ADMIN_USERS:
        ADMIN_USERS.remove(user_id)
        if user_id in ADMIN_PERMISSIONS:
            del ADMIN_PERMISSIONS[user_id]

        await query.answer("✅ Администратор удален", show_alert=True)
        await show_admin_users(query, ctx)
    else:
        await query.answer("❌ Пользователь не является админом", show_alert=True)


async def cmd_add_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления админа по ID."""
    user_id = update.effective_user.id
    if user_id != ADMIN_CHAT_ID:  # Только главный админ может добавлять
        await update.message.reply_text("⛔️ Только главный администратор может добавлять новых админов")
        return

    if not ctx.args:
        await update.message.reply_text("Использование: /add_admin <user_id> [permissions]\n\nПример: /add_admin 123456789 applications,stats")
        return

    try:
        new_admin_id = int(ctx.args[0])
        permissions = ctx.args[1].split(",") if len(
            ctx.args) > 1 else ["applications", "stats"]

        ADMIN_USERS.add(new_admin_id)
        ADMIN_PERMISSIONS[new_admin_id] = permissions

        await update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен как администратор\n"
                                        f"🔑 Права доступа: {', '.join(permissions)}")

        # Уведомляем нового админа
        try:
            await ctx.bot.send_message(
                chat_id=new_admin_id,
                text="🎉 Вы назначены администратором бота!\n\n"
                     "Используйте команду /admin для доступа к панели управления."
            )
        except Exception as e:
            log.warning("Failed to notify new admin: %s", e)

    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")
    except Exception as e:
        log.error("Error adding admin: %s", e)
        await update.message.reply_text("❌ Ошибка при добавлении администратора")

# ========================= Main ==============================


async def main_async():
    # --- ДИАГНОСТИЧЕСКАЯ ИНФОРМАЦИЯ ---
    log.info("🚀 BOT STARTING - Version 3.1")
    log.info("📊 Environment check:")
    log.info("  - BOT_TOKEN: %s", "SET" if TOKEN else "NOT_SET")
    log.info("  - ADMIN_CHAT_ID: %s", ADMIN_CHAT_ID)
    log.info("  - OPENROUTER_API_KEY: %s",
             "SET" if OPENROUTER_API_KEY else "NOT_SET")
    log.info("  - WEBHOOK_URL: %s",
             f"https://{PUBLIC_HOST}/{TOKEN}" if PUBLIC_HOST and TOKEN else "NOT_SET")
    log.info("  - PORT: %s", PORT)
    log.info("  - DATABASE_URL: %s",
             "SET" if os.getenv("DATABASE_URL") else "NOT_SET")

    # --- Quick diagnostics of critical env-vars (redacted where needed) ---
    masked_hash = (API_HASH[:5] + "…" + API_HASH[-2:]
                   ) if API_HASH else "None"
    log.info(
        "Startup config ⇒ API_ID=%s, API_HASH=%s (len=%d), TARGET_CHANNEL_ID=%s, TARGET_CHANNEL_USERNAME=%s",
        API_ID,
        masked_hash,
        len(API_HASH or ""),
        TARGET_CHANNEL_ID,
        TARGET_CHANNEL_USERNAME,
    )

    if not all([TOKEN, ADMIN_CHAT_ID, PUBLIC_HOST]):
        log.critical(
            "Missing env vars: YOUR_BOT_TOKEN / ADMIN_CHAT_ID / MY_RAILWAY_PUBLIC_URL")
        return

    try:

        application = Application.builder().token(TOKEN).updater(None).build()

        # === Init database ===
        log.info("🗄️ Initializing database...")
        log.info("🗄️ Initializing database...")
        await init_models()
        log.info("✅ Database initialized successfully")
        log.info("✅ Database initialized successfully")
        application.bot_data["db_sessionmaker"] = async_sessionmaker

        # === Telethon client ===
        log.info("🔗 Setting up Telethon client...")
        telethon_client = None
        if API_ID and API_HASH:
            session_str = os.getenv("TELETHON_USER_SESSION")
            log.info("TELETHON_USER_SESSION status: %s",
                     "SET" if session_str and session_str.strip() else "EMPTY/NOT_SET")

            if session_str and session_str.strip():
                try:
                    # Используем пользовательскую сессию для чтения каналов
                    log.info("Creating Telethon client with user session...")
                    telethon_client = TelegramClient(
                        StringSession(session_str), API_ID, API_HASH)

                    # Важно: подключаемся без интерактивной аутентификации
                    await telethon_client.connect()
                    if not await telethon_client.is_user_authorized():
                        log.error(
                            "TELETHON_USER_SESSION is invalid - user not authorized")
                        await telethon_client.disconnect()
                        telethon_client = None
                    else:
                        me = await telethon_client.get_me()
                        log.info("✅ Telethon client started with user session: %s",
                                 me.username or f"ID:{me.id}")
                        application.bot_data["telethon"] = telethon_client
                except Exception as e:
                    log.error(
                        "Telethon session error: %s. External parsing disabled.", e)
                    if telethon_client:
                        try:
                            await telethon_client.disconnect()
                        except:
                            pass
                    telethon_client = None
            else:
                # Без пользовательской сессии внешние каналы недоступны
                log.warning(
                    "⚠️ TELETHON_USER_SESSION not set - external channel parsing disabled")
                log.warning(
                    "To enable: generate session with session_gen.py and set TELETHON_USER_SESSION variable")
                telethon_client = None
        else:
            log.warning("⚠️ API_ID or API_HASH missing - Telethon disabled")

        application.add_handler(CommandHandler("start", cmd_start))
        application.add_handler(CommandHandler("setup_menu", cmd_setup_menu))
        application.add_handler(CommandHandler(
            ["postai", "post"], cmd_post_ai))
        application.add_handler(CommandHandler("admin", cmd_admin))
        application.add_handler(CommandHandler("add_admin", cmd_add_admin))
        application.add_handler(CommandHandler(
            "set_channel", cmd_set_channel, filters.ChatType.CHANNEL))
        application.add_handler(CommandHandler(
            "set_channel_id", cmd_set_channel_id, filters.ChatType.PRIVATE))
        application.add_handler(CallbackQueryHandler(admin_callback_handler))
        application.add_handler(MessageHandler(
            filters.ChatType.PRIVATE & filters.FORWARDED, handle_forward))
        application.add_handler(MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, ai_private_chat))
        application.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND, debug))

        # aiohttp app
        app = web.Application()
        app["bot"] = application.bot
        app["application"] = application
        app.router.add_post(f"/{TOKEN}", handle_telegram)
        app.router.add_route("*", "/submit", handle_submit)

        # === Configure OpenRouter ===
        if OPENROUTER_API_KEY:
            openai.api_key = OPENROUTER_API_KEY
            openai.api_base = "https://openrouter.ai/api/v1"

        # === Resolve channel ID (once) ===
        target_channel_id = None
        if TARGET_CHANNEL_ID:
            target_channel_id = int(TARGET_CHANNEL_ID)
        else:
            try:
                chat = await application.bot.get_chat(TARGET_CHANNEL_USERNAME)
                target_channel_id = chat.id
                log.info("Resolved @%s -> %s",
                         TARGET_CHANNEL_USERNAME, target_channel_id)
            except Exception as e:
                log.error("Cannot resolve channel username %s: %s",
                          TARGET_CHANNEL_USERNAME, e)

        application.bot_data["TARGET_CHANNEL_ID"] = target_channel_id

        # Set webhook & default menu button with error handling
        try:
            await setup_menu(application.bot)
            log.info("Menu button set successfully")
        except Exception as e:
            log.error("Failed to set menu button: %s", e)

        try:
            # Проверяем текущий webhook перед установкой
            webhook_info = await application.bot.get_webhook_info()
            current_url = f"https://{PUBLIC_HOST}/{TOKEN}"

            if webhook_info.url != current_url:
                await application.bot.set_webhook(url=current_url)
                log.info("Webhook set to https://%s/%s", PUBLIC_HOST, TOKEN)
            else:
                log.info("Webhook already set correctly: %s", webhook_info.url)
        except Exception as e:
            log.error("Failed to set webhook: %s", e)
            # Продолжаем работу даже если webhook не установился
            log.warning(
                "Bot will continue without webhook - polling mode disabled")

        # === CRITICAL: Start HTTP server IMMEDIATELY ===
        log.info("🚀 Starting HTTP server setup...")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        log.info("✅ HTTP server running on port %s - webhook ready!", PORT)

        # === Schedule autoposting job ===
        if target_channel_id:
            application.job_queue.run_repeating(
                ai_post_job,
                interval=timedelta(hours=POST_INTERVAL_HOURS),
                first=timedelta(minutes=1),
                name="ai_posting",
            )
            log.info("Autoposting job scheduled every %s hours",
                     POST_INTERVAL_HOURS)

        # === Schedule analytics jobs ===
        if telethon_client:
            log.info("Scheduling Telethon-based external channel jobs...")
            application.job_queue.run_repeating(
                collect_subscribers_job,
                interval=timedelta(days=1),
                first=timedelta(minutes=5),
                name="collect_subscribers",
            )
            log.info("✓ collect_subscribers_job scheduled (daily)")

            application.job_queue.run_repeating(
                scan_external_channels_job,
                interval=timedelta(minutes=10),
                first=timedelta(seconds=30),
                name="scan_external_channels",
            )
            log.info("✓ scan_external_channels_job scheduled (every 10 min)")
        else:
            log.warning("⚠️ Telethon unavailable - using RSS alternative")

        # === RSS парсинг как альтернатива (работает всегда) ===
        log.info("Scheduling RSS-based content parsing...")
        application.job_queue.run_repeating(
            scan_rss_sources_job,
            interval=timedelta(minutes=15),
            first=timedelta(seconds=30),
            name="scan_rss_sources",
        )
        log.info("✓ scan_rss_sources_job scheduled (every 15 min)")

        # === Комментирование для максимальной активности ===
        if target_channel_id:
            application.job_queue.run_repeating(
                comment_on_post_job,
                interval=timedelta(minutes=20),  # Комментируем каждые 20 минут
                # Первый комментарий через 3 минуты
                first=timedelta(minutes=3),
                name="comment_posts",
            )
            log.info("✓ comment_on_post_job scheduled (every 20 min)")

            # Дополнительный быстрый RSS парсинг для максимальной активности
            application.job_queue.run_repeating(
                scan_rss_sources_job,
                interval=timedelta(minutes=8),  # Ускоренный парсинг
                first=timedelta(minutes=1),
                name="scan_rss_fast",
            )
            log.info("✓ Fast RSS scanning enabled (every 8 min)")

        # === RSS статистика ===
        application.job_queue.run_repeating(
            get_rss_stats_job,
            interval=timedelta(minutes=60),  # Статистика каждый час
            first=timedelta(minutes=10),     # Первая статистика через 10 минут
            name="rss_statistics",
        )
        log.info("✓ RSS statistics job scheduled (every 60 min)")

        # === Система опросов для удержания пользователей ===
        if target_channel_id:
            application.job_queue.run_repeating(
                create_poll_job,
                interval=timedelta(hours=12),   # Опросы 2 раза в день
                first=timedelta(minutes=15),    # Первый опрос через 15 минут
                name="channel_polls",
            )
            log.info("✓ Poll creation job scheduled (every 12 hours)")

            # Активности для удержания подписчиков
            application.job_queue.run_repeating(
                channel_activity_job,
                interval=timedelta(minutes=45),  # Активности каждые 45 минут
                # Первая активность через 7 минут
                first=timedelta(minutes=7),
                name="channel_activities",
            )
            log.info("✓ Channel activity job scheduled (every 45 min)")

        # === Автоматическое привлечение новых подписчиков ===
        if target_channel_id:
            # Вирусный контент для привлечения аудитории
            application.job_queue.run_repeating(
                auto_subscriber_attraction_job,
                # Вирусный контент 4 раза в день
                interval=timedelta(hours=6),
                # Первый вирусный пост через 25 минут
                first=timedelta(minutes=25),
                name="viral_content",
            )
            log.info("✓ Viral content job scheduled (every 6 hours)")

            # Кросс-промо активности
            application.job_queue.run_repeating(
                cross_promotion_job,
                interval=timedelta(hours=8),     # Промо контент 3 раза в день
                first=timedelta(minutes=35),     # Первое промо через 35 минут
                name="cross_promotion",
            )
            log.info("✓ Cross promotion job scheduled (every 8 hours)")

        async with application:
            await application.start()
            log.info("Bot & HTTP server running on port %s", PORT)
            # Notify admin that bot started and autoposting scheduled
            try:
                status_msg = f"🤖 Бот запущен в МАКСИМАЛЬНОЙ АКТИВНОСТИ!\n📊 Постинг каждый {POST_INTERVAL_HOURS}ч (60% парсинг / 40% AI)\n💬 Комментирование каждые 20 мин\n🚀 Быстрый RSS-парсинг каждые 8 мин\n📈 RSS статистика каждый час\n🗳️ Опросы каждые 12 часов\n🎯 Активности каждые 45 мин\n🔥 Вирусный контент каждые 6 часов\n⭐ Промо контент каждые 8 часов\n🚫 Картинки убраны - только текст\n🔄 15 RSS источников активно\n✅ Умная коммуникация с клиентами"
                if telethon_client:
                    status_msg += f"\n✅ Внешние каналы: {', '.join(EXTERNAL_CHANNELS) if EXTERNAL_CHANNELS else 'не настроены'}"
                else:
                    status_msg += "\n⚠️ Парсинг внешних каналов отключен (нет TELETHON_USER_SESSION)\n✅ RSS-парсинг активен (15 источников)"
                await application.bot.send_message(chat_id=ADMIN_CHAT_ID, text=status_msg)
            except Exception as e:
                log.warning("Cannot notify admin: %s", e)
            # run forever
            await asyncio.Event().wait()
    except Exception as e:
        log.error("Main async function failed: %s", e)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
