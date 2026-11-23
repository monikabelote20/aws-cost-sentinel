from datetime import UTC, datetime, timedelta

import pytest

from cost_sentinel.checks.snapshots import find_old_snapshots
from cost_sentinel.settings import Settings

REGION = "us-east-1"


def _snapshot(ec2, size):
    vol = ec2.create_volume(AvailabilityZone="us-east-1a", Size=size)
    return ec2.create_snapshot(VolumeId=vol["VolumeId"])["SnapshotId"]


def test_flags_snapshots_past_the_age_threshold(session):
    ec2 = session.client("ec2", region_name=REGION)
    snap = _snapshot(ec2, 200)
    later = datetime.now(UTC) + timedelta(days=120)

    findings = find_old_snapshots(session, REGION, Settings(snapshot_age_days=90), now=later)

    mine = [f for f in findings if f.resource_id == snap]
    assert len(mine) == 1
    assert mine[0].monthly_cost == pytest.approx(10.0)
    assert mine[0].details["age_days"] >= 119


def test_recent_snapshots_are_ignored(session):
    ec2 = session.client("ec2", region_name=REGION)
    snap = _snapshot(ec2, 20)

    findings = find_old_snapshots(session, REGION, Settings(snapshot_age_days=90))

    assert snap not in {f.resource_id for f in findings}


def test_snapshots_backing_an_ami_are_kept(session):
    ec2 = session.client("ec2", region_name=REGION)
    image_id = ec2.register_image(Name="golden-image", RootDeviceName="/dev/xvda")["ImageId"]
    [image] = ec2.describe_images(ImageIds=[image_id])["Images"]
    ami_snapshots = {m["Ebs"]["SnapshotId"] for m in image["BlockDeviceMappings"] if "Ebs" in m}
    later = datetime.now(UTC) + timedelta(days=365)

    findings = find_old_snapshots(session, REGION, Settings(snapshot_age_days=30), now=later)

    assert ami_snapshots
    assert ami_snapshots.isdisjoint({f.resource_id for f in findings})
