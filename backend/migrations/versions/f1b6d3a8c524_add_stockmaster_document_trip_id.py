"""add trip_id to StockMaster_document (deliveries to a kar that's out)

Revision ID: f1b6d3a8c524
Revises: e7a4c2b9d613
Create Date: 2026-10-17 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1b6d3a8c524'
down_revision: Union[str, Sequence[str], None] = 'e7a4c2b9d613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('StockMaster_document', sa.Column('trip_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_StockMaster_document_trip_id'), 'StockMaster_document', ['trip_id'], unique=False)
    op.create_foreign_key(
        'fk_StockMaster_document_trip_id', 'StockMaster_document', 'StockMaster_kar_trip',
        ['trip_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_StockMaster_document_trip_id', 'StockMaster_document', type_='foreignkey')
    op.drop_index(op.f('ix_StockMaster_document_trip_id'), table_name='StockMaster_document')
    op.drop_column('StockMaster_document', 'trip_id')
