"""add mode and action to tagscan header and line data

Revision ID: e7b3c9a41d58
Revises: d5a2f8b13e77
Create Date: 2026-09-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b3c9a41d58'
down_revision: Union[str, Sequence[str], None] = 'd5a2f8b13e77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_header_data', sa.Column('mode', sa.String(length=255), nullable=True))
    op.add_column('Tagscan_header_data', sa.Column('action', sa.String(length=255), nullable=True))
    op.add_column('Tagscan_line_data', sa.Column('mode', sa.String(length=255), nullable=True))
    op.add_column('Tagscan_line_data', sa.Column('action', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_line_data', 'action')
    op.drop_column('Tagscan_line_data', 'mode')
    op.drop_column('Tagscan_header_data', 'action')
    op.drop_column('Tagscan_header_data', 'mode')
