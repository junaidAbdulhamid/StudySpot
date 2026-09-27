from datetime import datetime, time

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Created, Identity, Timestamps
from app.models.enums import (
    ConfidenceLevel,
    NoiseLevel,
    NoisePreference,
    OccupancySource,
    StudyStyle,
)


def enum_type(cls):
    return Enum(
        cls,
        values_callable=lambda e: [x.value for x in e],
        native_enum=False,
        create_constraint=True,
        name=cls.__name__.lower(),
        validate_strings=True,
    )


location_amenities = Table(
    "location_amenities",
    Base.metadata,
    Column("location_id", ForeignKey("study_locations.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)
preference_amenities = Table(
    "preference_amenities",
    Base.metadata,
    Column(
        "preference_id", ForeignKey("user_preferences.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)


class Campus(Identity, Timestamps, Base):
    __tablename__ = "campuses"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude"),
    )
    name: Mapped[str] = mapped_column(String(160))
    university_name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    timezone: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    buildings: Mapped[list["Building"]] = relationship(
        back_populates="campus", passive_deletes=True
    )


class Building(Identity, Timestamps, Base):
    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint("campus_id", "name"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude"),
    )
    campus_id: Mapped[str] = mapped_column(
        ForeignKey("campuses.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    short_name: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(300))
    campus: Mapped[Campus] = relationship(back_populates="buildings")
    locations: Mapped[list["StudyLocation"]] = relationship(
        back_populates="building", passive_deletes=True
    )


class Amenity(Identity, Base):
    __tablename__ = "amenities"
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    icon: Mapped[str] = mapped_column(String(80))


class StudyLocation(Identity, Timestamps, Base):
    __tablename__ = "study_locations"
    __table_args__ = (
        UniqueConstraint("building_id", "slug"),
        CheckConstraint("capacity >= 0", name="capacity"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude"),
        Index("ix_study_locations_geo_point", "geo_point", postgresql_using="gist"),
    )
    building_id: Mapped[str] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(160))
    floor: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geo_point: Mapped[WKBElement] = mapped_column(
        Geography("POINT", srid=4326, spatial_index=False),
        Computed("ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography", persisted=True),
    )
    capacity: Mapped[int] = mapped_column(Integer)
    noise_level: Mapped[NoiseLevel] = mapped_column(enum_type(NoiseLevel))
    image_url: Mapped[str | None] = mapped_column(String(500))
    opening_time: Mapped[time] = mapped_column(Time)
    closing_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    building: Mapped[Building] = relationship(back_populates="locations")
    amenities: Mapped[list[Amenity]] = relationship(
        secondary=location_amenities, order_by="Amenity.slug"
    )


class User(Identity, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("points >= 0", name="points"),
        CheckConstraint("reliability_score BETWEEN 0 AND 1", name="reliability"),
    )
    auth_provider_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    email: Mapped[str] = mapped_column(String(254))
    display_name: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")


class UserPreference(Identity, Timestamps, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(
            "max_walking_minutes > 0 AND max_walking_minutes <= 240", name="walking_minutes"
        ),
        CheckConstraint("study_duration_hours > 0 AND study_duration_hours <= 12", name="duration"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    noise_preference: Mapped[NoisePreference] = mapped_column(enum_type(NoisePreference))
    study_style: Mapped[StudyStyle] = mapped_column(enum_type(StudyStyle))
    max_walking_minutes: Mapped[int] = mapped_column(Integer)
    study_duration_hours: Mapped[float] = mapped_column(Float, default=1, server_default="1")
    preferred_amenities: Mapped[list[Amenity]] = relationship(
        secondary=preference_amenities, order_by="Amenity.slug"
    )


class Favorite(Identity, Created, Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "location_id"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[str] = mapped_column(
        ForeignKey("study_locations.id", ondelete="CASCADE"), index=True
    )


class OccupancyEstimate(Identity, Created, Base):
    __tablename__ = "occupancy_estimates"
    __table_args__ = (
        CheckConstraint("occupancy_percent BETWEEN 0 AND 100", name="percent"),
        Index("ix_estimates_location_time", "location_id", "estimated_at"),
    )
    location_id: Mapped[str] = mapped_column(ForeignKey("study_locations.id", ondelete="CASCADE"))
    occupancy_percent: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[ConfidenceLevel] = mapped_column(enum_type(ConfidenceLevel))
    source: Mapped[OccupancySource] = mapped_column(enum_type(OccupancySource))
    estimated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class OccupancyObservation(Identity, Created, Base):
    __tablename__ = "occupancy_observations"
    __table_args__ = (
        CheckConstraint("occupancy_percent BETWEEN 0 AND 100", name="percent"),
        CheckConstraint("occupied_seats >= 0", name="occupied_seats"),
        CheckConstraint("total_seats >= 0", name="total_seats"),
        CheckConstraint("occupied_seats <= total_seats", name="seat_counts"),
        Index("ix_observations_location_time", "location_id", "observed_at"),
    )
    location_id: Mapped[str] = mapped_column(ForeignKey("study_locations.id", ondelete="CASCADE"))
    occupancy_percent: Mapped[int] = mapped_column(Integer)
    occupied_seats: Mapped[int | None] = mapped_column(Integer)
    total_seats: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[OccupancySource] = mapped_column(enum_type(OccupancySource))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OccupancyPrediction(Identity, Created, Base):
    __tablename__ = "occupancy_predictions"
    __table_args__ = (
        CheckConstraint("predicted_occupancy BETWEEN 0 AND 100", name="percent"),
        UniqueConstraint("location_id", "target_time", "model_version"),
        Index("ix_predictions_location_time", "location_id", "target_time"),
    )
    location_id: Mapped[str] = mapped_column(ForeignKey("study_locations.id", ondelete="CASCADE"))
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    predicted_occupancy: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[ConfidenceLevel] = mapped_column(enum_type(ConfidenceLevel))
    model_version: Mapped[str] = mapped_column(String(80))
    source: Mapped[OccupancySource] = mapped_column(
        enum_type(OccupancySource), default=OccupancySource.SEED
    )
