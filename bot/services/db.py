"""Database layer – SQLAlchemy async models & session maker.

Tables:
    Category        – справочник направлений услуг
    User            – клиент Telegram / WebApp
    Application     – заявка клиента на услугу
    Admin           – администраторы / юристы с ролями
    Payment         – онлайн-оплата заявки
    Log             – системные логи (для будущего)

Usage:
    from bot.services.db import async_sessionmaker, init_db
    await init_db()  # создаёт таблицы при старте (если нет Alembic)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    MetaData,
    String,
    Integer,
    BigInteger,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey,
    Text,
    JSON,
    func,
    text,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "async_engine",
    "async_sessionmaker",
    "Base",
    "init_db",
    # models
    "Category",
    "User",
    "Application",
    "Admin",
    "Payment",
    "Log",
]

# Import Enhanced AI models to ensure they're included in metadata
try:
    from .ai_enhanced_models import (
        UserProfile, DialogueSession, DialogueMessage, MessageEmbedding,
        CategoryEmbedding, AIMetrics, UserPreference, TrainingData
    )
except ImportError:
    pass  # Models might not be available yet

logger = logging.getLogger(__name__)

# =================
# DATABASE SETUP
# =================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Default local SQLite with async driver
    DATABASE_URL = "sqlite+aiosqlite:///bot.db"
    print("🔧 Using SQLite for local development")
else:
    # Fix Railway PostgreSQL URL for async
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1)
    # Fix SQLite URLs to use async driver
    elif DATABASE_URL.startswith("sqlite:///") and "aiosqlite" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    print(f"🔗 Using production database: {DATABASE_URL[:50]}...")

# Настройка для локальной разработки
if not os.getenv("DATABASE_URL"):
    print("🔗 Using fallback local SQLite database")
    DATABASE_URL = "sqlite+aiosqlite:///bot.db"

async_engine = create_async_engine(
    DATABASE_URL, echo=False, pool_pre_ping=True)
async_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine, expire_on_commit=False
)

metadata_obj = MetaData()


class Base(DeclarativeBase):
    metadata = metadata_obj


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    applications: Mapped[list["Application"]
                         ] = relationship(back_populates="category")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    email: Mapped[Optional[str]] = mapped_column(String(120))
    preferred_contact: Mapped[str] = mapped_column(
        String(20), default="telegram")
    applications: Mapped[list["Application"]
                         ] = relationship(back_populates="user")


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    subcategory: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    contact_method: Mapped[Optional[str]] = mapped_column(String(32))
    contact_time: Mapped[Optional[str]] = mapped_column(String(32))
    files_data: Mapped[Optional[dict]] = mapped_column(JSON)
    utm_source: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), default="new")  # new/processing/completed
    price: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2))
    notes: Mapped[Optional[str]] = mapped_column(
        Text)  # 🔧 ДОБАВЛЕНО: Заметки администратора
    assigned_admin: Mapped[Optional[str]] = mapped_column(
        String(64))  # 🔧 ДОБАВЛЕНО: ID назначенного админа

    user: Mapped["User"] = relationship(back_populates="applications")
    category: Mapped["Category"] = relationship(back_populates="applications")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="application")


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    role: Mapped[str] = mapped_column(
        String(32), default="operator")  # operator / lawyer / super
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    status: Mapped[str] = mapped_column(
        String(20), default="pending")  # pending/paid/failed
    link: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(
        back_populates="payments")


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())


# -------- DB init ----------

async def init_db() -> None:
    """Create tables if they don't exist (for first run)"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # 🚨 КРИТИЧЕСКИЙ ФИКС: Telegram ID overflow INTEGER → BIGINT
        try:
            print("🔧 Checking for Telegram ID overflow fix...")

            # Проверяем тип колонки users.tg_id
            result = await conn.execute(text("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'tg_id'
                AND table_schema = 'public'
            """))

            current_type = result.scalar_one_or_none()

            if current_type == "integer":
                print("🚨 APPLYING CRITICAL FIX: Converting INTEGER → BIGINT...")

                # Фиксим users.tg_id
                await conn.execute(text("ALTER TABLE users ALTER COLUMN tg_id TYPE BIGINT;"))
                print("   ✅ users.tg_id → BIGINT")

                # Фиксим admins.tg_id (если существует)
                admin_check = await conn.execute(text("""
                    SELECT data_type FROM information_schema.columns 
                    WHERE table_name = 'admins' AND column_name = 'tg_id'
                    AND table_schema = 'public'
                """))

                if admin_check.scalar_one_or_none() == "integer":
                    await conn.execute(text("ALTER TABLE admins ALTER COLUMN tg_id TYPE BIGINT;"))
                    print("   ✅ admins.tg_id → BIGINT")

                print("🎉 TELEGRAM ID OVERFLOW FIXED! Large IDs now supported.")

            elif current_type == "bigint":
                print("✅ Telegram ID overflow already fixed (BIGINT detected)")
            else:
                print(f"⚠️  Unexpected tg_id type: {current_type}")

        except Exception as e:
            print(f"⚠️  Could not apply Telegram ID fix: {e}")
            # Не критично - продолжаем инициализацию

    # seed default categories if empty
    async with async_sessionmaker() as session:
        result = await session.execute(func.count(Category.id))
        if result.scalar_one() == 0:
            default_names = [
                "Страховые споры",
                "Семейное право",
                "Наследство",
                "Трудовые споры",
                "Жилищные вопросы",
                "Банкротство физлиц",
                "Налоговые консультации",
                "Административные штрафы",
                "Арбитраж / бизнес",
                "Защита прав потребителей",
                "Миграционное право",
                "Уголовные дела",
            ]
            session.add_all([Category(name=n) for n in default_names])
            await session.commit()
