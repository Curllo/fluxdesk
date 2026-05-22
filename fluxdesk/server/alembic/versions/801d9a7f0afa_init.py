"""init

Revision ID: 801d9a7f0afa
Revises: 
Create Date: 2026-05-05 12:33:16.036013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801d9a7f0afa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    op.create_table(
        'windows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('position_x', sa.Float(), default=100),
        sa.Column('position_y', sa.Float(), default=100),
        sa.Column('width', sa.Float(), default=400),
        sa.Column('height', sa.Float(), default=300),
        sa.Column('always_on_top', sa.Integer(), default=1),
        sa.Column('is_minimized', sa.Integer(), default=0),
        sa.Column('display_index', sa.Integer(), default=0),
        sa.Column('opacity', sa.Float(), default=1.0),
        sa.Column('data_json', sa.Text(), default='{}'),
        sa.Column('created_at', sa.String(), default=''),
        sa.Column('updated_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('window_id', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.Text(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'todos',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('window_id', sa.String(), nullable=True),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('completed', sa.Integer(), default=0),
        sa.Column('priority', sa.Integer(), default=1),
        sa.Column('due_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), default=''),
        sa.Column('updated_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'notes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('window_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), default=''),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), default=''),
        sa.Column('updated_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'reminders',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('time', sa.String(), nullable=False),
        sa.Column('repeat', sa.String(), default='once'),
        sa.Column('dismissed', sa.Integer(), default=0),
        sa.Column('created_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'note_embeddings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('note_id', sa.String(), nullable=False),
        sa.Column('embedding_json', sa.Text(), nullable=False),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'pomodoro_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('duration', sa.Integer(), default=25),
        sa.Column('started_at', sa.String(), default=''),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.Column('interrupted', sa.Integer(), default=0),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Remove initial schema."""
    op.drop_table('pomodoro_sessions')
    op.drop_table('note_embeddings')
    op.drop_table('reminders')
    op.drop_table('notes')
    op.drop_table('todos')
    op.drop_table('messages')
    op.drop_table('windows')
