#!/usr/bin/env python3
"""Local test runner for the bot without Railway dependencies."""

from bot.services.db import init_db, async_sessionmaker, Category
from aiohttp import web
import os
import asyncio
from pathlib import Path

# Set environment variables for local testing FIRST
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["BOT_TOKEN"] = "test_token_123"
os.environ["ADMIN_CHAT_ID"] = "123456789"
os.environ["RAILWAY_PUBLIC_DOMAIN"] = "localhost:8080"
os.environ["PORT"] = "8080"

# Import after setting env vars


async def create_test_db():
    """Create and seed test database"""
    print("🔧 Creating test database...")

    # Initialize database
    await init_db()

    # Check if categories exist
    async with async_sessionmaker() as session:
        from sqlalchemy import func, select
        result = await session.execute(select(func.count(Category.id)))
        count = result.scalar_one()

        if count == 0:
            print("📝 Seeding categories...")
            categories = [
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
                "Уголовные дела"
            ]

            for cat_name in categories:
                category = Category(name=cat_name)
                session.add(category)

            await session.commit()
            print(f"✅ Added {len(categories)} categories")
        else:
            print(f"✅ Database already has {count} categories")


async def test_webapp():
    """Test the webapp endpoints"""
    print("🌐 Testing webapp...")

    # Create test app
    app = web.Application()

    # Simple test handler
    async def handle_test(request):
        return web.Response(text="WebApp is working!")

    async def handle_webapp(request):
        html_path = Path(__file__).parent / "webapp" / "index.html"
        if html_path.exists():
            return web.FileResponse(html_path)
        else:
            return web.Response(text="WebApp HTML not found", status=404)

    async def handle_submit(request):
        return web.json_response({
            "status": "ok",
            "message": "Local test - form submitted successfully"
        })

    # Add routes
    app.router.add_get("/", handle_test)
    app.router.add_get("/webapp/", handle_webapp)
    app.router.add_post("/submit", handle_submit)
    app.router.add_static("/webapp/", path=Path(__file__).parent / "webapp")

    return app


async def main():
    """Main test function"""
    print("🚀 Starting local test...")

    try:
        # Setup database
        await create_test_db()

        # Create test web app
        app = await test_webapp()

        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 8080)
        await site.start()

        print("✅ Local server started!")
        print("🌐 WebApp: http://localhost:8080/webapp/")
        print("🧪 Test endpoint: http://localhost:8080/")
        print("📋 Submit test: POST http://localhost:8080/submit")
        print("\n💡 Press Ctrl+C to stop")

        # Keep running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\n👋 Stopping local test...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
