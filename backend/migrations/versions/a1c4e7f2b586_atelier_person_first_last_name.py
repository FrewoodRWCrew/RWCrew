"""Atelier person: first name + family name as the key, email not unique, bracelet number

Revision ID: a1c4e7f2b586
Revises: f9b3d6e1a475
Create Date: 2026-10-26 12:00:00.000000

At the counter a person is now typed as first name, family name, then email.
The combination of first and family name (without case and extra spaces) is
the unique key; the email is still required but no longer unique. Existing
names are split on their first space (no space = everything is the first name
and the family name is left empty). New: an optional, unique bracelet number
(the festival personal number on the future wristband).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7f2b586'
down_revision: Union[str, Sequence[str], None] = 'f9b3d6e1a475'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _key(first: str, last: str) -> str:
    """The same key as module_5/desk_service.name_key."""
    return f"{' '.join(first.lower().split())}|{' '.join(last.lower().split())}"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Atelier_person', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('Atelier_person', sa.Column('last_name', sa.String(length=255), nullable=True))
    op.add_column('Atelier_person', sa.Column('name_key', sa.String(length=511), nullable=True))

    bind = op.get_bind()
    for person_id, name in bind.execute(sa.text('SELECT id, name FROM "Atelier_person"')).all():
        first, _space, last = (name or "").strip().partition(" ")
        bind.execute(
            sa.text('UPDATE "Atelier_person" SET first_name = :first, last_name = :last, name_key = :key WHERE id = :id'),
            {"first": first, "last": last.strip(), "key": f"{_key(first, last)}#{person_id}", "id": person_id},
        )
    # The id suffix above keeps old duplicates apart; drop it where the plain key is free.
    bind.execute(sa.text(
        '''UPDATE "Atelier_person" p SET name_key = split_part(name_key, '#', 1)
           WHERE NOT EXISTS (
               SELECT 1 FROM "Atelier_person" o
               WHERE o.id < p.id AND split_part(o.name_key, '#', 1) = split_part(p.name_key, '#', 1)
           )'''
    ))

    op.alter_column('Atelier_person', 'first_name', nullable=False)
    op.alter_column('Atelier_person', 'last_name', nullable=False)
    op.alter_column('Atelier_person', 'name_key', nullable=False)
    op.create_index(op.f('ix_Atelier_person_name_key'), 'Atelier_person', ['name_key'], unique=True)
    op.drop_index(op.f('ix_Atelier_person_email'), table_name='Atelier_person')
    op.create_index(op.f('ix_Atelier_person_email'), 'Atelier_person', ['email'], unique=False)
    op.drop_column('Atelier_person', 'name')
    op.add_column('Atelier_person', sa.Column('bracelet_number', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_Atelier_person_bracelet_number'), 'Atelier_person', ['bracelet_number'], unique=True)


def downgrade() -> None:
    """Downgrade schema (fails if two persons share an email)."""
    op.drop_index(op.f('ix_Atelier_person_bracelet_number'), table_name='Atelier_person')
    op.drop_column('Atelier_person', 'bracelet_number')
    op.add_column('Atelier_person', sa.Column('name', sa.String(length=255), nullable=True))
    op.execute('UPDATE "Atelier_person" SET name = trim(first_name || \' \' || last_name)')
    op.alter_column('Atelier_person', 'name', nullable=False)
    op.drop_index(op.f('ix_Atelier_person_email'), table_name='Atelier_person')
    op.create_index(op.f('ix_Atelier_person_email'), 'Atelier_person', ['email'], unique=True)
    op.drop_index(op.f('ix_Atelier_person_name_key'), table_name='Atelier_person')
    op.drop_column('Atelier_person', 'name_key')
    op.drop_column('Atelier_person', 'last_name')
    op.drop_column('Atelier_person', 'first_name')
