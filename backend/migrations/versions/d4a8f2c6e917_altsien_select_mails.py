"""Altsien Select mails: editable mail texts and a CC list

Revision ID: d4a8f2c6e917
Revises: d2a7c4e9b136
Create Date: 2026-11-07 12:00:00.000000

AltsienSelect_mail_template holds the subject/body of the mails Altsien Select
sends (seeded with "ploegfiche": the Ploegfiche PDF a Kernlid can ask for once
every wizard step is done). AltsienSelect_settings is a single row (id 1) with
the addresses that get a copy of every Altsien Select mail.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a8f2c6e917'
down_revision: Union[str, Sequence[str], None] = 'd2a7c4e9b136'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    templates = op.create_table(
        'AltsienSelect_mail_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=30), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.bulk_insert(
        templates,
        [
            {
                'key': 'ploegfiche',
                'subject': 'Ploegfiche {ploeg} – {jaartal}',
                'body': (
                    'Dag {naam},\n\n'
                    'Alle stappen van de Ploeg Wizard voor ploeg {ploeg} ({jaartal}) zijn afgerond.\n'
                    'In bijlage vind je de Ploegfiche met alle bevestigde gegevens:\n'
                    '{stappen}\n\n'
                    'Verstuurd op {datum}.\n\n'
                    'Bedankt!\n'
                    'Altsien'
                ),
                'active': True,
            },
        ],
    )

    settings = op.create_table(
        'AltsienSelect_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cc_addresses', sa.Text(), server_default='', nullable=False),
        sa.Column('updated_by_name', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.bulk_insert(settings, [{'id': 1, 'cc_addresses': ''}])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('AltsienSelect_settings')
    op.drop_table('AltsienSelect_mail_template')
