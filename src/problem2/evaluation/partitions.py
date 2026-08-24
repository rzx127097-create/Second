"""Fail-closed G5 scenario partition guard."""

from __future__ import annotations

from pathlib import Path

from problem2.experiments.g5_contract import G5ContractError, load_g5_contract


class PartitionAccessError(ValueError):
    """Raised before an undeclared or unauthorized scenario can be read."""


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _strict_partition_state() -> tuple[dict[str, tuple[int, ...]], dict[str, bool], str]:
    try:
        contract = load_g5_contract(REPOSITORY_ROOT)
    except (G5ContractError, OSError) as exc:
        raise PartitionAccessError("frozen G5 contract is invalid") from exc
    ranges = {
        "development": contract.partitions["development_scenarios"],
        "validation": contract.partitions["validation"],
        "sealed_test": contract.partitions["sealed_test"],
    }
    flags = {
        "validation_accessed": contract.validation_accessed,
        "sealed_accessed": contract.sealed_accessed,
    }
    protocol_hash = contract.file_hashes["configs/problem2/g5/protocol.yaml"]
    return ranges, flags, protocol_hash


PARTITION_RANGES, ACCESS_FLAGS, PARTITION_CONTRACT_SHA256 = _strict_partition_state()


def assert_partition_allowed(partition: str, scenario_id: int) -> str:
    ranges, _, _ = _strict_partition_state()
    if not isinstance(partition, str) or partition not in ranges:
        raise PartitionAccessError("scenario partition is undeclared")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise PartitionAccessError("scenario ID must be an integer")
    if scenario_id not in ranges[partition]:
        raise PartitionAccessError("scenario ID is outside its declared partition")
    if partition == "sealed_test":
        raise PartitionAccessError("sealed-test access is forbidden during G5 Task 6")
    if partition == "validation":
        raise PartitionAccessError("validation access is not authorized during G5 Task 6")
    return partition


__all__ = [
    "PARTITION_CONTRACT_SHA256",
    "PARTITION_RANGES",
    "PartitionAccessError",
    "assert_partition_allowed",
]
