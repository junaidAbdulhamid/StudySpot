"""Normalize times; quarantine invalid values with aggregate counts only."""

import pandas as pd

from ml.src.extraction import SOURCES
from ml.src.snapshot import check_source_columns


def normalize(tables):
    check_source_columns(tables)
    result, quality = {}, {}
    ids = set(tables["locations"].location_id)
    if tables["locations"].location_id.duplicated().any():
        raise ValueError("Duplicate locations")
    for name, original in tables.items():
        frame = original.copy()
        for column in frame.columns:
            if column.endswith("_at"):
                # Naive timestamps must never silently acquire a timezone.
                nonnull = frame[column].dropna()
                if any(pd.Timestamp(x).tzinfo is None for x in nonnull):
                    raise ValueError(f"Naive timestamp in {name}.{column}")
                frame[column] = pd.to_datetime(frame[column], utc=True)
        duplicates = 0
        if "id" in frame:
            duplicates = int(frame.duplicated().sum())
            frame = frame.drop_duplicates()
            if frame.id.duplicated().any():
                raise ValueError(f"Conflicting event IDs in {name}")
        valid = pd.Series(True, index=frame.index)
        if name in SOURCES:
            event = SOURCES[name][1]
            valid &= frame[event].notna() & frame.created_at.notna() & frame.location_id.isin(ids)
            frame["available_at"] = frame[[event, "created_at"]].max(axis=1)
        for column in ("occupancy_percent", "normalized_value"):
            if column in frame:
                values = pd.to_numeric(frame[column], errors="coerce")
                valid &= values.between(0, 100) | (frame[column].isna() & (name == "estimates"))
                frame[column] = values
        for column in ("confidence_score", "user_reliability_at_submission"):
            if column in frame:
                valid &= pd.to_numeric(frame[column], errors="coerce").between(0, 1)
        if name == "estimates":
            valid &= frame.signal_count.ge(0)
        if name == "observations":
            exact = frame.occupied_seats.notna() | frame.total_seats.notna()
            valid &= ~exact | (
                frame.total_seats.gt(0)
                & frame.occupied_seats.ge(0)
                & frame.occupied_seats.le(frame.total_seats)
            )
        if name == "checkins":
            valid &= frame.expires_at.gt(frame.checked_in_at)
            valid &= frame.checked_out_at.isna() | frame.checked_out_at.ge(frame.checked_in_at)
            valid &= frame.updated_at.notna()
            frame["checkout_available_at"] = (
                frame[["checked_out_at", "updated_at", "created_at"]]
                .max(axis=1)
                .where(frame.checked_out_at.notna())
            )
        if name == "validations":
            valid &= frame.validation_type.isin(["accurate", "more_crowded", "less_crowded"])
        if name == "locations":
            valid &= frame.capacity.ge(0) & frame.available_at.notna()
        if name == "weather" and len(frame):
            valid &= frame.temperature_c.between(-90, 60) & frame.precipitation_mm.ge(0)
            valid &= frame.observed_at.notna() & frame.available_at.notna()
        if name == "calendar" and len(frame):
            if frame.duplicated(["campus_id", "date"]).any():
                raise ValueError("Duplicate academic calendar dates")
            valid &= frame.academic_period.isin(
                ["REGULAR", "MIDTERM", "READING_DAY", "FINAL_EXAM", "BREAK", "HOLIDAY"]
            )
            valid &= frame.available_at.notna()
        quality[name] = {
            "input": len(original),
            "duplicates_removed": duplicates,
            "invalid_removed": int((~valid).sum()),
        }
        result[name] = frame.loc[valid].reset_index(drop=True)
    return result, quality
