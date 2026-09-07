"""add is_open and color to intervention status

Revision ID: 1ee641e811a9
Revises: e4bd8c67f498
Create Date: 2026-09-07 19:09:48.000459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ee641e811a9'
down_revision: Union[str, Sequence[str], None] = 'e4bd8c67f498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('InterventionRequests_status', sa.Column('is_open', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('InterventionRequests_status', sa.Column('color', sa.String(length=20), server_default=sa.text("'gray'"), nullable=False))
    op.execute(
        """
        UPDATE "InterventionRequests_status"
        SET is_open = false
        WHERE name IN ('Geleverd', 'Gecanceled', 'Geweigerd door Altsien')
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('InterventionRequests_status', 'color')
    op.drop_column('InterventionRequests_status', 'is_open')
