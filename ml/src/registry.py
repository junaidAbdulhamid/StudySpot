"""Explicit feature allowlist and machine-readable lineage for Phase 7."""


def feature_registry(config):
    registry = {}

    def add(names, source, description, dtype="float", bounds=None):
        for name in names.split():
            registry[name] = {
                "type": dtype,
                "source": source,
                "description": description,
                "range": bounds,
                "inference_available": True,
                "leakage_control": "Events and knowledge time <= prediction time; location-local computation",
            }

    add(
        "occupancy_now",
        "OccupancyEstimate",
        "Latest non-seed estimate known at T within configured age",
        bounds=[0, 100],
    )
    add(
        "current_confidence_score",
        "OccupancyEstimate",
        "Confidence decayed from estimate event time",
        bounds=[0, 1],
    )
    add(
        "recent_signal_count signal_age_seconds",
        "OccupancyEstimate",
        "Latest estimate's signal count / age in seconds; absent count is zero",
    )
    add(
        "active_checkins",
        "CheckIn",
        "Known starts minus known checkout or scheduled expiry; not physical headcount",
        "int",
    )
    add(
        "capacity",
        "StudyLocation",
        "Latest metadata only after its available_at; no retroactive metadata inference",
    )
    add(
        "noise_level floor building_id campus_id",
        "StudyLocation/Building/Campus",
        "Categorical metadata known at T",
        "string",
    )
    add(
        "metadata_missing occupancy_missing weather_missing calendar_missing",
        "Pipeline",
        "Explicit absence indicator",
        "bool",
    )
    add(
        "hour_of_day minute_of_hour day_of_week month week_of_year",
        "Campus.timezone",
        "Local wall time components; Monday=0; ISO week",
        "int",
    )
    add("is_weekend", "Campus.timezone", "Local Saturday/Sunday", "bool")
    add(
        "sin_hour cos_hour sin_day cos_day",
        "Campus.timezone",
        "Sine/cosine at 24h and 7day periods",
        bounds=[-1, 1],
    )
    add(
        "is_open",
        "StudyLocation",
        "Known active location inside daily opening interval; overnight and DST aware",
        "bool",
    )
    add(
        "minutes_since_open minutes_until_close",
        "StudyLocation",
        "Elapsed real minutes; null when closed or metadata unknown",
    )
    add(
        "academic_period",
        "AcademicCalendar import",
        "Local date join using calendar published by T, else UNKNOWN",
        "string",
    )
    add(
        "is_exam_period is_class_day is_holiday",
        "AcademicCalendar import",
        "Nullable calendar flags; unknown is not false",
        "bool",
    )
    add(
        "temperature_c precipitation_mm",
        "Weather import",
        "Latest observed weather known by T, maximum age 60 minutes; never future actuals",
    )
    for window in config.report_windows:
        add(
            f"report_count_{window}m",
            "CrowdReport",
            f"Number of known reports in (T-{window}m,T]",
            "int",
        )
    add(
        "mean_report_value_30m weighted_report_value_30m report_std_30m",
        "CrowdReport",
        "Known 30m values: mean, submission-reliability weighted mean, population standard deviation; null if no reports",
    )
    add(
        "verified_report_fraction_30m mean_report_reliability_30m",
        "CrowdReport",
        "Known 30m mean verified flag / immutable submission reliability",
        bounds=[0, 1],
    )
    for window in (15, 30):
        add(
            f"checkins_started_{window}m checkouts_{window}m",
            "CheckIn",
            f"Known event count in (T-{window}m,T]; later checkout excluded",
            "int",
        )
    add(
        "net_checkin_change_30m",
        "CheckIn",
        "Known starts minus known checkouts in 30m; excludes scheduled expiry",
        "int",
    )
    add(
        "validations_accurate_30m validations_more_crowded_30m validations_less_crowded_30m",
        "OccupancyValidation",
        "Known validation category counts in (T-30m,T]",
        "int",
    )
    add(
        "validation_agreement_rate",
        "OccupancyValidation",
        "Accurate / all known validations in 30m, null for none",
        bounds=[0, 1],
    )
    for window in config.lag_minutes:
        add(
            f"occupancy_lag_{window}m",
            "OccupancyEstimate",
            f"occupancy_now reconstructed at exactly T-{window}m",
            bounds=[0, 100],
        )
        add(f"occupancy_lag_{window}m_missing", "Pipeline", "Lag unavailable", "bool")
    for window in config.rolling_minutes:
        add(
            f"occupancy_rolling_mean_{window}m occupancy_rolling_std_{window}m",
            "OccupancyEstimate",
            f"Mean / population std of known bucket values in (T-{window}m,T]; skips missing",
        )
        add(
            f"occupancy_rolling_count_{window}m",
            "OccupancyEstimate",
            f"Number of non-null bucket values in (T-{window}m,T]",
        )
    if 60 in config.lag_minutes:
        add(
            "occupancy_trend_60m",
            "OccupancyEstimate",
            "occupancy_now minus lag at T-60m",
            bounds=[-100, 100],
        )
    return registry
