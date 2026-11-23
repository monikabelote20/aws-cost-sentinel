from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    """A resource that costs money without doing useful work."""

    check: str
    resource_id: str
    region: str
    summary: str
    monthly_cost: float
    details: dict = field(default_factory=dict, compare=False, hash=False)
    tags: dict = field(default_factory=dict, compare=False, hash=False)
