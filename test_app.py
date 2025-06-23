#!/usr/bin/env python3
"""
Минимальный тестовый сервер для проверки Railway
"""
import os
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def handle_root(request):
    """Главная страница"""
    return web.json_response({
        "status": "OK",
        "message": "🚀 Railway TEST SERVER работает!",
        "version": "3.1-test",
        "env_vars": {
            "PORT": os.getenv("PORT", "8000"),
            "BOT_TOKEN": "SET" if os.getenv("YOUR_BOT_TOKEN") else "NOT_SET",
            "ADMIN_CHAT_ID": "SET" if os.getenv("ADMIN_CHAT_ID") else "NOT_SET",
            "PUBLIC_HOST": "SET" if os.getenv("MY_RAILWAY_PUBLIC_URL") else "NOT_SET"
        }
    })


async def handle_health(request):
    """Health check"""
    return web.json_response({"status": "healthy", "service": "railway-test"})


def create_app():
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/test', handle_root)
    return app


def main():
    port = int(os.getenv("PORT", 8000))
    log.info(f"🚀 Starting test server on port {port}")

    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
