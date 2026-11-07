"""store the lock code per kar (KarTracker_karren.kar_code)

Revision ID: e5b9c3d7a428
Revises: d4a8f2c6e917
Create Date: 2026-11-07

The kar code was only calculated from the kar number with the admin formula.
It is now stored per kar, so a later change of the formula doesn't change the
code of a lock that wasn't physically changed. Existing kars are filled once
with what the current formula gives (digits of the kar number: B001 -> 1);
after that the code is typed by hand on KarManagement.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.modules.module_2.karcode_formula import DEFAULT_KARCODE_FORMULA, formula_code_for_kar_nummer


# revision identifiers, used by Alembic.
revision: str = 'e5b9c3d7a428'
down_revision: Union[str, Sequence[str], None] = 'd4a8f2c6e917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('KarTracker_karren', sa.Column('kar_code', sa.String(length=20), nullable=True))

    connection = op.get_bind()
    # The formula in use right now (the settings row, else the default).
    formula = connection.execute(
        sa.text('SELECT karcode_formula FROM "KarTracker_settings" WHERE id = 1')
    ).scalar() or DEFAULT_KARCODE_FORMULA

    # One-time fill: each kar gets the code the current formula gives.
    karren = connection.execute(sa.text('SELECT id, kar_nummer FROM "KarTracker_karren"')).all()
    for kar_id, kar_nummer in karren:
        code = formula_code_for_kar_nummer(formula, kar_nummer)
        if code is not None:
            connection.execute(
                sa.text('UPDATE "KarTracker_karren" SET kar_code = :code WHERE id = :id'),
                {"code": code[:20], "id": kar_id},
            )


def downgrade() -> None:
    op.drop_column('KarTracker_karren', 'kar_code')
