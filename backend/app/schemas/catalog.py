from datetime import datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    ConfidenceLevel,
    NoiseLevel,
    NoisePreference,
    OccupancySource,
    StudyStyle,
)


class Data[T](BaseModel):
    data: T


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CampusCreate(Coordinates):
    name: str = Field(min_length=1, max_length=160)
    university_name: str = Field(min_length=1, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=100)
    timezone: str

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown timezone") from exc
        return value


class CampusRead(CampusCreate, ReadModel):
    id: str
    created_at: datetime
    updated_at: datetime


class BuildingCreate(Coordinates):
    campus_id: str
    name: str = Field(min_length=1, max_length=160)
    short_name: str = Field(max_length=40)
    address: str | None = Field(default=None, max_length=300)


class BuildingRead(BuildingCreate, ReadModel):
    id: str
    created_at: datetime
    updated_at: datetime


class AmenityRead(ReadModel):
    id: str
    name: str
    slug: str
    icon: str


class OccupancyEstimateRead(BaseModel):
    percent: int = Field(ge=0, le=100)
    level: Literal["available", "moderate", "busy", "full"]
    confidence: ConfidenceLevel
    source: OccupancySource
    estimated_at: datetime


class PredictionRead(ReadModel):
    id: str
    location_id: str
    target_time: datetime
    predicted_occupancy: int = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    source: OccupancySource
    model_version: str
    created_at: datetime


class ObservationRead(ReadModel):
    occupancy_percent: int = Field(ge=0, le=100)
    observed_at: datetime
    source: OccupancySource


class Hours(BaseModel):
    open: str
    close: str


class LocationCreate(Coordinates):
    building_id: str
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=160)
    floor: str = Field(max_length=80)
    description: str
    capacity: int = Field(ge=0)
    noise_level: NoiseLevel
    image_url: str | None = None
    opening_time: time
    closing_time: time
    is_active: bool = True


class LocationListItem(Coordinates):
    id: str
    name: str
    slug: str
    floor: str
    description: str
    capacity: int
    building: BuildingRead
    campus: CampusRead
    amenities: list[AmenityRead]
    noise_level: NoiseLevel
    image_url: str | None
    hours: Hours
    current_occupancy: OccupancyEstimateRead | None
    predictions: list[PredictionRead]
    historical: list[ObservationRead]


class LocationDetail(LocationListItem):
    created_at: datetime
    updated_at: datetime


LocationRead = LocationDetail


class Pagination(BaseModel):
    page: int = Field(default=1, ge=1, le=100000)
    page_size: int = Field(default=20, ge=1, le=100)


class LocationQuery(Pagination):
    search: str = Field(default="", max_length=200)
    building_id: str | None = None
    campus_id: str | None = None
    noise_level: NoiseLevel | None = None
    amenities: str = Field(
        default="", max_length=1000, description="Comma-separated amenity slugs; all must match"
    )
    min_occupancy: int = Field(default=0, ge=0, le=100)
    max_occupancy: int = Field(default=100, ge=0, le=100)
    open_now: bool | None = None

    @model_validator(mode="after")
    def occupancy_range(self):
        if self.min_occupancy > self.max_occupancy:
            raise ValueError("min_occupancy must be <= max_occupancy")
        return self


class UserRead(ReadModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    points: int
    reliability_score: float
    onboarding_completed: bool


class PreferenceRead(ReadModel):
    id: str
    user_id: str
    noise_preference: NoisePreference
    study_style: StudyStyle
    max_walking_minutes: int
    study_duration_hours: float
    preferred_amenities: list[AmenityRead]


class PreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    noise_preference: NoisePreference | None = None
    study_style: StudyStyle | None = None
    max_walking_minutes: int | None = Field(default=None, gt=0, le=240)
    study_duration_hours: float | None = Field(default=None, gt=0, le=12)
    preferred_amenities: list[str] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def reject_explicit_null(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Preference fields cannot be null")
        return self


class FavoriteRead(ReadModel):
    id: str
    user_id: str
    location_id: str
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """Every failing response uses this shape. Details of the cause are never exposed."""

    error: ErrorDetail


_ERROR_DESCRIPTIONS = {
    401: "A valid Supabase access token is required.",
    403: "Access denied.",
    404: "The requested record does not exist.",
    422: "Query parameters or body failed validation.",
    503: "The database or PostGIS is unavailable.",
}


def errors(*statuses: int) -> dict[int | str, dict]:
    """Document the shared error envelope for the statuses a route can return."""
    return {
        status: {"model": ErrorEnvelope, "description": _ERROR_DESCRIPTIONS[status]}
        for status in statuses
    }


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500, pattern=r"^https://")

    @model_validator(mode="after")
    def nonnull_name(self):
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("Display name cannot be null")
        return self
