"""
Session Manager - управление сессиями диалогов.

Создает и управляет сессиями пользователей, определяет когда начинать новую сессию.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from ...db import async_sessionmaker, User
from ...ai_enhanced_models import DialogueSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Менеджер сессий диалогов"""

    def __init__(self):
        self.initialized = False
        self.session_timeout_hours = 24  # таймаут сессии в часах
        self.active_sessions = {}  # кэш активных сессий

    async def initialize(self):
        """Инициализация менеджера сессий"""
        try:
            logger.info("🔧 Initializing Session Manager...")
            self.initialized = True
            logger.info("✅ Session Manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Session Manager: {e}")
            self.initialized = False

    async def get_or_create_session(self, user_id: int) -> Optional[DialogueSession]:
        """Получение или создание сессии для пользователя"""
        try:
            # Проверяем активную сессию в кэше
            if user_id in self.active_sessions:
                session = self.active_sessions[user_id]
                # Проверяем, не истекла ли сессия
                if self._is_session_active(session):
                    return session
                else:
                    # Завершаем старую сессию
                    await self._end_session(session)
                    del self.active_sessions[user_id]

            async with async_sessionmaker() as db_session:
                # ИСПРАВЛЕНО: Сначала проверяем/создаем пользователя
                user_result = await db_session.execute(
                    select(User).where(User.tg_id == user_id)
                )
                user = user_result.scalar_one_or_none()

                if not user:
                    # Создаем базового пользователя если его нет
                    user = User(
                        tg_id=user_id,
                        first_name="Пользователь",
                        preferred_contact="telegram"
                    )
                    db_session.add(user)
                    await db_session.commit()
                    await db_session.refresh(user)
                    logger.info(
                        f"✅ Created missing user with tg_id: {user_id}")

                # Ищем активную сессию в БД по правильному user.id
                cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
                result = await db_session.execute(
                    select(DialogueSession)
                    .where(
                        DialogueSession.user_id == user.id,  # ИСПРАВЛЕНО: используем user.id
                        DialogueSession.resolution_status == "ongoing",
                        DialogueSession.last_activity >= cutoff_time
                    )
                    .order_by(desc(DialogueSession.last_activity))
                    .limit(1)
                )

                existing_session = result.scalar_one_or_none()

                if existing_session:
                    # Обновляем активность
                    existing_session.last_activity = datetime.now()
                    await db_session.commit()

                    # Добавляем в кэш
                    self.active_sessions[user_id] = existing_session
                    return existing_session

                # Создаем новую сессию с правильным user.id
                new_session = DialogueSession(
                    user_id=user.id,  # ИСПРАВЛЕНО: используем user.id, не tg_id
                    session_uuid=str(uuid.uuid4()),
                    context_summary="",
                    message_count=0,
                    resolution_status="ongoing"
                )

                db_session.add(new_session)
                await db_session.commit()
                await db_session.refresh(new_session)

                # Добавляем в кэш
                self.active_sessions[user_id] = new_session
                return new_session

        except Exception as e:
            logger.error(
                f"Failed to get/create session for user {user_id}: {e}")
            return None

    async def update_session_context(
        self,
        session: DialogueSession,
        category: str = None,
        intent: str = None
    ):
        """Обновление контекста сессии"""
        try:
            if category:
                session.detected_intent = intent

                if not session.detected_categories:
                    session.detected_categories = []

                if category not in session.detected_categories:
                    session.detected_categories.append(category)

            session.last_activity = datetime.now()

            # Обновляем в БД
            async with async_sessionmaker() as db_session:
                await db_session.merge(session)
                await db_session.commit()

        except Exception as e:
            logger.error(f"Failed to update session context: {e}")

    async def _end_session(self, session: DialogueSession):
        """Завершение сессии"""
        try:
            session.resolution_status = "ended"
            session.ended_at = datetime.now()

            async with async_sessionmaker() as db_session:
                await db_session.merge(session)
                await db_session.commit()

        except Exception as e:
            logger.error(f"Failed to end session: {e}")

    def _is_session_active(self, session: DialogueSession) -> bool:
        """Проверка активности сессии"""
        if session.resolution_status != "ongoing":
            return False

        cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
        return session.last_activity >= cutoff_time

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья менеджера сессий"""
        return {
            "status": "ok" if self.initialized else "not_initialized",
            "active_sessions": len(self.active_sessions),
            "session_timeout_hours": self.session_timeout_hours
        }
