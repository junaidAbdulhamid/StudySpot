"""Durable crowd contributions and aggregate occupancy. Redis is disposable."""

import json
from datetime import UTC, datetime, timedelta

from geoalchemy2 import Geography
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models import (
    CheckIn,
    CrowdReport,
    OccupancyEstimate,
    OccupancyObservation,
    OccupancyValidation,
    StudyLocation,
    User,
)
from app.models.enums import CheckInStatus, OccupancySource, ValidationType
from app.services.occupancy_estimator import NORMALIZED, ReportSignal, estimate_occupancy


def cache_key(location_id: str) -> str:
    return f"studyspot:occupancy:{location_id}"


def report_limit_key(user_id: str, location_id: str) -> str:
    return f"studyspot:ratelimit:report:{user_id}:{location_id}"


def estimate_payload(estimate: OccupancyEstimate) -> dict:
    return {
        "estimate_id": estimate.id,
        "occupancy_percent": estimate.occupancy_percent,
        "confidence_score": estimate.confidence_score,
        "confidence_label": estimate.confidence.value,
        "updated_at": estimate.estimated_at.isoformat(),
        "signal_count": estimate.signal_count,
        "signal_summary": {
            "recent_reports": estimate.recent_report_count,
            "active_checkins": estimate.active_checkin_count,
            "recent_validations": estimate.recent_validation_count,
            "trusted_observation": estimate.manual_observation_used,
        },
    }


def redis_client():
    return Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=0.15,
        socket_timeout=0.15,
        decode_responses=True,
    )


def publish_cache(location_id: str, estimate: OccupancyEstimate) -> None:
    if get_settings().app_env == "test":
        return
    try:
        redis_client().setex(cache_key(location_id), 60, json.dumps(estimate_payload(estimate)))
    except RedisError:
        pass


def verify_proximity(
    db: Session, location: StudyLocation, latitude, longitude
) -> tuple[bool, float | None]:
    if latitude is None or longitude is None:
        return False, None
    origin = cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )
    distance = db.scalar(
        select(func.ST_Distance(StudyLocation.geo_point, origin)).where(
            StudyLocation.id == location.id
        )
    )
    return distance <= get_settings().checkin_radius_meters, round(distance, 1)


