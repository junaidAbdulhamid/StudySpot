from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import Database
from app.schemas.catalog import Data, PredictionRead, errors
from app.services.catalog import PredictionService

router = APIRouter(tags=["predictions"])


@router.get(
    "/locations/{location_id}/predictions",
    response_model=Data[list[PredictionRead]],
    summary="List persisted future occupancy forecasts",
    description="Persisted future records only. Seed records are labeled source=seed and model_version=seed-v1. Rerun seed to refresh expired demo forecasts.",
    responses=errors(404, 422, 503),
)
def predictions(
    location_id: str, db: Database, hours_ahead: Annotated[int, Query(ge=1, le=24)] = 4
):
    return {"data": PredictionService(db).list(location_id, hours_ahead)}
