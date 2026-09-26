from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import Database
from app.schemas.catalog import BuildingRead, Data, Page, Pagination, errors
from app.services.catalog import BuildingService

router = APIRouter(prefix="/buildings", tags=["buildings"])


class BuildingQuery(Pagination):
    campus_id: str | None = None


@router.get(
    "",
    response_model=Page[BuildingRead],
    summary="List buildings",
    description="Paginated buildings, optionally narrowed to one campus with campus_id.",
    responses=errors(422, 503),
)
def list_buildings(db: Database, query: Annotated[BuildingQuery, Query()]):
    return BuildingService(db).list(
        Pagination(page=query.page, page_size=query.page_size), query.campus_id
    )


@router.get(
    "/{building_id}",
    response_model=Data[BuildingRead],
    summary="Get one building",
    responses=errors(404, 503),
)
def get_building(building_id: str, db: Database):
    return {"data": BuildingService(db).get(building_id)}
