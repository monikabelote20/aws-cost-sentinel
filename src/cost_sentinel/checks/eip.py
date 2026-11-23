from cost_sentinel.models import Finding
from cost_sentinel.pricing import PUBLIC_IPV4_MONTH
from cost_sentinel.settings import Settings


def find_unassociated_eips(session, region: str, settings: Settings | None = None) -> list[Finding]:
    """Elastic IPs that are allocated but not associated with anything.

    Since February 2024 every public IPv4 address is billed hourly, but an idle
    Elastic IP is pure waste: release it or attach it.
    """
    ec2 = session.client("ec2", region_name=region)
    findings = []
    for addr in ec2.describe_addresses()["Addresses"]:
        if addr.get("AssociationId") or addr.get("InstanceId") or addr.get("NetworkInterfaceId"):
            continue
        findings.append(
            Finding(
                check="eip-unassociated",
                resource_id=addr.get("AllocationId", addr["PublicIp"]),
                region=region,
                summary=f"{addr['PublicIp']}, not associated",
                monthly_cost=PUBLIC_IPV4_MONTH,
                details={"public_ip": addr["PublicIp"]},
                tags={t["Key"]: t["Value"] for t in addr.get("Tags", [])},
            )
        )
    return findings
