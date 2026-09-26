"""add module-10 (Mobile App)

Revision ID: b7d2e4f6a801
Revises: f1a8c5d2e9b6
Create Date: 2026-09-24 10:00:00.000000

Adds the "Mobile App" module (module-10): the web-side download page for the
smartphone app. seed.py only inserts modules on a brand-new database, so
existing databases (test/production) get the row from this migration.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7d2e4f6a801'
down_revision: Union[str, Sequence[str], None] = 'f1a8c5d2e9b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the module row only if it is not already there.
    op.execute(
        'INSERT INTO "Landing_modules" (key, name, sort_order, is_active) '
        "SELECT 'module-10', 'Mobile App', 10, true "
        'WHERE NOT EXISTS (SELECT 1 FROM "Landing_modules" WHERE key = \'module-10\')'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DELETE FROM "Landing_modules" WHERE key = \'module-10\'')
