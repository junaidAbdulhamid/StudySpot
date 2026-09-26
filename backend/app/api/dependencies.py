from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.services.users import UserService

Database = Annotated[Session, Depends(get_db)]


def development_user_id(db: Database) -> str:
    settings = get_settings()
    if not settings.dev_user_enabled or settings.app_env not in {"development", "test"}:
        raise AppError("DEVELOPMENT_IDENTITY_DISABLED", "Development identity is disabled.", 403)
    UserService(db).get(settings.dev_user_id)
    return settings.dev_user_id


def require_development_user(user_id: str, identity: Annotated[str, Depends(development_user_id)]):
    if user_id != identity:
        raise AppError(
            "USER_ACCESS_DENIED", "Only the configured development user is available.", 403
        )
    return identity


DevUser = Annotated[str, Depends(require_development_user)]