class OccupancyService:
    def __init__(self, db: Session):
        self.db = db

    def location(self, location_id: str):
        row = self.db.scalar(
            select(StudyLocation)
            .where(StudyLocation.id == location_id, StudyLocation.is_active.is_(True))
            .with_for_update()
        )
        if row is None:
            raise AppError("LOCATION_NOT_FOUND", "Study location was not found.")
        return row

    def current(self, location_id: str):
        if self.db.get(StudyLocation, location_id) is None:
            raise AppError("LOCATION_NOT_FOUND", "Study location was not found.")
        return self.db.scalar(
            select(OccupancyEstimate)
            .where(
                OccupancyEstimate.location_id == location_id,
                OccupancyEstimate.estimated_at
                >= datetime.now(UTC) - timedelta(minutes=get_settings().occupancy_max_age_minutes),
                OccupancyEstimate.source != OccupancySource.SEED,
            )
            .order_by(OccupancyEstimate.estimated_at.desc(), OccupancyEstimate.id.desc())
            .limit(1)
        )

    def current_payload(self, location_id: str) -> dict | None:
        if self.db.get(StudyLocation, location_id) is None:
            raise AppError("LOCATION_NOT_FOUND", "Study location was not found.")
        if get_settings().app_env != "test":
            try:
                cached = redis_client().get(cache_key(location_id))
                if cached:
                    snapshot = json.loads(cached)
                    if datetime.fromisoformat(snapshot["updated_at"]) >= datetime.now(
                        UTC
                    ) - timedelta(minutes=get_settings().occupancy_max_age_minutes):
                        return snapshot
            except (RedisError, ValueError, TypeError):
                pass
        row = self.current(location_id)
        if row:
            publish_cache(location_id, row)
            return estimate_payload(row)
        return None

    def recompute(self, location_id: str, now: datetime):
        window = now - timedelta(hours=2)
        reports = self.db.scalars(
            select(CrowdReport).where(
                CrowdReport.location_id == location_id,
                CrowdReport.submitted_at >= window,
            )
        ).all()
        active = (
            self.db.scalar(
                select(func.count())
                .select_from(CheckIn)
                .where(
                    CheckIn.location_id == location_id,
                    CheckIn.status == CheckInStatus.ACTIVE,
                    CheckIn.expires_at > now,
                )
            )
            or 0
        )
        validations = self.db.scalars(
            select(OccupancyValidation).where(
                OccupancyValidation.location_id == location_id,
                OccupancyValidation.submitted_at >= window,
            )
        ).all()
        manual = self.db.scalar(
            select(OccupancyObservation)
            .where(
                OccupancyObservation.location_id == location_id,
                OccupancyObservation.source == OccupancySource.MANUAL,
                OccupancyObservation.observed_at <= now,
            )
            .order_by(OccupancyObservation.observed_at.desc())
            .limit(1)
        )
        result = estimate_occupancy(
            now,
            [
                ReportSignal(
                    r.normalized_value,
                    r.submitted_at,
                    r.user_reliability_at_submission,
                    r.location_verified,
                )
                for r in reports
            ],
            active_checkins=active,
            accurate_validations=sum(
                v.validation_type == ValidationType.ACCURATE for v in validations
            ),
            disagreeing_validations=sum(
                v.validation_type != ValidationType.ACCURATE for v in validations
            ),
            manual_percent=manual.occupancy_percent if manual else None,
            manual_at=manual.observed_at if manual else None,
            half_life_minutes=get_settings().report_half_life_minutes,
        )
        row = OccupancyEstimate(
            location_id=location_id,
            occupancy_percent=result.percent,
            confidence=result.confidence,
            confidence_score=result.confidence_score,
            signal_count=result.signal_count,
            recent_report_count=len(reports),
            active_checkin_count=active,
            recent_validation_count=len(validations),
            manual_observation_used=bool(
                manual and 0 <= (now - manual.observed_at).total_seconds() <= 3600
            ),
            source=OccupancySource.DERIVED,
            estimated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def assess_reliability(self, location_id: str, estimate: OccupancyEstimate, now: datetime):
        """Tiny, one-time changes only after independent recent consensus exists."""
        if estimate.occupancy_percent is None or estimate.confidence_score < 0.4:
            return
        reports = self.db.scalars(
            select(CrowdReport).where(
                CrowdReport.location_id == location_id,
                CrowdReport.submitted_at >= now - timedelta(minutes=30),
            )
        ).all()
        if len({report.user_id for report in reports}) < 3:
            return
        for report in reports:
            if report.reliability_evaluated_at is not None:
                continue
            owner = self.db.get(User, report.user_id)
            difference = abs(report.normalized_value - estimate.occupancy_percent)
            delta = 0.01 if difference <= 20 else -0.01 if difference >= 40 else 0
            if delta:
                owner.reliability_score = round(
                    max(0.2, min(1, owner.reliability_score + delta)), 3
                )
            report.reliability_evaluated_at = now

    def active_checkin(self, user_id: str, now: datetime | None = None):
        now = now or datetime.now(UTC)
        return self.db.scalar(
            select(CheckIn).where(
                CheckIn.user_id == user_id,
                CheckIn.status == CheckInStatus.ACTIVE,
                CheckIn.expires_at > now,
            )
        )

    def checkin(self, user: User, location_id: str, latitude=None, longitude=None):
        now = datetime.now(UTC)
        self.db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
        location = self.location(location_id)
        prior = self.db.scalar(
            select(CheckIn)
            .where(CheckIn.user_id == user.id, CheckIn.status == CheckInStatus.ACTIVE)
            .with_for_update()
        )
        if prior and prior.expires_at > now and prior.location_id == location_id:
            return prior
        changed = {location_id}
        if prior:
            prior.status = (
                CheckInStatus.EXPIRED if prior.expires_at <= now else CheckInStatus.COMPLETED
            )
            prior.checked_out_at = min(now, prior.expires_at)
            changed.add(prior.location_id)
        verified, distance = verify_proximity(self.db, location, latitude, longitude)
        row = CheckIn(
            user_id=user.id,
            location_id=location_id,
            status=CheckInStatus.ACTIVE,
            checked_in_at=now,
            expires_at=now + timedelta(hours=get_settings().checkin_duration_hours),
            location_verified=verified,
            verification_distance_meters=distance,
        )
        self.db.add(row)
        self.db.flush()
        estimates = {identifier: self.recompute(identifier, now) for identifier in sorted(changed)}
        self.db.commit()
        for identifier, estimate in estimates.items():
            publish_cache(identifier, estimate)
        return row

    def checkout(self, user: User, checkin_id: str):
        now = datetime.now(UTC)
        self.db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
        row = self.db.scalar(
            select(CheckIn)
            .where(CheckIn.id == checkin_id, CheckIn.user_id == user.id)
            .with_for_update()
        )
        if row is None:
            raise AppError("CHECKIN_NOT_FOUND", "Check-in was not found.")
        if row.status != CheckInStatus.ACTIVE:
            return row
        self.location(row.location_id)
        row.status = CheckInStatus.EXPIRED if row.expires_at <= now else CheckInStatus.COMPLETED
        row.checked_out_at = min(now, row.expires_at)
        estimate = self.recompute(row.location_id, now)
        self.db.commit()
        publish_cache(row.location_id, estimate)
        return row

    def report(self, user: User, location_id: str, level, latitude=None, longitude=None):
        now = datetime.now(UTC)
        self.db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
        location = self.location(location_id)
        if get_settings().app_env != "test":
            try:
                if redis_client().exists(report_limit_key(user.id, location_id)):
                    raise AppError(
                        "REPORT_RATE_LIMIT",
                        "You can report this space again in a few minutes.",
                        429,
                    )
            except RedisError:
                pass
        latest = self.db.scalar(
            select(CrowdReport)
            .where(CrowdReport.user_id == user.id, CrowdReport.location_id == location_id)
            .order_by(CrowdReport.submitted_at.desc())
            .limit(1)
        )
        if latest and latest.submitted_at > now - timedelta(
            minutes=get_settings().report_cooldown_minutes
        ):
            raise AppError(
                "REPORT_RATE_LIMIT", "You can report this space again in a few minutes.", 429
            )
        verified, _ = verify_proximity(self.db, location, latitude, longitude)
        row = CrowdReport(
            user_id=user.id,
            location_id=location_id,
            crowd_level=level,
            normalized_value=NORMALIZED[level],
            submitted_at=now,
            location_verified=verified,
            user_reliability_at_submission=user.reliability_score,
        )
        self.db.add(row)
        self.db.flush()
        estimate = self.recompute(location_id, now)
        self.assess_reliability(location_id, estimate, now)
        self.db.commit()
        publish_cache(location_id, estimate)
        if get_settings().app_env != "test":
            try:
                redis_client().setex(
                    report_limit_key(user.id, location_id),
                    get_settings().report_cooldown_minutes * 60,
                    "1",
                )
            except RedisError:
                pass
        return row

    def validate(
        self, user: User, location_id: str, estimate_id: str, kind, latitude=None, longitude=None
    ):
        now = datetime.now(UTC)
        self.db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
        location = self.location(location_id)
        current = self.current(location_id)
        if current is None or current.id != estimate_id or current.occupancy_percent is None:
            raise AppError("ESTIMATE_CHANGED", "This estimate changed. Refresh and try again.", 409)
        duplicate = self.db.scalar(
            select(OccupancyValidation).where(
                OccupancyValidation.user_id == user.id,
                OccupancyValidation.estimate_id == estimate_id,
            )
        )
        if duplicate:
            raise AppError("ALREADY_VALIDATED", "You already reviewed this estimate.", 429)
        latest = self.db.scalar(
            select(OccupancyValidation)
            .where(
                OccupancyValidation.user_id == user.id,
                OccupancyValidation.location_id == location_id,
            )
            .order_by(OccupancyValidation.submitted_at.desc())
            .limit(1)
        )
        if latest and latest.submitted_at > now - timedelta(
            minutes=get_settings().validation_cooldown_minutes
        ):
            raise AppError(
                "VALIDATION_RATE_LIMIT", "You can review this space again in a few minutes.", 429
            )
        verified, _ = verify_proximity(self.db, location, latitude, longitude)
        row = OccupancyValidation(
            user_id=user.id,
            location_id=location_id,
            estimate_id=estimate_id,
            validation_type=kind,
            location_verified=verified,
            submitted_at=now,
        )
        self.db.add(row)
        self.db.flush()
        estimate = self.recompute(location_id, now)
        self.db.commit()
        publish_cache(location_id, estimate)
        return row

    def expire_due(self):
        now = datetime.now(UTC)
        rows = self.db.scalars(
            select(CheckIn)
            .where(CheckIn.status == CheckInStatus.ACTIVE, CheckIn.expires_at <= now)
            .with_for_update(skip_locked=True)
            .limit(100)
        ).all()
        changed = sorted({row.location_id for row in rows})
        for identifier in changed:
            self.location(identifier)
        for row in rows:
            row.status = CheckInStatus.EXPIRED
            row.checked_out_at = row.expires_at
        estimates = {identifier: self.recompute(identifier, now) for identifier in changed}
        self.db.commit()
        for identifier, estimate in estimates.items():
            publish_cache(identifier, estimate)
        return len(rows)
