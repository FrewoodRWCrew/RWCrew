"""StockMaster tag places: the last known place of every product tag

Revision ID: a3d8f6c2e914
Revises: e5b9c3d7a428
Create Date: 2026-11-09 21:04:41.509548

The RWCrew Pi books StockMaster stock live with RFID tags. Every product tag
gets its last known place (free / kar / out on a trip / written off; NULL =
unknown) and every tag a Pi booking moves gets a StockMaster_movement_tag row
(the trace, and what a reversal needs). No backfill: every existing tag starts
as unknown.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d8f6c2e914'
down_revision: Union[str, Sequence[str], None] = 'e5b9c3d7a428'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('StockMaster_movement_tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('movement_id', sa.Integer(), nullable=True),
    sa.Column('rfid_tag_id', sa.Integer(), nullable=True),
    sa.Column('epc', sa.String(length=255), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=True),
    sa.Column('from_place', sa.String(length=12), nullable=True),
    sa.Column('from_kar_id', sa.Integer(), nullable=True),
    sa.Column('from_trip_id', sa.Integer(), nullable=True),
    sa.Column('from_document_id', sa.Integer(), nullable=True),
    sa.Column('to_place', sa.String(length=12), nullable=True),
    sa.Column('to_kar_id', sa.Integer(), nullable=True),
    sa.Column('to_trip_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['StockMaster_document.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['from_document_id'], ['StockMaster_document.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['from_kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['from_trip_id'], ['StockMaster_kar_trip.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['movement_id'], ['StockMaster_movement.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['rfid_tag_id'], ['Tagscan_rfid_tag.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['to_kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['to_trip_id'], ['StockMaster_kar_trip.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_StockMaster_movement_tag_document_id'), 'StockMaster_movement_tag', ['document_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_movement_tag_epc'), 'StockMaster_movement_tag', ['epc'], unique=False)
    op.create_index(op.f('ix_StockMaster_movement_tag_rfid_tag_id'), 'StockMaster_movement_tag', ['rfid_tag_id'], unique=False)
    op.add_column('Tagscan_rfid_tag', sa.Column('stock_place', sa.String(length=12), nullable=True))
    op.add_column('Tagscan_rfid_tag', sa.Column('stock_kar_id', sa.Integer(), nullable=True))
    op.add_column('Tagscan_rfid_tag', sa.Column('stock_trip_id', sa.Integer(), nullable=True))
    op.add_column('Tagscan_rfid_tag', sa.Column('stock_document_id', sa.Integer(), nullable=True))
    op.add_column('Tagscan_rfid_tag', sa.Column('stock_place_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_Tagscan_rfid_tag_stock_kar_id'), 'Tagscan_rfid_tag', ['stock_kar_id'], unique=False)
    op.create_foreign_key('Tagscan_rfid_tag_stock_kar_id_fkey', 'Tagscan_rfid_tag', 'KarTracker_karren', ['stock_kar_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('Tagscan_rfid_tag_stock_trip_id_fkey', 'Tagscan_rfid_tag', 'StockMaster_kar_trip', ['stock_trip_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('Tagscan_rfid_tag_stock_document_id_fkey', 'Tagscan_rfid_tag', 'StockMaster_document', ['stock_document_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('Tagscan_rfid_tag_stock_document_id_fkey', 'Tagscan_rfid_tag', type_='foreignkey')
    op.drop_constraint('Tagscan_rfid_tag_stock_trip_id_fkey', 'Tagscan_rfid_tag', type_='foreignkey')
    op.drop_constraint('Tagscan_rfid_tag_stock_kar_id_fkey', 'Tagscan_rfid_tag', type_='foreignkey')
    op.drop_index(op.f('ix_Tagscan_rfid_tag_stock_kar_id'), table_name='Tagscan_rfid_tag')
    op.drop_column('Tagscan_rfid_tag', 'stock_place_at')
    op.drop_column('Tagscan_rfid_tag', 'stock_document_id')
    op.drop_column('Tagscan_rfid_tag', 'stock_trip_id')
    op.drop_column('Tagscan_rfid_tag', 'stock_kar_id')
    op.drop_column('Tagscan_rfid_tag', 'stock_place')
    op.drop_index(op.f('ix_StockMaster_movement_tag_rfid_tag_id'), table_name='StockMaster_movement_tag')
    op.drop_index(op.f('ix_StockMaster_movement_tag_epc'), table_name='StockMaster_movement_tag')
    op.drop_index(op.f('ix_StockMaster_movement_tag_document_id'), table_name='StockMaster_movement_tag')
    op.drop_table('StockMaster_movement_tag')
