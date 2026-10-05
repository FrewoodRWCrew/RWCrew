"""add StockMaster (module-4) tables

Revision ID: f2c7a9d4e815
Revises: d4b9e2f7a153
Create Date: 2026-10-05 12:00:00.000000

Module 4 becomes "StockMaster": the warehouse stock of MasterData products,
as free stock (on the product's fixed bin) and loaded in KarTracker's kars.
Adds:
- the four StockMaster_* custom-roles tables (same shape as module 8's)
- StockMaster_reason (seeded with a few common reasons)
- StockMaster_document + StockMaster_movement (the booking ledger)
- StockMaster_balance (current stock per product per place)
- StockMaster_kar_trip (kar departures and returns)
- StockMaster_kar_requirement (what each kar needs per season)
- MasterData_product.stock_return_to and .min_stock
and renames the module-4 tile from "Module 4" to "StockMaster".
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c7a9d4e815'
down_revision: Union[str, Sequence[str], None] = 'd4b9e2f7a153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'StockMaster_screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_screens_key'), 'StockMaster_screens', ['key'], unique=True)

    op.create_table(
        'StockMaster_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_roles_name'), 'StockMaster_roles', ['name'], unique=True)

    op.create_table(
        'StockMaster_role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_create', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['StockMaster_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screen_id'], ['StockMaster_screens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'screen_id', name='uq_stockmaster_role_permissions_role_screen'),
    )

    op.create_table(
        'StockMaster_user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['StockMaster_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    reason_table = op.create_table(
        'StockMaster_reason',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('applies_to', sa.String(length=20), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'StockMaster_document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_number', sa.String(length=30), nullable=False),
        sa.Column('doc_type', sa.String(length=20), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=True),
        sa.Column('kar_nummer', sa.String(length=50), nullable=True),
        sa.Column('from_kar_id', sa.Integer(), nullable=True),
        sa.Column('from_kar_nummer', sa.String(length=50), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('festival_id', sa.Integer(), nullable=True),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('reason_id', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reversal_of_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('tagscan_header_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id']),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['from_kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reason_id'], ['StockMaster_reason.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reversal_of_id'], ['StockMaster_document.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tagscan_header_id'], ['Tagscan_header_data.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_document_doc_number'), 'StockMaster_document', ['doc_number'], unique=True)
    op.create_index(op.f('ix_StockMaster_document_doc_type'), 'StockMaster_document', ['doc_type'], unique=False)
    op.create_index(op.f('ix_StockMaster_document_season_id'), 'StockMaster_document', ['season_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_document_kar_id'), 'StockMaster_document', ['kar_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_document_created_by'), 'StockMaster_document', ['created_by'], unique=False)
    op.create_index(op.f('ix_StockMaster_document_created_at'), 'StockMaster_document', ['created_at'], unique=False)

    op.create_table(
        'StockMaster_movement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('from_bucket', sa.String(length=10), nullable=False),
        sa.Column('from_kar_id', sa.Integer(), nullable=True),
        sa.Column('to_bucket', sa.String(length=10), nullable=False),
        sa.Column('to_kar_id', sa.Integer(), nullable=True),
        sa.Column('bin_snapshot', sa.String(length=255), nullable=True),
        sa.Column('tagscan_line_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['StockMaster_document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id']),
        sa.ForeignKeyConstraint(['from_kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_kar_id'], ['KarTracker_karren.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tagscan_line_id'], ['Tagscan_line_data.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tagscan_line_id'),
    )
    op.create_index(op.f('ix_StockMaster_movement_document_id'), 'StockMaster_movement', ['document_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_movement_product_id'), 'StockMaster_movement', ['product_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_movement_from_kar_id'), 'StockMaster_movement', ['from_kar_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_movement_to_kar_id'), 'StockMaster_movement', ['to_kar_id'], unique=False)

    op.create_table(
        'StockMaster_balance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id']),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_balance_product_id'), 'StockMaster_balance', ['product_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_balance_kar_id'), 'StockMaster_balance', ['kar_id'], unique=False)
    op.create_index(
        'uq_stockmaster_balance_free', 'StockMaster_balance', ['product_id'], unique=True,
        postgresql_where=sa.text('kar_id IS NULL'),
    )
    op.create_index(
        'uq_stockmaster_balance_kar', 'StockMaster_balance', ['product_id', 'kar_id'], unique=True,
        postgresql_where=sa.text('kar_id IS NOT NULL'),
    )

    op.create_table(
        'StockMaster_kar_trip',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('festival_id', sa.Integer(), nullable=True),
        sa.Column('dispatch_document_id', sa.Integer(), nullable=False),
        sa.Column('return_document_id', sa.Integer(), nullable=True),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id']),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dispatch_document_id'], ['StockMaster_document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['return_document_id'], ['StockMaster_document.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_StockMaster_kar_trip_kar_id'), 'StockMaster_kar_trip', ['kar_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_kar_trip_season_id'), 'StockMaster_kar_trip', ['season_id'], unique=False)

    op.create_table(
        'StockMaster_kar_requirement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('kar_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kar_id'], ['KarTracker_karren.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['MasterData_product.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'kar_id', 'product_id', name='uq_stockmaster_kar_requirement'),
    )
    op.create_index(op.f('ix_StockMaster_kar_requirement_season_id'), 'StockMaster_kar_requirement', ['season_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_kar_requirement_kar_id'), 'StockMaster_kar_requirement', ['kar_id'], unique=False)
    op.create_index(op.f('ix_StockMaster_kar_requirement_product_id'), 'StockMaster_kar_requirement', ['product_id'], unique=False)

    op.add_column('MasterData_product', sa.Column('stock_return_to', sa.String(length=10), server_default='kar', nullable=False))
    op.add_column('MasterData_product', sa.Column('min_stock', sa.Integer(), nullable=True))

    seeded_at = datetime.now(timezone.utc)
    op.bulk_insert(
        reason_table,
        [
            {'name': 'Verbruikt', 'applies_to': 'book_out', 'active': True, 'sort_order': 1, 'created_at': seeded_at},
            {'name': 'Defect', 'applies_to': 'book_out', 'active': True, 'sort_order': 2, 'created_at': seeded_at},
            {'name': 'Verloren', 'applies_to': 'book_out', 'active': True, 'sort_order': 3, 'created_at': seeded_at},
            {'name': 'Telverschil', 'applies_to': 'count', 'active': True, 'sort_order': 4, 'created_at': seeded_at},
            {'name': 'Correctie', 'applies_to': None, 'active': True, 'sort_order': 5, 'created_at': seeded_at},
        ],
    )

    op.execute('UPDATE "Landing_modules" SET name = \'StockMaster\' WHERE key = \'module-4\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Module 4\' WHERE key = \'module-4\'')
    op.drop_column('MasterData_product', 'min_stock')
    op.drop_column('MasterData_product', 'stock_return_to')
    op.drop_table('StockMaster_kar_requirement')
    op.drop_table('StockMaster_kar_trip')
    op.drop_index('uq_stockmaster_balance_kar', table_name='StockMaster_balance')
    op.drop_index('uq_stockmaster_balance_free', table_name='StockMaster_balance')
    op.drop_table('StockMaster_balance')
    op.drop_table('StockMaster_movement')
    op.drop_table('StockMaster_document')
    op.drop_table('StockMaster_reason')
    op.drop_table('StockMaster_user_roles')
    op.drop_table('StockMaster_role_permissions')
    op.drop_index(op.f('ix_StockMaster_roles_name'), table_name='StockMaster_roles')
    op.drop_table('StockMaster_roles')
    op.drop_index(op.f('ix_StockMaster_screens_key'), table_name='StockMaster_screens')
    op.drop_table('StockMaster_screens')
