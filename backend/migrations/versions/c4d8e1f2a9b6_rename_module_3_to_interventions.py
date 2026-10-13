"""rename module-3 to Interventions

Revision ID: c4d8e1f2a9b6
Revises: a7c2e9f4b318
Create Date: 2026-10-13 00:00:00.000000

Pure data change: module-3 is renamed from "Intervention Requests" to
"Interventions". seed.py never overwrites an existing module's name, so an
already-seeded database needs this update applied directly. No schema changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e1f2a9b6'
down_revision: Union[str, Sequence[str], None] = 'a7c2e9f4b318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Interventions\' WHERE key = \'module-3\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Intervention Requests\' WHERE key = \'module-3\'')
