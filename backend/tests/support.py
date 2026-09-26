"""Shared safety checks for tests and the browser-test API server."""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def configure_test_database():
    values = dotenv_values(Path(__file__).parents[1] / ".env")
    test_url = os.environ.get("TEST_DATABASE_URL") or values.get("TEST_DATABASE_URL")
    if not test_url:
        raise RuntimeError("Set TEST_DATABASE_URL to a dedicated local database ending in _test")
    url = make_url(test_url)
    original = os.environ.get("DATABASE_URL") or values.get("DATABASE_URL")
    if (
        not url.database
        or not url.database.endswith("_test")
        or url.host not in {"localhost", "127.0.0.1", "db"}
    ):
        raise RuntimeError("Tests require a local PostgreSQL database ending in _test")
    if original and make_url(original).set(password=None) == url.set(password=None):
        raise RuntimeError("Test and application databases must differ")
    os.environ.update(
        DATABASE_URL=test_url,
        APP_ENV="test",
        DEBUG="false",
        DEV_USER_ENABLED="true",
        DEV_USER_ID="dev-studyspot",
    )
    return test_url, url


def ensure_database(url):
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True
    )
    with admin.connect() as connection:
        if not connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": url.database}
        ):
            quoted = connection.dialect.identifier_preparer.quote(url.database)
            connection.execute(text(f"CREATE DATABASE {quoted}"))
    admin.dispose()
