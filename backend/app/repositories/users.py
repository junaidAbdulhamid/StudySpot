from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import Amenity, Favorite, User, UserPreference
from app.schemas.catalog import Pagination


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, identifier):
        return self.db.get(User, identifier)


class FavoriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, user_id, pagination: Pagination):
        condition = Favorite.user_id == user_id
        total = self.db.scalar(select(func.count()).select_from(Favorite).where(condition))
        rows = self.db.scalars(
            select(Favorite)
            .where(condition)
            .order_by(Favorite.created_at, Favorite.id)
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
        ).all()
        return rows, total

    def add(self, user_id, location_id):
        self.db.execute(
            insert(Favorite)
            .values(id=str(uuid4()), user_id=user_id, location_id=location_id)
            .on_conflict_do_nothing(index_elements=[Favorite.user_id, Favorite.location_id])
        )
        return self.db.scalar(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.location_id == location_id)
        )

    def remove(self, user_id, location_id):
        self.db.execute(
            delete(Favorite).where(Favorite.user_id == user_id, Favorite.location_id == location_id)
        )


class PreferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id, lock=False):
        statement = (
            select(UserPreference)
            .where(UserPreference.user_id == user_id)
            .options(selectinload(UserPreference.preferred_amenities))
        )
        if lock:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def amenities(self, slugs):
        return self.db.scalars(select(Amenity).where(Amenity.slug.in_(slugs))).all()
