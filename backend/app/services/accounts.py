from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.auth import VerifiedIdentity
from app.models import User, UserPreference
from app.schemas.catalog import ProfileUpdate, UserRead


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def synchronize(self, identity: VerifiedIdentity) -> User:
        # Unique provider ID and ON CONFLICT serialize concurrent first requests.
        # Email never selects/merges an account. Editable profile fields survive login.
        self.db.execute(
            insert(User)
            .values(
                id=str(uuid4()),
                auth_provider_id=identity.subject,
                email=identity.email,
                display_name=identity.display_name,
            )
            .on_conflict_do_update(
                index_elements=[User.auth_provider_id], set_={"email": identity.email}
            )
        )
        user = self.db.scalar(select(User).where(User.auth_provider_id == identity.subject))
        self.db.execute(
            insert(UserPreference)
            .values(
                id=str(uuid4()),
                user_id=user.id,
                noise_preference="quiet",
                study_style="solo",
                max_walking_minutes=10,
                study_duration_hours=1,
            )
            .on_conflict_do_nothing(index_elements=[UserPreference.user_id])
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, patch: ProfileUpdate):
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        self.db.commit()
        return UserRead.model_validate(user)

    def delete_application_data(self, user: User):
        """Internal deletion primitive, NOT a claim of Supabase identity deletion.

        A future privileged deletion coordinator must revoke/delete the provider
        identity before this transaction to prevent automatic account recreation.
        FK cascades remove preferences, preference amenities and favorites.
        """
        self.db.execute(delete(User).where(User.id == user.id))
        self.db.commit()
