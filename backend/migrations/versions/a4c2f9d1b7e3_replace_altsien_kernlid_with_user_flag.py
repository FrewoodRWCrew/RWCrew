"""replace altsien kernlid contacts with a user flag

Adds Landing_users.is_altsien_kernlid + Landing_users.phone, re-points the
three tables that referenced MasterData_altsien_kernlid (team_kernlid,
KarTracker_distributiepunten, KarTracker_afleverlocaties) at Landing_users,
then drops MasterData_altsien_kernlid and its permission screen.

Existing contacts are matched to users by email (case-insensitive): a
matched user gets the flag (and the contact's phone, if they had none) and
keeps the links; links to unmatched contacts are dropped.

Revision ID: a4c2f9d1b7e3
Revises: e7b3c9a41d58
Create Date: 2026-09-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4c2f9d1b7e3'
down_revision: Union[str, Sequence[str], None] = 'e7b3c9a41d58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TABLE = "MasterData_altsien_kernlid"
USERS = "Landing_users"
JOIN_TABLE = "MasterData_team_kernlid"
NULLABLE_REF_TABLES = ["KarTracker_distributiepunten", "KarTracker_afleverlocaties"]


def _drop_fks_to(table: str, referred_table: str) -> None:
    """Drop every foreign key on `table` that points at `referred_table`
    (looked up by inspection, since the auto-generated names aren't known)."""
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if fk["referred_table"] == referred_table and fk["name"]:
            op.drop_constraint(fk["name"], table, type_="foreignkey")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1. New user columns.
    op.add_column(USERS, sa.Column("is_altsien_kernlid", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column(USERS, sa.Column("phone", sa.String(length=255), nullable=True))

    # 2. Match contacts to users by email; flag the users and copy phones.
    contacts = bind.execute(sa.text(f'SELECT id, email, telephone_number FROM "{OLD_TABLE}"')).fetchall()
    users_by_email = {
        row.email.lower(): row.id for row in bind.execute(sa.text(f'SELECT id, email FROM "{USERS}"')).fetchall()
    }
    old_to_user: dict[int, int] = {}
    for contact in contacts:
        user_id = users_by_email.get(contact.email.lower())
        if user_id is None:
            continue
        old_to_user[contact.id] = user_id
        bind.execute(
            sa.text(
                f'UPDATE "{USERS}" SET is_altsien_kernlid = true, '
                f"phone = COALESCE(NULLIF(phone, ''), :phone) WHERE id = :user_id"
            ),
            {"phone": contact.telephone_number, "user_id": user_id},
        )

    # 3. Drop the old FKs, remap the ids, then add FKs to Landing_users.
    for table in [JOIN_TABLE, *NULLABLE_REF_TABLES]:
        _drop_fks_to(table, OLD_TABLE)

    join_rows = bind.execute(sa.text(f'SELECT team_id, altsien_kernlid_id FROM "{JOIN_TABLE}"')).fetchall()
    new_links = {(row.team_id, old_to_user[row.altsien_kernlid_id]) for row in join_rows if row.altsien_kernlid_id in old_to_user}
    bind.execute(sa.text(f'DELETE FROM "{JOIN_TABLE}"'))
    for team_id, user_id in sorted(new_links):
        bind.execute(
            sa.text(f'INSERT INTO "{JOIN_TABLE}" (team_id, altsien_kernlid_id) VALUES (:team_id, :user_id)'),
            {"team_id": team_id, "user_id": user_id},
        )

    for table in NULLABLE_REF_TABLES:
        rows = bind.execute(
            sa.text(f'SELECT id, altsien_kernlid_id FROM "{table}" WHERE altsien_kernlid_id IS NOT NULL')
        ).fetchall()
        for row in rows:
            bind.execute(
                sa.text(f'UPDATE "{table}" SET altsien_kernlid_id = :new_id WHERE id = :id'),
                {"new_id": old_to_user.get(row.altsien_kernlid_id), "id": row.id},
            )

    op.create_foreign_key(
        "fk_masterdata_team_kernlid_user", JOIN_TABLE, USERS, ["altsien_kernlid_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_kartracker_distributiepunten_kernlid_user",
        "KarTracker_distributiepunten", USERS, ["altsien_kernlid_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_kartracker_afleverlocaties_kernlid_user",
        "KarTracker_afleverlocaties", USERS, ["altsien_kernlid_id"], ["id"], ondelete="SET NULL",
    )

    # 4. Drop the contact table and its permission screen (permission rows cascade).
    op.drop_table(OLD_TABLE)
    bind.execute(sa.text('DELETE FROM "MasterData_screens" WHERE key = :key'), {"key": "masterdata.altsien-kernleden"})


def downgrade() -> None:
    """Downgrade schema. The contact table comes back EMPTY (its data is not
    restorable), so every link to a Kernlid is cleared."""
    bind = op.get_bind()

    for table in [JOIN_TABLE, *NULLABLE_REF_TABLES]:
        _drop_fks_to(table, USERS)

    bind.execute(sa.text(f'DELETE FROM "{JOIN_TABLE}"'))
    for table in NULLABLE_REF_TABLES:
        bind.execute(sa.text(f'UPDATE "{table}" SET altsien_kernlid_id = NULL'))

    op.create_table(
        OLD_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telephone_number", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(None, JOIN_TABLE, OLD_TABLE, ["altsien_kernlid_id"], ["id"], ondelete="CASCADE")
    for table in NULLABLE_REF_TABLES:
        op.create_foreign_key(None, table, OLD_TABLE, ["altsien_kernlid_id"], ["id"])

    op.drop_column(USERS, "phone")
    op.drop_column(USERS, "is_altsien_kernlid")
