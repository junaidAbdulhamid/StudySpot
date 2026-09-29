"""Seeded development data; never writes fake contributions into the application DB."""

import math

import numpy as np
import pandas as pd

from ml.src.config import utc
from ml.src.extraction import SOURCES
from ml.src.snapshot import ALLOWED


def generate_history(start="2026-09-01T00:00:00Z", days=7, locations=3, seed=42):
    if not 1 <= days <= 366 or not 1 <= locations <= 100:
        raise ValueError("Development generator supports 1..366 days and 1..100 locations")
    rng = np.random.default_rng(seed)
    start = utc(start)
    end = start + pd.Timedelta(days=days)
    times = pd.date_range(start, end, freq="15min", inclusive="left")
    data = {name: [] for name in ALLOWED}
    truth = []
    known = start - pd.Timedelta(days=365)
    for day in pd.date_range(start.floor("D") - pd.Timedelta(days=1), end.ceil("D"), freq="D"):
        exam = day.day % 9 == 0
        holiday = day.day % 13 == 0
        data["calendar"].append(
            {
                "date": str(day.date()),
                "campus_id": "synthetic-campus",
                "academic_period": "HOLIDAY" if holiday else "FINAL_EXAM" if exam else "REGULAR",
                "is_class_day": day.dayofweek < 5 and not holiday,
                "is_exam_period": exam,
                "is_holiday": holiday,
                "available_at": known,
            }
        )
    for number in range(locations):
        location_id = f"synthetic-location-{number}"
        capacity = int(rng.integers(60, 200))
        data["locations"].append(
            {
                "location_id": location_id,
                "campus_id": "synthetic-campus",
                "building_id": f"synthetic-building-{number // 2}",
                "capacity": capacity,
                "noise_level": ["quiet", "moderate", "social"][number % 3],
                "floor": str(number + 1),
                "timezone": "America/New_York",
                "opening_time": "07:00:00",
                "closing_time": "01:00:00",
                "is_active": True,
                "available_at": known,
            }
        )
        for index, timestamp in enumerate(times):
            local = timestamp.tz_convert("America/New_York")
            hour = local.hour + local.minute / 60
            value = 12 + 55 * math.exp(-(((hour - 14 - number * 0.3) / 4) ** 2))
            value *= 0.65 if local.dayofweek >= 5 else 1
            value += 15 if local.day % 9 == 0 else 0
            value *= 0.4 if local.day % 13 == 0 else 1
            value += rng.normal(0, 7) + (25 if rng.random() < 0.015 else 0)
            value = float(np.clip(value, 0, 100)) if hour >= 7 or hour < 1 else 0.0
            truth.append(
                {"location_id": location_id, "timestamp": timestamp, "true_occupancy": value}
            )
            base = {"location_id": location_id}
            if rng.random() > 0.12:
                data["estimates"].append(
                    dict(
                        base,
                        id=f"e-{number}-{index}",
                        estimated_at=timestamp,
                        created_at=timestamp,
                        occupancy_percent=float(np.clip(value + rng.normal(0, 8), 0, 100)),
                        confidence_score=float(rng.uniform(0.3, 0.9)),
                        signal_count=int(rng.integers(1, 15)),
                        source="crowd_report",
                    )
                )
            if index % 4 == 0 and rng.random() > 0.25:
                data["observations"].append(
                    dict(
                        base,
                        id=f"o-{number}-{index}",
                        observed_at=timestamp,
                        created_at=timestamp + pd.Timedelta(minutes=int(rng.choice([0, 0, 20]))),
                        occupied_seats=round(value * capacity / 100),
                        total_seats=capacity,
                        occupancy_percent=round(value),
                        source="manual",
                    )
                )
            for report in range(int(rng.poisson(1.5 if value > 20 else 0.3))):
                submitted = timestamp + pd.Timedelta(minutes=int(rng.integers(0, 15)))
                reported = float(np.clip(value + rng.normal(0, 18), 0, 100))
                if rng.random() < 0.01:
                    reported = 180.0  # Deliberate quarantined corrupt row.
                data["reports"].append(
                    dict(
                        base,
                        id=f"r-{number}-{index}-{report}",
                        submitted_at=submitted,
                        created_at=submitted + pd.Timedelta(minutes=int(rng.choice([0, 0, 0, 20]))),
                        normalized_value=reported,
                        location_verified=bool(rng.random() < 0.7),
                        user_reliability_at_submission=float(rng.uniform(0.3, 1)),
                    )
                )
            if rng.random() < value / 250:
                checkout = timestamp + pd.Timedelta(minutes=int(rng.integers(15, 180)))
                data["checkins"].append(
                    dict(
                        base,
                        id=f"c-{number}-{index}",
                        checked_in_at=timestamp,
                        created_at=timestamp,
                        checked_out_at=checkout,
                        updated_at=checkout + pd.Timedelta(minutes=int(rng.choice([0, 0, 15]))),
                        expires_at=timestamp + pd.Timedelta(hours=4),
                    )
                )
            if rng.random() < 0.12:
                data["validations"].append(
                    dict(
                        base,
                        id=f"v-{number}-{index}",
                        submitted_at=timestamp,
                        created_at=timestamp,
                        validation_type=str(
                            rng.choice(
                                ["accurate", "more_crowded", "less_crowded"], p=[0.7, 0.15, 0.15]
                            )
                        ),
                    )
                )
    frames = {
        name: pd.DataFrame(
            rows, columns=SOURCES[name][2] if name in SOURCES else sorted(ALLOWED[name])
        )
        for name, rows in data.items()
    }
    return (
        frames,
        {
            "synthetic": True,
            "seed": seed,
            "source_start": start.isoformat(),
            "source_end": end.isoformat(),
            "generator_version": "0.6.0",
        },
        pd.DataFrame(truth),
    )
