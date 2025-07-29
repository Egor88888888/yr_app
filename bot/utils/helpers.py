#!/usr/bin/env python3
"""
Common utility functions used throughout the bot.
"""

import re
import html
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2"""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

def format_phone_number(phone: str) -> str:
    """Format phone number for display"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format Russian phone numbers
    if digits.startswith('7') and len(digits) == 11:
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif digits.startswith('8') and len(digits) == 11:
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    
    return phone  # Return original if can't format

def validate_email(email: str) -> bool:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check if it's a valid Russian phone number
    return (len(digits) == 11 and digits.startswith(('7', '8'))) or \
           (len(digits) == 10 and digits.startswith('9'))

def format_price(price_kopecks: int) -> str:
    """Format price from kopecks to rubles"""
    rubles = price_kopecks / 100
    return f"{rubles:,.0f} ₽"

def format_datetime(dt: datetime, include_seconds: bool = False) -> str:
    """Format datetime for display"""
    if include_seconds:
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    return dt.strftime("%d.%m.%Y %H:%M")

def format_relative_time(dt: datetime) -> str:
    """Format relative time (e.g., '5 minutes ago')"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "только что"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def sanitize_html(text: str) -> str:
    """Sanitize HTML content"""
    return html.escape(text)

def extract_user_info(update) -> Dict[str, Any]:
    """Extract user information from update"""
    user = update.effective_user
    if not user:
        return {}
    
    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "language_code": user.language_code,
    }

def generate_unique_id() -> str:
    """Generate unique identifier"""
    import uuid
    return str(uuid.uuid4())

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """Split list into chunks of size n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 Б"
    
    size_names = ["Б", "КБ", "МБ", "ГБ"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def is_valid_callback_data(data: str) -> bool:
    """Validate callback data format"""
    from bot.config.settings import MAX_CALLBACK_DATA_LENGTH
    return len(data) <= MAX_CALLBACK_DATA_LENGTH and ':' in data

def parse_callback_data(data: str) -> Dict[str, str]:
    """Parse callback data into components"""
    if not is_valid_callback_data(data):
        return {}
    
    parts = data.split(':', 1)
    if len(parts) != 2:
        return {}
    
    return {
        "action": parts[0],
        "payload": parts[1]
    }

def create_callback_data(action: str, payload: str = "") -> str:
    """Create properly formatted callback data"""
    from bot.config.settings import MAX_CALLBACK_DATA_LENGTH
    
    data = f"{action}:{payload}" if payload else action
    
    if len(data) > MAX_CALLBACK_DATA_LENGTH:
        # Truncate payload if too long
        max_payload = MAX_CALLBACK_DATA_LENGTH - len(action) - 1
        if max_payload > 0:
            data = f"{action}:{payload[:max_payload]}"
        else:
            data = action
    
    return data

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data showing only first few characters"""
    if len(data) <= visible_chars:
        return "*" * len(data)
    return data[:visible_chars] + "*" * (len(data) - visible_chars)

def get_russian_plural(count: int, forms: tuple) -> str:
    """Get correct Russian plural form based on count"""
    if len(forms) != 3:
        return forms[0] if forms else ""
    
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]  # 1, 21, 31, ...
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return forms[1]  # 2-4, 22-24, ...
    else:
        return forms[2]  # 0, 5-20, 25-30, ...

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    return wrapper