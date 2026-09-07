"""make intervention request team optional with free text fallback

Revision ID: fdb0f1aaaf02
Revises: 1ee641e811a9
Create Date: 2026-09-07 21:13:03.316032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdb0f1aaaf02'
down_revision: Union[str, Sequence[str], None] = '1ee641e811a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The public (no-login) intervention-request form lets a customer type a
    # Ploeg name that isn't in MasterData_team yet, so team_id can no longer
    # be required — team_name (free text) carries the typed name instead.
    op.alter_column('InterventionRequests_request', 'team_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('InterventionRequests_request', sa.Column('team_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('InterventionRequests_request', 'team_name')
    op.alter_column('InterventionRequests_request', 'team_id', existing_type=sa.Integer(), nullable=False)
