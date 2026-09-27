from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import CurrentUser, Database
from app.schemas.catalog import Data, FavoriteRead, Page, Pagination, errors
from app.services.users import FavoriteService

router = APIRouter(prefix="/me/favorites", tags=["favorites"])


@router.get(
    "",
    response_model=Page[FavoriteRead],
    summary="List your saved study zones",
    responses=errors(401, 404, 422, 503),
)
def list_favorites(
    db: Database, current_user: CurrentUser, pagination: Annotated[Pagination, Query()]
):
    return FavoriteService(db).list(current_user.id, pagination)


@router.post(
    "/{location_id}",
    response_model=Data[FavoriteRead],
    summary="Save a study zone",
    description="Idempotent add. Concurrent duplicates are prevented by a database unique constraint.",
    responses=errors(401, 404, 503),
)
def add_favorite(location_id: str, db: Database, current_user: CurrentUser):
    return {"data": FavoriteService(db).add(current_user.id, location_id)}


@router.delete(
    "/{location_id}",
    status_code=204,
    summary="Remove a saved study zone",
    description="Idempotent remove; absence also returns 204.",
    responses=errors(401, 404, 503),
)
def remove_favorite(location_id: str, db: Database, current_user: CurrentUser):
    FavoriteService(db).remove(current_user.id, location_id)
    return Response(status_code=204)
