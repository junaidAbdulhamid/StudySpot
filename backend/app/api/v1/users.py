from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import Database, DevUser, development_user_id
from app.schemas.catalog import Data, UserRead, errors
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["development user"])


@router.get(
    "/development",
    response_model=Data[UserRead],
    summary="Resolve the configured development user",
    description="Development identity discovery, not authentication. Disabled unless explicitly enabled in development/test.",
    responses=errors(403, 503),
)
def development_user(db: Database, identity: Annotated[str, Depends(development_user_id)]):
    return {"data": UserService(db).get(identity)}


@router.get(
    "/{user_id}",
    response_model=Data[UserRead],
    summary="Get the development user",
    description="Phase 3 replaces the path identity with an authenticated subject.",
    responses=errors(403, 404, 503),
)
def get_user(db: Database, identity: DevUser):
    return {"data": UserService(db).get(identity)}
