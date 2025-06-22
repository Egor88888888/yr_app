from __future__ import annotations
# avoid circular? maybe import inside function.

"""Background jobs for analytics and external channel parsing."""

import os
from datetime import datetime, timedelta
from typing import List
import logging

from telethon import functions, types
from telethon.client import TelegramClient
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Subscriber, ExternalPost

# Environment thresholds
VIEWS_THRESHOLD = int(os.getenv("VIEWS_THRESHOLD", 500))
REACTIONS_THRESHOLD = int(os.getenv("REACTIONS_THRESHOLD", 10))
EXTERNAL_CHANNELS: List[str] = [c.strip() for c in os.getenv(
    "EXTERNAL_CHANNELS", "").split(',') if c.strip()]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _total_reactions(msg: types.Message) -> int:
    if msg.reactions and isinstance(msg.reactions, types.MessageReactions):
        return sum(r.count for r in msg.reactions.results)
    return 0


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

        popular = [m for m in messages if (
            m.views or 0) >= VIEWS_THRESHOLD or _total_reactions(m) >= REACTIONS_THRESHOLD]
        saved = 0
        async with session_maker() as session:
            for m in popular:
                exists = await session.scalar(select(ExternalPost.id).where(
                    ExternalPost.channel == channel,
                    ExternalPost.message_id == m.id
                ))
                if exists:
                    continue
                post = ExternalPost(
                    channel=channel,
                    message_id=m.id,
                    date=m.date or datetime.utcnow(),
                    views=m.views,
                    reactions=_total_reactions(m),
                    text=m.message,
                )
                session.add(post)
                saved += 1
            await session.commit()
        if saved:
            log.info("scan_external: saved %s new posts from %s", saved, channel)
        else:
            log.info("scan_external: no new popular posts from %s", channel)


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
