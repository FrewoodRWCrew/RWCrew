"""rename module 2 to kartracker

Revision ID: 9c4e2b7a1d35
Revises: a7c3e5d91b20
Create Date: 2026-10-09 22:10:00.000000

Pure data change: KarTracker's own migration (3a5fbec6deb5) renamed module-2
with an UPDATE, which did nothing on a database whose module rows were only
seeded afterwards — the seed (app/modules/registry.py) then still wrote the
placeholder "Module 2". Only that placeholder name is replaced, so a name an
admin chose on purpose is left alone. No schema changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4e2b7a1d35'
down_revision: Union[str, Sequence[str], None] = 'a7c3e5d91b20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        'UPDATE "Landing_modules" SET name = \'KarTracker\' WHERE key = \'module-2\' AND name = \'Module 2\''
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        'UPDATE "Landing_modules" SET name = \'Module 2\' WHERE key = \'module-2\' AND name = \'KarTracker\''
    )
