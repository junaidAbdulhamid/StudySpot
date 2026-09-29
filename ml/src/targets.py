"""Targets can use late ground truth, but never silently treat weak evidence as truth."""

import numpy as np
import pandas as pd

from ml.src.aggregation import EventWindow, asof_rows
from ml.src.config import QUALITIES


def build_targets(tables, times, config):
    trusted = tables["observations"]
    trusted = trusted[
        (trusted.source == "manual") & trusted.total_seats.gt(0) & trusted.occupied_seats.notna()
    ]
    observations = asof_rows(
        trusted, times, "observed_at", config.observation_max_age_minutes, False
    )
    estimates = tables["estimates"]
    estimates = estimates[estimates.source != "seed"]
    estimates = asof_rows(estimates, times, "estimated_at", config.estimate_max_age_minutes, False)
    reports = EventWindow(tables["reports"], "submitted_at")
    rows = []
    for timestamp, observation, estimate in zip(times, observations, estimates, strict=True):
        value, tier, source = np.nan, QUALITIES[3], "unknown"
        if observation:
            value = observation["occupied_seats"] / observation["total_seats"] * 100
            tier, source = QUALITIES[0], "trusted_observation"
        elif estimate and pd.notna(estimate["occupancy_percent"]):
            value = estimate["occupancy_percent"]
            evidence = reports.at(estimate["estimated_at"], 30)
            confidence = estimate["confidence_score"] * 2 ** (
                -(timestamp - estimate["estimated_at"]).total_seconds()
                / 60
                / config.confidence_half_life_minutes
            )
            strong = (
                len(evidence) >= config.consensus_min_reports
                and confidence >= config.consensus_min_confidence
                and evidence.normalized_value.std(ddof=0) <= config.consensus_max_std
                and evidence.location_verified.mean() >= config.consensus_min_verified_fraction
            )
            tier, source = (
                (QUALITIES[1], "crowd_consensus") if strong else (QUALITIES[2], "weak_estimate")
            )
        rows.append(
            {
                "target_occupancy": value,
                "target_quality": tier,
                "target_weight": config.target_weights[QUALITIES.index(tier)],
                "target_source": source,
            }
        )
    return pd.DataFrame(rows, index=times)
