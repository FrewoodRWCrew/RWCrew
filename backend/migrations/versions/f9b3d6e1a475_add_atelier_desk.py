"""add Atelier counter desk (persons, hand-outs) and package quantity 1

Revision ID: f9b3d6e1a475
Revises: e8a2c5d9f364
Create Date: 2026-10-26 10:00:00.000000

Block 4 of the Atelier module: the counter. A person (name + email) picks up
one piece per package article (Atelier_handout + Atelier_handout_line) and
brings it back later. At the desk every package article is 1 piece, so all
existing package lines are set to 1 per person.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9b3d6e1a475'
down_revision: Union[str, Sequence[str], None] = 'e8a2c5d9f364'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'Atelier_person',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('last_team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['last_team_id'], ['MasterData_team.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_person_email'), 'Atelier_person', ['email'], unique=True)
    op.create_table(
        'Atelier_handout',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('stock_document_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id']),
        sa.ForeignKeyConstraint(['person_id'], ['Atelier_person.id']),
        sa.ForeignKeyConstraint(['stock_document_id'], ['Atelier_stock_document.id']),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    for column in ('person_id', 'festival_id', 'team_id', 'day', 'status'):
        op.create_index(op.f(f'ix_Atelier_handout_{column}'), 'Atelier_handout', [column], unique=False)
    op.create_table(
        'Atelier_handout_line',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('handout_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('article_size_id', sa.Integer(), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('return_document_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['Atelier_article.id']),
        sa.ForeignKeyConstraint(['article_size_id'], ['Atelier_article_size.id']),
        sa.ForeignKeyConstraint(['handout_id'], ['Atelier_handout.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['return_document_id'], ['Atelier_stock_document.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_handout_line_handout_id'), 'Atelier_handout_line', ['handout_id'], unique=False)

    # At the desk every package article is 1 piece per person.
    op.execute('UPDATE "Atelier_reservation_line" SET quantity_per_person = 1')


def downgrade() -> None:
    """Downgrade schema (package quantities stay 1)."""
    op.drop_index(op.f('ix_Atelier_handout_line_handout_id'), table_name='Atelier_handout_line')
    op.drop_table('Atelier_handout_line')
    for column in ('status', 'day', 'team_id', 'festival_id', 'person_id'):
        op.drop_index(op.f(f'ix_Atelier_handout_{column}'), table_name='Atelier_handout')
    op.drop_table('Atelier_handout')
    op.drop_index(op.f('ix_Atelier_person_email'), table_name='Atelier_person')
    op.drop_table('Atelier_person')
