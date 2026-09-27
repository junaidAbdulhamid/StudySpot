from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import VerifiedIdentity, unauthorized, verify_access_token
from app.core.database import get_db
from app.models import User
from app.services.accounts import AccountService

Database = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


def get_verified_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> VerifiedIdentity:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or len(credentials.credentials) > 16384
    ):
        raise unauthorized()
    return verify_access_token(credentials.credentials)


def get_current_user(
    db: Database, identity: Annotated[VerifiedIdentity, Depends(get_verified_identity)]
) -> User:
    return AccountService(db).synchronize(identity)


CurrentUser = Annotated[User, Depends(get_current_user)]
