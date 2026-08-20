"""Fail-closed validation for the frozen G1 evidence registries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import subprocess
from typing import Any, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_VERSION = "g1.1-contract-remediation.v1"
REGISTRY_IDS = {
    "parameter_registry.yaml": "G1-PARAMETERS",
    "literature_source_ledger.yaml": "G1-SOURCES",
    "experiment_matrix.yaml": "G1-EXPERIMENT-MATRIX",
    "scenario_seed_manifest.yaml": "G1-SCENARIO-SEEDS",
    "job_identity_contract.yaml": "G1-JOB-IDENTITY",
    "raw_episode_schema.yaml": "G1-RAW-EPISODE",
    "validated_long_table_schema.yaml": "G1-VALIDATED-TABLE",
    "artifact_manifest_schema.yaml": "G1-ARTIFACT-MANIFEST",
    "sealed_test_lock.yaml": "G1-SEALED-TEST",
    "output_root_contract.yaml": "G1-OUTPUT-ROOT",
}
REGISTRY_NAMES = tuple(REGISTRY_IDS)
SCHEMA_VERSION = "g1.v1"
FROZEN_STATUS = "design_frozen"
PRIMARY_METHODS = [
    "sr_mappo_mobile",
    "sr_mappo_fixed",
    "sr_mappo_astar",
    "mappo_mobile",
    "sr_mappo_two_stage",
]
SCALE_HORIZONS = {
    "g20x20_d2": 150,
    "g20x30_d3": 180,
    "g20x40_d3": 220,
    "g30x30_d3": 220,
    "g30x40_d4": 280,
    "g30x50_d4": 350,
}
TRAINING_SEEDS = [42, 123, 2024, 3407, 7919]
FAIRNESS_FIELDS = (
    "equal_environment",
    "equal_total_pesticide",
    "equal_initial_vehicle_inventory",
    "equal_transfer_rate",
    "equal_service_cap",
    "equal_setup_service_time",
    "equal_training_seed_protocol",
    "equal_evaluation_scenario_ids",
    "equal_horizon",
    "equal_information_conditions",
    "equal_evaluation_budget",
)
METRICS = {
    "reduction_rate": ("number", "1", "primary_outcome"),
    "success_at_0_85": ("boolean", "1", "primary_outcome"),
    "request_count": ("integer", "count", "service"),
    "request_completed_count": ("integer", "count", "service"),
    "rendezvous_distance_m": ("number", "m", "mechanism"),
    "waiting_steps": ("integer", "step", "mechanism"),
    "pesticide_disabled_steps": ("integer", "step", "mechanism"),
    "return_steps": ("integer", "step", "mechanism"),
    "effective_spray_steps": ("integer", "step", "mechanism"),
    "transferred_pesticide_l": ("number", "L", "mechanism"),
    "vehicle_travel_steps": ("integer", "step", "operational"),
    "vehicle_idle_steps": ("integer", "step", "operational"),
    "vehicle_stranded_inventory_l": ("number", "L", "operational"),
    "decision_runtime_s": ("number", "s", "operational"),
    "initial_uav_pesticide_l": ("number", "L", "resource"),
    "final_uav_pesticide_l": ("number", "L", "resource"),
    "initial_vehicle_inventory_l": ("number", "L", "resource"),
    "final_vehicle_inventory_l": ("number", "L", "resource"),
    "requested_pesticide_l": ("number", "L", "resource"),
    "sprayed_pesticide_l": ("number", "L", "resource"),
    "total_available_supply_l": ("number", "L", "resource"),
}
RAW_IDENTITY_FIELDS = (
    ("run_id", "string"),
    ("method", "string"),
    ("scale", "string"),
    ("training_seed", "integer"),
    ("scenario_id", "string"),
    ("config_hash", "string"),
    ("git_commit", "string"),
    ("termination_reason", "string"),
)
JOB_STATES = ["pending", "running", "completed", "failed", "stale"]
RECOVERY_FIELDS = [
    "run_id",
    "identity",
    "state",
    "started_at",
    "updated_at",
    "config_hash",
    "git_commit",
]
ARTIFACT_REQUIRED_FIELDS = [
    "artifact_id",
    "artifact_type",
    "source_paths",
    "source_hashes",
    "generator",
    "generator_commit",
    "generator_sha256",
    "generator_version",
    "output_path",
    "output_sha256",
    "created_at",
    "data_status",
]
ARTIFACT_SCHEMA_FIELDS = [
    "artifact_id",
    "artifact_type",
    "source_paths",
    "source_hashes",
    "generator",
    "generator_commit",
    "generator_sha256",
    "generator_version",
    "output_path",
    "output_sha256",
    "created_at",
    "data_status",
]
RESULT_ARTIFACT_STATUSES = ["validated", "locked_summary"]
SERVICE_TRANSFER_CONTRACT = {
    "service_cap_parameter_id": "service.transfer_cap",
    "transfer_volume_l": {
        "operation": "minimum",
        "operands": [
            "uav_free_capacity_l",
            "service_cap_l",
            "vehicle_remaining_inventory_l",
        ],
    },
    "accounting_boundary": "service_completion",
}
REQUEST_TRIGGER_CONTRACT = {
    "safety_margin_parameter_id": "service.request_safety_margin",
    "remaining_spray_endurance_s": {
        "operation": "divide",
        "numerator": "uav_remaining_pesticide_l",
        "denominator": "spray_flow_l_per_s",
    },
    "spray_flow_conversion": {
        "source_parameter_id": "uav.spray_flow",
        "from_unit": "L/min",
        "to_unit": "L/s",
        "operation": "divide_by_60",
    },
    "request_when": {
        "left": "remaining_spray_endurance_s",
        "operator": "less_than_or_equal",
        "right": {
            "operation": "sum",
            "operands": [
                "estimated_time_to_service_s",
                "request_safety_margin_s",
            ],
        },
    },
    "zero_spray_flow_policy": "do_not_trigger_from_endurance_rule",
    "active_request_policy": "at_most_one_active_request_per_uav",
}
FORBIDDEN_ROOTS = [
    "outputs/sr_mappo_paper_v1",
    "C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper",
    "D:/Pycharm/Locust_rl",
]
ROAD_METADATA_FIELDS = [
    "source_hash",
    "crs",
    "bbox",
    "grid_shape",
    "topology_checksum",
    "code_version",
]
PARAMETER_SOURCE_TYPES = {
    "manual",
    "standard",
    "field-study",
    "peer-reviewed-study",
    "expert",
    "assumption",
}
SOURCE_TYPES = {
    "assumption",
    "equipment_manual",
    "field_study",
    "expert_confirmation",
    "source_conversion",
}
FORBIDDEN_ALGORITHM = re.compile(
    r"(?:\bhappo\b|\bhapppo\b|ag[-_ ]?sr[-_ ]?mappo)", re.IGNORECASE
)
FORBIDDEN_MATURITY = re.compile(
    r"(?:\bM[234]\b|implementation(?:\s+tests?)?\s+verif|pilot\s+results?\s+indicate|"
    r"formal\s+experiments?\s+show|significantly\s+outperforms?|\bproves?\b|"
    r"real\s+deployment\s+verified|universally\s+optimal)",
    re.IGNORECASE,
)


def load_yaml(path: Path) -> object:
    """Load YAML using the safe loader."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_job_identity(
    method: str,
    scale: str,
    training_seed: int,
    config_hash: str,
    git_commit: str,
) -> str:
    values = (method, scale, str(training_seed), config_hash, git_commit)
    if any("|" in value for value in values):
        raise ValueError("job identity fields cannot contain '|'")
    return "|".join(values)


