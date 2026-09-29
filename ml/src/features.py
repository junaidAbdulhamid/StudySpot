"""Feature definitions shared by offline builds and the Phase 7 contract."""

import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ml.src.aggregation import EventWindow, active_counts, asof_rows


def operating_hours(timestamp, opening, closing, timezone):
    local = timestamp.tz_convert(timezone)
    opening, closing = time.fromisoformat(str(opening)), time.fromisoformat(str(closing))
    date = local.date()
    if closing <= opening and local.time().replace(tzinfo=None) < closing:
        date -= timedelta(days=1)
    # Choose the earliest occurrence of ambiguous opening, latest closing; shift nonexistent times forward.
    start = pd.Timestamp(datetime.combine(date, opening)).tz_localize(
        timezone, ambiguous=True, nonexistent="shift_forward"
    )
    end_date = date + timedelta(days=int(closing <= opening))
    end = pd.Timestamp(datetime.combine(end_date, closing)).tz_localize(
        timezone, ambiguous=False, nonexistent="shift_forward"
    )
    is_open = start <= timestamp < end
    return (
        is_open,
        (timestamp - start).total_seconds() / 60 if is_open else np.nan,
        (end - timestamp).total_seconds() / 60 if is_open else np.nan,
    )


def build_features(location, tables, times, config):
    ZoneInfo(location["timezone"])
    estimates = tables["estimates"]
    estimates = estimates[estimates.source != "seed"]
    current = asof_rows(estimates, times, "estimated_at", config.estimate_max_age_minutes)
    reports = EventWindow(tables["reports"], "submitted_at")
    validations = EventWindow(tables["validations"], "submitted_at")
    checkins = EventWindow(tables["checkins"], "checked_in_at")
    checkout_events = tables["checkins"].dropna(subset=["checked_out_at"]).copy()
    checkout_events["available_at"] = checkout_events.checkout_available_at
    checkouts = EventWindow(checkout_events, "checked_out_at")
    active = active_counts(tables["checkins"], times)
    calendar = tables["calendar"]
    weather = tables["weather"]
    weather_rows = []
    if len(weather):
        weather = weather.copy()
        weather["id"] = weather.index.astype(str)
        weather_rows = asof_rows(weather, times, "observed_at", 60)
    rows = []
    for index, timestamp in enumerate(times):
        local = timestamp.tz_convert(location["timezone"])
        metadata_known = location["available_at"] <= timestamp
        is_open, since, until = operating_hours(
            timestamp, location["opening_time"], location["closing_time"], location["timezone"]
        )
        estimate = current[index]
        age = (timestamp - estimate["estimated_at"]).total_seconds() if estimate else np.nan
        row = {
            "location_id": location["location_id"],
            "timestamp": timestamp,
            "occupancy_now": estimate["occupancy_percent"] if estimate else np.nan,
            "current_confidence_score": estimate["confidence_score"]
            * 2 ** (-age / 60 / config.confidence_half_life_minutes)
            if estimate
            else np.nan,
            "recent_signal_count": estimate["signal_count"] if estimate else 0,
            "signal_age_seconds": age,
            "active_checkins": int(active[index]),
            "capacity": location["capacity"] if metadata_known else np.nan,
            "noise_level": location["noise_level"] if metadata_known else None,
            "floor": location["floor"] if metadata_known else None,
            "building_id": location["building_id"] if metadata_known else None,
            "campus_id": location["campus_id"] if metadata_known else None,
            "metadata_missing": not metadata_known,
            "hour_of_day": local.hour,
            "minute_of_hour": local.minute,
            "day_of_week": local.dayofweek,
            "is_weekend": local.dayofweek >= 5,
            "month": local.month,
            "week_of_year": local.isocalendar().week,
            "sin_hour": math.sin(2 * math.pi * (local.hour + local.minute / 60) / 24),
            "cos_hour": math.cos(2 * math.pi * (local.hour + local.minute / 60) / 24),
            "sin_day": math.sin(2 * math.pi * local.dayofweek / 7),
            "cos_day": math.cos(2 * math.pi * local.dayofweek / 7),
            "is_open": bool(is_open and metadata_known and location["is_active"]),
            "minutes_since_open": since if metadata_known else np.nan,
            "minutes_until_close": until if metadata_known else np.nan,
            "academic_period": "UNKNOWN",
            "is_exam_period": None,
            "is_class_day": None,
            "is_holiday": None,
            "temperature_c": np.nan,
            "precipitation_mm": np.nan,
            "feature_max_available_at": estimate["available_at"] if estimate else pd.NaT,
        }
        known_times = [row["feature_max_available_at"]]
        if metadata_known:
            known_times.append(location["available_at"])
        for window in config.report_windows:
            evidence = reports.at(timestamp, window)
            row[f"report_count_{window}m"] = len(evidence)
            if len(evidence):
                known_times.append(evidence.available_at.max())
        evidence = reports.at(timestamp, 30)
        weights = evidence.user_reliability_at_submission.astype(float)
        row.update(
            {
                "mean_report_value_30m": evidence.normalized_value.mean(),
                "weighted_report_value_30m": np.average(evidence.normalized_value, weights=weights)
                if len(evidence) and weights.sum()
                else np.nan,
                "report_std_30m": evidence.normalized_value.std(ddof=0),
                "verified_report_fraction_30m": evidence.location_verified.mean(),
                "mean_report_reliability_30m": weights.mean(),
            }
        )
        if len(evidence):
            known_times.append(evidence.available_at.max())
        for window in (15, 30):
            starts, ends = checkins.at(timestamp, window), checkouts.at(timestamp, window)
            row[f"checkins_started_{window}m"], row[f"checkouts_{window}m"] = len(starts), len(ends)
            known_times.extend([starts.available_at.max(), ends.available_at.max()])
        row["net_checkin_change_30m"] = row["checkins_started_30m"] - row["checkouts_30m"]
        evidence = validations.at(timestamp, 30)
        for kind in ("accurate", "more_crowded", "less_crowded"):
            row[f"validations_{kind}_30m"] = int((evidence.validation_type == kind).sum())
        row["validation_agreement_rate"] = (
            (evidence.validation_type == "accurate").mean() if len(evidence) else np.nan
        )
        known_times.append(evidence.available_at.max())
        if len(calendar):
            day = calendar[
                (calendar.date.astype(str) == str(local.date()))
                & (calendar.available_at <= timestamp)
            ]
            if len(day):
                item = day.iloc[0]
                for key in ("academic_period", "is_exam_period", "is_class_day", "is_holiday"):
                    row[key] = item[key]
                known_times.append(item.available_at)
        if weather_rows and weather_rows[index]:
            item = weather_rows[index]
            row.update({k: item[k] for k in ("temperature_c", "precipitation_mm")})
            known_times.append(item["available_at"])
        row["feature_max_available_at"] = max(
            (x for x in known_times if pd.notna(x)), default=pd.NaT
        )
        rows.append(row)
    frame = pd.DataFrame(rows).set_index("timestamp", drop=False)
    frame["occupancy_now"] = pd.to_numeric(frame.occupancy_now, errors="coerce")
    for window in config.lag_minutes:
        frame[f"occupancy_lag_{window}m"] = frame.occupancy_now.shift(
            window // config.bucket_minutes
        )
        frame[f"occupancy_lag_{window}m_missing"] = frame[f"occupancy_lag_{window}m"].isna()
    for window in config.rolling_minutes:
        rolling = frame.occupancy_now.rolling(window // config.bucket_minutes, min_periods=1)
        frame[f"occupancy_rolling_mean_{window}m"] = rolling.mean()
        frame[f"occupancy_rolling_std_{window}m"] = rolling.std(ddof=0)
        frame[f"occupancy_rolling_count_{window}m"] = rolling.count()
    if 60 in config.lag_minutes:
        frame["occupancy_trend_60m"] = frame.occupancy_now - frame.occupancy_lag_60m
    frame["occupancy_missing"] = frame.occupancy_now.isna()
    frame["weather_missing"] = frame.temperature_c.isna()
    frame["calendar_missing"] = frame.academic_period.eq("UNKNOWN")
    return frame
