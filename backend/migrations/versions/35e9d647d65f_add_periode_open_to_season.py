"""add periode_open to season

Revision ID: 35e9d647d65f
Revises: 10f588a47567
Create Date: 2026-09-15 20:08:13.080448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35e9d647d65f'
down_revision: Union[str, Sequence[str], None] = '10f588a47567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('MasterData_season', sa.Column('periode_open', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('MasterData_season', 'periode_open')
