"""Deterministic current-occupancy estimate; categories are assumptions, not headcounts."""

from dataclasses import dataclass
from datetime import datetime
from math import exp, log

from app.models.enums import ConfidenceLevel, CrowdLevel

NORMALIZED = {
    CrowdLevel.LOTS_OF_SEATS: 20,
    CrowdLevel.MODERATE: 50,
    CrowdLevel.BUSY: 75,
    CrowdLevel.NEARLY_FULL: 92,
}


@dataclass(frozen=True)
class ReportSignal:
    value: int
    at: datetime
    reliability: float
    verified: bool


@dataclass(frozen=True)
class EstimateResult:
    percent: int | None
    confidence_score: float
    confidence: ConfidenceLevel
    signal_count: int


def estimate_occupancy(
    now: datetime,
    reports: list[ReportSignal],
    active_checkins: int = 0,
    accurate_validations: int = 0,
    disagreeing_validations: int = 0,
    manual_percent: int | None = None,
    manual_at: datetime | None = None,
    half_life_minutes: int = 25,
) -> EstimateResult:
    weighted: list[tuple[int, float]] = []
    for item in reports:
        age = max(0, (now - item.at).total_seconds() / 60)
        if age > 120:
            continue
        weight = exp(-log(2) * age / half_life_minutes)
        weight *= 0.6 + 0.8 * max(0.2, min(1, item.reliability))
        weight *= 1.25 if item.verified else 0.8
        weighted.append((item.value, weight))
    trusted = (
        manual_percent is not None
        and manual_at is not None
        and (0 <= (now - manual_at).total_seconds() <= 3600)
    )
    count = (
        len(weighted)
        + active_checkins
        + accurate_validations
        + disagreeing_validations
        + int(trusted)
    )
    if not weighted and not trusted:
        return EstimateResult(None, 0, ConfidenceLevel.LOW, count)

    if weighted:
        ordered = sorted(weighted)
        midpoint = sum(weight for _, weight in ordered) / 2
        cumulative = 0.0
        robust = ordered[-1][0]
        for index, (value, weight) in enumerate(ordered):
            cumulative += weight
            if cumulative >= midpoint:
                robust = (
                    round((value + ordered[index + 1][0]) / 2)
                    if abs(cumulative - midpoint) < 1e-9 and index + 1 < len(ordered)
                    else value
                )
                break
        agreement = 1 - min(
            1,
            sum(weight * abs(value - robust) for value, weight in weighted)
            / (100 * sum(weight for _, weight in weighted)),
        )
        strength = sum(weight for _, weight in weighted)
        score = min(0.7, strength / (strength + 3)) * agreement
        score += min(0.07, active_checkins * 0.015)
        score += min(0.12, accurate_validations * 0.025)
        score -= min(0.2, disagreeing_validations * 0.04)
    else:
        robust, score = manual_percent, 0
    if trusted:
        robust = round((robust * 0.35 + manual_percent * 0.65) if weighted else manual_percent)
        score = max(score, 0.75)
    percent = max(0, min(100, round(robust)))
    score = max(0, min(1, round(score, 3)))
    confidence = (
        ConfidenceLevel.HIGH
        if score >= 0.7
        else ConfidenceLevel.MEDIUM
        if score >= 0.4
        else ConfidenceLevel.LOW
    )
    return EstimateResult(percent, score, confidence, count)


def effective_confidence(
    score: float, estimated_at: datetime, now: datetime, half_life_minutes: int = 45
) -> tuple[float, ConfidenceLevel]:
    age_minutes = max(0, (now - estimated_at).total_seconds() / 60)
    effective = round(score * exp(-log(2) * age_minutes / half_life_minutes), 3)
    label = (
        ConfidenceLevel.HIGH
        if effective >= 0.7
        else ConfidenceLevel.MEDIUM
        if effective >= 0.4
        else ConfidenceLevel.LOW
    )
    return effective, label
