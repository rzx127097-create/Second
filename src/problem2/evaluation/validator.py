"""Fail-closed validators for raw episodes and validated long tables."""

from __future__ import annotations

import base64
import hashlib
import math
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from problem2.experiments.artifacts import write_quarantine
from problem2.experiments.g5_contract import REDUCTION_RATE_EPSILON
from problem2.experiments.identity import canonical_evaluation_identity, canonical_training_identity
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from .schema import ARTIFACT_MANIFEST_SCHEMA, DYNAMIC_RAW_EPISODE_SCHEMA, RAW_EPISODE_SCHEMA
from .sealed_lock import SealedAccessError, assert_partition_allowed


class ValidationError(ValueError):
    pass


_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_HASH40 = re.compile(r"^[0-9a-f]{40}$")
_METHODS = {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile", "sr_mappo_fixed", "sr_mappo_astar", "sr_mappo_two_stage", "sr_mappo_nearest", "sr_mappo_urgency"}
_SCALES = {"g20x20_d2", "g20x30_d3", "g20x40_d3", "g30x30_d3", "g30x40_d4", "g30x50_d4"}
_DYNAMIC_METRIC_SOURCE = "dynamic_ecology_environment"
_DYNAMIC_FIELDS = tuple(
    field for field in DYNAMIC_RAW_EPISODE_SCHEMA["required"]
    if field not in RAW_EPISODE_SCHEMA["required"]
)
_DYNAMIC_SCALE_SPECS = {
    "g20x20_d2": ((20, 20), 150),
    "g20x30_d3": ((20, 30), 180),
    "g20x40_d3": ((20, 40), 220),
    "g30x30_d3": ((30, 30), 220),
    "g30x40_d4": ((30, 40), 280),
    "g30x50_d4": ((30, 50), 350),
}


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


@lru_cache(maxsize=1)
def _frozen_dynamic_config() -> DynamicEcologyConfig:
    root = Path(__file__).resolve().parents[3]
    return DynamicEcologyConfig.from_yaml(root / "configs" / "problem2" / "dynamic_pest_v1.yaml")


def validate_dynamic_episode(row: Any) -> None:
    """Validate one dynamic-ecology row against the frozen local contract."""

    if not isinstance(row, Mapping):
        raise ValidationError("dynamic episode must be an object")
    if row.get("metric_source") != _DYNAMIC_METRIC_SOURCE:
        raise ValidationError("metric_source must be dynamic_ecology_environment")
    missing = set(_DYNAMIC_FIELDS) - set(row)
    if missing:
        raise ValidationError(f"dynamic ecology provenance is incomplete: {', '.join(sorted(missing))}")
    initial = _number(row.get("initial_total_pest"), "initial_total_pest")
    final = _number(row.get("final_total_pest"), "final_total_pest", nonnegative=True)
    if initial <= 0.0:
        raise ValidationError("initial_total_pest must be positive")
    expected_rate = 1.0 - final / initial
    if not math.isclose(float(row.get("reduction_rate")), expected_rate, rel_tol=0.0, abs_tol=1e-12):
        raise ValidationError("dynamic reduction rate is not derived from pest totals")
    if row.get("success_at_0_85") is not (expected_rate >= 0.85):
        raise ValidationError("dynamic success threshold mismatch")

    config = _frozen_dynamic_config()
    if row["ecology_version"] != config.version:
        raise ValidationError("ecology_version drifted")
    if row["ecology_config_sha256"] != config.contract_sha256:
        raise ValidationError("ecology_config_sha256 drifted")
    if row["ecology_implementation_version"] != config.version:
        raise ValidationError("ecology_implementation_version drifted")
    if row["ecology_source_commit"] != "1ca9e5ccc5f77ed775cd2b607dd70d635720accf":
        raise ValidationError("ecology_source_commit drifted")

    scale = row.get("scale")
    partition = row.get("partition")
    scenario_id = row.get("scenario_id")
    if scale not in _DYNAMIC_SCALE_SPECS:
        raise ValidationError("dynamic scale is undeclared")
    if partition not in {"development", "validation"}:
        raise ValidationError("dynamic partition is undeclared")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise ValidationError("dynamic scenario_id must be an integer")
    allowed = range(10000, 10020) if partition == "development" else range(20000, 20050)
    if scenario_id not in allowed:
        raise ValidationError("dynamic scenario_id is outside its partition")
    shape, horizon = _DYNAMIC_SCALE_SPECS[scale]
    expected_scenario = generate_dynamic_scenario(partition, scenario_id, scale, shape, config)
    if row["ecology_scenario_sha256"] != expected_scenario.scenario_sha256:
        raise ValidationError("ecology_scenario_sha256 drifted")
    if row["dynamic_step_count"] != horizon:
        raise ValidationError("dynamic_step_count does not match the scale horizon")

    for key in ("initial_total_predator", "final_total_predator", "cumulative_deposited_effect", "terminal_mean_concentration", "terminal_max_concentration", "terminal_wind_strength"):
        _number(row[key], key, nonnegative=True)
    _number(row["terminal_wind_direction"], "terminal_wind_direction")
    if row["terminal_max_concentration"] < row["terminal_mean_concentration"]:
        raise ValidationError("terminal concentration extrema are inconsistent")


def validate_raw_episode(row: dict[str, Any], *, expected_provenance: dict[str, str] | None = None, verify_identity: bool = True, allow_validation_access: bool = False) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValidationError("episode row must be an object")
    required = set(RAW_EPISODE_SCHEMA["required"])
    missing = required - set(row)
    # Keep the pre-Task12 schema fixtures readable; canonical access rows are
    # required to carry candidate_id by CanonicalValidationStore.
    for compatibility_field in ("candidate_id", "candidate_manifest_sha256", "budget_manifest_sha256", "physical_scenario_contract_sha256"):
        if compatibility_field in missing:
            missing.remove(compatibility_field)
    extra = set(row) - set(RAW_EPISODE_SCHEMA["properties"])
    if missing:
        raise ValidationError(f"missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"unknown fields: {', '.join(sorted(extra))}")
    if "candidate_id" in row and (not isinstance(row["candidate_id"], str) or not row["candidate_id"]):
        raise ValidationError("candidate_id must be non-empty text")
    for key, value in row.items():
        _finite(value, key)
    for key in ("evaluation_identity", "canonical_training_identity", "config_hash", "protocol_hash", "checkpoint_hash", "evaluator_hash", "scenario_panel_hash", "candidate_manifest_sha256", "budget_manifest_sha256", "physical_scenario_contract_sha256"):
        if key not in row:
            continue
        if not isinstance(row[key], str) or not _HASH64.fullmatch(row[key]):
            raise ValidationError(f"{key} must be a lowercase SHA-256")
    if not isinstance(row["source_commit"], str) or not _HASH40.fullmatch(row["source_commit"]):
        raise ValidationError("source_commit must be a lowercase Git SHA-1")
    provenance_fields = ("source_commit", "config_hash", "protocol_hash", "checkpoint_hash", "evaluator_hash", "scenario_panel_hash")
    extra_provenance_fields = ("candidate_manifest_sha256", "budget_manifest_sha256", "physical_scenario_contract_sha256")
    expected_fields = set(provenance_fields)
    if any(field in row for field in extra_provenance_fields):
        expected_fields.update(extra_provenance_fields)
    if expected_provenance is None or set(expected_provenance) != expected_fields:
        raise ValidationError("provenance contract is incomplete")
    for field in (*provenance_fields, *(extra_provenance_fields if extra_provenance_fields[0] in row else ())):
        if row[field] != expected_provenance[field]:
            raise ValidationError(f"provenance drift: {field}")
    if verify_identity is not True:
        raise ValidationError("identity verification cannot be disabled")
    try:
        expected_identity = canonical_training_identity(row["method"], row["scale"], row["training_seed"], row["config_hash"], row["source_commit"])
    except ValueError as exc:
        raise ValidationError("canonical identity inputs are invalid") from exc
    if row["canonical_training_identity"] != expected_identity:
        raise ValidationError("canonical identity mismatch")
    expected_evaluation = canonical_evaluation_identity(row["canonical_training_identity"], row["condition_id"], row["scale"], row["training_seed"], row["scenario_id"], row["partition"], row["checkpoint_hash"], row["evaluator_hash"], row["scenario_panel_hash"])
    if row["evaluation_identity"] != expected_evaluation:
        raise ValidationError("evaluation identity mismatch")
    if row["method"] not in _METHODS or row["condition_id"] not in _METHODS:
        raise ValidationError("method/condition is undeclared")
    if row["scale"] not in _SCALES:
        raise ValidationError("scale is undeclared")
    for key in ("training_seed", "scenario_id", "episode_index", "interaction_count", "action_uav", "action_vehicle_slot"):
        if isinstance(row[key], bool) or not isinstance(row[key], int):
            raise ValidationError(f"{key} must be an integer")
    try:
        if row["partition"] == "validation" and allow_validation_access is True:
            if row["scenario_id"] not in range(20000, 20050):
                raise SealedAccessError("validation scenario identity is outside 20000-20049")
        else:
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
    metric_source = row.get("metric_source")
    if metric_source is not None and (
        not isinstance(metric_source, str)
        or metric_source not in {"action_driven_environment", _DYNAMIC_METRIC_SOURCE}
    ):
        raise ValidationError("metric_source is undeclared")
    if metric_source == _DYNAMIC_METRIC_SOURCE:
        validate_dynamic_episode(row)
    for key in ("initial_total_pest", "final_total_pest"):
        _number(row[key], key)
        if row[key] <= 0 and not (
            key == "final_total_pest"
            and metric_source == _DYNAMIC_METRIC_SOURCE
            and row[key] == 0
        ):
            raise ValidationError(f"{key} must be positive")
    epsilon = 0.0 if metric_source == _DYNAMIC_METRIC_SOURCE else REDUCTION_RATE_EPSILON
    expected_rate = 1.0 - float(row["final_total_pest"]) / (float(row["initial_total_pest"]) + epsilon)
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


def validate_long_table(rows: Iterable[dict[str, Any]], *, expected_identities: set[str] | None = None, expected_provenance: dict[str, str] | None = None, verify_identity: bool = True, allow_validation_access: bool = False) -> list[dict[str, Any]]:
    materialized = list(rows)
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    last_counter: dict[str, int] = {}
    for row in materialized:
        checked = validate_raw_episode(row, expected_provenance=expected_provenance, verify_identity=verify_identity, allow_validation_access=allow_validation_access)
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
        if field == "generator_version" and record[field] is None and record["data_status"] == "design_only":
            continue
        if not isinstance(record[field], str) or not record[field]:
            raise ValidationError(f"{field} is invalid")
    if record["data_status"] in {"validated", "locked_summary"} and any(record[field] is None for field in ("generator_commit", "generator_sha256", "generator_version", "output_sha256", "created_at")):
        raise ValidationError("validated artifact provenance/hash is incomplete")
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
    if record["data_status"] in {"validated", "locked_summary"}:
        from pathlib import Path
        output = Path(record["output_path"]).resolve()
        if not output.exists() or not output.is_file():
            raise ValidationError("artifact output does not exist")
        if hashlib.sha256(output.read_bytes()).hexdigest() != record["output_sha256"]:
            raise ValidationError("artifact output hash mismatch")
    return dict(record)


__all__ = ["ValidationError", "validate_dynamic_episode", "validate_raw_episode", "validate_long_table", "validate_artifact_manifest", "quarantine_invalid_row"]
