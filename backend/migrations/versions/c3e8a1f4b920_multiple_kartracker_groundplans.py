"""multiple kartracker groundplans

Revision ID: c3e8a1f4b920
Revises: b7d2e4f6a801
Create Date: 2026-09-25 10:00:00.000000

Turns KarTracker_groundplan from a single settings row (id=1) into a list
of ground plans, each with its own name. The existing plan (if any) is kept
and named "Grondplan"; a half-configured row (no image or missing corner
coordinates) is dropped, because every plan now needs both.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e8a1f4b920'
down_revision: Union[str, Sequence[str], None] = 'b7d2e4f6a801'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REQUIRED_COLUMNS = ['image_data', 'image_content_type', 'sw_latitude', 'sw_longitude', 'ne_latitude', 'ne_longitude']


def upgrade() -> None:
    """Upgrade schema."""
    # Give the existing plan a name via a temporary default, then drop the
    # default again so new plans must always supply their own name.
    with op.batch_alter_table('KarTracker_groundplan') as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=100), nullable=False, server_default='Grondplan'))
    with op.batch_alter_table('KarTracker_groundplan') as batch_op:
        batch_op.alter_column('name', server_default=None)

    # A row without an image or without all four corners can't be shown on
    # the map anyway — remove it so the columns can become required.
    op.execute(
        'DELETE FROM "KarTracker_groundplan" WHERE '
        + ' OR '.join(f'{column} IS NULL' for column in REQUIRED_COLUMNS)
    )
    with op.batch_alter_table('KarTracker_groundplan') as batch_op:
        batch_op.alter_column('image_data', existing_type=sa.LargeBinary(), nullable=False)
        batch_op.alter_column('image_content_type', existing_type=sa.String(length=100), nullable=False)
        for column in ['sw_latitude', 'sw_longitude', 'ne_latitude', 'ne_longitude']:
            batch_op.alter_column(column, existing_type=sa.Float(), nullable=False)

    # The old singleton row was inserted with an explicit id=1, so Postgres'
    # id sequence never moved; without this the first new plan would clash
    # with id 1 on insert.
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(
            "SELECT setval(pg_get_serial_sequence('\"KarTracker_groundplan\"', 'id'), "
            'COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM "KarTracker_groundplan"'
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Back to a single plan: keep only the oldest one, as id 1.
    op.execute('DELETE FROM "KarTracker_groundplan" WHERE id <> (SELECT MIN(id) FROM "KarTracker_groundplan")')
    op.execute('UPDATE "KarTracker_groundplan" SET id = 1')
    with op.batch_alter_table('KarTracker_groundplan') as batch_op:
        batch_op.alter_column('image_data', existing_type=sa.LargeBinary(), nullable=True)
        batch_op.alter_column('image_content_type', existing_type=sa.String(length=100), nullable=True)
        for column in ['sw_latitude', 'sw_longitude', 'ne_latitude', 'ne_longitude']:
            batch_op.alter_column(column, existing_type=sa.Float(), nullable=True)
        batch_op.drop_column('name')