def _required(data: dict[str, Any], fields: Sequence[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in data:
            errors.append(f"{label} missing required field: {field}")


def _nonempty_string(value: object, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a nonempty string")
        return False
    return True


def _strict_bool(value: object, label: str, errors: list[str], expected: bool | None = None) -> bool:
    if type(value) is not bool:
        errors.append(f"{label} must be a strict boolean")
        return False
    if expected is not None and value is not expected:
        errors.append(f"{label} must be {expected}")
        return False
    return True


def _number(value: object, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be numeric")
        return None
    return float(value)


def _list(value: object, label: str, errors: list[str]) -> list[Any] | None:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return None
    return value


def _mapping(value: object, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return None
    return value


def _iter_text(value: object) -> list[str]:
    if isinstance(value, dict):
        return [part for pair in value.items() for part in _iter_text(pair)]
    if isinstance(value, (list, tuple)):
        return [part for item in value for part in _iter_text(item)]
    return [value] if isinstance(value, str) else []


def _check_common(name: str, data: dict[str, Any], errors: list[str]) -> None:
    _required(data, ("schema_version", "registry_id", "status"), name, errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{name} has wrong schema version")
    if data.get("registry_id") != REGISTRY_IDS[name]:
        errors.append(f"{name} has wrong registry ID")
    expected_status = "locked" if name == "sealed_test_lock.yaml" else FROZEN_STATUS
    if data.get("status") != expected_status:
        errors.append(f"{name} must have status {expected_status}")
    text = "\n".join(_iter_text(data))
    if FORBIDDEN_ALGORITHM.search(text):
        errors.append(f"{name} contains a forbidden algorithm name or public rename")
    if FORBIDDEN_MATURITY.search(text):
        errors.append(f"{name} contains forbidden maturity or premature result/deployment wording")


def _check_resource_scope(data: dict[str, Any], name: str, errors: list[str]) -> None:
    def visit(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "resource_replenishment" and child != "pesticide_only":
                    errors.append(
                        f"{child_path} resource replenishment must be pesticide-only"
                    )
                if key == "battery_replenishment" and child != "inactive":
                    errors.append(
                        f"{child_path} battery replenishment must remain inactive"
                    )
                if key in {"battery_activation", "battery_replenishment_enabled"} and child is not False:
                    errors.append(f"{child_path} battery activation is forbidden")
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(data, name)


def _check_parameters(data: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    records = _list(data.get("parameters"), "parameters", errors)
    if records is None:
        return {}
    required = (
        "id", "name", "symbol", "meaning", "value", "unit", "min", "max",
        "source_type", "source_id", "source_value", "source_unit", "conversion",
        "status", "scope",
    )
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(records):
        label = f"parameters[{index}]"
        record = _mapping(value, label, errors)
        if record is None:
            continue
        _required(record, required, label, errors)
        for field in ("id", "name", "symbol", "meaning", "unit", "source_id", "source_unit", "conversion", "scope"):
            _nonempty_string(record.get(field), f"{label}.{field}", errors)
        parameter_id = record.get("id")
        if isinstance(parameter_id, str):
            if parameter_id in result:
                errors.append(f"duplicate parameter ID: {parameter_id}")
            result[parameter_id] = record
        source_type = record.get("source_type")
        if source_type not in PARAMETER_SOURCE_TYPES:
            errors.append(f"{label}.source_type is not an allowed enum")
        if record.get("status") not in {"verified", "provisional"}:
            errors.append(f"{label}.status is not an allowed parameter status")
        minimum = _number(record.get("min"), f"{label}.min", errors)
        current = _number(record.get("value"), f"{label}.value", errors)
        maximum = _number(record.get("max"), f"{label}.max", errors)
        _number(record.get("source_value"), f"{label}.source_value", errors)
        if None not in (minimum, current, maximum) and not minimum <= current <= maximum:
            errors.append(f"{label} range must satisfy min <= value <= max")
    service_cap = result.get("service.transfer_cap")
    if service_cap is None:
        errors.append("parameter registry missing required service cap parameter")
    elif service_cap.get("unit") != "L":
        errors.append("service cap parameter must use L")
    else:
        service_cap_minimum = _number(
            service_cap.get("min"), "service cap parameter minimum", errors
        )
        service_cap_value = _number(
            service_cap.get("value"), "service cap parameter value", errors
        )
        if service_cap_minimum is not None and service_cap_minimum <= 0:
            errors.append("service cap parameter minimum must be positive")
        if service_cap_value is not None and service_cap_value <= 0:
            errors.append("service cap parameter value must be positive")
    request_margin = result.get("service.request_safety_margin")
    if request_margin is None:
        errors.append("parameter registry missing required request safety-margin parameter")
    elif request_margin.get("unit") != "s":
        errors.append("request safety-margin parameter must use s")
    else:
        request_margin_minimum = _number(
            request_margin.get("min"), "request safety-margin parameter minimum", errors
        )
        request_margin_value = _number(
            request_margin.get("value"), "request safety-margin parameter value", errors
        )
        if request_margin_minimum is not None and request_margin_minimum < 0:
            errors.append("request safety-margin parameter minimum cannot be negative")
        if request_margin_value is not None and request_margin_value < 0:
            errors.append("request safety-margin parameter value cannot be negative")
    if data.get("service_transfer_contract") != SERVICE_TRANSFER_CONTRACT:
        errors.append("service cap transfer contract is missing or not exact")
    if data.get("request_trigger_contract") != REQUEST_TRIGGER_CONTRACT:
        errors.append("request trigger contract is missing or not exact")
    return result


def _check_sources(data: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    records = _list(data.get("sources"), "sources", errors)
    if records is None:
        return {}
    required = (
        "id", "source_type", "title", "authors", "venue", "year", "locator",
        "authority", "access_status", "full_text_status", "verification_status",
        "supports",
    )
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(records):
        label = f"sources[{index}]"
        record = _mapping(value, label, errors)
        if record is None:
            continue
        _required(record, required, label, errors)
        for field in ("id", "title", "venue", "authority"):
            _nonempty_string(record.get(field), f"{label}.{field}", errors)
        source_id = record.get("id")
        if isinstance(source_id, str):
            if source_id in result:
                errors.append(f"duplicate source ID: {source_id}")
            result[source_id] = record
        if record.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{label}.source_type is not an allowed enum")
        if not isinstance(record.get("authors"), list):
            errors.append(f"{label}.authors must be a list")
        verification = record.get("verification_status")
        if verification not in {"design_record", "pending", "verified"}:
            errors.append(f"{label}.verification_status is not an allowed enum")
        if record.get("access_status") not in {"read", "pending", "inaccessible"}:
            errors.append(f"{label}.access_status is not an allowed enum")
        if record.get("full_text_status") not in {"not_applicable", "pending", "metadata_only", "full_text"}:
            errors.append(f"{label}.full_text_status is not an allowed enum")
        if verification == "pending":
            _required(record, ("database", "authoritative_page", "applicability_limit"), label, errors)
            _nonempty_string(record.get("applicability_limit"), f"{label}.applicability_limit", errors)
        supports = _list(record.get("supports"), f"{label}.supports", errors)
        if supports is None:
            continue
        seen: set[str] = set()
        for support_index, support_value in enumerate(supports):
            support_label = f"{label}.supports[{support_index}]"
            support = _mapping(support_value, support_label, errors)
            if support is None:
                continue
            _required(support, ("parameter_id", "claim", "applicability_limit"), support_label, errors)
            for field in ("parameter_id", "claim", "applicability_limit"):
                _nonempty_string(support.get(field), f"{support_label}.{field}", errors)
            parameter_id = support.get("parameter_id")
            if isinstance(parameter_id, str):
                if parameter_id in seen:
                    errors.append(f"duplicate support for parameter {parameter_id} in source {source_id}")
                seen.add(parameter_id)
    return result


def _check_support_consistency(
    parameters: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    supported_pairs: set[tuple[str, str]] = set()
    for source_id, source in sources.items():
        supports = source.get("supports")
        if not isinstance(supports, list):
            continue
        for support in supports:
            if not isinstance(support, dict) or not isinstance(support.get("parameter_id"), str):
                continue
            parameter_id = support["parameter_id"]
            supported_pairs.add((source_id, parameter_id))
            parameter = parameters.get(parameter_id)
            if parameter is None:
                errors.append(f"source {source_id} support references unknown parameter {parameter_id}")
            elif parameter.get("source_id") != source_id:
                errors.append(f"source-to-parameter support mismatch for {source_id} and {parameter_id}")
    for parameter_id, parameter in parameters.items():
        source_id = parameter.get("source_id")
        if source_id not in sources:
            errors.append(f"parameter {parameter_id} references unknown source {source_id}")
        elif (source_id, parameter_id) not in supported_pairs:
            errors.append(f"parameter-to-source support missing for {parameter_id} and {source_id}")


def _check_matrix(data: dict[str, Any], errors: list[str]) -> None:
    methods = _list(data.get("methods"), "experiment methods", errors)
    if methods is not None:
        if methods != PRIMARY_METHODS:
            errors.append("experiment methods must use the exact primary method family")
        if len(methods) != len(set(str(item) for item in methods)):
            errors.append("duplicate method IDs")
    scales = _mapping(data.get("scales"), "experiment scales", errors)
    if scales is not None:
        if set(scales) != set(SCALE_HORIZONS):
            errors.append("experiment scales must define the exact six scales")
        for scale, horizon in SCALE_HORIZONS.items():
            record = _mapping(scales.get(scale), f"scale {scale}", errors)
            if record is not None and record != {"max_physical_decision_steps": horizon}:
                errors.append(f"{scale} has the wrong maximum horizon or fields")

    metric_records = _list(data.get("metrics"), "canonical metric dictionary", errors)
    observed_metrics: dict[str, tuple[object, object, object]] = {}
    if metric_records is not None:
        for index, value in enumerate(metric_records):
            label = f"metrics[{index}]"
            metric = _mapping(value, label, errors)
            if metric is None:
                continue
            if set(metric) != {"name", "type", "unit", "category"}:
                errors.append(f"{label} must contain exact metric fields")
            for field in ("name", "type", "unit", "category"):
                _nonempty_string(metric.get(field), f"{label}.{field}", errors)
            name = metric.get("name")
            if isinstance(name, str):
                if name in observed_metrics:
                    errors.append(f"duplicate metric name: {name}")
                observed_metrics[name] = (
                    metric.get("type"), metric.get("unit"), metric.get("category")
                )
        if list(observed_metrics) != list(METRICS) or observed_metrics != METRICS:
            errors.append("canonical metric dictionary does not match the exact metric contract")

    evaluation = _mapping(data.get("evaluation"), "evaluation", errors)
    if evaluation is not None:
        expected_groups = {
            "primary_outcomes": ["reduction_rate", "success_at_0_85"],
            "mechanism_metrics": [
                "rendezvous_distance_m", "waiting_steps", "pesticide_disabled_steps",
                "return_steps", "effective_spray_steps", "transferred_pesticide_l",
            ],
            "operational_metrics": [
                "request_count", "request_completed_count", "vehicle_travel_steps",
                "vehicle_idle_steps", "vehicle_stranded_inventory_l", "decision_runtime_s",
            ],
            "resource_metrics": [
                "initial_uav_pesticide_l", "final_uav_pesticide_l",
                "initial_vehicle_inventory_l", "final_vehicle_inventory_l",
                "requested_pesticide_l", "sprayed_pesticide_l", "total_available_supply_l",
            ],
        }
        for key, expected in expected_groups.items():
            if evaluation.get(key) != expected:
                errors.append(f"evaluation {key} does not match canonical metrics")
        if evaluation.get("success_threshold") != {"metric": "reduction_rate", "value": 0.85}:
            errors.append("evaluation success threshold is not exact")
        _strict_bool(
            evaluation.get("training_reward_is_diagnostic_only"),
            "evaluation.training_reward_is_diagnostic_only",
            errors,
            True,
        )

    protocol = _mapping(data.get("protocol"), "experiment protocol", errors)
    if protocol is not None:
        fairness = _mapping(protocol.get("fairness"), "protocol fairness", errors)
        if fairness is not None:
            if set(fairness) != set(FAIRNESS_FIELDS):
                errors.append("protocol fairness fields are incomplete or unexpected")
            for field in FAIRNESS_FIELDS:
                _strict_bool(fairness.get(field), f"fairness.{field}", errors, True)
        if protocol.get("exception_status") != "none_frozen":
            errors.append("protocol exception_status must be none_frozen")
        if protocol.get("resource_replenishment") != "pesticide_only":
            errors.append("protocol resource replenishment must be pesticide-only")
        if protocol.get("battery_replenishment") != "inactive":
            errors.append("protocol battery replenishment must remain inactive")


def _check_seeds(data: dict[str, Any], errors: list[str]) -> tuple[int | None, int | None]:
    partitions = _mapping(data.get("partitions"), "seed partitions", errors)
    if partitions is None:
        return None, None
    if set(partitions) != {"training", "validation", "sealed_test"}:
        errors.append("seed partitions must contain exactly training, validation, and sealed_test")
    expected = {
        "training": {
            "seeds": TRAINING_SEEDS,
            "purpose": "training",
            "tuning_allowed": True,
        },
        "validation": {
            "start": 20000,
            "end": 20049,
            "purpose": "checkpoint_selection_and_algorithm_tuning",
            "tuning_allowed": True,
        },
        "sealed_test": {
            "start": 30000,
            "end": 30099,
            "purpose": "sealed_test",
            "tuning_allowed": False,
            "locked": True,
        },
    }
    for label, expected_record in expected.items():
        record = _mapping(partitions.get(label), f"{label} partition", errors)
        if record is None:
            continue
        if record != expected_record:
            errors.append(f"{label} seed partition is not exact")
        if "tuning_allowed" in record:
            _strict_bool(record.get("tuning_allowed"), f"{label}.tuning_allowed", errors)
        if label == "sealed_test" and "locked" in record:
            _strict_bool(record.get("locked"), "sealed_test.locked", errors, True)
    if data.get("overlap_policy") != "disjoint":
        errors.append("seed overlap policy must be disjoint")
    training = partitions.get("training")
    validation = partitions.get("validation")
    sealed = partitions.get("sealed_test")
    training_values = training.get("seeds", []) if isinstance(training, dict) else []
    validation_values = (
        set(range(validation["start"], validation["end"] + 1))
        if isinstance(validation, dict)
        and isinstance(validation.get("start"), int)
        and isinstance(validation.get("end"), int)
        and validation["start"] <= validation["end"]
        else set()
    )
    sealed_values = (
        set(range(sealed["start"], sealed["end"] + 1))
        if isinstance(sealed, dict)
        and isinstance(sealed.get("start"), int)
        and isinstance(sealed.get("end"), int)
        and sealed["start"] <= sealed["end"]
        else set()
    )
    training_set = set(training_values) if isinstance(training_values, list) else set()
    if training_set & validation_values or training_set & sealed_values or validation_values & sealed_values:
        errors.append("seed partitions overlap")
    if isinstance(sealed, dict):
        return sealed.get("start"), sealed.get("end")
    return None, None


def _check_identity(data: dict[str, Any], errors: list[str]) -> None:
    expected_fields = ["method", "scale", "training_seed", "config_hash", "git_commit"]
    if data.get("identity_fields") != expected_fields:
        errors.append("job identity fields are not exact")
    serialization = _mapping(data.get("serialization"), "job identity serialization", errors)
    if serialization is not None:
        expected_serialization = {
            "separator": "|",
            "order": "identity_fields",
            "format": "method|scale|training_seed|config_hash|git_commit",
            "hash_algorithm": "SHA-256",
        }
        if serialization != expected_serialization:
            errors.append("job identity serialization must use the exact SHA-256 contract")
    if data.get("states") != JOB_STATES:
        errors.append("job states must be exactly pending/running/completed/failed/stale")
    if data.get("required_recovery_fields") != RECOVERY_FIELDS:
        errors.append("job recovery fields are not exact")
    if data.get("sealed_test_creation_gate") != "G7":
        errors.append("sealed job creation gate must be G7")


def _expected_raw_fields() -> list[dict[str, object]]:
    fields: list[dict[str, object]] = [
        {"name": name, "type": field_type, "required": True}
        for name, field_type in RAW_IDENTITY_FIELDS
    ]
    fields.extend(
        {"name": name, "type": field_type, "unit": unit, "required": True}
        for name, (field_type, unit, _category) in METRICS.items()
    )
    return fields


def _check_schema_fields(
    data: dict[str, Any],
    label: str,
    expected: list[dict[str, object]],
    errors: list[str],
) -> None:
    fields = _list(data.get("fields"), f"{label} fields", errors)
    if fields is None:
        return
    names: list[object] = []
    for index, value in enumerate(fields):
        field = _mapping(value, f"{label} fields[{index}]", errors)
        if field is None:
            continue
        names.append(field.get("name"))
        _nonempty_string(field.get("name"), f"{label} fields[{index}].name", errors)
        _nonempty_string(field.get("type"), f"{label} fields[{index}].type", errors)
        _strict_bool(field.get("required"), f"{label} fields[{index}].required", errors, True)
    if len(names) != len(set(str(name) for name in names)):
        errors.append(f"{label} has duplicate schema field names")
    if fields != expected:
        errors.append(f"{label} metric and identity fields are not exact")


def _check_artifact(data: dict[str, Any], errors: list[str]) -> None:
    required = _list(data.get("required_fields"), "artifact schema required_fields", errors)
    schema = _mapping(data.get("record_schema"), "artifact schema record_schema", errors)
    if required is not None:
        if required != ARTIFACT_REQUIRED_FIELDS or len(required) != len(set(str(item) for item in required)):
            errors.append("artifact schema required fields are incomplete, reordered, or duplicate")
    if schema is None:
        return
    if list(schema) != ARTIFACT_SCHEMA_FIELDS:
        errors.append("artifact schema record fields are not exact")
    def result_provenance(field_type: str) -> dict[str, object]:
        return {
            "type": field_type,
            "required": True,
            "non_null_when": RESULT_ARTIFACT_STATUSES,
        }

    expected_schema = {
        "artifact_id": {"type": "string", "required": True},
        "artifact_type": {
            "type": "string",
            "allowed": ["figure", "table", "text_block"],
            "required": True,
        },
        "source_paths": {"type": "list", "required": True},
        "source_hashes": {"type": "list", "required": True},
        "generator": {"type": "string", "required": True},
        "generator_commit": result_provenance("git_commit_or_null"),
        "generator_sha256": result_provenance("sha256_or_null"),
        "generator_version": result_provenance("string_or_null"),
        "output_path": {"type": "string", "required": True},
        "output_sha256": result_provenance("sha256_or_null"),
        "created_at": result_provenance("utc_datetime_or_null"),
        "data_status": {
            "type": "string",
            "allowed": ["design_only", "validated", "locked_summary"],
            "required": True,
        },
    }
    if schema != expected_schema:
        errors.append("artifact schema execution provenance contract is not exact")


def _check_sealed(
    data: dict[str, Any],
    manifest_range: tuple[int | None, int | None],
    errors: list[str],
) -> None:
    expected_keys = {
        "schema_version", "registry_id", "status", "scenario_range", "unlock_gate",
        "maximum_unlock_count", "actual_unlock_count", "tuning_allowed_before_unlock",
        "resource_replenishment", "battery_replenishment",
    }
    if set(data) != expected_keys:
        errors.append("sealed-test lock policy fields are not exact")
    scenario = _mapping(data.get("scenario_range"), "sealed-test scenario range", errors)
    lock_range = (None, None)
    if scenario is not None:
        lock_range = (scenario.get("start"), scenario.get("end"))
        if scenario != {"start": 30000, "end": 30099}:
            errors.append("sealed-test scenario range is not exact")
    if lock_range != manifest_range:
        errors.append("sealed-test range conflicts across lock and seed manifest")
    maximum_unlock_count = data.get("maximum_unlock_count")
    actual_unlock_count = data.get("actual_unlock_count")
    if data.get("unlock_gate") != "G7":
        errors.append("sealed-test unlock gate must be G7")
    if type(maximum_unlock_count) is not int or maximum_unlock_count != 1:
        errors.append("sealed-test maximum unlock count must be exactly one")
    if type(actual_unlock_count) is not int or actual_unlock_count != 0:
        errors.append("sealed-test actual unlock count must be zero while locked")
    _strict_bool(data.get("tuning_allowed_before_unlock"), "sealed-test tuning policy", errors, False)
    if data.get("resource_replenishment") != "pesticide_only":
        errors.append("sealed-test resource replenishment must be pesticide-only")
    if data.get("battery_replenishment") != "inactive":
        errors.append("sealed-test battery replenishment must remain inactive")


def _check_output(data: dict[str, Any], errors: list[str]) -> None:
    expected_keys = {
        "schema_version", "registry_id", "status", "root", "allowed_descendants_only",
        "forbidden_roots", "source_inputs", "derived_road_cache_required_metadata",
    }
    if set(data) != expected_keys:
        errors.append("output guard contract fields are incomplete or unexpected")
    if data.get("root") != "outputs/problem2_sr_mappo_v1":
        errors.append("output root must be outputs/problem2_sr_mappo_v1")
    _strict_bool(data.get("allowed_descendants_only"), "output allowed_descendants_only", errors, True)
    if data.get("forbidden_roots") != FORBIDDEN_ROOTS:
        errors.append("output guard forbidden roots are not exact")
    source_inputs = _mapping(data.get("source_inputs"), "output source_inputs", errors)
    if source_inputs is not None:
        if set(source_inputs) != {"osm_inputs_are_simulation_only", "source_files_read_only"}:
            errors.append("output source input guard fields are not exact")
        _strict_bool(source_inputs.get("osm_inputs_are_simulation_only"), "OSM simulation-only flag", errors, True)
        _strict_bool(source_inputs.get("source_files_read_only"), "source read-only flag", errors, True)
    if data.get("derived_road_cache_required_metadata") != ROAD_METADATA_FIELDS:
        errors.append("output guard derived road metadata requirements are not exact")


def _repository_commit(errors: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="strict",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        errors.append(f"could not resolve repository commit: {exc}")
        return ""


def _provenance(registry_hashes: dict[str, str], errors: list[str]) -> dict[str, Any]:
    validator_path = Path(__file__).resolve()
    try:
        validator_hash = hashlib.sha256(validator_path.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"could not hash validator file: {exc}")
        validator_hash = ""
    return {
        "registry_sha256": registry_hashes,
        "validator": {
            "path": validator_path.relative_to(ROOT).as_posix(),
            "sha256": validator_hash,
            "version": VALIDATOR_VERSION,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": _repository_commit(errors),
    }


def validate_registries(registry_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_files: list[str] = []
    registry_hashes: dict[str, str] = {}
    registries: dict[str, dict[str, Any]] = {}

    try:
        extra_yaml = sorted(
            path.name for path in registry_root.glob("*.yaml")
            if path.name not in REGISTRY_NAMES
        )
    except OSError as exc:
        errors.append(f"could not inspect registry root: {exc}")
        extra_yaml = []
    if extra_yaml:
        errors.append(f"unexpected G1 registry files: {extra_yaml}")

    for name in REGISTRY_NAMES:
        path = registry_root / name
        if not path.is_file():
            errors.append(f"missing registry file: {name}")
            continue
        checked_files.append(name)
        try:
            raw = path.read_bytes()
            registry_hashes[name] = hashlib.sha256(raw).hexdigest()
            value = yaml.safe_load(raw.decode("utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(f"could not load {name}: {exc}")
            continue
        data = _mapping(value, f"{name} root", errors)
        if data is None:
            continue
        registries[name] = data
        _check_common(name, data, errors)
        _check_resource_scope(data, name, errors)

    parameters: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    sealed_range: tuple[int | None, int | None] = (None, None)
    checkers = (
        ("parameter_registry.yaml", lambda data: parameters.update(_check_parameters(data, errors))),
        ("literature_source_ledger.yaml", lambda data: sources.update(_check_sources(data, errors))),
        ("experiment_matrix.yaml", lambda data: _check_matrix(data, errors)),
        ("scenario_seed_manifest.yaml", lambda data: None),
        ("job_identity_contract.yaml", lambda data: _check_identity(data, errors)),
        ("raw_episode_schema.yaml", lambda data: _check_schema_fields(data, "raw episode schema", _expected_raw_fields(), errors)),
        ("validated_long_table_schema.yaml", lambda data: _check_schema_fields(
            data,
            "validated table schema",
            _expected_raw_fields() + [
                {"name": "validation_status", "type": "string", "required": True},
                {"name": "source_row_reference", "type": "string", "required": True},
            ],
            errors,
        )),
        ("artifact_manifest_schema.yaml", lambda data: _check_artifact(data, errors)),
        ("output_root_contract.yaml", lambda data: _check_output(data, errors)),
    )
    for name, checker in checkers:
        data = registries.get(name)
        if data is None:
            continue
        try:
            checker(data)
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"{name} validation failed closed for malformed data: {type(exc).__name__}: {exc}")

    seed_data = registries.get("scenario_seed_manifest.yaml")
    if seed_data is not None:
        try:
            sealed_range = _check_seeds(seed_data, errors)
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"scenario_seed_manifest.yaml validation failed closed: {type(exc).__name__}: {exc}")
    sealed_data = registries.get("sealed_test_lock.yaml")
    if sealed_data is not None:
        try:
            _check_sealed(sealed_data, sealed_range, errors)
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"sealed_test_lock.yaml validation failed closed: {type(exc).__name__}: {exc}")
    _check_support_consistency(parameters, sources, errors)

    pending_count = sum(
        source.get("verification_status") == "pending" for source in sources.values()
    )
    if pending_count:
        warnings.append(
            f"{pending_count} external source records remain pending and are not verified evidence"
        )
    provenance = _provenance(registry_hashes, errors)
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "checked_files": checked_files,
        "counts": {
            "expected_files": len(REGISTRY_NAMES),
            "checked_files": len(checked_files),
            "parameters": len(parameters),
            "sources": len(sources),
            "metrics": len(METRICS),
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "provenance": provenance,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_registries(args.root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
