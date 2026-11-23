from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Thresholds shared by the checks."""

    snapshot_age_days: int = 90
    nat_idle_days: int = 14
    stopped_instance_days: int = 30
