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

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    MetaData,
    String,
    Integer,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey,
    Text,
    JSON,
    func,
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

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env not set")

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
    tg_id: Mapped[int] = mapped_column(Integer, unique=True)
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

    user: Mapped["User"] = relationship(back_populates="applications")
    category: Mapped["Category"] = relationship(back_populates="applications")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="application")


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True)
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
