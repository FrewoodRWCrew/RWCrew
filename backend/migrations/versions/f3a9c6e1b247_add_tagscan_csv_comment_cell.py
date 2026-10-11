"""add "CSV Comment" (csv_comment_cell) to tagscan header data, line data and rfid tag

Revision ID: f3a9c6e1b247
Revises: e5f1b3c8d462
Create Date: 2026-10-11 12:00:00.000000

Existing rows are filled by `python -m app.cli.backfill_tagscan_csv_comment`
(re-reads the archived CSVs in "Read Tags").
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9c6e1b247'
down_revision: Union[str, Sequence[str], None] = 'e5f1b3c8d462'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_header_data', sa.Column('csv_comment_cell', sa.Text(), nullable=True))
    op.add_column('Tagscan_line_data', sa.Column('csv_comment_cell', sa.Text(), nullable=True))
    op.add_column('Tagscan_rfid_tag', sa.Column('csv_comment_cell', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_rfid_tag', 'csv_comment_cell')
    op.drop_column('Tagscan_line_data', 'csv_comment_cell')
    op.drop_column('Tagscan_header_data', 'csv_comment_cell')
