"""add is_tag_managed and cost to MasterData_product

Revision ID: b8e3d1f5c702
Revises: c4d8e1f2a9b6
Create Date: 2026-10-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e3d1f5c702'
down_revision: Union[str, Sequence[str], None] = 'c4d8e1f2a9b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('MasterData_product', sa.Column('is_tag_managed', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('MasterData_product', sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('MasterData_product', 'cost')
    op.drop_column('MasterData_product', 'is_tag_managed')
