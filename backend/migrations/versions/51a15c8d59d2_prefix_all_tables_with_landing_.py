"""prefix all tables with Landing_

Revision ID: 51a15c8d59d2
Revises: dfaa6f259861
Create Date: 2026-08-29 20:57:42.224734

Renames every existing table to add a "Landing_" prefix (e.g. "users" ->
"Landing_users"), at the user's request. This uses ALTER TABLE ... RENAME
TO, which keeps all existing data and foreign keys intact — Postgres
tracks tables internally by an id, not by name, so a rename is always
safe and instant, unlike dropping and recreating the tables would be.

It also renames the three indexes SQLAlchemy auto-named after their old
table (e.g. "ix_users_email"), since our models otherwise expect those
indexes to be named after the NEW table name (e.g. "ix_Landing_users_email")
— without this, "alembic check" reports a mismatch even though the app
itself works fine either way. Explicitly-named constraints (e.g.
"uq_module_roles_user_module") don't need renaming, since their names
never depended on the table name in the first place.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '51a15c8d59d2'
down_revision: Union[str, Sequence[str], None] = 'dfaa6f259861'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The old -> new name for every table, reused by both upgrade and downgrade.
TABLE_RENAMES = [
    ("users", "Landing_users"),
    ("modules", "Landing_modules"),
    ("module_roles", "Landing_module_roles"),
    ("user_module_access", "Landing_user_module_access"),
    ("refresh_tokens", "Landing_refresh_tokens"),
]

# The old -> new name for the indexes SQLAlchemy auto-named after their
# table (one per unique, indexed column: Module.key, RefreshToken.token_hash,
# User.email).
INDEX_RENAMES = [
    ("ix_modules_key", "ix_Landing_modules_key"),
    ("ix_refresh_tokens_token_hash", "ix_Landing_refresh_tokens_token_hash"),
    ("ix_users_email", "ix_Landing_users_email"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for old_name, new_name in TABLE_RENAMES:
        op.rename_table(old_name, new_name)
    for old_name, new_name in INDEX_RENAMES:
        op.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')


def downgrade() -> None:
    """Downgrade schema."""
    for old_name, new_name in INDEX_RENAMES:
        op.execute(f'ALTER INDEX "{new_name}" RENAME TO "{old_name}"')
    for old_name, new_name in TABLE_RENAMES:
        op.rename_table(new_name, old_name)
