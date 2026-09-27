import pytest
from alembic.config import Config
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from alembic import command
from tests.support import configure_test_database, ensure_database

TEST_URL, url = configure_test_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.api.dependencies import get_current_user  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Favorite, User  # noqa: E402
from app.seed.run import seed  # noqa: E402

DEV_USER_ID = "dev-studyspot"


@pytest.fixture(scope="session")
def engine():
    try:
        ensure_database(url)
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=2)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(TEST_URL, hide_parameters=True)
    with Session(engine) as db:
        seed(db, DEV_USER_ID)
        # Browser recovery tests can leave this dedicated test profile changed.
        # Establish the favorite fixture without altering the developer database.
        db.execute(delete(Favorite).where(Favorite.user_id == DEV_USER_ID))
        db.add_all(
            [
                Favorite(user_id=DEV_USER_ID, location_id=identifier)
                for identifier in ("zone-1", "zone-6")
            ]
        )
        db.commit()
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
    # Bypasses Supabase token verification: authenticates every request as the
    # seeded dev user so tests exercise the real routes/services/repositories
    # without a live identity provider. app/core/auth.py stays fully untested
    # here on purpose — see test_auth.py for coverage of verify_access_token.
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, DEV_USER_ID)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def anonymous_client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
