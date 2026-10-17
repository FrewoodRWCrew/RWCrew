"""add limit_value to MasterData_product

Revision ID: d5f2a8c3e917
Revises: b8e3d1f5c702
Create Date: 2026-10-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f2a8c3e917'
down_revision: Union[str, Sequence[str], None] = 'b8e3d1f5c702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('MasterData_product', sa.Column('limit_value', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('MasterData_product', 'limit_value')
