"""add tagscan line data assigned_product_id

Revision ID: e5f1b3c8d462
Revises: d4e9a2b7c351
Create Date: 2026-10-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f1b3c8d462'
down_revision: Union[str, Sequence[str], None] = 'd4e9a2b7c351'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_line_data', sa.Column('assigned_product_id', sa.Integer(), nullable=True))

    # Backfill: matched lines get their tag's current product id.
    op.execute(
        '''
        UPDATE "Tagscan_line_data" SET assigned_product_id = (
            SELECT t.assigned_product_id FROM "Tagscan_rfid_tag" t
            WHERE t.id = "Tagscan_line_data".rfid_tag_id
        )
        WHERE rfid_tag_id IS NOT NULL AND status != 'cancelled'
        '''
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_line_data', 'assigned_product_id')
