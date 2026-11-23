"""Static us-east-1 list prices used for rough monthly estimates."""

# USD per GiB-month, EBS volume storage.
EBS_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

# EBS snapshots, standard tier, USD per GiB-month.
EBS_SNAPSHOT_GB_MONTH = 0.05

# io1/io2 also bill provisioned IOPS (first tier), USD per IOPS-month.
EBS_IOPS_MONTH = {"io1": 0.065, "io2": 0.065}

# gp3 includes 3,000 IOPS and 125 MB/s; extra is billed.
GP3_FREE_IOPS = 3000
GP3_IOPS_MONTH = 0.005
GP3_FREE_THROUGHPUT = 125
GP3_THROUGHPUT_MONTH = 0.04  # per MB/s-month

HOURS_PER_MONTH = 730

# Public IPv4 addresses, including idle Elastic IPs: $0.005 per hour.
PUBLIC_IPV4_MONTH = round(0.005 * HOURS_PER_MONTH, 2)

# NAT gateway hourly charge ($0.045/hour), excluding per-GB data processing.
NAT_GATEWAY_MONTH = round(0.045 * HOURS_PER_MONTH, 2)


def ebs_volume_monthly(
    volume_type: str, size_gib: int, iops: int = 0, throughput: int = 0
) -> float:
    """Estimate the monthly cost of an EBS volume."""
    cost = EBS_GB_MONTH.get(volume_type, EBS_GB_MONTH["gp2"]) * size_gib
    if volume_type in EBS_IOPS_MONTH:
        cost += EBS_IOPS_MONTH[volume_type] * iops
    if volume_type == "gp3":
        cost += max(0, iops - GP3_FREE_IOPS) * GP3_IOPS_MONTH
        cost += max(0, throughput - GP3_FREE_THROUGHPUT) * GP3_THROUGHPUT_MONTH
    return round(cost, 2)
