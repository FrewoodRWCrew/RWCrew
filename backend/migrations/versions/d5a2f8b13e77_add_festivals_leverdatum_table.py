"""add festivals leverdatum table

Revision ID: d5a2f8b13e77
Revises: c8e4a1f6d052
Create Date: 2026-09-19 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a2f8b13e77'
down_revision: Union[str, Sequence[str], None] = 'c8e4a1f6d052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('Festivals_leverdatum',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('festival_id', sa.Integer(), nullable=False),
    sa.Column('delivery_date', sa.Date(), nullable=True),
    sa.Column('pickup_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('festival_id', name='uq_leverdatum_festival')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('Festivals_leverdatum')
