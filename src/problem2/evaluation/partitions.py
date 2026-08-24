"""Fail-closed G5 scenario partition guard."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

import yaml


class PartitionAccessError(ValueError):
    """Raised before an undeclared or unauthorized scenario can be read."""


PROTOCOL_PATH = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "problem2"
    / "g5"
    / "protocol.yaml"
)


def _load_contract() -> tuple[dict[str, tuple[int, int]], dict[str, bool], str]:
    raw = PROTOCOL_PATH.read_bytes()
    payload = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != "g5.v1":
        raise RuntimeError("frozen G5 partition contract is invalid")
    partitions = payload.get("partitions")
    access = payload.get("access")
    if not isinstance(partitions, Mapping) or not isinstance(access, Mapping):
        raise RuntimeError("frozen G5 partition contract is incomplete")
    ranges: dict[str, tuple[int, int]] = {}
    for public, stored in (
        ("development", "development_scenarios"),
        ("validation", "validation"),
        ("sealed_test", "sealed_test"),
    ):
        record = partitions.get(stored)
        if not isinstance(record, Mapping):
            raise RuntimeError(f"frozen G5 partition lacks {stored}")
        start, end = record.get("start"), record.get("end")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start > end
        ):
            raise RuntimeError(f"frozen G5 partition range {stored} is invalid")
        ranges[public] = (start, end)
    flags = {
        "validation_accessed": access.get("validation_accessed"),
        "validation_tuning_authorized": access.get("validation_tuning_authorized"),
        "sealed_accessed": access.get("sealed_accessed"),
    }
    if any(type(value) is not bool for value in flags.values()):
        raise RuntimeError("frozen G5 access flags must be boolean")
    if flags["sealed_accessed"]:
        raise RuntimeError("sealed access must remain false during G5 Task 6")
    return ranges, flags, hashlib.sha256(raw).hexdigest()


PARTITION_RANGES, ACCESS_FLAGS, PARTITION_CONTRACT_SHA256 = _load_contract()


def assert_partition_allowed(partition: str, scenario_id: int) -> str:
    if not isinstance(partition, str) or partition not in PARTITION_RANGES:
        raise PartitionAccessError("scenario partition is undeclared")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise PartitionAccessError("scenario ID must be an integer")
    lower, upper = PARTITION_RANGES[partition]
    if not lower <= scenario_id <= upper:
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
