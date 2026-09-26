import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from tests.support import configure_test_database, ensure_database

TEST_URL, url = configure_test_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed.run import seed  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    ensure_database(url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(TEST_URL, hide_parameters=True)
    with Session(engine) as db:
        seed(db, "dev-studyspot")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
