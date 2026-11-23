from datetime import UTC, datetime, timedelta

from cost_sentinel.models import Finding
from cost_sentinel.pricing import NAT_GATEWAY_MONTH
from cost_sentinel.settings import Settings

# Traffic in either direction through the gateway counts as use.
TRAFFIC_METRICS = ("BytesOutToDestination", "BytesInFromDestination")


def _bytes_through(cloudwatch, nat_id: str, start: datetime, end: datetime) -> float:
    total = 0.0
    for metric in TRAFFIC_METRICS:
        resp = cloudwatch.get_metric_statistics(
            Namespace="AWS/NATGateway",
            MetricName=metric,
            Dimensions=[{"Name": "NatGatewayId", "Value": nat_id}],
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=["Sum"],
        )
        total += sum(point.get("Sum", 0.0) for point in resp.get("Datapoints", []))
    return total


def find_idle_nat_gateways(
    session, region: str, settings: Settings | None = None, now: datetime | None = None
) -> list[Finding]:
    """NAT gateways that moved no traffic during the last `settings.nat_idle_days` days.

    A NAT gateway bills by the hour whether or not anything uses it, so an idle
    one in a forgotten VPC costs about $33/month before data processing.
    Gateways younger than the look-back window are skipped.
    """
    settings = settings or Settings()
    now = now or datetime.now(UTC)
    start = now - timedelta(days=settings.nat_idle_days)
    ec2 = session.client("ec2", region_name=region)
    cloudwatch = session.client("cloudwatch", region_name=region)

    findings = []
    paginator = ec2.get_paginator("describe_nat_gateways")
    pages = paginator.paginate(Filters=[{"Name": "state", "Values": ["available"]}])
    for page in pages:
        for nat in page["NatGateways"]:
            if nat["CreateTime"] > start:
                continue
            nat_id = nat["NatGatewayId"]
            if _bytes_through(cloudwatch, nat_id, start, now) > 0:
                continue
            findings.append(
                Finding(
                    check="nat-idle",
                    resource_id=nat_id,
                    region=region,
                    summary=f"no traffic in {settings.nat_idle_days} days",
                    monthly_cost=NAT_GATEWAY_MONTH,
                    details={"vpc_id": nat.get("VpcId"), "subnet_id": nat.get("SubnetId")},
                    tags=_tags(nat.get("Tags")),
                )
            )
    return findings


def _tags(raw) -> dict:
    return {t["Key"]: t["Value"] for t in raw or []}
