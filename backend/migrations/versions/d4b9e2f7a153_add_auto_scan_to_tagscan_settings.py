"""add automatic background scan settings to tagscan settings

Revision ID: d4b9e2f7a153
Revises: c3f8a1e6d924
Create Date: 2026-10-04 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b9e2f7a153'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1e6d924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_settings', sa.Column('auto_scan_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('Tagscan_settings', sa.Column('auto_scan_interval_seconds', sa.Integer(), server_default='60', nullable=False))
    op.add_column('Tagscan_settings', sa.Column('last_auto_scan_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('Tagscan_settings', sa.Column('last_auto_scan_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_settings', 'last_auto_scan_summary')
    op.drop_column('Tagscan_settings', 'last_auto_scan_at')
    op.drop_column('Tagscan_settings', 'auto_scan_interval_seconds')
    op.drop_column('Tagscan_settings', 'auto_scan_enabled')
