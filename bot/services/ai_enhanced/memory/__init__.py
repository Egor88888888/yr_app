"""
Memory modules - система памяти диалогов и профилирования.

- dialogue_memory: долгосрочная память диалогов с пользователями
- user_profiler: создание и обновление профилей пользователей
- session_manager: управление сессиями диалогов
"""

from .dialogue_memory import DialogueMemory
from .user_profiler import UserProfiler
from .session_manager import SessionManager

__all__ = ["DialogueMemory", "UserProfiler", "SessionManager"]
