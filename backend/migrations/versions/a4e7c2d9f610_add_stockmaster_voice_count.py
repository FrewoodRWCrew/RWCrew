"""StockMaster voice counts: a kar counted by voice on the phone

Revision ID: a4e7c2d9f610
Revises: c8e2a5f1d394
Create Date: 2026-10-28 12:00:00.000000

The phone's "Spraaktelling" (scan a kar, Ophalen/Terugbrengen, say what is
there) saves a count + its product lines. Phase 1 only stores them; booking
them into stock comes later (document_id).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4e7c2d9f610'
down_revision: Union[str, Sequence[str], None] = 'c8e2a5f1d394'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'StockMaster_voice_count',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=True),
        sa.Column('kar_nummer', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancelled_by_name', sa.String(length=255), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id']),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['StockMaster_document.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_voice_count_season_id'), 'StockMaster_voice_count', ['season_id'])
    op.create_index(op.f('ix_StockMaster_voice_count_kar_id'), 'StockMaster_voice_count', ['kar_id'])
    op.create_index(op.f('ix_StockMaster_voice_count_status'), 'StockMaster_voice_count', ['status'])

    op.create_table(
        'StockMaster_voice_count_line',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('voice_count_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('spoken_text', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['voice_count_id'], ['StockMaster_voice_count.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('voice_count_id', 'product_id', name='uq_stockmaster_voice_count_line_product'),
    )
    op.create_index(
        op.f('ix_StockMaster_voice_count_line_voice_count_id'), 'StockMaster_voice_count_line', ['voice_count_id']
    )
    op.create_index(
        op.f('ix_StockMaster_voice_count_line_product_id'), 'StockMaster_voice_count_line', ['product_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_StockMaster_voice_count_line_product_id'), table_name='StockMaster_voice_count_line')
    op.drop_index(op.f('ix_StockMaster_voice_count_line_voice_count_id'), table_name='StockMaster_voice_count_line')
    op.drop_table('StockMaster_voice_count_line')
    op.drop_index(op.f('ix_StockMaster_voice_count_status'), table_name='StockMaster_voice_count')
    op.drop_index(op.f('ix_StockMaster_voice_count_kar_id'), table_name='StockMaster_voice_count')
    op.drop_index(op.f('ix_StockMaster_voice_count_season_id'), table_name='StockMaster_voice_count')
    op.drop_table('StockMaster_voice_count')
