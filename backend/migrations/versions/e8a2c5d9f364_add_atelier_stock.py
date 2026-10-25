"""add Atelier stock (documents, movements, balances)

Revision ID: e8a2c5d9f364
Revises: d7f1b4c8e253
Create Date: 2026-10-25 23:00:00.000000

Block 3 of the Atelier module: the clothing the atelier owns, per article
size and status (available, to wash, handed out), booked through documents
with movement lines (receipt, washed, write-off, count, reversal).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8a2c5d9f364'
down_revision: Union[str, Sequence[str], None] = 'd7f1b4c8e253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'Atelier_stock_document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_number', sa.String(length=30), nullable=False),
        sa.Column('doc_type', sa.String(length=20), nullable=False),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.String(length=20), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reversal_of_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reversal_of_id'], ['Atelier_stock_document.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_stock_document_doc_number'), 'Atelier_stock_document', ['doc_number'], unique=True)
    op.create_index(op.f('ix_Atelier_stock_document_doc_type'), 'Atelier_stock_document', ['doc_type'], unique=False)
    op.create_table(
        'Atelier_stock_movement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('article_size_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_size_id'], ['Atelier_article_size.id']),
        sa.ForeignKeyConstraint(['document_id'], ['Atelier_stock_document.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_stock_movement_document_id'), 'Atelier_stock_movement', ['document_id'], unique=False)
    op.create_index(
        op.f('ix_Atelier_stock_movement_article_size_id'), 'Atelier_stock_movement', ['article_size_id'], unique=False
    )
    op.create_table(
        'Atelier_stock_balance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_size_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['article_size_id'], ['Atelier_article_size.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_size_id', 'status', name='uq_atelier_stock_balance'),
    )
    op.create_index(
        op.f('ix_Atelier_stock_balance_article_size_id'), 'Atelier_stock_balance', ['article_size_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_Atelier_stock_balance_article_size_id'), table_name='Atelier_stock_balance')
    op.drop_table('Atelier_stock_balance')
    op.drop_index(op.f('ix_Atelier_stock_movement_article_size_id'), table_name='Atelier_stock_movement')
    op.drop_index(op.f('ix_Atelier_stock_movement_document_id'), table_name='Atelier_stock_movement')
    op.drop_table('Atelier_stock_movement')
    op.drop_index(op.f('ix_Atelier_stock_document_doc_type'), table_name='Atelier_stock_document')
    op.drop_index(op.f('ix_Atelier_stock_document_doc_number'), table_name='Atelier_stock_document')
    op.drop_table('Atelier_stock_document')
