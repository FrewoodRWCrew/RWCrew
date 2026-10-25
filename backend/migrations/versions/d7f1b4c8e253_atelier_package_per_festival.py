"""Atelier: the package moves into the reservation (per festival)

Revision ID: d7f1b4c8e253
Revises: c6e9a3b7d142
Create Date: 2026-10-25 21:00:00.000000

The Ploegpakketten screen (one package per team per season) is merged into
Reservaties: a reservation (festival + team) now holds both the number of
persons and its own package lines (Atelier_reservation_line). Existing season
packages are copied onto every active festival of their season, then
Atelier_team_package and the "atelier.teampackages" screen are removed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7f1b4c8e253'
down_revision: Union[str, Sequence[str], None] = 'c6e9a3b7d142'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'Atelier_reservation_line',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('quantity_per_person', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['Atelier_article.id']),
        sa.ForeignKeyConstraint(['reservation_id'], ['Atelier_reservation.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reservation_id', 'article_id', name='uq_atelier_reservation_line'),
    )
    op.create_index(
        op.f('ix_Atelier_reservation_line_reservation_id'), 'Atelier_reservation_line', ['reservation_id'], unique=False
    )

    bind = op.get_bind()
    # Every season package line, copied to each active festival of its season:
    # first make sure the festival + team has a reservation (0 persons) ...
    bind.execute(sa.text(
        '''
        INSERT INTO "Atelier_reservation" (season_id, festival_id, team_id, persons, updated_at)
        SELECT DISTINCT p.season_id, f.id, p.team_id, 0, now()
        FROM "Atelier_team_package" p
        JOIN "MasterData_festival" f ON f.season_id = p.season_id AND f.active
        WHERE NOT EXISTS (
            SELECT 1 FROM "Atelier_reservation" r WHERE r.festival_id = f.id AND r.team_id = p.team_id
        )
        '''
    ))
    # ... then add the package lines to it.
    bind.execute(sa.text(
        '''
        INSERT INTO "Atelier_reservation_line" (reservation_id, article_id, quantity_per_person)
        SELECT r.id, p.article_id, p.quantity_per_person
        FROM "Atelier_team_package" p
        JOIN "MasterData_festival" f ON f.season_id = p.season_id AND f.active
        JOIN "Atelier_reservation" r ON r.festival_id = f.id AND r.team_id = p.team_id
        '''
    ))

    op.drop_index(op.f('ix_Atelier_team_package_team_id'), table_name='Atelier_team_package')
    op.drop_index(op.f('ix_Atelier_team_package_season_id'), table_name='Atelier_team_package')
    op.drop_table('Atelier_team_package')

    # The Ploegpakketten screen no longer exists: drop its rights, then the screen.
    bind.execute(sa.text(
        'DELETE FROM "Atelier_role_permissions" WHERE screen_id IN '
        '(SELECT id FROM "Atelier_screens" WHERE key = :key)'
    ), {"key": "atelier.teampackages"})
    bind.execute(sa.text('DELETE FROM "Atelier_screens" WHERE key = :key'), {"key": "atelier.teampackages"})


def downgrade() -> None:
    """Downgrade schema. The per-festival lines can't be folded back into one
    season package reliably, so the season packages come back empty."""
    op.create_table(
        'Atelier_team_package',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('quantity_per_person', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['Atelier_article.id']),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'team_id', 'article_id', name='uq_atelier_team_package'),
    )
    op.create_index(op.f('ix_Atelier_team_package_season_id'), 'Atelier_team_package', ['season_id'], unique=False)
    op.create_index(op.f('ix_Atelier_team_package_team_id'), 'Atelier_team_package', ['team_id'], unique=False)
    op.drop_index(op.f('ix_Atelier_reservation_line_reservation_id'), table_name='Atelier_reservation_line')
    op.drop_table('Atelier_reservation_line')
