"""Public fail-closed boundary for validation and sealed-test access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import yaml


class SealedAccessError(PermissionError):
    pass


@dataclass(frozen=True)
class SealedLock:
    status: str
    maximum_unlock_count: int
    actual_unlock_count: int
    unlock_gate: str
    tuning_allowed_before_unlock: bool = False


def load_sealed_lock(path: Path) -> SealedLock:
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SealedAccessError("sealed lock cannot be loaded") from exc
    if not isinstance(payload, dict):
        raise SealedAccessError("sealed lock must be a mapping")
    required = {"status", "maximum_unlock_count", "actual_unlock_count", "unlock_gate"}
    if not required <= set(payload):
        raise SealedAccessError("sealed lock is incomplete")
    if payload["status"] != "locked" or payload["unlock_gate"] != "G7":
        raise SealedAccessError("sealed lock is invalid")
    if any(isinstance(payload[key], bool) or not isinstance(payload[key], int) for key in ("maximum_unlock_count", "actual_unlock_count")):
        raise SealedAccessError("sealed lock counters must be integers")
    if payload["maximum_unlock_count"] != 1 or payload["actual_unlock_count"] != 0:
        raise SealedAccessError("sealed lock count is invalid")
    return SealedLock("locked", 1, 0, "G7", bool(payload.get("tuning_allowed_before_unlock", False)))


def assert_no_sealed_access(gate: str, scenario_id: object | None = None, partition: object | None = None, sealed_accessed: object = False, path: object | None = None) -> None:
    if sealed_accessed:
        raise SealedAccessError("sealed access flag must remain false")
    if isinstance(scenario_id, int) and not isinstance(scenario_id, bool) and 30000 <= scenario_id <= 30099:
        raise SealedAccessError("sealed scenario access is forbidden")
    for value in (partition, path):
        if isinstance(value, (str, Path)) and "sealed" in str(value).lower():
            raise SealedAccessError("sealed path access is forbidden")
        if value is not None and not isinstance(value, (str, Path)):
            raise SealedAccessError("unsupported path/partition value")


def assert_partition_allowed(gate: str, partition: object, scenario_id: object) -> str:
    if gate not in {"G5", "G6", "G7"}:
        raise SealedAccessError("unknown gate")
    if not isinstance(partition, str) or not isinstance(scenario_id, int) or isinstance(scenario_id, bool):
        raise SealedAccessError("partition and scenario ID are invalid")
    if partition == "development" and 10000 <= scenario_id <= 10019:
        return partition
    if partition == "validation" and 20000 <= scenario_id <= 20049:
        if gate in {"G6", "G7"}:
            return partition
        raise SealedAccessError("validation access is not authorized")
    if partition in {"sealed", "sealed_test", "g7/sealed"} or 30000 <= scenario_id <= 30099:
        raise SealedAccessError("sealed-test access is forbidden")
    raise SealedAccessError("scenario is outside authorized partition")


def unlock_g7(path: Path, gate: str, operator: str, prerequisites: Mapping[str, Any]) -> SealedLock:
    lock = load_sealed_lock(path)
    if gate != "G7":
        raise SealedAccessError("G7 unlock requires current gate G7")
    required = ("g6_acceptance_pushed", "pre_unlock_audit_exact", "clean_frozen_source", "actual_unlock_count_zero")
    if not isinstance(operator, str) or not operator.strip() or any(prerequisites.get(key) is not True for key in required):
        raise SealedAccessError("G7 unlock prerequisites are not satisfied")
    raise SealedAccessError("sealed unlock is disabled until the persisted G7 gate is accepted")


__all__ = ["SealedAccessError", "SealedLock", "load_sealed_lock", "assert_no_sealed_access", "assert_partition_allowed", "unlock_g7"]
