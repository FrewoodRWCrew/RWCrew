"""add csv comment (product / comments column) to tagscan header and line data

Revision ID: c3f8a1e6d924
Revises: b9e4d2a7c631
Create Date: 2026-10-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1e6d924'
down_revision: Union[str, Sequence[str], None] = 'b9e4d2a7c631'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_header_data', sa.Column('csv_comment', sa.Text(), nullable=True))
    op.add_column('Tagscan_line_data', sa.Column('csv_comment', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_line_data', 'csv_comment')
    op.drop_column('Tagscan_header_data', 'csv_comment')
