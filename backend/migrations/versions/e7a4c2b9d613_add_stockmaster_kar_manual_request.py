"""add StockMaster_kar_manual_request

Revision ID: e7a4c2b9d613
Revises: d5f2a8c3e917
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a4c2b9d613'
down_revision: Union[str, Sequence[str], None] = 'd5f2a8c3e917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'StockMaster_kar_manual_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'kar_id', 'product_id', name='uq_stockmaster_kar_manual_request'),
    )
    op.create_index(op.f('ix_StockMaster_kar_manual_request_season_id'), 'StockMaster_kar_manual_request', ['season_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_kar_manual_request_kar_id'), 'StockMaster_kar_manual_request', ['kar_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_kar_manual_request_product_id'), 'StockMaster_kar_manual_request', ['product_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_StockMaster_kar_manual_request_product_id'), table_name='StockMaster_kar_manual_request')
    op.drop_index(op.f('ix_StockMaster_kar_manual_request_kar_id'), table_name='StockMaster_kar_manual_request')
    op.drop_index(op.f('ix_StockMaster_kar_manual_request_season_id'), table_name='StockMaster_kar_manual_request')
    op.drop_table('StockMaster_kar_manual_request')
