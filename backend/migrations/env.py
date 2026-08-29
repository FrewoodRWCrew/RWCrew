# This file tells Alembic (our database migration tool) two things:
#   1. Which database to connect to (we reuse our own app settings, so
#      there is only one place — app/core/config.py / the .env file — that
#      knows the real database connection details).
#   2. What our tables are SUPPED to look like (via target_metadata), so
#      "alembic revision --autogenerate" can compare that against the
#      database's current state and write the difference as a migration.

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings
from app.db.base import Base  # imports every model, registering them on Base.metadata

# This is the Alembic Config object, which provides access to the values
# within alembic.ini.
config = context.config

# Override whatever placeholder database URL is in alembic.ini with the
# real one from our application settings, so both always agree.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python's logging based on alembic.ini, if configured.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what autogenerate compares the live database against.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without connecting to a real database.

    Used when you want to produce a .sql script to run manually later,
    instead of having Alembic apply it directly.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the real database and apply migrations directly.

    This is the normal path used by "alembic upgrade head" during
    development and deployment.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
