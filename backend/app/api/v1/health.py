from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import Database
from app.core.exceptions import AppError
from app.schemas.catalog import errors

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Check API and database connectivity",
    description="Reports whether the API can reach PostgreSQL and whether PostGIS answers. No configuration is disclosed.",
    responses=errors(503),
)
def health(db: Database):
    try:
        db.execute(text("SELECT 1"))
        db.execute(text("SELECT PostGIS_Version()"))
    except SQLAlchemyError as exc:
        raise AppError("DATABASE_UNAVAILABLE", "Database or PostGIS is unavailable.", 503) from exc
    return {"status": "ok", "database": "connected", "postgis": "enabled"}
