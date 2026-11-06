"""Atelier tag trace: the EPC and source of every hand-out and return

Revision ID: c7f3a1e8d295
Revises: b6e2d9f4a817
Create Date: 2026-11-06 10:00:00.000000

A hand-out line keeps the EPC of the piece that went out (a fixed reference,
also when the tag is later deleted or linked to another piece in TagScan) and
the tag read when it came back. A pick-up and a return remember where they
were booked: "web" (the website's desk) or "pi" (RWCrew Pi). Existing lines
with a tag get their EPC copied.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f3a1e8d295'
down_revision: Union[str, Sequence[str], None] = 'b6e2d9f4a817'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Atelier_handout', sa.Column('source', sa.String(length=10), server_default='web', nullable=False))
    op.add_column('Atelier_handout_line', sa.Column('handout_epc', sa.String(length=255), nullable=True))
    op.add_column('Atelier_handout_line', sa.Column('return_rfid_tag_id', sa.Integer(), nullable=True))
    op.add_column('Atelier_handout_line', sa.Column('return_epc', sa.String(length=255), nullable=True))
    op.add_column('Atelier_handout_line', sa.Column('return_source', sa.String(length=10), nullable=True))
    op.create_index(op.f('ix_Atelier_handout_line_handout_epc'), 'Atelier_handout_line', ['handout_epc'], unique=False)
    op.create_index(op.f('ix_Atelier_handout_line_return_epc'), 'Atelier_handout_line', ['return_epc'], unique=False)
    op.create_foreign_key(
        'Atelier_handout_line_return_rfid_tag_id_fkey',
        'Atelier_handout_line',
        'Tagscan_rfid_tag',
        ['return_rfid_tag_id'],
        ['id'],
        ondelete='SET NULL',
    )
    # The lines that already went out by tag keep that tag's EPC.
    op.execute(
        'UPDATE "Atelier_handout_line" SET handout_epc = '
        '(SELECT epc_uid FROM "Tagscan_rfid_tag" t WHERE t.id = "Atelier_handout_line".rfid_tag_id) '
        'WHERE rfid_tag_id IS NOT NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('Atelier_handout_line_return_rfid_tag_id_fkey', 'Atelier_handout_line', type_='foreignkey')
    op.drop_index(op.f('ix_Atelier_handout_line_return_epc'), table_name='Atelier_handout_line')
    op.drop_index(op.f('ix_Atelier_handout_line_handout_epc'), table_name='Atelier_handout_line')
    op.drop_column('Atelier_handout_line', 'return_source')
    op.drop_column('Atelier_handout_line', 'return_epc')
    op.drop_column('Atelier_handout_line', 'return_rfid_tag_id')
    op.drop_column('Atelier_handout_line', 'handout_epc')
    op.drop_column('Atelier_handout', 'source')
