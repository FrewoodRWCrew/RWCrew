"""add intervention requests mailing recipient

Revision ID: b7d3e91a4c20
Revises: 33e7cc110bc7
Create Date: 2026-09-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3e91a4c20'
down_revision: Union[str, Sequence[str], None] = '33e7cc110bc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('InterventionRequests_mailing_recipient',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_InterventionRequests_mailing_recipient_email'), 'InterventionRequests_mailing_recipient', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_InterventionRequests_mailing_recipient_email'), table_name='InterventionRequests_mailing_recipient')
    op.drop_table('InterventionRequests_mailing_recipient')
