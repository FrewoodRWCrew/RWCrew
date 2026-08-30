"""capitalize tagscan module display name

Revision ID: 7e11500f338f
Revises: 3508ebb3e74d
Create Date: 2026-08-30 19:13:00.946000

Pure data change: the previous migration (3508ebb3e74d) set Module 1's
display name to "Tagscan", but the correct branding capitalizes the "S"
("TagScan"). No schema changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e11500f338f'
down_revision: Union[str, Sequence[str], None] = '3508ebb3e74d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'TagScan\' WHERE key = \'module-1\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Tagscan\' WHERE key = \'module-1\'')
