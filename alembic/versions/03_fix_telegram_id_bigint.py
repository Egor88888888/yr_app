"""Fix Telegram ID overflow - INTEGER to BIGINT migration

Revision ID: 03_fix_telegram_id_bigint
Revises: 02_content_intelligence_tables
Create Date: 2025-01-11 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03_fix_telegram_id_bigint'
down_revision = '02_content_intelligence_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    🔧 КРИТИЧЕСКИЙ ФИКС: Исправление переполнения Telegram ID

    ПРОБЛЕМА: PostgreSQL INTEGER поддерживает только до 2,147,483,647
    Telegram ID могут быть больше (например: 6922033571)

    РЕШЕНИЕ: Конвертация всех tg_id колонок в BIGINT
    """

    # 1. Основные таблицы - users.tg_id
    print("🔧 Converting users.tg_id INTEGER → BIGINT...")
    op.alter_column('users', 'tg_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BIGINT(),
                    existing_nullable=False)

    # 2. Админы - admins.tg_id
    print("🔧 Converting admins.tg_id INTEGER → BIGINT...")
    op.alter_column('admins', 'tg_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BIGINT(),
                    existing_nullable=False)

    # 3. Проверяем Enhanced AI таблицы (если существуют)
    # Эти таблицы могут не существовать в некоторых установках

    # Проверяем существование таблицы user_profiles
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()

    if 'user_profiles' in existing_tables:
        print("🔧 Found user_profiles table, checking for dependencies...")
        # Примечание: user_profiles.user_id ссылается на users.id (не tg_id),
        # поэтому не требует изменений

    if 'dialogue_sessions' in existing_tables:
        print("🔧 Found dialogue_sessions table, checking for dependencies...")
        # Примечание: dialogue_sessions.user_id также ссылается на users.id

    print("✅ All tg_id columns converted to BIGINT successfully!")
    print("🎯 This fixes: 'value out of int32 range' errors for large Telegram IDs")


def downgrade() -> None:
    """
    ⚠️  ОПАСНО: Откат может привести к потере данных!

    Если у вас есть Telegram ID > 2,147,483,647, они будут потеряны
    """
    print("⚠️  WARNING: Downgrading BIGINT → INTEGER may cause data loss!")
    print("⚠️  Large Telegram IDs (>2,147,483,647) will be lost!")

    # Откат для admins.tg_id
    op.alter_column('admins', 'tg_id',
                    existing_type=sa.BIGINT(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)

    # Откат для users.tg_id
    op.alter_column('users', 'tg_id',
                    existing_type=sa.BIGINT(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)

    print("⚠️  Downgrade completed - check for data integrity!")
