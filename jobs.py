from __future__ import annotations
# avoid circular? maybe import inside function.

"""Background jobs for analytics and external channel parsing."""

import os
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re
import hashlib

from telethon import functions, types
from telethon.client import TelegramClient
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Subscriber, ExternalPost

# Environment thresholds
VIEWS_THRESHOLD = int(os.getenv("VIEWS_THRESHOLD", 300))  # Снизил порог
REACTIONS_THRESHOLD = int(os.getenv("REACTIONS_THRESHOLD", 5))  # Снизил порог
EXTERNAL_CHANNELS: List[str] = [c.strip() for c in os.getenv(
    "EXTERNAL_CHANNELS", "").split(',') if c.strip()]

# RSS источники для альтернативного парсинга
RSS_SOURCES = [
    {
        "name": "banki_ru_news",
        "url": "https://www.banki.ru/xml/news.rss",
        "category": "banking"
    },
    {
        "name": "rbc_business",
        "url": "https://rssexport.rbc.ru/rbcnews/news/20/full.rss",
        "category": "business"
    },
    {
        "name": "kommersant_auto",
        "url": "https://www.kommersant.ru/RSS/section-auto.xml",
        "category": "auto"
    },
    {
        "name": "garant_news",
        "url": "https://www.garant.ru/rss/news.xml",
        "category": "legal"
    }
]

# Дополнительные источники контента
NEWS_KEYWORDS = [
    "страхование", "страховая", "выплата", "ущерб", "ДТП", "ОСАГО", "КАСКО",
    "страховщик", "возмещение", "компенсация", "полис", "франшиза",
    "автострахование", "медстрахование", "страхование жизни", "РСА",
    "страхователь", "выплаты по ОСАГО", "суд", "возмещение ущерба"
]

EXCLUDED_KEYWORDS = [
    "реклама", "продаю", "купить", "скидка", "акция", "промокод",
    "партнерский", "спонсор", "реклама", "bitcoin", "криптовалюта"
]

# Кэш обработанных новостей (по хэшу заголовка)
PROCESSED_NEWS = set()

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _total_reactions(msg: types.Message) -> int:
    if msg.reactions and isinstance(msg.reactions, types.MessageReactions):
        return sum(r.count for r in msg.reactions.results)
    return 0


def _is_relevant_content(text: str) -> bool:
    """Проверяет релевантность контента для страхового канала."""
    if not text:
        return False

    text_lower = text.lower()

    # Исключаем рекламу
    if any(keyword in text_lower for keyword in EXCLUDED_KEYWORDS):
        return False

    # Проверяем наличие ключевых слов
    relevant_score = sum(
        1 for keyword in NEWS_KEYWORDS if keyword in text_lower)

    # Контент релевантен если есть минимум 1 ключевое слово
    return relevant_score >= 1


def _extract_key_facts(text: str) -> str:
    """Извлекает ключевые факты из текста для последующей обработки AI."""
    if not text:
        return ""

    # Базовая очистка от лишнего
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Убираем ссылки и хэштеги в конце
    clean_lines = []
    for line in lines:
        if line.startswith(('http', '@', '#')) or 'подписывайтесь' in line.lower():
            break
        clean_lines.append(line)

    return '\n'.join(clean_lines[:5])  # Первые 5 строк


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

async def collect_subscribers_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Upsert subscribers of target channel once per day."""
    telethon_client: TelegramClient = ctx.bot_data.get("telethon")
    session_maker: async_sessionmaker = ctx.bot_data["db_sessionmaker"]
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not telethon_client or not channel_id:
        return

    async for participant in telethon_client.iter_participants(channel_id):
        async with session_maker() as session:
            await session.merge(Subscriber(
                id=participant.id,
                username=participant.username,
                first_name=participant.first_name,
                last_name=participant.last_name,
                is_bot=participant.bot or False,
                last_seen=datetime.utcnow(),
            ))
            await session.commit()


async def scan_external_channels_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Fetch recent posts from external channels and store popular ones."""
    if not EXTERNAL_CHANNELS:
        log.warning(
            "scan_external: EXTERNAL_CHANNELS is empty; set env var EXTERNAL_CHANNELS=vc_ru,rbc_news,…")
        return
    telethon_client: TelegramClient = ctx.bot_data.get("telethon")
    session_maker: async_sessionmaker = ctx.bot_data["db_sessionmaker"]
    if not telethon_client:
        return

    for channel in EXTERNAL_CHANNELS:
        log.info("scan_external: fetching %s", channel)
        try:
            messages = await telethon_client.get_messages(channel, limit=50)
        except Exception as e:
            log.warning("failed to fetch %s: %s", channel, e)
            continue

        # Фильтруем по популярности И релевантности
        popular = [m for m in messages if (
            (m.views or 0) >= VIEWS_THRESHOLD or _total_reactions(
                m) >= REACTIONS_THRESHOLD
        ) and _is_relevant_content(m.message)]

        log.info("scan_external: found %d popular + relevant messages from %s",
                 len(popular), channel)
        saved = 0
        async with session_maker() as session:
            for m in popular:
                exists = await session.scalar(select(ExternalPost.id).where(
                    ExternalPost.channel == channel,
                    ExternalPost.message_id == m.id
                ))
                if exists:
                    continue
                # Сохраняем очищенный текст для лучшей обработки AI
                clean_text = _extract_key_facts(m.message or "")
                post = ExternalPost(
                    channel=channel,
                    message_id=m.id,
                    date=m.date or datetime.utcnow(),
                    views=m.views,
                    reactions=_total_reactions(m),
                    text=clean_text,
                )
                session.add(post)
                saved += 1
            await session.commit()
        if saved:
            log.info("scan_external: saved %s new posts from %s", saved, channel)
        else:
            log.info("scan_external: no new popular posts from %s", channel)


