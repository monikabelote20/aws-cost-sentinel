from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Thresholds shared by the checks."""

    snapshot_age_days: int = 90
