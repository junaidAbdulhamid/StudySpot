from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.repositories.users import FavoriteRepository, PreferenceRepository, UserRepository
from app.schemas.catalog import (
    FavoriteRead,
    Page,
    Pagination,
    PreferenceRead,
    PreferenceUpdate,
    UserRead,
)
from app.services.catalog import LocationService


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get(self, identifier):
        row = self.repo.get(identifier)
        if row is None:
            raise AppError(
                "USER_NOT_FOUND", "Development user was not found. Run the seed command."
            )
        return UserRead.model_validate(row)


class FavoriteService:
    def __init__(self, db: Session):
        self.db, self.repo = db, FavoriteRepository(db)

    def list(self, user_id, pagination: Pagination):
        rows, total = self.repo.list(user_id, pagination)
        return Page[FavoriteRead](
            items=[FavoriteRead.model_validate(r) for r in rows],
            total=total,
            **pagination.model_dump(),
        )

    def add(self, user_id, location_id):
        LocationService(self.db).require(location_id)
        row = self.repo.add(user_id, location_id)
        self.db.commit()
        return FavoriteRead.model_validate(row)

    def remove(self, user_id, location_id):
        self.repo.remove(user_id, location_id)
        self.db.commit()


class PreferenceService:
    def __init__(self, db: Session):
        self.db, self.repo = db, PreferenceRepository(db)

    def require(self, user_id, lock=False):
        row = self.repo.get(user_id, lock=lock)
        if row is None:
            raise AppError(
                "PREFERENCES_NOT_FOUND", "Preferences were not found. Run the seed command."
            )
        return row

    def get(self, user_id):
        return PreferenceRead.model_validate(self.require(user_id))

    def update(self, user_id, patch: PreferenceUpdate):
        row = self.require(user_id, lock=True)
        values = patch.model_dump(exclude_unset=True)
        slugs = values.pop("preferred_amenities", None)
        if slugs is not None:
            amenities = self.repo.amenities(set(slugs))
            if len(amenities) != len(set(slugs)):
                raise AppError(
                    "INVALID_AMENITY", "One or more preferred amenities do not exist.", 422
                )
            row.preferred_amenities = amenities
        for key, value in values.items():
            setattr(row, key, value)
        self.db.commit()
        return PreferenceRead.model_validate(row)
