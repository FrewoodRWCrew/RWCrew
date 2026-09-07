"""rename module-3 to Intervention Requests

Revision ID: 733ddf4ec3d0
Revises: 0a5007b9640a
Create Date: 2026-09-06 00:00:00.000000

Pure data change: module-3 is becoming a real module ("Intervention
Requests") instead of the generic "Module 3" placeholder. seed.py never
overwrites an existing module's name, so an already-seeded database needs
this update applied directly. No schema changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '733ddf4ec3d0'
down_revision: Union[str, Sequence[str], None] = '0a5007b9640a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Intervention Requests\' WHERE key = \'module-3\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Module 3\' WHERE key = \'module-3\'')
