"""link RFID tags to Atelier pieces (Raspberry Pi desk)

Revision ID: b6e2d9f4a817
Revises: e5a1c7d3f486
Create Date: 2026-11-05 10:00:00.000000

An RFID tag sewn into a clothing piece says which Atelier article size it is
(Tagscan_rfid_tag.atelier_article_size_id), and a hand-out line remembers which
physical piece went out (Atelier_handout_line.rfid_tag_id). Both optional:
pieces without a tag keep working as before.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6e2d9f4a817'
down_revision: Union[str, Sequence[str], None] = 'e5a1c7d3f486'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Tagscan_rfid_tag', sa.Column('atelier_article_size_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_Tagscan_rfid_tag_atelier_article_size_id'), 'Tagscan_rfid_tag', ['atelier_article_size_id'], unique=False
    )
    op.create_foreign_key(
        'Tagscan_rfid_tag_atelier_article_size_id_fkey',
        'Tagscan_rfid_tag',
        'Atelier_article_size',
        ['atelier_article_size_id'],
        ['id'],
    )
    op.add_column('Atelier_handout_line', sa.Column('rfid_tag_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_Atelier_handout_line_rfid_tag_id'), 'Atelier_handout_line', ['rfid_tag_id'], unique=False)
    op.create_foreign_key(
        'Atelier_handout_line_rfid_tag_id_fkey',
        'Atelier_handout_line',
        'Tagscan_rfid_tag',
        ['rfid_tag_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('Atelier_handout_line_rfid_tag_id_fkey', 'Atelier_handout_line', type_='foreignkey')
    op.drop_index(op.f('ix_Atelier_handout_line_rfid_tag_id'), table_name='Atelier_handout_line')
    op.drop_column('Atelier_handout_line', 'rfid_tag_id')
    op.drop_constraint('Tagscan_rfid_tag_atelier_article_size_id_fkey', 'Tagscan_rfid_tag', type_='foreignkey')
    op.drop_index(op.f('ix_Tagscan_rfid_tag_atelier_article_size_id'), table_name='Tagscan_rfid_tag')
    op.drop_column('Tagscan_rfid_tag', 'atelier_article_size_id')
