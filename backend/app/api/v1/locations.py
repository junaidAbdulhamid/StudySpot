from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import Database
from app.schemas.catalog import (
    Data,
    LocationDetail,
    LocationListItem,
    LocationQuery,
    Page,
    errors,
)
from app.services.catalog import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get(
    "",
    response_model=Page[LocationListItem],
    summary="Search active study zones",
    description="Database-side search, AND amenity filters, occupancy ranges, and campus-local open status. No walking distance is computed.",
    responses=errors(422, 503),
)
def list_locations(db: Database, filters: Annotated[LocationQuery, Query()]):
    return LocationService(db).list(filters)


@router.get(
    "/{location_id}",
    response_model=Data[LocationDetail],
    summary="Get one study zone with building, campus, amenities, occupancy and forecasts",
    description="Everything the detail and occupancy screens render. Occupancy and forecasts are persisted seed records in this phase.",
    responses=errors(404, 503),
)
def get_location(location_id: str, db: Database):
    return {"data": LocationService(db).get(location_id)}
