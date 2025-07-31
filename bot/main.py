#!/usr/bin/env python3
"""
🏛️ ЮРИДИЧЕСКИЙ ЦЕНТР - REFACTORED MAIN MODULE

Simplified and modular main bot file using refactored components.
This replaces the massive 11,271-line main.py with a clean, maintainable structure.
"""

import asyncio
import logging
import os
from datetime import datetime

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# FORCE BLOCK Enhanced AI to prevent Azure API calls
DISABLE_ENHANCED_AI = os.getenv("DISABLE_ENHANCED_AI", "true").lower() == "true"
logger = logging.getLogger(__name__)

if DISABLE_ENHANCED_AI:
    logger.info("🚫 Enhanced AI FORCE DISABLED via environment variable - Azure prevention active")

# Import refactored modules
from bot.config.settings import TOKEN, validate_config, ADMIN_USERS, PRODUCTION_MODE
from bot.core.rate_limiter import rate_limiter
from bot.core.metrics import metrics, get_system_stats
from bot.services.db import init_db
from bot.services.ai_unified import unified_ai_service, ai_health_check
from bot.services.autopost_unified import initialize_autopost_system, autopost_system
from bot.handlers.user.commands import (
    cmd_start, message_handler_router, client_flow_callback, 
    handle_phone_input, initialize_ai_manager
)

# Import minimal admin handlers
from bot.handlers.smm_admin import register_smm_admin_handlers
from bot.handlers.quick_fixes import register_quick_fixes_handlers
from bot.handlers.production_testing import register_production_testing_handlers

logger = logging.getLogger(__name__)

