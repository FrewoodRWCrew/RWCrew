"""move the product master-data screens from MasterData to StockMaster

Revision ID: e6a1b4c8d235
Revises: d5e9f3a7b124
Create Date: 2026-10-24 20:00:00.000000

Products and their four lookup lists (Type, Magazijnen, Categorieën,
Limieten) are now maintained in StockMaster (module-4). Their new
stockmaster.* screens are added by StockMaster's sync_screens at startup
(unticked for every role); this removes the old masterdata.* screen rows and
their role grants. The product tables themselves are untouched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a1b4c8d235'
down_revision: Union[str, Sequence[str], None] = 'd5e9f3a7b124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The old MasterData screens: key -> (label, sort_order), for the downgrade.
OLD_SCREENS = {
    "masterdata.products": ("Products", 2),
    "masterdata.product-types": ("Type", 3),
    "masterdata.warehouses": ("Magazijnen", 4),
    "masterdata.product-categories": ("Categorieën", 5),
    "masterdata.product-limits": ("Limieten", 6),
}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for key in OLD_SCREENS:
        # Grants first (explicit, though the foreign key also cascades), then the screen.
        bind.execute(
            sa.text(
                'DELETE FROM "MasterData_role_permissions" WHERE screen_id IN '
                '(SELECT id FROM "MasterData_screens" WHERE key = :key)'
            ),
            {"key": key},
        )
        bind.execute(sa.text('DELETE FROM "MasterData_screens" WHERE key = :key'), {"key": key})


def downgrade() -> None:
    """Downgrade schema. The MasterData screens come back without any grants."""
    bind = op.get_bind()
    for key, (label, sort_order) in OLD_SCREENS.items():
        bind.execute(
            sa.text('INSERT INTO "MasterData_screens" (key, label, sort_order) VALUES (:key, :label, :sort_order)'),
            {"key": key, "label": label, "sort_order": sort_order},
        )
