from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.repositories.catalog import (
    BuildingRepository,
    CampusRepository,
    LocationRepository,
    OccupancyRepository,
    PredictionRepository,
)
from app.schemas.catalog import (
    AmenityRead,
    BuildingRead,
    CampusRead,
    Hours,
    LocationDetail,
    LocationListItem,
    LocationQuery,
    ObservationRead,
    OccupancyEstimateRead,
    Page,
    Pagination,
    PredictionRead,
)
from app.utils.occupancy import classify_occupancy


class CampusService:
    def __init__(self, db: Session):
        self.repo = CampusRepository(db)

    def list(self, pagination: Pagination):
        rows, total = self.repo.list(pagination)
        return Page[CampusRead](
            items=[CampusRead.model_validate(r) for r in rows],
            total=total,
            **pagination.model_dump(),
        )

    def get(self, identifier):
        row = self.repo.get(identifier)
        if row is None:
            raise AppError("CAMPUS_NOT_FOUND", "Campus was not found.")
        return CampusRead.model_validate(row)


class BuildingService:
    def __init__(self, db: Session):
        self.repo = BuildingRepository(db)

    def list(self, pagination: Pagination, campus_id=None):
        rows, total = self.repo.list(pagination, campus_id)
        return Page[BuildingRead](
            items=[BuildingRead.model_validate(r) for r in rows],
            total=total,
            **pagination.model_dump(),
        )

    def get(self, identifier):
        row = self.repo.get(identifier)
        if row is None:
            raise AppError("BUILDING_NOT_FOUND", "Building was not found.")
        return BuildingRead.model_validate(row)


class LocationService:
    def __init__(self, db: Session):
        self.repo, self.occupancy, self.predictions = (
            LocationRepository(db),
            OccupancyRepository(db),
            PredictionRepository(db),
        )

    def require(self, identifier):
        row = self.repo.get(identifier)
        if row is None:
            raise AppError("LOCATION_NOT_FOUND", "Study location was not found.")
        return row

    def assemble(self, rows, now):
        if not rows:
            return []
        ids = [r.id for r in rows]
        occupancy = self.occupancy.latest(ids, now)
        predictions, historical = defaultdict(list), defaultdict(list)
        for item in self.predictions.future(ids, now=now):
            predictions[item.location_id].append(PredictionRead.model_validate(item))
        for item in self.occupancy.history(ids, now):
            historical[item.location_id].append(ObservationRead.model_validate(item))
        results = []
        for row in rows:
            estimate = occupancy.get(row.id)
            results.append(
                LocationDetail(
                    id=row.id,
                    name=row.name,
                    slug=row.slug,
                    floor=row.floor,
                    description=row.description,
                    capacity=row.capacity,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    building=BuildingRead.model_validate(row.building),
                    campus=CampusRead.model_validate(row.building.campus),
                    amenities=[AmenityRead.model_validate(a) for a in row.amenities],
                    noise_level=row.noise_level,
                    image_url=row.image_url,
                    hours=Hours(
                        open=row.opening_time.strftime("%H:%M"),
                        close=row.closing_time.strftime("%H:%M"),
                    ),
                    current_occupancy=OccupancyEstimateRead(
                        percent=estimate.occupancy_percent,
                        level=classify_occupancy(estimate.occupancy_percent),
                        confidence=estimate.confidence,
                        source=estimate.source,
                        estimated_at=estimate.estimated_at,
                    )
                    if estimate
                    else None,
                    predictions=predictions[row.id],
                    historical=historical[row.id],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        return results

    def list(self, filters: LocationQuery):
        now = datetime.now(UTC)
        rows, total = self.repo.list(filters, now)
        return Page[LocationListItem](
            items=self.assemble(rows, now),
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    def get(self, identifier):
        return self.assemble([self.require(identifier)], datetime.now(UTC))[0]


class PredictionService:
    def __init__(self, db: Session):
        self.locations, self.repo = LocationService(db), PredictionRepository(db)

    def list(self, identifier, hours):
        self.locations.require(identifier)
        return [PredictionRead.model_validate(p) for p in self.repo.future([identifier], hours)]
