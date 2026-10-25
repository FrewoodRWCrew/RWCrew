"""Atelier wristband scans: scan log, scanners, wristband per festival, settings

Revision ID: b2d5f8a3c697
Revises: a1c4e7f2b586
Create Date: 2026-10-26 15:00:00.000000

Block 5 of the Atelier module: the wristband company posts a JSON message per
scan to a webhook. Every message is logged in Atelier_scan; scanners register
themselves in Atelier_scanner. A wristband number is now per festival
(Atelier_person_bracelet), so Atelier_person.bracelet_number is dropped (its
values had no festival). The email becomes optional. Atelier_settings holds
the "wristband required at pick-up" switch (row 1, off).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d5f8a3c697'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f2b586'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First the old one-number-per-person column (its index name is the same
    # as the new table's number index, and index names are database-wide).
    op.drop_index(op.f('ix_Atelier_person_bracelet_number'), table_name='Atelier_person')
    op.drop_column('Atelier_person', 'bracelet_number')
    op.alter_column('Atelier_person', 'email', nullable=True)

    op.create_table(
        'Atelier_scanner',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_scanner_device_id'), 'Atelier_scanner', ['device_id'], unique=True)
    op.create_table(
        'Atelier_scan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('status_detail', sa.String(length=255), nullable=True),
        sa.Column('event', sa.String(length=100), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('wristband_number', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('team_name', sa.String(length=255), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('profile_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('raw', sa.Text(), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['Atelier_person.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_scan_received_at'), 'Atelier_scan', ['received_at'], unique=False)
    op.create_index(op.f('ix_Atelier_scan_status'), 'Atelier_scan', ['status'], unique=False)
    op.create_index(op.f('ix_Atelier_scan_device_id'), 'Atelier_scan', ['device_id'], unique=False)
    op.create_table(
        'Atelier_person_bracelet',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('festival_id', sa.Integer(), nullable=False),
        sa.Column('number', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['festival_id'], ['MasterData_festival.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['Atelier_person.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('festival_id', 'number', name='uq_atelier_bracelet_number'),
        sa.UniqueConstraint('person_id', 'festival_id', name='uq_atelier_bracelet_person'),
    )
    op.create_index(op.f('ix_Atelier_person_bracelet_person_id'), 'Atelier_person_bracelet', ['person_id'], unique=False)
    op.create_index(op.f('ix_Atelier_person_bracelet_festival_id'), 'Atelier_person_bracelet', ['festival_id'], unique=False)
    op.create_index(op.f('ix_Atelier_person_bracelet_number'), 'Atelier_person_bracelet', ['number'], unique=False)
    settings = op.create_table(
        'Atelier_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wristband_required', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.bulk_insert(settings, [{'id': 1, 'wristband_required': False}])



def downgrade() -> None:
    """Downgrade schema (wristband numbers per festival are lost)."""
    op.execute('UPDATE "Atelier_person" SET email = \'\' WHERE email IS NULL')
    op.alter_column('Atelier_person', 'email', nullable=False)
    op.drop_table('Atelier_settings')
    op.drop_index(op.f('ix_Atelier_person_bracelet_number'), table_name='Atelier_person_bracelet')
    op.drop_index(op.f('ix_Atelier_person_bracelet_festival_id'), table_name='Atelier_person_bracelet')
    op.drop_index(op.f('ix_Atelier_person_bracelet_person_id'), table_name='Atelier_person_bracelet')
    op.drop_table('Atelier_person_bracelet')
    op.drop_index(op.f('ix_Atelier_scan_device_id'), table_name='Atelier_scan')
    op.drop_index(op.f('ix_Atelier_scan_status'), table_name='Atelier_scan')
    op.drop_index(op.f('ix_Atelier_scan_received_at'), table_name='Atelier_scan')
    op.drop_table('Atelier_scan')
    op.drop_index(op.f('ix_Atelier_scanner_device_id'), table_name='Atelier_scanner')
    op.drop_table('Atelier_scanner')
    op.add_column('Atelier_person', sa.Column('bracelet_number', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_Atelier_person_bracelet_number'), 'Atelier_person', ['bracelet_number'], unique=True)
