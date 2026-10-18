"""add Atelier (module-5) and Walkies (module-6) shells

Revision ID: b8e4d2a6c913
Revises: a3c9e5f1b708
Create Date: 2026-10-18 12:00:00.000000

Module 5 becomes "Atelier" (hand-out and return of festival clothing) and
module 6 becomes "Walkies" (the festival's walkie-talkies). For now both are
only a shell: each gets the four custom-roles tables (same shape as
StockMaster's), and their tiles are renamed from "Module 5" / "Module 6".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4d2a6c913'
down_revision: Union[str, Sequence[str], None] = 'a3c9e5f1b708'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Atelier: the four custom-roles tables ---
    op.create_table(
        'Atelier_screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_screens_key'), 'Atelier_screens', ['key'], unique=True)

    op.create_table(
        'Atelier_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_roles_name'), 'Atelier_roles', ['name'], unique=True)

    op.create_table(
        'Atelier_role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_create', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['Atelier_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screen_id'], ['Atelier_screens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'screen_id', name='uq_atelier_role_permissions_role_screen'),
    )

    op.create_table(
        'Atelier_user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['Atelier_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # --- Walkies: the four custom-roles tables ---
    op.create_table(
        'Walkies_screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Walkies_screens_key'), 'Walkies_screens', ['key'], unique=True)

    op.create_table(
        'Walkies_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Walkies_roles_name'), 'Walkies_roles', ['name'], unique=True)

    op.create_table(
        'Walkies_role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_create', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['Walkies_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screen_id'], ['Walkies_screens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'screen_id', name='uq_walkies_role_permissions_role_screen'),
    )

    op.create_table(
        'Walkies_user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['Walkies_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.execute("UPDATE \"Landing_modules\" SET name = 'Atelier' WHERE key = 'module-5'")
    op.execute("UPDATE \"Landing_modules\" SET name = 'Walkies' WHERE key = 'module-6'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE \"Landing_modules\" SET name = 'Module 6' WHERE key = 'module-6'")
    op.execute("UPDATE \"Landing_modules\" SET name = 'Module 5' WHERE key = 'module-5'")
    op.drop_table('Walkies_user_roles')
    op.drop_table('Walkies_role_permissions')
    op.drop_index(op.f('ix_Walkies_roles_name'), table_name='Walkies_roles')
    op.drop_table('Walkies_roles')
    op.drop_index(op.f('ix_Walkies_screens_key'), table_name='Walkies_screens')
    op.drop_table('Walkies_screens')
    op.drop_table('Atelier_user_roles')
    op.drop_table('Atelier_role_permissions')
    op.drop_index(op.f('ix_Atelier_roles_name'), table_name='Atelier_roles')
    op.drop_table('Atelier_roles')
    op.drop_index(op.f('ix_Atelier_screens_key'), table_name='Atelier_screens')
    op.drop_table('Atelier_screens')
