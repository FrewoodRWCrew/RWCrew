"""add masterdata module and relocate season

Revision ID: ad20428b51cd
Revises: 7e11500f338f
Create Date: 2026-08-30 21:38:16.569067

Turns module-9 into "MasterData": creates its custom-roles-with-per-screen-
permissions tables (same shape as TagScan's Tagscan_* tables), moves the
existing "Season" screen into it by renaming landing_md_season to
MasterData_season (data preserved, NOT dropped/recreated), renames the
module's display name, and grants every existing super admin access to
module-9 so nobody loses access to Season now that it requires normal
module access instead of a flat "super admin only" check.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad20428b51cd'
down_revision: Union[str, Sequence[str], None] = '7e11500f338f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('MasterData_roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_MasterData_roles_name'), 'MasterData_roles', ['name'], unique=True)
    op.create_table('MasterData_screens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_MasterData_screens_key'), 'MasterData_screens', ['key'], unique=True)
    op.create_table('MasterData_role_permissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('screen_id', sa.Integer(), nullable=False),
    sa.Column('can_view', sa.Boolean(), nullable=False),
    sa.Column('can_create', sa.Boolean(), nullable=False),
    sa.Column('can_edit', sa.Boolean(), nullable=False),
    sa.Column('can_delete', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['MasterData_roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['screen_id'], ['MasterData_screens.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('role_id', 'screen_id', name='uq_masterdata_role_permissions_role_screen')
    )
    op.create_table('MasterData_user_roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['MasterData_roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )

    # Move Season into MasterData: rename, don't drop/recreate, so the
    # existing seasons (2026-2029) survive untouched.
    op.rename_table('landing_md_season', 'MasterData_season')
    op.execute('ALTER INDEX ix_landing_md_season_name RENAME TO "ix_MasterData_season_name"')

    # Module 9 has real functionality now — rename its tile from the
    # generic placeholder name to "MasterData".
    op.execute('UPDATE "Landing_modules" SET name = \'MasterData\' WHERE key = \'module-9\'')

    # Season used to be reachable by every super admin unconditionally
    # (a flat is_super_admin check). Now it's a MasterData screen like any
    # other, which requires normal module access first. Grant that access
    # to every existing super admin so nobody is locked out by this move.
    op.execute(
        'INSERT INTO "Landing_user_module_access" (user_id, module_id, granted_at) '
        'SELECT u.id, m.id, now() FROM "Landing_users" u, "Landing_modules" m '
        'WHERE u.is_super_admin = true AND m.key = \'module-9\' '
        'AND NOT EXISTS ('
        '  SELECT 1 FROM "Landing_user_module_access" existing '
        '  WHERE existing.user_id = u.id AND existing.module_id = m.id'
        ')'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        'DELETE FROM "Landing_user_module_access" '
        'WHERE module_id = (SELECT id FROM "Landing_modules" WHERE key = \'module-9\') '
        'AND user_id IN (SELECT id FROM "Landing_users" WHERE is_super_admin = true)'
    )
    op.execute('UPDATE "Landing_modules" SET name = \'Module 9\' WHERE key = \'module-9\'')

    op.execute('ALTER INDEX "ix_MasterData_season_name" RENAME TO ix_landing_md_season_name')
    op.rename_table('MasterData_season', 'landing_md_season')

    op.drop_table('MasterData_user_roles')
    op.drop_table('MasterData_role_permissions')
    op.drop_index(op.f('ix_MasterData_screens_key'), table_name='MasterData_screens')
    op.drop_table('MasterData_screens')
    op.drop_index(op.f('ix_MasterData_roles_name'), table_name='MasterData_roles')
    op.drop_table('MasterData_roles')