class LegalCenterBot:
    """Main bot class managing all components"""
    
    def __init__(self):
        self.application = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("🚀 Initializing Legal Center Bot...")
            
            # Validate configuration
            validate_config()
            logger.info("✅ Configuration validated")
            
            # Initialize database
            await init_db()
            logger.info("✅ Database initialized")
            
            # Initialize AI services
            await initialize_ai_manager()
            logger.info("✅ AI services initialized")
            
            # Create telegram application
            self.application = Application.builder().token(TOKEN).build()
            
            # Initialize autopost system
            initialize_autopost_system(self.application)
            if autopost_system:
                await autopost_system.initialize()
                logger.info("✅ Autopost system initialized")
            
            # Register handlers
            await self._register_handlers()
            logger.info("✅ Handlers registered")
            
            # Set admin users
            logger.info(f"🔧 Admin users configured: {ADMIN_USERS}")
            
            # Update metrics
            metrics.start_time = datetime.now().timestamp()
            
            self.is_initialized = True
            logger.info("✅ Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            raise
    
    async def _register_handlers(self):
        """Register all bot handlers"""
        app = self.application
        
        # User command handlers
        app.add_handler(CommandHandler("start", cmd_start))
        
        # User callback handlers
        app.add_handler(CallbackQueryHandler(
            client_flow_callback, 
            pattern=r"^client_flow:"
        ))
        
        # Phone input handler (context-dependent)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"^[+]?[7-8][\d\s\-\(\)]+$"),
            handle_phone_input
        ))
        
        # General message handler
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler_router
        ))
        
        # Register additional handlers
        register_smm_admin_handlers(app)
        register_quick_fixes_handlers(app)
        register_production_testing_handlers(app)
        
        logger.info("📋 All handlers registered successfully")
    
    async def start(self):
        """Start the bot"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            logger.info("🚀 Starting Legal Center Bot...")
            
            # Start autopost system
            if autopost_system:
                await autopost_system.start_autopost_loop()
                logger.info("✅ Autopost system started")
            
            # Initialize application without polling
            logger.info(f"🔗 Bot starting in {'PRODUCTION' if PRODUCTION_MODE else 'DEVELOPMENT'} mode")
            await self.application.initialize()
            await self.application.start()
            
            # Set webhook in production mode
            if PRODUCTION_MODE:
                from bot.config.settings import WEBHOOK_URL, WEBHOOK_PATH
                webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
                try:
                    await self.application.bot.set_webhook(webhook_full_url)
                    logger.info(f"✅ Webhook set to: {webhook_full_url}")
                except Exception as e:
                    logger.error(f"❌ Failed to set webhook: {e}")
            
            logger.info("✅ Bot started successfully (webhook mode)")
            
            # Keep bot running in webhook mode
            if PRODUCTION_MODE:
                logger.info("🔄 Bot running in webhook mode - waiting for updates...")
                # Bot will stay alive through the FastAPI server
                while True:
                    await asyncio.sleep(60)  # Keep alive loop
            
        except Exception as e:
            logger.error(f"❌ Bot startup failed: {e}")
            raise
    
    async def stop(self):
        """Stop the bot gracefully"""
        try:
            logger.info("🛑 Stopping Legal Center Bot...")
            
            # Stop autopost system with timeout
            if autopost_system:
                try:
                    await asyncio.wait_for(autopost_system.stop_autopost_loop(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Autopost system stop timed out")
                except Exception as e:
                    logger.error(f"❌ Error stopping autopost: {e}")
            
            # Stop telegram application with timeout
            if self.application:
                try:
                    await asyncio.wait_for(self.application.stop(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Telegram app stop timed out")
                except Exception as e:
                    logger.error(f"❌ Error stopping telegram app: {e}")
            
            logger.info("✅ Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")

# Global bot instance
bot = LegalCenterBot()

# ================ HEALTH CHECK ENDPOINTS ================

async def health_check() -> dict:
    """Comprehensive system health check"""
    try:
        system_stats = get_system_stats()
        ai_status = await ai_health_check()
        autopost_stats = autopost_system.get_stats() if autopost_system else {"status": "not_initialized"}
        rate_limiter_stats = rate_limiter.get_stats()
        
        return {
            "status": "healthy" if bot.is_initialized else "initializing",
            "timestamp": datetime.now().isoformat(),
            "production_mode": PRODUCTION_MODE,
            "components": {
                "bot": "initialized" if bot.is_initialized else "not_initialized",
                "database": "connected",  # Assumed if we got this far
                "ai_services": ai_status,
                "autopost": autopost_stats,
                "rate_limiter": rate_limiter_stats
            },
            "metrics": system_stats
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ================ ADMIN HELPER FUNCTIONS ================

async def notify_all_admins(message: str, keyboard=None):
    """Notify all admin users"""
    if not bot.application:
        logger.error("Bot application not initialized")
        return
    
    for admin_id in ADMIN_USERS:
        try:
            await bot.application.bot.send_message(
                chat_id=admin_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USERS

# ================ STARTUP FUNCTIONS ================

async def main():
    """Main entry point"""
    try:
        # Configure logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        
        logger.info("🏛️ Legal Center Bot - Starting up...")
        
        # Start the bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        try:
            await bot.stop()
        except Exception as stop_error:
            logger.error(f"❌ Error during bot shutdown: {stop_error}")

if __name__ == "__main__":
    """Direct execution entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        exit(1)

# ================ LEGACY EXPORTS ================
# These exports maintain backward compatibility with existing code

# Global variables for backward compatibility
ADMIN_USERS_GLOBAL = ADMIN_USERS
ai_enhanced_manager = None  # Will be set by initialize_ai_manager
autopost_job = None  # Legacy reference

# Functions for backward compatibility
async def initialize_enhanced_ai():
    """Legacy function - use initialize_ai_manager instead"""
    await initialize_ai_manager()

def get_bot_application():
    """Get the bot application instance"""
    return bot.application

def get_system_metrics():
    """Get system metrics"""
    return get_system_stats()

# Export main components for other modules
__all__ = [
    'bot', 'health_check', 'notify_all_admins', 'is_admin',
    'ADMIN_USERS_GLOBAL', 'get_bot_application', 'get_system_metrics'
]