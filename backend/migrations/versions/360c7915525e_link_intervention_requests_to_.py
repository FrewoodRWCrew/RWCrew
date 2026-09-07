"""link intervention requests to masterdata teams

Revision ID: 360c7915525e
Revises: 7f9d4e32609d
Create Date: 2026-09-07 17:26:05.548297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '360c7915525e'
down_revision: Union[str, Sequence[str], None] = '7f9d4e32609d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # team_id starts nullable so any existing rows can be backfilled below
    # before the NOT NULL constraint is added — a straight nullable=False
    # add_column would fail against a table that already has rows.
    op.add_column('InterventionRequests_request', sa.Column('team_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_intervention_requests_request_team_id',
        'InterventionRequests_request',
        'MasterData_team',
        ['team_id'],
        ['id'],
    )

    # Preserve the free-text association and link only exact, unique matches.
    op.execute(
        """
        UPDATE "InterventionRequests_request"
        SET team_id = (
            SELECT id
            FROM "MasterData_team"
            WHERE "MasterData_team".name = "InterventionRequests_request".association_name
        )
        WHERE team_id IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_intervention_requests_request_team_id', 'InterventionRequests_request', type_='foreignkey')
    op.drop_column('InterventionRequests_request', 'team_id')
