import pytest

from cost_sentinel.checks.eip import find_unassociated_eips

REGION = "us-east-1"


def test_flags_idle_elastic_ip(session):
    ec2 = session.client("ec2", region_name=REGION)
    idle = ec2.allocate_address(Domain="vpc")

    findings = find_unassociated_eips(session, REGION)

    assert [f.resource_id for f in findings] == [idle["AllocationId"]]
    assert findings[0].monthly_cost == pytest.approx(3.65)


def test_ignores_associated_elastic_ip(session):
    ec2 = session.client("ec2", region_name=REGION)
    image = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    instance_id = ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1)["Instances"][0][
        "InstanceId"
    ]
    used = ec2.allocate_address(Domain="vpc")
    ec2.associate_address(AllocationId=used["AllocationId"], InstanceId=instance_id)

    assert find_unassociated_eips(session, REGION) == []
