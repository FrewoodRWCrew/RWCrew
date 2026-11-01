"""Wristband scans leave Atelier: shared tables, TagScan is now called Scans

Revision ID: c3e8f1a7d264
Revises: e3a7c1f5b842
Create Date: 2026-11-01 16:00:00.000000

Wristband scans will serve Walkies too, so Atelier_scan / Atelier_scanner are
renamed (their data stays) and a scan remembers which module's counter used
it. module-1's display name changes from TagScan to Scans; its key, screen keys
and Tagscan_* tables stay. The registry only seeds a module's name once, so
the existing row is renamed here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e8f1a7d264'
down_revision: Union[str, Sequence[str], None] = 'e3a7c1f5b842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('Atelier_scan', 'Wristband_scan')
    op.rename_table('Atelier_scanner', 'Wristband_scanner')
    # The indexes follow the table names, as a fresh create_all would name them.
    op.execute('ALTER INDEX "ix_Atelier_scan_received_at" RENAME TO "ix_Wristband_scan_received_at"')
    op.execute('ALTER INDEX "ix_Atelier_scan_status" RENAME TO "ix_Wristband_scan_status"')
    op.execute('ALTER INDEX "ix_Atelier_scan_device_id" RENAME TO "ix_Wristband_scan_device_id"')
    op.execute('ALTER INDEX "ix_Atelier_scanner_device_id" RENAME TO "ix_Wristband_scanner_device_id"')
    op.add_column('Wristband_scan', sa.Column('used_by_module', sa.String(length=20), nullable=True))
    # Until now only Atelier could use a scan.
    op.execute("""UPDATE "Wristband_scan" SET used_by_module = 'module-5' WHERE status = 'used'""")
    op.execute("""UPDATE "Landing_modules" SET name = 'Scans' WHERE key = 'module-1'""")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""UPDATE "Landing_modules" SET name = 'TagScan' WHERE key = 'module-1'""")
    op.drop_column('Wristband_scan', 'used_by_module')
    op.execute('ALTER INDEX "ix_Wristband_scanner_device_id" RENAME TO "ix_Atelier_scanner_device_id"')
    op.execute('ALTER INDEX "ix_Wristband_scan_device_id" RENAME TO "ix_Atelier_scan_device_id"')
    op.execute('ALTER INDEX "ix_Wristband_scan_status" RENAME TO "ix_Atelier_scan_status"')
    op.execute('ALTER INDEX "ix_Wristband_scan_received_at" RENAME TO "ix_Atelier_scan_received_at"')
    op.rename_table('Wristband_scanner', 'Atelier_scanner')
    op.rename_table('Wristband_scan', 'Atelier_scan')
