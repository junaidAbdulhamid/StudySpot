from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Database
from app.schemas.catalog import Data, errors
from app.schemas.occupancy import (
    CheckInCreate,
    CheckInRead,
    ConfidenceRead,
    ContributionRead,
    CrowdReportCreate,
    CurrentOccupancy,
    SignalSummary,
    ValidationCreate,
)
from app.services.occupancy import OccupancyService
from app.services.occupancy_estimator import effective_confidence
from app.utils.occupancy import classify_occupancy

router = APIRouter(tags=["occupancy"])


@router.post("/checkins", response_model=Data[CheckInRead], responses=errors(401, 404, 422, 503))
def checkin(payload: CheckInCreate, db: Database, user: CurrentUser):
    return {
        "data": OccupancyService(db).checkin(
            user, payload.location_id, payload.latitude, payload.longitude
        )
    }


@router.get(
    "/me/checkins/active", response_model=Data[CheckInRead | None], responses=errors(401, 503)
)
def active_checkin(db: Database, user: CurrentUser):
    return {"data": OccupancyService(db).active_checkin(user.id)}


@router.post(
    "/checkins/{checkin_id}/checkout",
    response_model=Data[CheckInRead],
    responses=errors(401, 404, 503),
)
def checkout(checkin_id: str, db: Database, user: CurrentUser):
    return {"data": OccupancyService(db).checkout(user, checkin_id)}


@router.post(
    "/crowd-reports",
    response_model=Data[ContributionRead],
    responses=errors(401, 404, 422, 429, 503),
)
def report(payload: CrowdReportCreate, db: Database, user: CurrentUser):
    row = OccupancyService(db).report(
        user, payload.location_id, payload.crowd_level, payload.latitude, payload.longitude
    )
    return {
        "data": ContributionRead(
            id=row.id, location_id=row.location_id, submitted_at=row.submitted_at
        )
    }


@router.post(
    "/occupancy-validations",
    response_model=Data[ContributionRead],
    responses=errors(401, 404, 409, 422, 429, 503),
)
def validate(payload: ValidationCreate, db: Database, user: CurrentUser):
    row = OccupancyService(db).validate(
        user,
        payload.location_id,
        payload.estimate_id,
        payload.validation_type,
        payload.latitude,
        payload.longitude,
    )
    return {
        "data": ContributionRead(
            id=row.id, location_id=row.location_id, submitted_at=row.submitted_at
        )
    }


@router.get(
    "/locations/{location_id}/occupancy",
    response_model=Data[CurrentOccupancy],
    responses=errors(404, 503),
)
def current(location_id: str, db: Database):
    snapshot = OccupancyService(db).current_payload(location_id)
    now = datetime.now(UTC)
    updated_at = datetime.fromisoformat(snapshot["updated_at"]) if snapshot else None
    effective_score, effective_label = (
        effective_confidence(snapshot["confidence_score"], updated_at, now)
        if snapshot
        else (0, None)
    )
    return {
        "data": CurrentOccupancy(
            location_id=location_id,
            estimate_id=snapshot["estimate_id"] if snapshot else None,
            occupancy_percent=snapshot["occupancy_percent"] if snapshot else None,
            occupancy_level=classify_occupancy(snapshot["occupancy_percent"])
            if snapshot and snapshot["occupancy_percent"] is not None
            else "unknown",
            confidence=ConfidenceRead(
                score=effective_score,
                label=effective_label.value if effective_label else "low",
            ),
            updated_at=updated_at,
            freshness_seconds=max(0, int((now - updated_at).total_seconds()))
            if updated_at
            else None,
            signal_count=snapshot["signal_count"] if snapshot else 0,
            signal_summary=SignalSummary(**snapshot["signal_summary"])
            if snapshot
            else SignalSummary(
                recent_reports=0, active_checkins=0, recent_validations=0, trusted_observation=False
            ),
        )
    }
