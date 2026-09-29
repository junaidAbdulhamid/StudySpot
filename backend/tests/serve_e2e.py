"""Start a seeded API isolated from developer favorites/preferences for Playwright."""

import os

from tests.support import configure_test_database, ensure_database

_, url = configure_test_database()
ensure_database(url)
os.environ["SUPABASE_URL"] = "http://127.0.0.1:8002/test-auth"
os.environ["SUPABASE_ANON_KEY"] = "e2e-public-key"

import uvicorn  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from alembic import command  # noqa: E402
from app.core.database import get_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402
    CheckIn,
    CrowdReport,
    OccupancyEstimate,
    OccupancyValidation,
    User,
)
from app.seed.run import seed  # noqa: E402
from tests.e2e_auth import router as auth_router  # noqa: E402

command.upgrade(Config("alembic.ini"), "head")
with get_session_factory()() as db:
    seed(db, "dev-studyspot")
    for model in (OccupancyValidation, CheckIn, CrowdReport, OccupancyEstimate):
        db.execute(delete(model))
    db.execute(delete(User).where(User.auth_provider_id.is_not(None)))
    db.commit()
app = create_app()
app.include_router(auth_router)
uvicorn.run(app, host="127.0.0.1", port=8002, access_log=False)
