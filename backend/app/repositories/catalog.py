from datetime import UTC, datetime, timedelta

from geoalchemy2 import Geography
from sqlalchemy import Time, and_, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Amenity,
    Building,
    Campus,
    OccupancyEstimate,
    OccupancyObservation,
    OccupancyPrediction,
    StudyLocation,
)
from app.schemas.catalog import LocationQuery, Pagination


class CampusRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, identifier):
        return self.db.get(Campus, identifier)

    def list(self, pagination: Pagination):
        return (
            self.db.scalars(
                select(Campus)
                .order_by(Campus.name, Campus.id)
                .offset((pagination.page - 1) * pagination.page_size)
                .limit(pagination.page_size)
            ).all(),
            self.db.scalar(select(func.count()).select_from(Campus)),
        )


class BuildingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, identifier):
        return self.db.get(Building, identifier)

    def list(self, pagination: Pagination, campus_id=None):
        query = select(Building)
        if campus_id:
            query = query.where(Building.campus_id == campus_id)
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        return self.db.scalars(
            query.order_by(Building.name, Building.id)
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
        ).all(), total


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def options():
        return (
            joinedload(StudyLocation.building).joinedload(Building.campus),
            selectinload(StudyLocation.amenities),
        )

    def get(self, identifier):
        return self.db.scalar(
            select(StudyLocation)
            .where(StudyLocation.id == identifier, StudyLocation.is_active.is_(True))
            .options(*self.options())
        )

    def filtered_query(self, filters: LocationQuery, now: datetime):
        latest = (
            select(OccupancyEstimate.occupancy_percent)
            .where(
                OccupancyEstimate.location_id == StudyLocation.id,
                OccupancyEstimate.estimated_at <= now,
            )
            .order_by(OccupancyEstimate.estimated_at.desc(), OccupancyEstimate.id.desc())
            .limit(1)
            .correlate(StudyLocation)
            .scalar_subquery()
        )
        query = (
            select(StudyLocation)
            .join(StudyLocation.building)
            .join(Building.campus)
            .where(StudyLocation.is_active.is_(True))
        )
        if filters.search.strip():
            term = filters.search.strip()
            query = query.where(
                or_(
                    StudyLocation.name.icontains(term, autoescape=True),
                    StudyLocation.floor.icontains(term, autoescape=True),
                    Building.name.icontains(term, autoescape=True),
                    StudyLocation.amenities.any(Amenity.name.icontains(term, autoescape=True)),
                )
            )
        if filters.building_id:
            query = query.where(StudyLocation.building_id == filters.building_id)
        if filters.campus_id:
            query = query.where(Building.campus_id == filters.campus_id)
        if filters.noise_level:
            query = query.where(StudyLocation.noise_level == filters.noise_level)
        for slug in set(x.strip() for x in filters.amenities.split(",") if x.strip()):
            query = query.where(StudyLocation.amenities.any(Amenity.slug == slug))
        if filters.min_occupancy > 0 or filters.max_occupancy < 100:
            query = query.where(latest.between(filters.min_occupancy, filters.max_occupancy))
        if filters.open_now is not None:
            local_time = cast(func.timezone(Campus.timezone, now), Time)
            is_open = or_(
                StudyLocation.opening_time == StudyLocation.closing_time,
                and_(
                    StudyLocation.opening_time < StudyLocation.closing_time,
                    local_time >= StudyLocation.opening_time,
                    local_time < StudyLocation.closing_time,
                ),
                and_(
                    StudyLocation.opening_time > StudyLocation.closing_time,
                    or_(
                        local_time >= StudyLocation.opening_time,
                        local_time < StudyLocation.closing_time,
                    ),
                ),
            )
            query = query.where(is_open if filters.open_now else ~is_open)
        return query

    def find_nearby(self, filters, now):
        origin = cast(
            func.ST_SetSRID(func.ST_MakePoint(filters.longitude, filters.latitude), 4326),
            Geography(geometry_type="POINT", srid=4326),
        )
        distance = func.ST_Distance(StudyLocation.geo_point, origin).label("distance_meters")
        query = self.filtered_query(filters, now).where(
            func.ST_DWithin(StudyLocation.geo_point, origin, filters.radius_meters)
        )
        return self.db.execute(
            query.add_columns(distance)
            .options(*self.options())
            .order_by(distance, StudyLocation.id)
            .limit(filters.limit)
        ).all()

    def list(self, filters: LocationQuery, now: datetime):
        query = self.filtered_query(filters, now)
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = self.db.scalars(
            query.options(*self.options())
            .order_by(StudyLocation.name, StudyLocation.floor, StudyLocation.id)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        ).all()
        return rows, total


class OccupancyRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest(self, ids: list[str], now: datetime):
        rows = self.db.scalars(
            select(OccupancyEstimate)
            .where(OccupancyEstimate.location_id.in_(ids), OccupancyEstimate.estimated_at <= now)
            .distinct(OccupancyEstimate.location_id)
            .order_by(
                OccupancyEstimate.location_id,
                OccupancyEstimate.estimated_at.desc(),
                OccupancyEstimate.id.desc(),
            )
        ).all()
        return {row.location_id: row for row in rows}

    def history(self, ids: list[str], now: datetime):
        ranked = (
            select(
                OccupancyObservation.id,
                func.row_number()
                .over(
                    partition_by=OccupancyObservation.location_id,
                    order_by=OccupancyObservation.observed_at.desc(),
                )
                .label("position"),
            )
            .where(
                OccupancyObservation.location_id.in_(ids), OccupancyObservation.observed_at <= now
            )
            .subquery()
        )
        return self.db.scalars(
            select(OccupancyObservation)
            .join(ranked, ranked.c.id == OccupancyObservation.id)
            .where(ranked.c.position <= 8)
            .order_by(OccupancyObservation.observed_at)
        ).all()


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def future(self, ids: list[str], hours: int = 4, now: datetime | None = None):
        now = now or datetime.now(UTC)
        return self.db.scalars(
            select(OccupancyPrediction)
            .where(
                OccupancyPrediction.location_id.in_(ids),
                OccupancyPrediction.target_time >= now,
                OccupancyPrediction.target_time <= now + timedelta(hours=hours),
            )
            .distinct(OccupancyPrediction.location_id, OccupancyPrediction.target_time)
            .order_by(
                OccupancyPrediction.location_id,
                OccupancyPrediction.target_time,
                OccupancyPrediction.created_at.desc(),
                OccupancyPrediction.id.desc(),
            )
        ).all()
