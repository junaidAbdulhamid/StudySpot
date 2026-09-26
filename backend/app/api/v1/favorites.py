from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import Database, DevUser
from app.schemas.catalog import Data, FavoriteRead, Page, Pagination, errors
from app.services.users import FavoriteService

router = APIRouter(prefix="/users/{user_id}/favorites", tags=["favorites"])


@router.get(
    "",
    response_model=Page[FavoriteRead],
    summary="List the development user's saved study zones",
    responses=errors(403, 404, 422, 503),
)
def list_favorites(db: Database, identity: DevUser, pagination: Annotated[Pagination, Query()]):
    return FavoriteService(db).list(identity, pagination)


@router.post(
    "/{location_id}",
    response_model=Data[FavoriteRead],
    summary="Save a study zone",
    description="Idempotent add. Concurrent duplicates are prevented by a database unique constraint.",
    responses=errors(403, 404, 503),
)
def add_favorite(location_id: str, db: Database, identity: DevUser):
    return {"data": FavoriteService(db).add(identity, location_id)}


@router.delete(
    "/{location_id}",
    status_code=204,
    summary="Remove a saved study zone",
    description="Idempotent remove; absence also returns 204.",
    responses=errors(403, 404, 503),
)
def remove_favorite(location_id: str, db: Database, identity: DevUser):
    FavoriteService(db).remove(identity, location_id)
    return Response(status_code=204)
