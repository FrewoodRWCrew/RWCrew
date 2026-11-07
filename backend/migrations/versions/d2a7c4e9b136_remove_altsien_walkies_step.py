"""remove Altsien Select's "walkies" wizard step progress

Revision ID: d2a7c4e9b136
Revises: c7f3a1e8d295
Create Date: 2026-11-07

Walkie-talkies are not managed in Altsien Select (decided 2026-11-07), so the
placeholder step "walkies" was removed from module_8/steps.py. Its stored
"done" rows would otherwise keep counting in progress overviews.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd2a7c4e9b136'
down_revision = 'c7f3a1e8d295'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM \"AltsienSelect_step_progress\" WHERE step_key = 'walkies'")


def downgrade() -> None:
    # The deleted progress rows can't be restored; nothing to do.
    pass
