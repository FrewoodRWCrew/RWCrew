"""add an optional picture to MasterData_product

Revision ID: a7c2e9f4b318
Revises: f3a9c6e1b247
Create Date: 2026-10-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c2e9f4b318'
down_revision: Union[str, Sequence[str], None] = 'f3a9c6e1b247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('MasterData_product', sa.Column('image_data', sa.LargeBinary(), nullable=True))
    op.add_column('MasterData_product', sa.Column('image_content_type', sa.String(length=100), nullable=True))
    op.add_column('MasterData_product', sa.Column('image_updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('MasterData_product', 'image_updated_at')
    op.drop_column('MasterData_product', 'image_content_type')
    op.drop_column('MasterData_product', 'image_data')
