"""add active to kartracker afleverlocatie

Revision ID: b3c1d7e2a9f4
Revises: f0457ce24094
Create Date: 2026-09-19 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c1d7e2a9f4'
down_revision: Union[str, Sequence[str], None] = 'f0457ce24094'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('KarTracker_afleverlocaties', sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('KarTracker_afleverlocaties', 'active')
