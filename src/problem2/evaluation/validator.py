"""Fail-closed validators for raw episodes and validated long tables."""

from __future__ import annotations

import base64
import hashlib
import math
import re
from typing import Any, Iterable

from problem2.experiments.artifacts import write_quarantine
from problem2.experiments.g5_contract import REDUCTION_RATE_EPSILON
from .schema import ARTIFACT_MANIFEST_SCHEMA, RAW_EPISODE_SCHEMA
from .sealed_lock import SealedAccessError, assert_partition_allowed


class ValidationError(ValueError):
    pass


_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_HASH40 = re.compile(r"^[0-9a-f]{40}$")
_METHODS = {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile", "sr_mappo_fixed", "sr_mappo_astar", "sr_mappo_two_stage", "sr_mappo_nearest", "sr_mappo_urgency"}
_SCALES = {"g20x20_d2", "g20x30_d3", "g20x40_d3", "g30x30_d3", "g30x40_d4", "g30x50_d4"}


def _finite(value: Any, name: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError(f"{name} must be finite")


def _number(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValidationError(f"{name} must be a finite number")
    result = float(value)
    if nonnegative and result < 0.0:
        raise ValidationError(f"{name} must be non-negative")
    return result


def validate_raw_episode(row: dict[str, Any], *, expected_provenance: dict[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValidationError("episode row must be an object")
    required = set(RAW_EPISODE_SCHEMA["required"])
    missing = required - set(row)
    extra = set(row) - required
    if missing:
        raise ValidationError(f"missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"unknown fields: {', '.join(sorted(extra))}")
    for key, value in row.items():
        _finite(value, key)
    for key in ("evaluation_identity", "canonical_training_identity", "config_hash", "protocol_hash", "checkpoint_hash", "evaluator_hash", "scenario_panel_hash"):
        if not isinstance(row[key], str) or not _HASH64.fullmatch(row[key]):
            raise ValidationError(f"{key} must be a lowercase SHA-256")
    if not isinstance(row["source_commit"], str) or not _HASH40.fullmatch(row["source_commit"]):
        raise ValidationError("source_commit must be a lowercase Git SHA-1")
    provenance_fields = ("source_commit", "config_hash", "protocol_hash", "checkpoint_hash", "evaluator_hash", "scenario_panel_hash")
    if expected_provenance is not None:
        if set(expected_provenance) != set(provenance_fields):
            raise ValidationError("provenance contract is incomplete")
        for field in provenance_fields:
            if row[field] != expected_provenance[field]:
                raise ValidationError(f"provenance drift: {field}")
    if row["method"] not in _METHODS or row["condition_id"] not in _METHODS:
        raise ValidationError("method/condition is undeclared")
    if row["scale"] not in _SCALES:
        raise ValidationError("scale is undeclared")
    if isinstance(row["training_seed"], bool) or not isinstance(row["training_seed"], int):
        raise ValidationError("training_seed must be an integer")
    if isinstance(row["scenario_id"], bool) or not isinstance(row["scenario_id"], int):
        raise ValidationError("scenario ID must be an integer")
    try:
        assert_partition_allowed(gate="G5", partition=row["partition"], scenario_id=row["scenario_id"])
    except SealedAccessError as exc:
        raise ValidationError(f"sealed partition: {exc}") from exc
    if row["interaction_count"] < 0 or row["episode_index"] < 0:
        raise ValidationError("counters must be non-negative")
    if row["terminated"] is not True:
        raise ValidationError("terminal row is required")
    if not isinstance(row["termination_reason"], str) or not row["termination_reason"]:
        raise ValidationError("termination reason is required")
    if row["action_uav"] not in range(6) or row["action_vehicle_slot"] not in range(4):
        raise ValidationError("illegal action")
    for key in ("initial_total_pest", "final_total_pest"):
        _number(row[key], key)
        if row[key] <= 0:
            raise ValidationError(f"{key} must be positive")
    expected_rate = 1.0 - float(row["final_total_pest"]) / (float(row["initial_total_pest"]) + REDUCTION_RATE_EPSILON)
    if not math.isclose(float(row["reduction_rate"]), expected_rate, rel_tol=1e-9, abs_tol=1e-12):
        raise ValidationError("reduction rate mismatch")
    if not isinstance(row["success_at_0_85"], bool) or row["success_at_0_85"] != (float(row["reduction_rate"]) >= 0.85):
        raise ValidationError("success threshold mismatch")
    _number(row["reduction_rate"], "reduction_rate")
    _number(row["resource_conservation_residual_l"], "resource_conservation_residual_l")
    if _number(row["battery_replenishment_l"], "battery_replenishment_l") != 0.0:
        raise ValidationError("battery replenishment must be zero")
    expected_residual = float(row["pesticide_initial_l"]) - float(row["pesticide_remaining_l"]) - float(row["pesticide_transferred_l"])
    if abs(float(row["resource_conservation_residual_l"]) - expected_residual) > 1e-9:
        raise ValidationError("resource conservation residual")
    for key in ("pesticide_initial_l", "pesticide_remaining_l", "pesticide_transferred_l", "rendezvous_distance_m", "vehicle_service_travel_m", "waiting_steps", "completed_request_waiting_steps", "pesticide_disabled_steps", "return_steps", "effective_spray_steps", "decision_runtime_s"):
        _number(row[key], key, nonnegative=True)
    if not isinstance(row["source_locator"], str) or not row["source_locator"]:
        raise ValidationError("source locator is required")
    return dict(row)


def validate_long_table(rows: Iterable[dict[str, Any]], *, expected_identities: set[str] | None = None, expected_provenance: dict[str, str] | None = None) -> list[dict[str, Any]]:
    materialized = list(rows)
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    last_counter: dict[str, int] = {}
    for row in materialized:
        checked = validate_raw_episode(row, expected_provenance=expected_provenance)
        identity = checked["evaluation_identity"]
        if identity in seen:
            raise ValidationError("duplicate evaluation identity")
        seen.add(identity)
        if identity in last_counter and checked["episode_index"] <= last_counter[identity]:
            raise ValidationError("nonmonotonic counters")
        last_counter[identity] = checked["episode_index"]
        checked["validation_status"] = "validated"
        checked["source_row_reference"] = checked["source_locator"]
        validated.append(checked)
    if expected_identities is not None and seen != set(expected_identities):
        raise ValidationError("incomplete expected cells")
    return validated


def quarantine_invalid_row(path, raw: bytes, *, locator: str, reason: str) -> dict[str, str]:
    if not isinstance(raw, bytes):
        raise TypeError("raw row must be UTF-8 bytes")
    return write_quarantine(path, raw, locator=locator, reason=reason)


def validate_artifact_manifest(record: dict[str, Any], *, output_root: str | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValidationError("artifact manifest must be an object")
    required = set(ARTIFACT_MANIFEST_SCHEMA["required"])
    if required - set(record) or set(record) - required:
        raise ValidationError("artifact manifest has missing or unknown fields")
    if record["artifact_type"] not in {"figure", "table", "text_block", "raw_episode", "validated_table"}:
        raise ValidationError("artifact type is undeclared")
    if record["data_status"] not in {"design_only", "validated", "locked_summary"}:
        raise ValidationError("artifact data status is undeclared")
    for field in ("source_paths", "source_hashes"):
        if not isinstance(record[field], list):
            raise ValidationError(f"{field} must be a list")
    if not all(isinstance(value, str) and value for value in record["source_paths"]):
        raise ValidationError("artifact source path is invalid")
    if len(record["source_paths"]) != len(record["source_hashes"]):
        raise ValidationError("artifact source path/hash lengths differ")
    for digest in record["source_hashes"]:
        if not isinstance(digest, str) or not _HASH64.fullmatch(digest):
            raise ValidationError("artifact source hash is invalid")
    if not isinstance(record["artifact_id"], str) or not _HASH64.fullmatch(record["artifact_id"]):
        raise ValidationError("artifact ID is invalid")
    if not isinstance(record["output_path"], str) or not record["output_path"]:
        raise ValidationError("artifact output path is invalid")
    generator_commit = record["generator_commit"]
    if generator_commit is not None and (not isinstance(generator_commit, str) or not _HASH40.fullmatch(generator_commit)):
        raise ValidationError("generator commit is invalid")
    for field in ("generator_sha256", "output_sha256"):
        value = record[field]
        if value is not None and (not isinstance(value, str) or not _HASH64.fullmatch(value)):
            raise ValidationError(f"{field} is invalid")
    for field in ("generator", "generator_version"):
        if not isinstance(record[field], str) or not record[field]:
            raise ValidationError(f"{field} is invalid")
    if output_root is not None:
        from pathlib import Path
        root = Path(output_root).resolve()
        output = Path(record["output_path"]).resolve()
        try:
            relative = output.relative_to(root)
        except ValueError as exc:
            raise ValidationError("artifact output escapes frozen root") from exc
        if not relative.parts:
            raise ValidationError("artifact output must be a descendant")
    return dict(record)


__all__ = ["ValidationError", "validate_raw_episode", "validate_long_table", "validate_artifact_manifest", "quarantine_invalid_row"]
