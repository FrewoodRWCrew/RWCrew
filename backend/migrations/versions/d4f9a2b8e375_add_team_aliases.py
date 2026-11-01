"""Team aliases: other names a team goes by in outside applications

Revision ID: d4f9a2b8e375
Revises: c3e8f1a7d264
Create Date: 2026-11-01 17:00:00.000000

The wristband company's team names can differ slightly from ours, so a team can
have aliases on its fiche, which the wristband scans also match on.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f9a2b8e375'
down_revision: Union[str, Sequence[str], None] = 'c3e8f1a7d264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'MasterData_team_alias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('alias', sa.String(length=255), nullable=False),
        sa.Column('alias_key', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_MasterData_team_alias_team_id'), 'MasterData_team_alias', ['team_id'], unique=False)
    op.create_index(op.f('ix_MasterData_team_alias_alias_key'), 'MasterData_team_alias', ['alias_key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_MasterData_team_alias_alias_key'), table_name='MasterData_team_alias')
    op.drop_index(op.f('ix_MasterData_team_alias_team_id'), table_name='MasterData_team_alias')
    op.drop_table('MasterData_team_alias')
