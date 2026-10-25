"""add KarTracker_settings (karcode formula)

Revision ID: a7c3e9f1b524
Revises: e6a1b4c8d235
Create Date: 2026-10-25 12:00:00.000000

Single-row settings table for KarTracker, starting with the karcode formula
used by the "Karcode Simulator" screen. Row 1 is inserted with the formula of
the old Excel sheet, so the simulator works right away.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e9f1b524'
down_revision: Union[str, Sequence[str], None] = 'e6a1b4c8d235'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    settings = op.create_table(
        'KarTracker_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('karcode_formula', sa.Text(), nullable=False),
        sa.Column('karcode_updated_by', sa.Integer(), nullable=True),
        sa.Column('karcode_updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('karcode_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['karcode_updated_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.bulk_insert(settings, [{'id': 1, 'karcode_formula': 'LEFT(kar*500+3118; 4)'}])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('KarTracker_settings')
