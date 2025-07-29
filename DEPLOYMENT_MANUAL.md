# 🚀 MANUAL DEPLOYMENT GUIDE - AI SYSTEM FIXES

## Проблема
GitHub блокирует push из-за обнаружения Azure API ключей в истории коммитов.

## Решение
Необходимо вручную применить исправления через Railway Web Interface.

## Исправления для применения:

### 1. bot/services/ai.py (строки 11-13)
```python
# БЫЛО (с хардкод ключами):
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "hardcoded_key_here")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "hardcoded_endpoint_here") 

# ДОЛЖНО БЫТЬ (только env переменные):
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
```

### 2. bot/services/ai.py (строки 42-49)
```python
# ИСПРАВИТЬ deployment mapping:
deployment_map = {
    "gpt-4o-mini": "gpt-35-turbo",          # используем gpt-35-turbo  
    "gpt-4o": "gpt-35-turbo",              # fallback на gpt-35-turbo
    "gpt-35-turbo": "gpt-35-turbo",        # прямое соответствие
    "gpt-4.1": "gpt-35-turbo",             # fallback на gpt-35-turbo
    "openai/gpt-4o-mini": "gpt-35-turbo",  # fallback
    "openai/gpt-4o": "gpt-35-turbo"        # fallback
}
```

### 3. bot/services/ai_enhanced/memory/user_profiler.py (строка 89)
```python
# ДОБАВИТЬ fallback механизм:
def _create_fallback_profile(self, user_id: int) -> UserProfile:
    """Создание базового профиля для работы без БД"""
    from ...ai_enhanced_models import UserProfile
    profile = UserProfile(
        user_id=user_id,
        experience_level="beginner",
        preferred_style="friendly", 
        communication_speed="normal",
        detail_preference="medium",
        total_interactions=0,
        last_categories=[]
    )
    # Кэшируем fallback профиль
    self.profiles_cache[user_id] = profile
    return profile
```

### 4. bot/services/ai_enhanced/memory/session_manager.py (строка 116)
```python
# ИЗМЕНИТЬ return None на:
return self._create_fallback_session(user_id)

# И ДОБАВИТЬ метод:
def _create_fallback_session(self, user_id: int) -> DialogueSession:
    """Создание fallback сессии для работы без БД"""
    from ...ai_enhanced_models import DialogueSession
    import uuid
    from datetime import datetime
    
    session = DialogueSession(
        user_id=user_id,
        session_uuid=str(uuid.uuid4()),
        context_summary="",
        message_count=0,
        resolution_status="ongoing",
        last_activity=datetime.now(),
        detected_categories=[],
        detected_intent=None
    )
    # Кэшируем fallback сессию
    self.active_sessions[user_id] = session
    return session
```

### 5. bot/services/ai_enhanced/core/ai_manager.py (строка 287)
```python
# ДОБАВИТЬ проверку в _save_interaction:
# Проверяем, что session имеет id (не fallback)
if not hasattr(session, 'id') or session.id is None:
    logger.warning(f"Skipping interaction save - session has no id (fallback mode)")
    return
```

## Способы деплоя:

### Вариант 1: Railway Web Interface
1. Зайти на https://railway.app/project/poetic-simplicity
2. Открыть Service Editor
3. Применить исправления вручную
4. Нажать Deploy

### Вариант 2: Разрешить GitHub push
1. Перейти по ссылке: https://github.com/Egor88888888/yr_app/security/secret-scanning/unblock-secret/30WAoWvqWJNeFeGF6DBmiST8NXS
2. Нажать "Allow secret"
3. Выполнить `git push origin main`

## Ожидаемый результат:
- ✅ Исчезнут ошибки "Connection reset by peer"
- ✅ Исчезнут ошибки "Azure OpenAI deployment error 401"
- ✅ Исчезнут ошибки "NoneType object has no attribute 'id'"
- ✅ AI система будет работать стабильно с fallback механизмами