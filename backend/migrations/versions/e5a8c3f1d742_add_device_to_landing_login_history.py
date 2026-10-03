"""add device type and user agent to landing login history

Revision ID: e5a8c3f1d742
Revises: c4f7a2d9e815
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a8c3f1d742'
down_revision: Union[str, Sequence[str], None] = 'c4f7a2d9e815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Landing_login_history', sa.Column('device_type', sa.String(length=16), nullable=True))
    op.add_column('Landing_login_history', sa.Column('user_agent', sa.String(length=512), nullable=True))
    # Logins from the former native smartphone app (source "mobile") were by
    # definition made on a phone; every other existing row stays unknown.
    op.execute('UPDATE "Landing_login_history" SET device_type = \'mobile\' WHERE source = \'mobile\'')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Landing_login_history', 'user_agent')
    op.drop_column('Landing_login_history', 'device_type')
