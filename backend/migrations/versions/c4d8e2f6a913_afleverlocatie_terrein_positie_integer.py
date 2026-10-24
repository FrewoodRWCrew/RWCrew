"""afleverlocatie terrein_positie becomes the delivery-tour position (integer)

Revision ID: c4d8e2f6a913
Revises: b8e4d2a6c913
Create Date: 2026-10-24 12:00:00.000000

KarTracker_afleverlocaties.terrein_positie was free text; it now holds the
location's position in the delivery tour (1, 2, 3, ...), set on the new
"Leveringsvolgorde" screen. Values that already are a plain whole number are
kept, every other text becomes NULL (= not yet in the tour).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e2f6a913'
down_revision: Union[str, Sequence[str], None] = 'b8e4d2a6c913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'KarTracker_afleverlocaties',
        'terrein_positie',
        existing_type=sa.String(length=255),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using=(
            "CASE WHEN trim(terrein_positie) ~ '^[0-9]{1,9}$' "
            "AND trim(terrein_positie)::integer > 0 "
            "THEN trim(terrein_positie)::integer END"
        ),
    )
    op.create_index(
        op.f('ix_KarTracker_afleverlocaties_terrein_positie'),
        'KarTracker_afleverlocaties',
        ['terrein_positie'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_KarTracker_afleverlocaties_terrein_positie'), table_name='KarTracker_afleverlocaties')
    op.alter_column(
        'KarTracker_afleverlocaties',
        'terrein_positie',
        existing_type=sa.Integer(),
        type_=sa.String(length=255),
        existing_nullable=True,
        postgresql_using='terrein_positie::varchar',
    )
