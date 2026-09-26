from enum import StrEnum


class NoiseLevel(StrEnum):
    QUIET = "quiet"
    MODERATE = "moderate"
    SOCIAL = "social"


class NoisePreference(StrEnum):
    QUIET = "quiet"
    MODERATE = "moderate"
    SOCIAL = "social"
    ANY = "any"


class StudyStyle(StrEnum):
    SOLO = "solo"
    GROUP = "group"
    BOTH = "both"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OccupancySource(StrEnum):
    SEED = "seed"
    MANUAL = "manual"
    CROWD_REPORT = "crowd_report"
    MODEL = "model"
    DERIVED = "derived"
    SENSOR = "sensor"
