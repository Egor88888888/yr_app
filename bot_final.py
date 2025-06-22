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
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import timedelta
import openai
from typing import Optional
from telegram.constants import ChatAction
import aiohttp
import io
# === Analytics & External parsing ===
from db import init_models, async_sessionmaker
from jobs import collect_subscribers_job, scan_external_channels_job, post_from_external_job, EXTERNAL_CHANNELS
from telethon import TelegramClient
from telethon.sessions import StringSession
from collections import deque

########################### CONFIG ###########################
TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # string
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

POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", 4))
# === Telethon & analytics config ===
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
##############################################################

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

MEDIA_POOL = [
    # Photos
    {"url": "https://images.pexels.com/photos/701775/pexels-photo-701775.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/806137/pexels-photo-806137.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/5668840/pexels-photo-5668840.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/4425839/pexels-photo-4425839.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/235569/pexels-photo-235569.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/5682738/pexels-photo-5682738.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/672630/pexels-photo-672630.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    {"url": "https://images.pexels.com/photos/3768893/pexels-photo-3768893.jpeg?auto=compress&cs=tinysrgb&w=800", "kind": "photo"},
    # Short thematic video (dashcam)
    {"url": "https://filesamples.com/samples/video/mp4/sample_640x360.mp4", "kind": "video"},
]

# Keep track of last 5 media URLs, module-level to avoid attribute errors
RECENT_MEDIA: deque[str] = deque(maxlen=5)

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


def _media_url(item):
    return item["url"] + f"&rand={random.randint(1,999999)}" if "?" in item["url"] else item["url"] + f"?rand={random.randint(1,999999)}"

# ===================== Telegram handlers =====================


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Нажмите кнопку \"📝 Подать заявку\" рядом со строкой ввода⬇️")


async def debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    log.debug("Update: %s", update)

# ====================== HTTP handlers ========================


