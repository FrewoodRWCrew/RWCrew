"""Atelier mail templates: the texts of the Uitgifte / Inname mails

Revision ID: c8e2a5f1d394
Revises: b2d5f8a3c697
Create Date: 2026-10-26 18:00:00.000000

After Ophalen and Terugbrengen at the counter desk the person gets a mail.
Its subject and body (with placeholders such as {voornaam}) are edited on
Atelier's "Instellingen > E-mails" screen; both rows are seeded with the same
default Dutch text as module_5/notifications.py DEFAULT_TEMPLATES.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2a5f1d394'
down_revision: Union[str, Sequence[str], None] = 'b2d5f8a3c697'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    templates = op.create_table(
        'Atelier_mail_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=20), nullable=False),
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
                'key': 'handout',
                'subject': 'Je atelierkledij voor {festival}',
                'body': (
                    'Dag {voornaam},\n\n'
                    'Je hebt op {dag} aan de balie van het atelier deze kledij opgehaald voor ploeg {ploeg}:\n'
                    '{stuks}\n\n'
                    'Breng alles na je shift terug naar de balie van het atelier.\n\n'
                    'Bedankt!\n'
                    'Het atelier'
                ),
                'active': True,
            },
            {
                'key': 'return',
                'subject': 'Je kledij is teruggebracht – {festival}',
                'body': (
                    'Dag {voornaam},\n\n'
                    'We hebben deze kledij goed terug ontvangen:\n'
                    '{stuks}\n\n'
                    'Nog in jouw bezit:\n'
                    '{openstaand}\n\n'
                    'Bedankt!\n'
                    'Het atelier'
                ),
                'active': True,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('Atelier_mail_template')
