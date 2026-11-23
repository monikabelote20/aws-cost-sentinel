from cost_sentinel.models import Finding
from cost_sentinel.pricing import ebs_volume_monthly
from cost_sentinel.settings import Settings


def find_unattached_volumes(
    session, region: str, settings: Settings | None = None
) -> list[Finding]:
    """EBS volumes in the `available` state are billed but attached to nothing."""
    ec2 = session.client("ec2", region_name=region)
    findings = []
    paginator = ec2.get_paginator("describe_volumes")
    pages = paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}])
    for page in pages:
        for vol in page["Volumes"]:
            vtype = vol.get("VolumeType", "gp2")
            size = vol["Size"]
            cost = ebs_volume_monthly(vtype, size, vol.get("Iops", 0), vol.get("Throughput", 0))
            findings.append(
                Finding(
                    check="ebs-unattached",
                    resource_id=vol["VolumeId"],
                    region=region,
                    summary=f"{size} GiB {vtype}, unattached",
                    monthly_cost=cost,
                    details={"created": vol["CreateTime"].isoformat()},
                )
            )
    return findings
