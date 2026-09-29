from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CheckInStatus, CrowdLevel, ValidationType


class CoordinatesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both coordinates or neither")
        return self


class CheckInCreate(CoordinatesInput):
    location_id: str


class CrowdReportCreate(CoordinatesInput):
    location_id: str
    crowd_level: CrowdLevel


class ValidationCreate(CoordinatesInput):
    location_id: str
    estimate_id: str
    validation_type: ValidationType


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    location_id: str
    status: CheckInStatus
    checked_in_at: datetime
    checked_out_at: datetime | None
    expires_at: datetime
    location_verified: bool


class ContributionRead(BaseModel):
    id: str
    location_id: str
    submitted_at: datetime


class ConfidenceRead(BaseModel):
    score: float
    label: str


class SignalSummary(BaseModel):
    recent_reports: int
    active_checkins: int
    recent_validations: int
    trusted_observation: bool


class CurrentOccupancy(BaseModel):
    location_id: str
    estimate_id: str | None
    occupancy_percent: int | None
    occupancy_level: str
    confidence: ConfidenceRead
    updated_at: datetime | None
    freshness_seconds: int | None
    signal_count: int
    signal_summary: SignalSummary
