from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Database
from app.schemas.catalog import Data, PreferenceRead, PreferenceUpdate, errors
from app.services.users import PreferenceService

router = APIRouter(prefix="/me/preferences", tags=["preferences"])


@router.get(
    "",
    response_model=Data[PreferenceRead],
    summary="Read stored study preferences",
    responses=errors(401, 404, 503),
)
def get_preferences(db: Database, current_user: CurrentUser):
    return {"data": PreferenceService(db).get(current_user.id)}


@router.patch(
    "",
    response_model=Data[PreferenceRead],
    summary="Update study preferences",
    description="Partial update. Omitted fields keep their stored value; explicit nulls and unknown fields are rejected.",
    responses=errors(401, 404, 422, 503),
)
def update_preferences(patch: PreferenceUpdate, db: Database, current_user: CurrentUser):
    return {"data": PreferenceService(db).update(current_user.id, patch)}