# ---------------------------------------------------------------------------
# RSS Parsing Functions
# ---------------------------------------------------------------------------

async def fetch_rss_feed(url: str, timeout: int = 10) -> Optional[str]:
    """Получает RSS ленту по URL."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
    except Exception as e:
        log.warning("RSS fetch failed for %s: %s", url, e)
    return None


def parse_rss_items(rss_content: str) -> List[Dict[str, str]]:
    """Парсит RSS XML и возвращает список новостей."""
    items = []
    try:
        root = ET.fromstring(rss_content)

        # Поддержка разных форматов RSS
        for item in root.findall(".//item"):
            title = item.find("title")
            description = item.find("description")
            link = item.find("link")
            pub_date = item.find("pubDate")

            if title is not None and title.text:
                # Очистка HTML тегов из описания
                desc_text = ""
                if description is not None and description.text:
                    desc_text = re.sub(
                        r'<[^>]+>', '', description.text).strip()

                items.append({
                    "title": title.text.strip(),
                    "description": desc_text,
                    "link": link.text.strip() if link is not None and link.text else "",
                    "pub_date": pub_date.text.strip() if pub_date is not None and pub_date.text else ""
                })
    except Exception as e:
        log.error("RSS parsing failed: %s", e)

    return items


def get_content_hash(title: str, description: str) -> str:
    """Создает хэш контента для проверки уникальности."""
    content = f"{title}{description}".lower()
    return hashlib.md5(content.encode()).hexdigest()


async def scan_rss_sources_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Сканирует RSS источники и сохраняет релевантные новости."""
    session_maker: async_sessionmaker = ctx.bot_data["db_sessionmaker"]

    for source in RSS_SOURCES:
        log.info("scan_rss: fetching %s (%s)",
                 source["name"], source["category"])

        try:
            rss_content = await fetch_rss_feed(source["url"])
            if not rss_content:
                log.warning("scan_rss: failed to fetch %s", source["name"])
                continue

            items = parse_rss_items(rss_content)
            log.info("scan_rss: parsed %d items from %s",
                     len(items), source["name"])

            relevant_items = []
            for item in items:
                # Проверяем релевантность
                full_text = f"{item['title']} {item['description']}"
                if _is_relevant_content(full_text):
                    # Проверяем уникальность
                    content_hash = get_content_hash(
                        item['title'], item['description'])
                    if content_hash not in PROCESSED_NEWS:
                        relevant_items.append((item, content_hash))
                        PROCESSED_NEWS.add(content_hash)

            log.info("scan_rss: found %d relevant + unique items from %s",
                     len(relevant_items), source["name"])

            # Сохраняем в базу
            saved = 0
            async with session_maker() as session:
                for item, content_hash in relevant_items:
                    # Используем хэш как message_id для RSS источников
                    exists = await session.scalar(select(ExternalPost.id).where(
                        ExternalPost.channel == source["name"],
                        # Первые 8 символов хэша как int
                        ExternalPost.message_id == int(content_hash[:8], 16)
                    ))
                    if exists:
                        continue

                    # Готовим сжатый текст для AI
                    clean_text = f"{item['title']}\n\n{_extract_key_facts(item['description'])}"

                    post = ExternalPost(
                        channel=source["name"],
                        message_id=int(content_hash[:8], 16),
                        date=datetime.utcnow(),
                        views=500,  # Фиксированный "рейтинг" для RSS
                        reactions=10,
                        text=clean_text,
                    )
                    session.add(post)
                    saved += 1

                await session.commit()

            if saved:
                log.info("scan_rss: saved %d new posts from %s",
                         saved, source["name"])

        except Exception as e:
            log.error("scan_rss: error processing %s: %s", source["name"], e)


# ---------------------------------------------------------------------------
# Posting job
# ---------------------------------------------------------------------------


async def post_from_external_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Pick one unsent external post, rewrite via AI, publish, mark as posted."""
    telethon_client = ctx.bot  # not used but keep signature
    session_maker: async_sessionmaker = ctx.bot_data["db_sessionmaker"]
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        return

    async with session_maker() as session:
        post: ExternalPost | None = await session.scalar(
            select(ExternalPost).where(ExternalPost.posted.is_(False)
                                       ).order_by(ExternalPost.views.desc()).limit(1)
        )
        if not post:
            log.info("post_external: no unposted items found")
            return

        # AI rewrite
        site_brief = (
            "Ты копирайтер канала 'Страховая справедливость'. Перепиши новость для нашей аудитории страховых выплат, сохраняя факты, добавь один вывод, но убери упоминания конкурентов. 400-500 символов, максимум две эмодзи."
        )
        from bot_final import _ai_complete, humanize

        messages = [
            {"role": "system", "content": site_brief},
            {"role": "user", "content": post.text or ""},
        ]
        text = await _ai_complete(messages, temperature=0.7, max_tokens=600)
        if text:
            text = await humanize(text)
        else:
            text = post.text or ""

        from bot_final import send_media
        # Reuse send_media helper
        bot = ctx.bot
        await send_media(bot, channel_id, text, reply_markup=None)
        log.info("post_external: posted message %s from %s views=%s",
                 post.message_id, post.channel, post.views)

        post.posted = True
        await session.commit()
