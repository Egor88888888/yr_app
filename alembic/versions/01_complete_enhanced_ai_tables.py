"""Complete Enhanced AI tables

Revision ID: 01_enhanced_ai
Revises: 5c5e6fd40450
Create Date: 2025-07-09 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01_enhanced_ai'
down_revision: Union[str, None] = '5c5e6fd40450'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to applications table
    op.add_column('applications', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column(
        'assigned_admin', sa.String(length=64), nullable=True))

    # Create Enhanced AI tables

    # 1. User Profiles
    op.create_table('user_profiles',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('experience_level', sa.String(
                        length=20), nullable=False),
                    sa.Column('preferred_style', sa.String(
                        length=20), nullable=False),
                    sa.Column('communication_speed', sa.String(
                        length=20), nullable=False),
                    sa.Column('detail_preference', sa.String(
                        length=20), nullable=False),
                    sa.Column('total_interactions',
                              sa.Integer(), nullable=False),
                    sa.Column('successful_resolutions',
                              sa.Integer(), nullable=False),
                    sa.Column('average_rating', sa.Float(), nullable=True),
                    sa.Column('frequent_categories', sa.JSON(), nullable=True),
                    sa.Column('last_categories', sa.JSON(), nullable=True),
                    sa.Column('ai_enabled', sa.Boolean(), nullable=False),
                    sa.Column('personalization_enabled',
                              sa.Boolean(), nullable=False),
                    sa.Column('memory_enabled', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('user_id')
                    )

    # 2. Dialogue Sessions
    op.create_table('dialogue_sessions',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('session_uuid', sa.String(
                        length=36), nullable=False),
                    sa.Column('context_summary', sa.Text(), nullable=True),
                    sa.Column('detected_intent', sa.String(
                        length=50), nullable=True),
                    sa.Column('detected_categories', sa.JSON(), nullable=True),
                    sa.Column('message_count', sa.Integer(), nullable=False),
                    sa.Column('resolution_status', sa.String(
                        length=20), nullable=False),
                    sa.Column('satisfaction_rating',
                              sa.Integer(), nullable=True),
                    sa.Column('last_activity', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('ended_at', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('session_uuid')
                    )

    # 3. Dialogue Messages
    op.create_table('dialogue_messages',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('session_id', sa.Integer(), nullable=False),
                    sa.Column('role', sa.String(length=10), nullable=False),
                    sa.Column('content', sa.Text(), nullable=False),
                    sa.Column('intent_confidence', sa.Float(), nullable=True),
                    sa.Column('category_predictions',
                              sa.JSON(), nullable=True),
                    sa.Column('response_time_ms', sa.Integer(), nullable=True),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['session_id'], ['dialogue_sessions.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # 4. Message Embeddings
    op.create_table('message_embeddings',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('message_id', sa.Integer(), nullable=False),
                    sa.Column('embedding', sa.LargeBinary(), nullable=False),
                    sa.Column('model_name', sa.String(
                        length=50), nullable=False),
                    sa.Column('dimension', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['message_id'], ['dialogue_messages.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('message_id')
                    )

    # 5. Category Embeddings
    op.create_table('category_embeddings',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('category_id', sa.Integer(), nullable=False),
                    sa.Column('embedding', sa.LargeBinary(), nullable=False),
                    sa.Column('model_name', sa.String(
                        length=50), nullable=False),
                    sa.Column('training_samples',
                              sa.Integer(), nullable=False),
                    sa.Column('accuracy_score', sa.Float(), nullable=True),
                    sa.Column('last_retrained', sa.DateTime(
                        timezone=True), nullable=True),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['category_id'], ['categories.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('category_id')
                    )

    # 6. AI Metrics
    op.create_table('ai_metrics',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('metric_date', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('total_requests', sa.Integer(), nullable=False),
                    sa.Column('successful_requests',
                              sa.Integer(), nullable=False),
                    sa.Column('average_response_time',
                              sa.Float(), nullable=False),
                    sa.Column('average_satisfaction',
                              sa.Float(), nullable=True),
                    sa.Column('classification_accuracy',
                              sa.Float(), nullable=True),
                    sa.Column('intent_detection_accuracy',
                              sa.Float(), nullable=True),
                    sa.Column('total_tokens_used',
                              sa.Integer(), nullable=False),
                    sa.Column('total_cost_usd', sa.Float(), nullable=True),
                    sa.Column('personalized_requests',
                              sa.Integer(), nullable=False),
                    sa.Column('memory_usage_mb', sa.Float(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )

    # 7. User Preferences
    op.create_table('user_preferences',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('preference_key', sa.String(
                        length=50), nullable=False),
                    sa.Column('preference_value', sa.Text(), nullable=False),
                    sa.Column('confidence_score', sa.Float(), nullable=False),
                    sa.Column('source', sa.String(length=20), nullable=False),
                    sa.Column('usage_count', sa.Integer(), nullable=False),
                    sa.Column('last_used', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )

    # 8. Training Data
    op.create_table('training_data',
                    sa.Column('id', sa.Integer(),
                              autoincrement=True, nullable=False),
                    sa.Column('input_text', sa.Text(), nullable=False),
                    sa.Column('expected_category_id',
                              sa.Integer(), nullable=True),
                    sa.Column('expected_intent', sa.String(
                        length=50), nullable=True),
                    sa.Column('source', sa.String(length=20), nullable=False),
                    sa.Column('quality_score', sa.Float(), nullable=False),
                    sa.Column('validated', sa.Boolean(), nullable=False),
                    sa.Column('used_in_training',
                              sa.Boolean(), nullable=False),
                    sa.Column('training_accuracy', sa.Float(), nullable=True),
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['expected_category_id'], ['categories.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade() -> None:
    # Drop Enhanced AI tables in reverse order
    op.drop_table('training_data')
    op.drop_table('user_preferences')
    op.drop_table('ai_metrics')
    op.drop_table('category_embeddings')
    op.drop_table('message_embeddings')
    op.drop_table('dialogue_messages')
    op.drop_table('dialogue_sessions')
    op.drop_table('user_profiles')

    # Drop added columns from applications
    op.drop_column('applications', 'assigned_admin')
    op.drop_column('applications', 'notes')
