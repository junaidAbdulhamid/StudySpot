from fastapi import APIRouter

from app.api.dependencies import Database, DevUser
from app.schemas.catalog import Data, PreferenceRead, PreferenceUpdate, errors
from app.services.users import PreferenceService

router = APIRouter(prefix="/users/{user_id}/preferences", tags=["preferences"])


@router.get(
    "",
    response_model=Data[PreferenceRead],
    summary="Read stored study preferences",
    responses=errors(403, 404, 503),
)
def get_preferences(db: Database, identity: DevUser):
    return {"data": PreferenceService(db).get(identity)}


@router.patch(
    "",
    response_model=Data[PreferenceRead],
    summary="Update study preferences",
    description="Partial update. Omitted fields keep their stored value; explicit nulls and unknown fields are rejected.",
    responses=errors(403, 404, 422, 503),
)
def update_preferences(patch: PreferenceUpdate, db: Database, identity: DevUser):
    return {"data": PreferenceService(db).update(identity, patch)}
