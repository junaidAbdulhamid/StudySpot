from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import Database
from app.schemas.catalog import CampusRead, Data, Page, Pagination, errors
from app.services.catalog import CampusService

router = APIRouter(prefix="/campuses", tags=["campuses"])


@router.get(
    "",
    response_model=Page[CampusRead],
    summary="List campuses",
    description="Paginated campuses. StudySpot launches with GMU Fairfax but is not modelled around a single university.",
    responses=errors(422, 503),
)
def list_campuses(db: Database, pagination: Annotated[Pagination, Query()]):
    return CampusService(db).list(pagination)


@router.get(
    "/{campus_id}",
    response_model=Data[CampusRead],
    summary="Get one campus",
    responses=errors(404, 503),
)
def get_campus(campus_id: str, db: Database):
    return {"data": CampusService(db).get(campus_id)}