async def handle_submit(request: web.Request) -> web.Response:
    """Receive data from mini-app, notify admin, answer WebAppQuery."""
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    data = await request.json()
    query_id = data.get("queryId")
    payload = data.get("payload", {})
    log.info("/submit payload=%s", payload)

    # Notify admin
    try:
        problems = ", ".join(payload.get("problems", []))
        name = payload.get("name", "-")
        phone = payload.get("phone", "-")
        desc = payload.get("description", "-")
        text = f"🔔 Заявка\n{name}\n{phone}\n{problems}\n{desc}"
        await request.app["bot"].send_message(chat_id=ADMIN_CHAT_ID, text=text)
    except Exception as e:
        log.error("Admin send failed: %s", e)

    # Close mini-app
    try:
        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Заявка принята",
            input_message_content=InputTextMessageContent(
                "✅ Спасибо! Заявка получена."),
        )
        await request.app["bot"].answer_web_app_query(query_id, result)
    except Exception as e:
        log.error("answerWebAppQuery failed: %s", e)

    return web.json_response({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


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
        fact = random.choice(FACTS_OSAGO_OSGOP)
        user_prompt = f"Расскажи аудитории один факт: {fact}. Сохрани цифры и ссылку на закон (коротко). Объясни, чем это полезно пострадавшим."

    messages = [
        {"role": "system", "content": site_brief},
        {"role": "user", "content": user_prompt},
    ]
    text = await _ai_complete(messages, temperature=0.8, max_tokens=600)
    if text:
        text = await humanize(text)
    return text


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
    # show typing
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
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
        fallback = "Спасибо за вопрос! Наш специалист скоро свяжется с вами.\n\nНажмите кнопку \"Подать заявку\" — и наш специалист свяжется с вами"
        await update.message.reply_text(fallback)
        return

    # First humanize, then guarantee CTA line
    answer = await humanize(answer)
    cta = "Нажмите кнопку \"Подать заявку\" — и наш специалист свяжется с вами"
    if cta not in answer:
        answer = f"{answer}\n\n{cta}"
    await update.message.reply_text(answer)


async def ai_post_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Periodic job: post AI-generated text to target channel."""
    log.info("[ai_post_job] tick")
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        log.warning(
            "[ai_post_job] TARGET_CHANNEL_ID not resolved; skip posting")
        return

    text = await generate_ai_post()
    if not text:
        log.warning("[ai_post_job] generate_ai_post returned None")
        return

    bot_username = ctx.bot.username or ""  # safe fallback
    startapp_link = f"https://t.me/{bot_username}?startapp"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Подать заявку", url=startapp_link)],
        [InlineKeyboardButton("💬 Получить помощь онлайн",
                              url=f"https://t.me/{bot_username}?start=channel")]
    ])
    ok = await send_media(ctx.bot, channel_id, text, markup)
    if ok:
        log.info("[ai_post_job] Post sent to channel %s", channel_id)
    else:
        log.warning("[ai_post_job] Failed to send media; fallback posted")

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
    startapp_link = f"https://t.me/{bot_username}?startapp"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Подать заявку", url=startapp_link)],
        [InlineKeyboardButton("💬 Получить помощь онлайн",
                              url=f"https://t.me/{bot_username}?start=channel")]
    ])
    await send_media(ctx.bot, channel_id, text, markup)
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


async def send_media(bot, chat_id: int, caption: str, reply_markup):
    """Send photo or video with fallback to text-only."""
    # Telegram limits: photo caption 1024 chars, video caption 1024 chars
    if len(caption) > 1000:
        caption = caption[:997] + "..."
        log.warning("Caption truncated to %d chars", len(caption))

    tried_urls: set[str] = set(RECENT_MEDIA)
    max_attempts = min(5, len(MEDIA_POOL))
    for _ in range(max_attempts):
        # pick media that hasn't been tried yet to avoid repeat attempts
        media_candidates = [
            m for m in MEDIA_POOL if m["url"] not in tried_urls]
        if not media_candidates:
            break
        media = random.choice(media_candidates)
        tried_urls.add(media["url"])

        data = await fetch_bytes(_media_url(media))
        if not data:
            continue  # try another media file

        file_name = "media.jpg" if media["kind"] == "photo" else "media.mp4"
        input_file = InputFile(io.BytesIO(data), filename=file_name)
        try:
            if media["kind"] == "photo":
                await bot.send_photo(chat_id=chat_id, photo=input_file, caption=caption, reply_markup=reply_markup)
            else:
                await bot.send_video(chat_id=chat_id, video=input_file, caption=caption, reply_markup=reply_markup)
            # success — запоминаем url
            RECENT_MEDIA.append(media["url"])
            return True
        except Exception as e:
            log.warning("send_%s failed: %s", media["kind"], e)
    # fallback
    await bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)
    return False

# ========================= Main ==============================


async def main_async():
    # --- Quick diagnostics of critical env-vars (redacted where needed) ---
    masked_hash = (API_HASH[:5] + "…" + API_HASH[-2:]) if API_HASH else "None"
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

    application = Application.builder().token(TOKEN).updater(None).build()

    # === Init database ===
    await init_models()
    application.bot_data["db_sessionmaker"] = async_sessionmaker

    # === Telethon client ===
    telethon_client = None
    if API_ID and API_HASH:
        session_str = os.getenv("TELETHON_USER_SESSION")
        try:
            if session_str and session_str.strip():
                # Используем пользовательскую сессию для чтения каналов
                telethon_client = TelegramClient(
                    StringSession(session_str), API_ID, API_HASH)
                await telethon_client.start()
                me = await telethon_client.get_me()
                log.info("Telethon client started with user session %s",
                         me.username or me.id)
                application.bot_data["telethon"] = telethon_client
            else:
                # Без пользовательской сессии внешние каналы недоступны
                log.warning(
                    "TELETHON_USER_SESSION not set - external channel parsing disabled")
                log.warning(
                    "To enable: generate session with session_gen.py and set TELETHON_USER_SESSION variable")
                telethon_client = None
        except Exception as e:
            log.error(
                "Telethon init failed: %s. Analytics & external posting disabled.", e)
            telethon_client = None

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler(["postai", "post"], cmd_post_ai))
    application.add_handler(CommandHandler(
        "set_channel", cmd_set_channel, filters.ChatType.CHANNEL))
    application.add_handler(CommandHandler(
        "set_channel_id", cmd_set_channel_id, filters.ChatType.PRIVATE))
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

    # Set webhook & default menu button
    await setup_menu(application.bot)
    await application.bot.set_webhook(url=f"https://{PUBLIC_HOST}/{TOKEN}")
    log.info("Webhook set to https://%s/%s", PUBLIC_HOST, TOKEN)

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
        log.info("Scheduling external channel jobs...")
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

        application.job_queue.run_repeating(
            post_from_external_job,
            interval=timedelta(minutes=10),
            first=timedelta(minutes=1),
            name="post_external_content",
        )
        log.info("✓ post_external_content_job scheduled (every 10 min)")
    else:
        log.warning(
            "❌ External jobs NOT scheduled - Telethon client unavailable")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    async with application:
        await application.start()
        log.info("Bot & HTTP server running on port %s", PORT)
        # Notify admin that bot started and autoposting scheduled
        try:
            status_msg = f"🤖 Бот запущен. AI-постинг каждые {POST_INTERVAL_HOURS}ч."
            if telethon_client:
                status_msg += f"\n✅ Внешние каналы: {', '.join(EXTERNAL_CHANNELS) if EXTERNAL_CHANNELS else 'не настроены'}"
            else:
                status_msg += "\n⚠️ Парсинг внешних каналов отключен (нет TELETHON_USER_SESSION)"
            await application.bot.send_message(chat_id=ADMIN_CHAT_ID, text=status_msg)
        except Exception as e:
            log.warning("Cannot notify admin: %s", e)
        # run forever
        await asyncio.Event().wait()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
