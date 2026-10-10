"""add tagscan rfid tag kar_id

Revision ID: c3d8f1a6e247
Revises: 9c4e2b7a1d35
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d8f1a6e247'
down_revision: Union[str, Sequence[str], None] = '9c4e2b7a1d35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_rfid_tag', sa.Column('kar_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_Tagscan_rfid_tag_kar_id'), 'Tagscan_rfid_tag', ['kar_id'], unique=False)
    op.create_foreign_key(
        'Tagscan_rfid_tag_kar_id_fkey', 'Tagscan_rfid_tag', 'KarTracker_karren', ['kar_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('Tagscan_rfid_tag_kar_id_fkey', 'Tagscan_rfid_tag', type_='foreignkey')
    op.drop_index(op.f('ix_Tagscan_rfid_tag_kar_id'), table_name='Tagscan_rfid_tag')
    op.drop_column('Tagscan_rfid_tag', 'kar_id')
