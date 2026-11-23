from cost_sentinel.checks.ebs import find_unattached_volumes
from cost_sentinel.checks.eip import find_unassociated_eips
from cost_sentinel.checks.snapshots import find_old_snapshots

ALL_CHECKS = {
    "ebs-unattached": find_unattached_volumes,
    "eip-unassociated": find_unassociated_eips,
    "snapshot-old": find_old_snapshots,
}

__all__ = ["ALL_CHECKS"]
