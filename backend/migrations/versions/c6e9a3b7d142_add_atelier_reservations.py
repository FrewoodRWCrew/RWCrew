"""add Atelier reservations and the article size split

Revision ID: c6e9a3b7d142
Revises: b5d8f2a6c931
Create Date: 2026-10-25 18:00:00.000000

Block 2 of the Atelier module: per team per festival the number of persons
(Atelier_reservation), and per article size the share (%) used to estimate
how many pieces of each size to prepare.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6e9a3b7d142'
down_revision: Union[str, Sequence[str], None] = 'b5d8f2a6c931'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'Atelier_reservation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('persons', sa.Integer(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('festival_id', 'team_id', name='uq_atelier_reservation'),
    )
    op.create_index(op.f('ix_Atelier_reservation_season_id'), 'Atelier_reservation', ['season_id'], unique=False)
    op.create_index(op.f('ix_Atelier_reservation_festival_id'), 'Atelier_reservation', ['festival_id'], unique=False)
    op.create_index(op.f('ix_Atelier_reservation_team_id'), 'Atelier_reservation', ['team_id'], unique=False)
    op.add_column('Atelier_article_size', sa.Column('size_share_pct', sa.Numeric(precision=5, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Atelier_article_size', 'size_share_pct')
    op.drop_index(op.f('ix_Atelier_reservation_team_id'), table_name='Atelier_reservation')
    op.drop_index(op.f('ix_Atelier_reservation_festival_id'), table_name='Atelier_reservation')
    op.drop_index(op.f('ix_Atelier_reservation_season_id'), table_name='Atelier_reservation')
    op.drop_table('Atelier_reservation')
