"""add KarTracker speciale levertoeren + team link table

Revision ID: d5e9f3a7b124
Revises: c4d8e2f6a913
Create Date: 2026-10-24 18:00:00.000000

New KarTracker master data "Speciale levertoeren" (special delivery tours
such as "Kleine wastoer", "Ijsblokken") and the many-to-many link
MasterData_team_speciale_levertoer set on MasterData's team fiche.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e9f3a7b124'
down_revision: Union[str, Sequence[str], None] = 'c4d8e2f6a913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'KarTracker_speciale_levertoeren',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_KarTracker_speciale_levertoeren_name'), 'KarTracker_speciale_levertoeren', ['name'], unique=True
    )
    op.create_table(
        'MasterData_team_speciale_levertoer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('levertoer_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['levertoer_id'], ['KarTracker_speciale_levertoeren.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'levertoer_id', name='uq_masterdata_team_speciale_levertoer'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('MasterData_team_speciale_levertoer')
    op.drop_index(op.f('ix_KarTracker_speciale_levertoeren_name'), table_name='KarTracker_speciale_levertoeren')
    op.drop_table('KarTracker_speciale_levertoeren')
