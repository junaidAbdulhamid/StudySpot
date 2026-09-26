"""Start a seeded API isolated from developer favorites/preferences for Playwright."""

from tests.support import configure_test_database, ensure_database

_, url = configure_test_database()
ensure_database(url)

import uvicorn  # noqa: E402
from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.core.database import get_session_factory  # noqa: E402
from app.seed.run import seed  # noqa: E402

command.upgrade(Config("alembic.ini"), "head")
with get_session_factory()() as db:
    seed(db, "dev-studyspot")
uvicorn.run("app.main:app", host="127.0.0.1", port=8002, access_log=False)
