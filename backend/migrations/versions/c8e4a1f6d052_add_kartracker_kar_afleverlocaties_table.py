"""add kartracker kar afleverlocaties table

Revision ID: c8e4a1f6d052
Revises: b3c1d7e2a9f4
Create Date: 2026-09-19 21:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e4a1f6d052'
down_revision: Union[str, Sequence[str], None] = 'b3c1d7e2a9f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('KarTracker_kar_afleverlocaties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.Column('festival_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('afleverlocatie_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['afleverlocatie_id'], ['KarTracker_afleverlocaties.id'], ),
    sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('season_id', 'festival_id', 'team_id', name='uq_kar_afleverlocatie_season_festival_team')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('KarTracker_kar_afleverlocaties')
