"""add Altsien Select (module-8) tables

Revision ID: e7a4c2b19f53
Revises: d9f3b2a7c416
Create Date: 2026-09-26 00:00:00.000000

Module 8 becomes "Altsien Select": a Ploeg Wizard in which Altsien
Kernleden make their per-team choices for a season. Adds:
- MasterData_team_festival (at which festivals a team is active per season)
- the four AltsienSelect_* custom-roles tables (same shape as module 3's)
- AltsienSelect_step_progress (which wizard steps are done)
- AltsienSelect_request_status (seeded New / In Progress / Completed)
- AltsienSelect_special_requests
and renames the module-8 tile from "Module 8" to "Altsien Select".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a4c2b19f53'
down_revision: Union[str, Sequence[str], None] = 'd9f3b2a7c416'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'MasterData_team_festival',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'team_id', 'festival_id', name='uq_masterdata_team_festival'),
    )

    op.create_table(
        'AltsienSelect_screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_AltsienSelect_screens_key'), 'AltsienSelect_screens', ['key'], unique=True)

    op.create_table(
        'AltsienSelect_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_AltsienSelect_roles_name'), 'AltsienSelect_roles', ['name'], unique=True)

    op.create_table(
        'AltsienSelect_role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_create', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['AltsienSelect_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screen_id'], ['AltsienSelect_screens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'screen_id', name='uq_altsienselect_role_permissions_role_screen'),
    )

    op.create_table(
        'AltsienSelect_user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['AltsienSelect_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table(
        'AltsienSelect_step_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('step_key', sa.String(length=100), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'team_id', 'step_key', name='uq_altsienselect_step_progress'),
    )

    request_status = op.create_table(
        'AltsienSelect_request_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_open', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('color', sa.String(length=20), server_default=sa.text("'gray'"), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_AltsienSelect_request_status_name'), 'AltsienSelect_request_status', ['name'], unique=True
    )
    op.bulk_insert(
        request_status,
        [
            {'name': 'New', 'is_open': True, 'color': 'blue', 'sort_order': 1},
            {'name': 'In Progress', 'is_open': True, 'color': 'amber', 'sort_order': 2},
            {'name': 'Completed', 'is_open': False, 'color': 'green', 'sort_order': 3},
        ],
    )

    op.create_table(
        'AltsienSelect_special_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('organisation_note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['Landing_users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['status_id'], ['AltsienSelect_request_status.id']),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.execute('UPDATE "Landing_modules" SET name = \'Altsien Select\' WHERE key = \'module-8\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE "Landing_modules" SET name = \'Module 8\' WHERE key = \'module-8\'')
    op.drop_table('AltsienSelect_special_requests')
    op.drop_index(op.f('ix_AltsienSelect_request_status_name'), table_name='AltsienSelect_request_status')
    op.drop_table('AltsienSelect_request_status')
    op.drop_table('AltsienSelect_step_progress')
    op.drop_table('AltsienSelect_user_roles')
    op.drop_table('AltsienSelect_role_permissions')
    op.drop_index(op.f('ix_AltsienSelect_roles_name'), table_name='AltsienSelect_roles')
    op.drop_table('AltsienSelect_roles')
    op.drop_index(op.f('ix_AltsienSelect_screens_key'), table_name='AltsienSelect_screens')
    op.drop_table('AltsienSelect_screens')
    op.drop_table('MasterData_team_festival')
