"""Atelier return statuses: why a piece came back with a problem

Revision ID: e3a7c1f5b842
Revises: a4e7c2d9f610
Create Date: 2026-11-01 20:00:00.000000

The list is kept on Atelier's "Masterdata > Retourstatussen" screen (seeded
with two statuses); the desk picks one per piece on Terugbrengen, stored on
the hand-out line (NULL = no remark).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a7c1f5b842'
down_revision: Union[str, Sequence[str], None] = 'a4e7c2d9f610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    statuses = op.create_table(
        'Atelier_return_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.bulk_insert(statuses, [{'name': 'Beschadigd', 'active': True}, {'name': 'Zeer vuil', 'active': True}])
    op.add_column('Atelier_handout_line', sa.Column('return_status_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_atelier_handout_line_return_status',
        'Atelier_handout_line',
        'Atelier_return_status',
        ['return_status_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_atelier_handout_line_return_status', 'Atelier_handout_line', type_='foreignkey')
    op.drop_column('Atelier_handout_line', 'return_status_id')
    op.drop_table('Atelier_return_status')
