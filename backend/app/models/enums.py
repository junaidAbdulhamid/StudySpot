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


class CheckInStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class CrowdLevel(StrEnum):
    LOTS_OF_SEATS = "lots_of_seats"
    MODERATE = "moderate"
    BUSY = "busy"
    NEARLY_FULL = "nearly_full"


class ValidationType(StrEnum):
    ACCURATE = "accurate"
    MORE_CROWDED = "more_crowded"
    LESS_CROWDED = "less_crowded"
