import re
from datetime import UTC, datetime

from cost_sentinel.models import Finding
from cost_sentinel.pricing import ebs_volume_monthly
from cost_sentinel.settings import Settings

# e.g. "User initiated (2026-01-05 10:20:30 GMT)"
_STOPPED_AT = re.compile(r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?:GMT|UTC)\)")


def stopped_since(reason: str) -> datetime | None:
    """Parse the stop time out of an instance's StateTransitionReason."""
    match = _STOPPED_AT.search(reason or "")
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _volume_costs(ec2, volume_ids: list[str]) -> tuple[float, int]:
    if not volume_ids:
        return 0.0, 0
    cost, size = 0.0, 0
    for vol in ec2.describe_volumes(VolumeIds=volume_ids)["Volumes"]:
        size += vol["Size"]
        cost += ebs_volume_monthly(
            vol.get("VolumeType", "gp2"), vol["Size"], vol.get("Iops", 0), vol.get("Throughput", 0)
        )
    return round(cost, 2), size


def find_long_stopped_instances(
    session, region: str, settings: Settings | None = None, now: datetime | None = None
) -> list[Finding]:
    """Instances stopped for more than `settings.stopped_instance_days` days.

    Stopped instances don't bill compute, but their EBS volumes keep billing.
    The estimate is the monthly cost of the attached volumes.
    """
    settings = settings or Settings()
    now = now or datetime.now(UTC)
    ec2 = session.client("ec2", region_name=region)

    findings = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])
    for page in pages:
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                since = stopped_since(inst.get("StateTransitionReason", ""))
                if since is None:
                    continue
                age = (now - since).days
                if age < settings.stopped_instance_days:
                    continue
                volumes = [
                    m["Ebs"]["VolumeId"] for m in inst.get("BlockDeviceMappings", []) if "Ebs" in m
                ]
                cost, size = _volume_costs(ec2, volumes)
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                name = tags.get("Name")
                label = f"{name}, " if name else ""
                findings.append(
                    Finding(
                        check="instance-stopped",
                        resource_id=inst["InstanceId"],
                        region=region,
                        summary=f"{label}stopped {age} days, {len(volumes)} vol / {size} GiB",
                        monthly_cost=cost,
                        details={
                            "instance_type": inst.get("InstanceType"),
                            "stopped_at": since.isoformat(),
                            "volumes": volumes,
                        },
                        tags=tags,
                    )
                )
    return findings
