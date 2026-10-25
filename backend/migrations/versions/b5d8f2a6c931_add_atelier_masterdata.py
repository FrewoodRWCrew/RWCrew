"""add Atelier masterdata (sizes, articles, article sizes, team packages)

Revision ID: b5d8f2a6c931
Revises: a7c3e9f1b524
Create Date: 2026-10-25 15:00:00.000000

Block 1 of the Atelier module: the clothing catalogue (articles + the sizes
each comes in) and, per season, what every member of a team gets. The size
list is seeded with XS-XXL for Women, Men and Unisex plus "OneSize" (Unisex).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d8f2a6c931'
down_revision: Union[str, Sequence[str], None] = 'a7c3e9f1b524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_SIZE_NAMES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SEED_FITS = ['women', 'men', 'unisex']


def upgrade() -> None:
    """Upgrade schema."""
    sizes = op.create_table(
        'Atelier_size',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('fit', sa.String(length=10), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'fit', name='uq_atelier_size_name_fit'),
    )
    op.create_table(
        'Atelier_article',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('colour', sa.String(length=100), nullable=True),
        sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_tag_managed', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('image_data', sa.LargeBinary(), nullable=True),
        sa.Column('image_content_type', sa.String(length=100), nullable=True),
        sa.Column('image_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_Atelier_article_code'), 'Atelier_article', ['code'], unique=True)
    op.create_table(
        'Atelier_article_size',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('size_id', sa.Integer(), nullable=False),
        sa.Column('min_stock', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['Atelier_article.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['size_id'], ['Atelier_size.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id', 'size_id', name='uq_atelier_article_size'),
    )
    op.create_index(op.f('ix_Atelier_article_size_article_id'), 'Atelier_article_size', ['article_id'], unique=False)
    op.create_table(
        'Atelier_team_package',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('quantity_per_person', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['Atelier_article.id']),
        sa.ForeignKeyConstraint(['season_id'], ['MasterData_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['MasterData_team.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'team_id', 'article_id', name='uq_atelier_team_package'),
    )
    op.create_index(op.f('ix_Atelier_team_package_season_id'), 'Atelier_team_package', ['season_id'], unique=False)
    op.create_index(op.f('ix_Atelier_team_package_team_id'), 'Atelier_team_package', ['team_id'], unique=False)

    # The starting size list: XS-XXL for every fit, then OneSize (Unisex).
    seed = [
        {'name': name, 'fit': fit, 'sort_order': (index + 1) * 10, 'active': True}
        for fit in SEED_FITS
        for index, name in enumerate(SEED_SIZE_NAMES)
    ]
    seed.append({'name': 'OneSize', 'fit': 'unisex', 'sort_order': 100, 'active': True})
    op.bulk_insert(sizes, seed)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_Atelier_team_package_team_id'), table_name='Atelier_team_package')
    op.drop_index(op.f('ix_Atelier_team_package_season_id'), table_name='Atelier_team_package')
    op.drop_table('Atelier_team_package')
    op.drop_index(op.f('ix_Atelier_article_size_article_id'), table_name='Atelier_article_size')
    op.drop_table('Atelier_article_size')
    op.drop_index(op.f('ix_Atelier_article_code'), table_name='Atelier_article')
    op.drop_table('Atelier_article')
    op.drop_table('Atelier_size')
