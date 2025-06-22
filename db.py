from __future__ import annotations

"""Async SQLAlchemy models & engine setup.
Usage:
    from db import async_sessionmaker, init_models
    await init_models()
"""

import os
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, BigInteger, Index
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

RAW_DATABASE_URL = os.getenv("DATABASE_URL")

# If var missing, fallback to in-memory SQLite to keep bot alive (analytics disabled)
if not RAW_DATABASE_URL:
    log.warning(
        "DATABASE_URL not set – analytics DB will run in-memory SQLite (volatile).")
    RAW_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Railway gives sync DSN; convert to asyncpg driver if necessary
if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

engine = create_async_engine(
    DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True)  # telegram user id
    username: Mapped[Optional[str]] = mapped_column(
        String(length=64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(
        String(length=64), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(
        String(length=64), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)


class ExternalPost(Base):
    __tablename__ = "external_posts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(length=128), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    views: Mapped[Optional[int]] = mapped_column(Integer)
    reactions: Mapped[Optional[int]] = mapped_column(Integer)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_channel_msg", "channel", "message_id", unique=True),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def init_models() -> None:
    """Create tables if they don't exist (simple metadata.create_all)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure new columns exist when code updated without migrations
        try:
            await conn.exec_driver_sql(
                "ALTER TABLE external_posts ADD COLUMN IF NOT EXISTS posted BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            # Ignore if DB not postgres or column already exists
            pass
