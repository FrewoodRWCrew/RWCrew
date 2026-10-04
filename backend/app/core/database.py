# This file sets up the connection between our FastAPI backend and the
# PostgreSQL database, using a toolkit called SQLAlchemy.

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.timezone import BELGIAN_TZ_NAME


# All our database tables (models) will inherit from this "Base" class.
# SQLAlchemy uses it behind the scenes to keep track of every table we define.
class Base(DeclarativeBase):
    pass


# The "engine" is the object that actually knows how to talk to the
# PostgreSQL database over the network, using the connection string from
# our settings.
engine = create_engine(settings.database_url)


@event.listens_for(engine, "connect")
def _use_belgian_time(dbapi_connection, _connection_record) -> None:
    """Run every Postgres connection in Belgian time.

    Timestamps then come back with their Belgian offset (+01:00/+02:00), and
    a date-time typed in a form (sent without a timezone) is read as Belgian
    time instead of UTC. Done in autocommit so a later rollback can't undo
    it. SQLite (tests) has no session timezone, so it is skipped there.
    """
    if engine.dialect.name != "postgresql":
        return
    dbapi_connection.autocommit = True
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET TIME ZONE '{BELGIAN_TZ_NAME}'")
    cursor.close()
    dbapi_connection.autocommit = False


# A "session factory": every time we call SessionLocal(), we get a fresh,
# independent database session (a temporary workspace for running queries).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session to a single request, then always close it.

    FastAPI calls this function for every request that needs database
    access. It hands out one session, waits for the request to finish, and
    then closes the session again — even if something went wrong — so we
    never leak open database connections.
    """
    # Open a new session for this request.
    db = SessionLocal()
    try:
        # Give control back to whatever code needs the session (a "yield"
        # pauses this function here until the request is done).
        yield db
    finally:
        # Always close the session afterwards, whether the request
        # succeeded or raised an error.
        db.close()
