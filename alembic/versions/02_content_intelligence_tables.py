"""Add content intelligence tables

Revision ID: 02_content_intelligence
Revises: 01_complete_enhanced_ai_tables
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '02_content_intelligence'
down_revision = '01_complete_enhanced_ai_tables'
branch_labels = None
depends_on = None

def upgrade():
    # Content Items table
    op.create_table('content_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('publish_date', sa.DateTime(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('relevance_score', sa.Float(), default=0.0),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('used_in_post', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.now),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
        sa.UniqueConstraint('content_hash')
    )
    
    # Post History table
    op.create_table('post_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_text', sa.Text(), nullable=False),
        sa.Column('post_hash', sa.String(length=64), nullable=False),
        sa.Column('channel_id', sa.String(length=50), nullable=False),
        sa.Column('posted_at', sa.DateTime(), default=datetime.now),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_hash')
    )

    # Create indexes for better performance
    op.create_index('ix_content_items_source', 'content_items', ['source'])
    op.create_index('ix_content_items_category', 'content_items', ['category'])
    op.create_index('ix_content_items_created_at', 'content_items', ['created_at'])
    op.create_index('ix_post_history_posted_at', 'post_history', ['posted_at'])

def downgrade():
    op.drop_index('ix_post_history_posted_at', table_name='post_history')
    op.drop_index('ix_content_items_created_at', table_name='content_items')
    op.drop_index('ix_content_items_category', table_name='content_items')
    op.drop_index('ix_content_items_source', table_name='content_items')
    op.drop_table('post_history')
    op.drop_table('content_items')
