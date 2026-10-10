"""add tagscan line data kar_nummer

Revision ID: d4e9a2b7c351
Revises: c3d8f1a6e247
Create Date: 2026-10-10 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e9a2b7c351'
down_revision: Union[str, Sequence[str], None] = 'c3d8f1a6e247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_line_data', sa.Column('kar_nummer', sa.String(length=50), nullable=True))

    # Backfill: lines matched to a tag that is already linked to a kar.
    op.execute(
        '''
        UPDATE "Tagscan_line_data" SET kar_nummer = (
            SELECT k.kar_nummer FROM "Tagscan_rfid_tag" t
            JOIN "KarTracker_karren" k ON k.id = t.kar_id
            WHERE t.id = "Tagscan_line_data".rfid_tag_id
        )
        WHERE rfid_tag_id IS NOT NULL AND status != 'cancelled'
        '''
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_line_data', 'kar_nummer')
