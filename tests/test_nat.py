from datetime import UTC, datetime, timedelta

import pytest

from cost_sentinel.checks.nat import find_idle_nat_gateways
from cost_sentinel.settings import Settings

REGION = "us-east-1"


@pytest.fixture
def nat_gateway(session):
    ec2 = session.client("ec2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"]
    eip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    nat = ec2.create_nat_gateway(SubnetId=subnet, AllocationId=eip)["NatGateway"]
    return nat["NatGatewayId"]


def _send_traffic(session, nat_id, when):
    session.client("cloudwatch", region_name=REGION).put_metric_data(
        Namespace="AWS/NATGateway",
        MetricData=[
            {
                "MetricName": "BytesOutToDestination",
                "Dimensions": [{"Name": "NatGatewayId", "Value": nat_id}],
                "Timestamp": when,
                "Value": 52_428_800,
                "Unit": "Bytes",
            }
        ],
    )


def test_idle_gateway_is_flagged(session, nat_gateway):
    later = datetime.now(UTC) + timedelta(days=30)

    findings = find_idle_nat_gateways(session, REGION, Settings(nat_idle_days=14), now=later)

    assert [f.resource_id for f in findings] == [nat_gateway]
    assert findings[0].monthly_cost == pytest.approx(32.85)
    assert findings[0].summary == "no traffic in 14 days"


def test_gateway_with_traffic_is_not_flagged(session, nat_gateway):
    later = datetime.now(UTC) + timedelta(days=30)
    _send_traffic(session, nat_gateway, later - timedelta(days=2))

    assert find_idle_nat_gateways(session, REGION, Settings(nat_idle_days=14), now=later) == []


def test_new_gateway_is_skipped(session, nat_gateway):
    # Created moments ago: younger than the look-back window, so not judged yet.
    assert find_idle_nat_gateways(session, REGION, Settings(nat_idle_days=14)) == []
