"""drop legacy association_name from intervention requests

Revision ID: f1a8c5d2e9b6
Revises: a4c2f9d1b7e3
Create Date: 2026-09-20 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1a8c5d2e9b6'
down_revision: Union[str, Sequence[str], None] = 'a4c2f9d1b7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Migration 360c7915525e was edited after it had already run on some
    # databases: the original version dropped "association_name", the edited
    # version kept it. Databases that ran the edited version (test/production)
    # therefore still have this NOT NULL column, which the model no longer
    # writes, so every insert failed with a 500. Databases that ran the
    # original version (local dev) no longer have it — hence IF EXISTS, so this
    # is a no-op there.
    #
    # Keep any legacy free-text name that couldn't be matched to a team by
    # copying it into team_name (the model's free-text Ploeg field) first.
    # Guarded by a column-existence check because the UPDATE would fail on
    # databases where the column is already gone.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'InterventionRequests_request'
                  AND column_name = 'association_name'
            ) THEN
                UPDATE "InterventionRequests_request"
                SET team_name = association_name
                WHERE team_id IS NULL AND team_name IS NULL AND association_name <> '';
            END IF;
        END $$;
        """
    )
    op.execute('ALTER TABLE "InterventionRequests_request" DROP COLUMN IF EXISTS association_name')


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to restore: the column is legacy and no code reads or writes it.
    pass
