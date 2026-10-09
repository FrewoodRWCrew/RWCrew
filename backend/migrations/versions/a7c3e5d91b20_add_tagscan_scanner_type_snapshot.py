"""add tagscan scanner type snapshot

Revision ID: a7c3e5d91b20
Revises: f2c7a9d4e815
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e5d91b20'
down_revision: Union[str, Sequence[str], None] = 'f2c7a9d4e815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_header_data', sa.Column('scanner_type', sa.String(length=255), nullable=True))
    op.add_column('Tagscan_line_data', sa.Column('scanner_type', sa.String(length=255), nullable=True))

    # Backfill: existing rows matched to a scanner get that scanner's Type name.
    for table in ('Tagscan_header_data', 'Tagscan_line_data'):
        op.execute(
            f'''
            UPDATE "{table}" SET scanner_type = (
                SELECT pt.name FROM "Tagscan_scanners" s
                JOIN "MasterData_product_type" pt ON pt.id = s.type_id
                WHERE s.id = "{table}".scanner_id
            )
            WHERE scanner_id IS NOT NULL
            '''
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Tagscan_line_data', 'scanner_type')
    op.drop_column('Tagscan_header_data', 'scanner_type')
