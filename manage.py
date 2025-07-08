#!/usr/bin/env python3
"""Management utility for DB migrations and seed.
Usage:
  python manage.py db_upgrade   – run Alembic upgrade head
  python manage.py seed_categories
"""
from bot.services.db import async_engine, async_sessionmaker, init_db, Category
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

# Ensure project is importable
sys.path.append(str(Path(__file__).parent))


aSYNC_CMDS = {
    "db_upgrade": "_db_upgrade",
    "seed_categories": "_seed_categories",
}


async def _db_upgrade():
    """Run Alembic migrations to head (on the fly, no alembic folder)."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", async_engine.url.render_as_string(hide_password=False))
    command.upgrade(alembic_cfg, "head")


async def _seed_categories():
    """Insert default categories again (idempotent)."""
    async with async_sessionmaker() as session:
        cnt = (await session.execute(text("SELECT count(*) FROM categories"))).scalar_one()
        if cnt:
            print("Categories already seeded (", cnt, ")")
            return
        await init_db()  # ensure tables exist
        print("Categories seeded")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in aSYNC_CMDS:
        print("Usage: manage.py [db_upgrade|seed_categories]")
        return
    cmd = sys.argv[1]
    asyncio.run(globals()[aSYNC_CMDS[cmd]]())


if __name__ == "__main__":
    main()
