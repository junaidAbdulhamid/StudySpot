"""Bounded, identity-free extraction in a consistent read-only PostgreSQL snapshot."""

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import bindparam, create_engine, text

from ml.src.config import utc

SOURCES = {
    "estimates": (
        "occupancy_estimates",
        "estimated_at",
        [
            "id",
            "location_id",
            "estimated_at",
            "created_at",
            "occupancy_percent",
            "confidence_score",
            "signal_count",
            "source",
        ],
    ),
    "observations": (
        "occupancy_observations",
        "observed_at",
        [
            "id",
            "location_id",
            "observed_at",
            "created_at",
            "occupancy_percent",
            "occupied_seats",
            "total_seats",
            "source",
        ],
    ),
    "reports": (
        "crowd_reports",
        "submitted_at",
        [
            "id",
            "location_id",
            "submitted_at",
            "created_at",
            "normalized_value",
            "location_verified",
            "user_reliability_at_submission",
        ],
    ),
    "checkins": (
        "checkins",
        "checked_in_at",
        [
            "id",
            "location_id",
            "checked_in_at",
            "created_at",
            "checked_out_at",
            "expires_at",
            "updated_at",
        ],
    ),
    "validations": (
        "occupancy_validations",
        "submitted_at",
        [
            "id",
            "location_id",
            "submitted_at",
            "created_at",
            "validation_type",
        ],
    ),
}


def extract_source(connection, name, start, end, location_ids):
    table, event_time, columns = SOURCES[name]
    # Identifiers are internal constants; all caller input is bound.
    lower = "expires_at >= :start" if name == "checkins" else f"{event_time} >= :start"
    query = text(
        f"SELECT {', '.join(columns)} FROM {table} "
        f"WHERE {lower} AND {event_time} < :end AND location_id IN :locations "
        f"ORDER BY location_id, {event_time}, id"
    ).bindparams(bindparam("locations", expanding=True))
    chunks = pd.read_sql_query(
        query,
        connection,
        params={
            "start": start.to_pydatetime(),
            "end": end.to_pydatetime(),
            "locations": location_ids,
        },
        chunksize=10_000,
    )
    frames = list(chunks)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)


def extract_database(url, config):
    engine = create_engine(url)
    start = utc(config.start) - pd.Timedelta(minutes=config.lookback_minutes)
    end = utc(config.end) + pd.Timedelta(minutes=max(config.horizons))
    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text("SET LOCAL statement_timeout = '60s'"))
                query = text("""
                    SELECT l.id AS location_id, l.capacity, l.noise_level, l.floor,
                           l.opening_time, l.closing_time, l.is_active,
                           b.id AS building_id, c.id AS campus_id, c.timezone,
                           GREATEST(l.updated_at, b.updated_at, c.updated_at) AS available_at
                    FROM study_locations l JOIN buildings b ON b.id = l.building_id
                    JOIN campuses c ON c.id = b.campus_id
                """)
                locations = pd.read_sql_query(query, conn)
                if config.location_ids:
                    locations = locations[locations.location_id.isin(config.location_ids)]
                locations = locations.copy()
                for column in ("opening_time", "closing_time"):
                    locations[column] = locations[column].astype(str)
                ids = locations.location_id.tolist()
                snapshot = {name: extract_source(conn, name, start, end, ids) for name in SOURCES}
                snapshot["locations"] = locations
                snapshot["calendar"] = pd.DataFrame()
                snapshot["weather"] = pd.DataFrame()
    finally:
        engine.dispose()
    return snapshot, {
        "synthetic": False,
        "extracted_at": datetime.now(UTC).isoformat(),
        "source_start": start.isoformat(),
        "source_end": end.isoformat(),
        "knowledge_time_policy": "max(event_time, created_at); checkout max(event_time, updated_at)",
    }
