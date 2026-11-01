"""Wristband webhook token: generated in the app instead of set in .env

Revision ID: e5a1c7d3f486
Revises: d4f9a2b8e375
Create Date: 2026-11-01 21:00:00.000000

The token the wristband company sends is now generated on the Scans module's
Settings screen. Only its hash is stored, in the single Tagscan_settings row.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a1c7d3f486'
down_revision: Union[str, Sequence[str], None] = 'd4f9a2b8e375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_settings', sa.Column('wristband_token_hash', sa.String(length=64), nullable=True))
    op.add_column('Tagscan_settings', sa.Column('wristband_token_generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('Tagscan_settings', sa.Column('wristband_token_last_used_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_settings', 'wristband_token_last_used_at')
    op.drop_column('Tagscan_settings', 'wristband_token_generated_at')
    op.drop_column('Tagscan_settings', 'wristband_token_hash')
