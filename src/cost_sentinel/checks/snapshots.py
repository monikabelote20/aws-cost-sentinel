from datetime import UTC, datetime, timedelta

from cost_sentinel.models import Finding
from cost_sentinel.pricing import EBS_SNAPSHOT_GB_MONTH
from cost_sentinel.settings import Settings


def _ami_snapshot_ids(ec2) -> set[str]:
    """Snapshots referenced by our own AMIs must stay until the AMI is deregistered."""
    ids = set()
    for image in ec2.describe_images(Owners=["self"])["Images"]:
        for mapping in image.get("BlockDeviceMappings", []):
            snap = mapping.get("Ebs", {}).get("SnapshotId")
            if snap:
                ids.add(snap)
    return ids


def find_old_snapshots(
    session, region: str, settings: Settings | None = None, now: datetime | None = None
) -> list[Finding]:
    """Snapshots older than `settings.snapshot_age_days` that no AMI depends on.

    The cost uses the full volume size, so it is an upper bound: snapshots are
    incremental and often bill for less.
    """
    settings = settings or Settings()
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=settings.snapshot_age_days)
    ec2 = session.client("ec2", region_name=region)
    keep = _ami_snapshot_ids(ec2)
    findings = []
    paginator = ec2.get_paginator("describe_snapshots")
    for page in paginator.paginate(OwnerIds=["self"]):
        for snap in page["Snapshots"]:
            if snap["SnapshotId"] in keep or snap["StartTime"] > cutoff:
                continue
            age = (now - snap["StartTime"]).days
            size = snap["VolumeSize"]
            findings.append(
                Finding(
                    check="snapshot-old",
                    resource_id=snap["SnapshotId"],
                    region=region,
                    summary=f"{size} GiB, {age} days old",
                    monthly_cost=round(size * EBS_SNAPSHOT_GB_MONTH, 2),
                    details={"volume_id": snap.get("VolumeId"), "age_days": age},
                )
            )
    return findings
