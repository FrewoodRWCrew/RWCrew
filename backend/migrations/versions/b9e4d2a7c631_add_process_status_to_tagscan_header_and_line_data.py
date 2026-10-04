"""add process status and comment to tagscan header and line data

Revision ID: b9e4d2a7c631
Revises: a7d3e9b2c418
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9e4d2a7c631'
down_revision: Union[str, Sequence[str], None] = 'a7d3e9b2c418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('Tagscan_header_data', 'Tagscan_line_data')


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.add_column(table, sa.Column('process_status', sa.String(length=20), server_default='new', nullable=False))
        op.add_column(table, sa.Column('process_comment', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f(f'ix_{table}_process_status'), table, ['process_status'], unique=False)
        # Everything logged before processing existed counts as handled, so
        # only CSVs scanned from now on show up as "awaiting".
        op.execute(
            f'UPDATE "{table}" SET process_status = \'loaded\', '
            f'process_comment = \'Existing before processing was introduced\''
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.drop_index(op.f(f'ix_{table}_process_status'), table_name=table)
        op.drop_column(table, 'processed_at')
        op.drop_column(table, 'process_comment')
        op.drop_column(table, 'process_status')
