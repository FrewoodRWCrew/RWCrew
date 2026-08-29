# "conftest.py" is a special pytest filename: fixtures defined here are
# automatically available to every test file in this folder (and its
# subfolders), without needing to import them manually.
#
# Our tests run against a real, temporary SQLite database file instead of
# PostgreSQL. This keeps tests fast and avoids requiring Docker/Postgres
# to be running just to run the test suite. Our models only use standard
# column types (integers, strings, booleans, dates, a plain enum), so the
# same table definitions work correctly on both databases.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.db.base import Base
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh, empty in-memory database for a single test."""
    # "sqlite:///:memory:" creates a temporary database that only exists
    # in RAM and disappears as soon as the test finishes. By default,
    # SQLAlchemy would open a NEW, separate in-memory database for every
    # connection it makes — StaticPool instead forces it to keep reusing
    # the one single connection, so every query in this test actually
    # sees the same in-memory database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Unlike PostgreSQL, SQLite ignores foreign-key rules (like our
    # "delete this user's access rows when the user is deleted") unless
    # explicitly told to enforce them. This makes deleting a user behave
    # the same way in tests as it does against the real database.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    # Create every table our models define, from scratch, in this
    # temporary database.
    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide an HTTP test client for our FastAPI app, wired to the
    temporary test database instead of the real one.
    """

    def _get_test_db() -> Generator[Session, None, None]:
        # Hand out the SAME session the test itself is using, so anything
        # a test sets up (e.g. creating a user directly) is visible to the
        # API calls made through this client, and vice versa.
        yield db_session

    # Tell FastAPI to use our test database function instead of the real
    # get_db, only for the lifetime of this fixture.
    app.dependency_overrides[get_db] = _get_test_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
