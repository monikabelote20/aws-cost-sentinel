from cost_sentinel.checks.ebs import find_unattached_volumes

ALL_CHECKS = {
    "ebs-unattached": find_unattached_volumes,
}

__all__ = ["ALL_CHECKS"]
