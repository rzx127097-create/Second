"""Self-contained dynamic ecology contracts for Problem 2."""

from .config import (
    DYNAMIC_ECOLOGY_VERSION,
    DynamicEcologyConfig,
    DynamicEcologyConfigError,
    verify_problem1_lineage,
)

__all__ = [
    "DYNAMIC_ECOLOGY_VERSION",
    "DynamicEcologyConfig",
    "DynamicEcologyConfigError",
    "verify_problem1_lineage",
]
