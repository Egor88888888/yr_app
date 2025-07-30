#!/usr/bin/env python3
"""
Centralized configuration management for the bot.
All environment variables and constants should be defined here.
"""

import os
from typing import Set, Dict, Any
from collections import defaultdict

# ================ CORE CONFIGURATION ================

# Bot credentials
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Environment settings
PRODUCTION_MODE = os.getenv("RAILWAY_ENVIRONMENT") == "production"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# ================ RATE LIMITING ================

RATE_LIMIT_REQUESTS = 10  # requests
RATE_LIMIT_WINDOW = 60    # seconds
user_request_counts = defaultdict(list)  # user_id -> [timestamps]
blocked_users: Set[int] = set()

# ================ AUTOPOST SETTINGS ================

# Autopost configuration - DISABLED BY DEFAULT
POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", "10"))
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID", "-1002768745137")
TARGET_CHANNEL_USERNAME = os.getenv("TARGET_CHANNEL_USERNAME", "@legal_consult_center")
AUTOPOST_ENABLED_BY_DEFAULT = False  # Autopost disabled by default

# ================ ADMIN CONFIGURATION ================

# Admin users (from environment)
admin_ids_str = os.getenv("ADMIN_CHAT_ID", "")
ADMIN_USERS = set()
if admin_ids_str:
    try:
        ADMIN_USERS = {int(uid.strip()) for uid in admin_ids_str.split(",")}
    except ValueError:
        ADMIN_USERS = {int(admin_ids_str)} if admin_ids_str.isdigit() else set()

# Additional admin users
ADDITIONAL_ADMINS = {6373924442, 439952839}  # Known admin users
ADMIN_USERS.update(ADDITIONAL_ADMINS)

# ================ WEB APP SETTINGS ================

# Web application URLs
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "localhost")
WEBAPP_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}/webapp/"
if RAILWAY_PUBLIC_DOMAIN == "localhost":
    WEBAPP_URL = "https://localhost/webapp/"

# ================ API KEYS ================

# AI Services - PRIMARY: OpenAI GPT API
OPENAI_API_KEY = os.getenv("API_GPT")  # Primary AI API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Fallback
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Legacy support
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Payment system
CLOUDPAYMENTS_PUBLIC_ID = os.getenv("CLOUDPAYMENTS_PUBLIC_ID")
CLOUDPAYMENTS_SECRET_KEY = os.getenv("CLOUDPAYMENTS_SECRET_KEY")

# Google Sheets
GOOGLE_SHEETS_CREDS_JSON = os.getenv("GOOGLE_SHEETS_CREDS_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Notifications
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
SMS_RU_API_KEY = os.getenv("SMS_RU_API_KEY")

# Telethon (for channel management) 
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TELETHON_USER_SESSION = os.getenv("TELETHON_USER_SESSION")

# ================ BUSINESS LOGIC CONSTANTS ================

# Service categories
LEGAL_CATEGORIES = [
    "business_law", "family_law", "real_estate", "tax_law",
    "labor_law", "criminal_law", "civil_law", "contract_law",
    "intellectual_property", "immigration_law", "bankruptcy", "other"
]

# Pricing configuration
SERVICE_PRICES = {
    "consultation": 5000,  # Base consultation price in kopecks
    "document_review": 10000,
    "legal_representation": 50000,
    "contract_drafting": 15000,
}

# Message limits and timeouts
MAX_MESSAGE_LENGTH = 4096
MAX_CALLBACK_DATA_LENGTH = 64
REQUEST_TIMEOUT = 30  # seconds
DATABASE_TIMEOUT = 10  # seconds

# File upload limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = {'.pdf', '.doc', '.docx', '.txt', '.jpg', '.png'}

# ================ MONITORING ================

# System metrics (initialized as empty, populated at runtime)
SYSTEM_METRICS = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "ai_requests": 0,
    "autopost_count": 0,
    "start_time": None,
}

# ================ LOGGING CONFIGURATION ================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ================ FEATURE FLAGS ================

# Feature toggles
ENABLE_AI_ENHANCED = os.getenv("ENABLE_AI_ENHANCED", "true").lower() == "true"
ENABLE_AUTOPOST = os.getenv("ENABLE_AUTOPOST", "false").lower() == "true"  # Disabled by default
ENABLE_PAYMENTS = bool(CLOUDPAYMENTS_PUBLIC_ID)
ENABLE_SHEETS_INTEGRATION = bool(GOOGLE_SHEETS_CREDS_JSON)
ENABLE_NOTIFICATIONS = bool(MAILGUN_API_KEY)

# ================ VALIDATION ================

def validate_config():
    """Validate critical configuration on startup"""
    errors = []
    
    if not TOKEN:
        errors.append("BOT_TOKEN is required")
    
    if not ADMIN_CHAT_ID:
        errors.append("ADMIN_CHAT_ID is required")
    
    if PRODUCTION_MODE and not OPENAI_API_KEY and not OPENROUTER_API_KEY and not AZURE_OPENAI_API_KEY:
        errors.append("AI API key is required in production (API_GPT, OPENROUTER_API_KEY, or AZURE_OPENAI_API_KEY)")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# ================ HELPER FUNCTIONS ================

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USERS

def get_webapp_url(page: str = "") -> str:
    """Get webapp URL for specific page"""
    return f"{WEBAPP_URL}{page}".rstrip("/")

def is_production() -> bool:
    """Check if running in production mode"""
    return PRODUCTION_MODE

def is_debug() -> bool:
    """Check if debug mode is enabled"""
    return DEBUG_MODE