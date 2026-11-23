import pytest

from cost_sentinel.checks.ebs import find_unattached_volumes
from cost_sentinel.cli import run_checks
from cost_sentinel.pricing import ebs_volume_monthly
from cost_sentinel.report import render_text

REGION = "us-east-1"


def _instance(ec2):
    image = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    return ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1)["Instances"][0]["InstanceId"]


def test_flags_only_unattached_volumes(session):
    ec2 = session.client("ec2", region_name=REGION)
    idle = ec2.create_volume(AvailabilityZone="us-east-1a", Size=100, VolumeType="gp3")
    used = ec2.create_volume(AvailabilityZone="us-east-1a", Size=50, VolumeType="gp2")
    instance_id = _instance(ec2)
    ec2.attach_volume(VolumeId=used["VolumeId"], InstanceId=instance_id, Device="/dev/sdf")

    findings = find_unattached_volumes(session, REGION)

    ids = {f.resource_id for f in findings}
    assert idle["VolumeId"] in ids
    assert used["VolumeId"] not in ids


def test_unattached_volume_cost(session):
    ec2 = session.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=500, VolumeType="gp2")

    [finding] = [f for f in find_unattached_volumes(session, REGION) if "500 GiB" in f.summary]

    assert finding.monthly_cost == pytest.approx(50.0)
    assert finding.check == "ebs-unattached"


@pytest.mark.parametrize(
    ("vtype", "size", "iops", "throughput", "expected"),
    [
        ("gp3", 100, 3000, 125, 8.0),
        ("gp3", 100, 6000, 250, 8.0 + 15.0 + 5.0),
        ("io1", 100, 1000, 0, 12.5 + 65.0),
        ("sc1", 1000, 0, 0, 15.0),
        ("unknown", 10, 0, 0, 1.0),
    ],
)
def test_ebs_pricing(vtype, size, iops, throughput, expected):
    assert ebs_volume_monthly(vtype, size, iops, throughput) == pytest.approx(expected)


def test_text_report_sorted_by_cost(session):
    ec2 = session.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=900, VolumeType="gp3")

    findings = run_checks(session, REGION, ["ebs-unattached"])
    report = render_text(findings)

    assert findings[0].monthly_cost >= findings[-1].monthly_cost
    assert report.splitlines()[-1].startswith(f"{len(findings)} findings")
