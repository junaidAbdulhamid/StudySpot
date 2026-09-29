"""Idempotent demo seed: preserves existing user choices; refreshes only seed telemetry."""

import json
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models import (
    Amenity,
    Building,
    Campus,
    Favorite,
    OccupancyEstimate,
    OccupancyObservation,
    OccupancyPrediction,
    StudyLocation,
    User,
    UserPreference,
)
from app.models.enums import ConfidenceLevel, NoisePreference, OccupancySource, StudyStyle

DATA = json.loads(Path(__file__).with_name("phase1.json").read_text())


def slug(value: str) -> str:
    return value.lower().replace(" ", "-")


def seed(db: Session, dev_user_id: str) -> dict[str, int]:
    # Serialize seed commands so even concurrent runs are deterministic.
    db.execute(text("SELECT pg_advisory_xact_lock(72499123)"))
    campus = db.get(Campus, "gmu-fairfax")
    if campus is None:
        campus = Campus(
            id="gmu-fairfax",
            name="Fairfax Campus",
            university_name="George Mason University",
            slug="gmu-fairfax",
            timezone="America/New_York",
            latitude=DATA["campus"]["latitude"],
            longitude=DATA["campus"]["longitude"],
        )
        db.add(campus)
        db.flush()
    amenities = {}
    for name in [*DATA["amenities"], "Quiet zone"]:
        identifier = slug(name)
        item = db.scalar(select(Amenity).where(Amenity.slug == identifier))
        if item is None:
            item = Amenity(
                id=identifier,
                name=name,
                slug=identifier,
                icon="flash-outline" if name == "Outlets" else "grid-outline",
            )
            db.add(item)
        amenities[name] = item
    db.flush()
    now = datetime.now(UTC).replace(microsecond=0)
    next_hour = now.replace(minute=0, second=0) + timedelta(hours=1)
    for zone in DATA["locations"]:
        building_id = slug(zone["building"])
        building = db.get(Building, building_id)
        if building is None:
            building = Building(
                id=building_id,
                campus_id=campus.id,
                name=zone["building"],
                short_name=zone["building"],
                latitude=zone["latitude"],
                longitude=zone["longitude"],
                address=None,
            )
            db.add(building)
            db.flush()
        location = db.get(StudyLocation, zone["id"])
        if location is None:
            location = StudyLocation(
                id=zone["id"],
                building_id=building.id,
                name=zone["name"],
                slug=slug(zone["floor"]),
                floor=zone["floor"],
                description=zone["description"],
                latitude=zone["latitude"],
                longitude=zone["longitude"],
                capacity=zone["capacity"],
                noise_level=zone["noiseLevel"],
                image_url=None,
                opening_time=time.fromisoformat(zone["hours"]["open"]),
                closing_time=time.fromisoformat(zone["hours"]["close"]),
                amenities=[amenities[name] for name in zone["amenities"]],
            )
            db.add(location)
            db.flush()
        # Remove seed-only telemetry. Never overwrite future manually collected observations.
        for model in (OccupancyEstimate, OccupancyObservation, OccupancyPrediction):
            db.execute(
                delete(model).where(
                    model.location_id == location.id, model.source == OccupancySource.SEED
                )
            )
        for i, prediction in enumerate(zone["predictions"][1:]):
            db.add(
                OccupancyPrediction(
                    id=f"seed-prediction-{location.id}-{i}",
                    location_id=location.id,
                    target_time=next_hour + timedelta(hours=i),
                    predicted_occupancy=prediction["percent"],
                    confidence=ConfidenceLevel.MEDIUM,
                    model_version="seed-v1",
                    source=OccupancySource.SEED,
                )
            )
        for i, percent in enumerate(zone["historical"]):
            db.add(
                OccupancyObservation(
                    id=f"seed-observation-{location.id}-{i}",
                    location_id=location.id,
                    occupancy_percent=percent,
                    occupied_seats=round(zone["capacity"] * percent / 100),
                    total_seats=zone["capacity"],
                    source=OccupancySource.SEED,
                    observed_at=now - timedelta(hours=(8 - i) * 2),
                )
            )
    user = db.get(User, dev_user_id)
    new_user = user is None
    if new_user:
        user = User(
            id=dev_user_id, email="dev@studyspot.local", display_name="Alex Morgan", avatar_url=None
        )
        db.add(user)
        db.flush()
    preference = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if preference is None:
        db.add(
            UserPreference(
                id=f"preferences-{user.id}",
                user_id=user.id,
                noise_preference=NoisePreference.QUIET,
                study_style=StudyStyle.SOLO,
                max_walking_minutes=10,
                study_duration_hours=1,
                preferred_amenities=[amenities["Outlets"]],
            )
        )
    if new_user:
        for zone in DATA["locations"]:
            if zone["isFavorite"]:
                db.add(Favorite(user_id=user.id, location_id=zone["id"]))
    db.commit()
    return {"locations": len(DATA["locations"]), "predictions": len(DATA["locations"]) * 4}


def main():
    settings = get_settings()
    if settings.app_env not in {"development", "test"} or not settings.dev_user_enabled:
        raise SystemExit("Seed requires development/test with DEV_USER_ENABLED=true")
    with get_session_factory()() as db:
        print(json.dumps(seed(db, settings.dev_user_id)))


if __name__ == "__main__":
    main()
