"""add max_initial_stock to MasterData_product

Revision ID: a3c9e5f1b708
Revises: f1b6d3a8c524
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c9e5f1b708'
down_revision: Union[str, Sequence[str], None] = 'f1b6d3a8c524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('MasterData_product', sa.Column('max_initial_stock', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('MasterData_product', 'max_initial_stock')
