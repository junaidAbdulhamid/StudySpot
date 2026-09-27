from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Database
from app.schemas.catalog import Data, ProfileUpdate, UserRead, errors
from app.services.accounts import AccountService

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=Data[UserRead], responses=errors(401, 503))
def get_me(current_user: CurrentUser):
    return {"data": current_user}


@router.patch("", response_model=Data[UserRead], responses=errors(401, 422, 503))
def update_me(patch: ProfileUpdate, db: Database, current_user: CurrentUser):
    return {"data": AccountService(db).update(current_user, patch)}
