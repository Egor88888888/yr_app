from __future__ import annotations

"""Background jobs for analytics and external channel parsing."""

import os
from datetime import datetime, timedelta
from typing import List

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
        return
    telethon_client: TelegramClient = ctx.bot_data.get("telethon")
    session_maker: async_sessionmaker = ctx.bot_data["db_sessionmaker"]
    if not telethon_client:
        return

    for channel in EXTERNAL_CHANNELS:
        try:
            messages = await telethon_client.get_messages(channel, limit=50)
        except Exception as e:
            ctx.job.logger.warning("failed to fetch %s: %s", channel, e)
            continue

        popular = [m for m in messages if (
            m.views or 0) >= VIEWS_THRESHOLD or _total_reactions(m) >= REACTIONS_THRESHOLD]
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
            await session.commit()
