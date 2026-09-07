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
    op.create_foreign_key(None, 'InterventionRequests_request', 'MasterData_team', ['team_id'], ['id'])

    # Point every existing request at whatever team happens to exist
    # (arbitrarily, the lowest id) — there's no way to infer the right
    # team from the free-text "association_name" being dropped below, and
    # in practice this only ever runs against this app's own dev data.
    op.execute(
        """
        UPDATE "InterventionRequests_request"
        SET team_id = (SELECT id FROM "MasterData_team" ORDER BY id LIMIT 1)
        WHERE team_id IS NULL
        """
    )
    op.alter_column('InterventionRequests_request', 'team_id', nullable=False)

    op.drop_column('InterventionRequests_request', 'association_name')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('InterventionRequests_request', sa.Column('association_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.execute("""UPDATE "InterventionRequests_request" SET association_name = ''""")
    op.alter_column('InterventionRequests_request', 'association_name', nullable=False)
    op.drop_constraint(None, 'InterventionRequests_request', type_='foreignkey')
    op.drop_column('InterventionRequests_request', 'team_id')
