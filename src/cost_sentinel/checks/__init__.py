from cost_sentinel.checks.ebs import find_unattached_volumes
from cost_sentinel.checks.eip import find_unassociated_eips
from cost_sentinel.checks.instances import find_long_stopped_instances
from cost_sentinel.checks.nat import find_idle_nat_gateways
from cost_sentinel.checks.snapshots import find_old_snapshots

ALL_CHECKS = {
    "ebs-unattached": find_unattached_volumes,
    "eip-unassociated": find_unassociated_eips,
    "instance-stopped": find_long_stopped_instances,
    "nat-idle": find_idle_nat_gateways,
    "snapshot-old": find_old_snapshots,
}

__all__ = ["ALL_CHECKS"]
