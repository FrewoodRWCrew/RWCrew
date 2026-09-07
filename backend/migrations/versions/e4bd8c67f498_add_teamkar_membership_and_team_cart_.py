"""add teamkar membership table, replace team_cart free text with a user fk

Revision ID: e4bd8c67f498
Revises: 360c7915525e
Create Date: 2026-09-07 17:51:05.270908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4bd8c67f498'
down_revision: Union[str, Sequence[str], None] = '360c7915525e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('InterventionRequests_teamkar_member',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['Landing_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )

    # The old free-text "Team Kar" values can't be mapped onto real users,
    # so they're intentionally dropped here — same tradeoff already made by
    # 360c7915525e for "association_name" (this only ever runs against this
    # app's own dev data).
    op.add_column('InterventionRequests_request', sa.Column('team_cart_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'InterventionRequests_request', 'Landing_users', ['team_cart_user_id'], ['id'], ondelete='SET NULL')
    op.drop_column('InterventionRequests_request', 'team_cart')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('InterventionRequests_request', sa.Column('team_cart', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'InterventionRequests_request', type_='foreignkey')
    op.drop_column('InterventionRequests_request', 'team_cart_user_id')
    op.drop_table('InterventionRequests_teamkar_member')
