from datetime import UTC, datetime, timedelta

import pytest

from cost_sentinel.checks.instances import find_long_stopped_instances, stopped_since
from cost_sentinel.settings import Settings

REGION = "us-east-1"


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("User initiated (2026-01-05 10:20:30 GMT)", datetime(2026, 1, 5, 10, 20, 30, tzinfo=UTC)),
        (
            "User initiated (2025-12-31 23:59:59 UTC)",
            datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
        ),
        ("Server.SpotInstanceTermination", None),
        ("", None),
    ],
)
def test_stopped_since(reason, expected):
    assert stopped_since(reason) == expected


def _stopped_instance(ec2, name):
    image = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    inst = ec2.run_instances(
        ImageId=image,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": name}]}],
    )["Instances"][0]
    ec2.stop_instances(InstanceIds=[inst["InstanceId"]])
    return inst["InstanceId"]


def test_long_stopped_instance_is_flagged_with_volume_cost(session):
    ec2 = session.client("ec2", region_name=REGION)
    instance_id = _stopped_instance(ec2, "old-build-box")
    later = datetime.now(UTC) + timedelta(days=45)

    [finding] = find_long_stopped_instances(
        session, REGION, Settings(stopped_instance_days=30), now=later
    )

    assert finding.resource_id == instance_id
    assert finding.summary.startswith("old-build-box, stopped 4")
    assert finding.monthly_cost > 0
    assert finding.tags["Name"] == "old-build-box"
    assert finding.details["volumes"]


def test_recently_stopped_instance_is_ignored(session):
    ec2 = session.client("ec2", region_name=REGION)
    _stopped_instance(ec2, "paused-yesterday")

    assert find_long_stopped_instances(session, REGION, Settings(stopped_instance_days=30)) == []


def test_running_instances_are_ignored(session):
    ec2 = session.client("ec2", region_name=REGION)
    image = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1)
    later = datetime.now(UTC) + timedelta(days=90)

    assert find_long_stopped_instances(session, REGION, now=later) == []
