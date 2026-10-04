"""add masterdata team responsible

Revision ID: c4f7a2d9e815
Revises: b7d3e91a4c20
Create Date: 2026-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f7a2d9e815'
down_revision: Union[str, Sequence[str], None] = 'b7d3e91a4c20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('MasterData_team_responsible',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=50), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_MasterData_team_responsible_season_id'), 'MasterData_team_responsible', ['season_id'], unique=False)
    op.create_index(op.f('ix_MasterData_team_responsible_team_id'), 'MasterData_team_responsible', ['team_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_MasterData_team_responsible_team_id'), table_name='MasterData_team_responsible')
    op.drop_index(op.f('ix_MasterData_team_responsible_season_id'), table_name='MasterData_team_responsible')
    op.drop_table('MasterData_team_responsible')
