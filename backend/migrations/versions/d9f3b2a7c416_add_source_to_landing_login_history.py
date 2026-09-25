"""add source to landing login history

Revision ID: d9f3b2a7c416
Revises: c3e8a1f4b920
Create Date: 2026-09-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9f3b2a7c416'
down_revision: Union[str, Sequence[str], None] = 'c3e8a1f4b920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Landing_login_history', sa.Column('source', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Landing_login_history', 'source')
