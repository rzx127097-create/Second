from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable

import pytest
import yaml

from scripts.audit_g1_registries import build_job_identity, validate_registries


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = ROOT / "docs" / "evidence" / "g1"
REGISTRY_NAMES = (
    "parameter_registry.yaml",
    "literature_source_ledger.yaml",
    "experiment_matrix.yaml",
    "scenario_seed_manifest.yaml",
    "job_identity_contract.yaml",
    "raw_episode_schema.yaml",
    "validated_long_table_schema.yaml",
    "artifact_manifest_schema.yaml",
    "sealed_test_lock.yaml",
    "output_root_contract.yaml",
)
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
CANONICAL_METRICS = {
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


def load(name: str, root: Path = REGISTRY_ROOT) -> dict[str, Any]:
    with (root / name).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    assert isinstance(value, dict)
    return value


def write(name: str, root: Path, value: object) -> None:
    (root / name).write_text(
        yaml.safe_dump(value, sort_keys=False), encoding="utf-8"
    )


def copy_registry_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "g1"
    shutil.copytree(REGISTRY_ROOT, destination)
    return destination


def test_all_g1_registries_have_exact_identity_and_status() -> None:
    for name in REGISTRY_NAMES:
        registry = load(name)
        assert registry["schema_version"] == "g1.v1"
        assert registry["registry_id"] == REGISTRY_IDS[name]
        expected_status = "locked" if name == "sealed_test_lock.yaml" else "design_frozen"
        assert registry["status"] == expected_status


def test_canonical_metrics_fairness_and_table_schemas_are_complete() -> None:
    matrix = load("experiment_matrix.yaml")
    metrics = {
        item["name"]: (item["type"], item["unit"], item["category"])
        for item in matrix["metrics"]
    }
    assert metrics == CANONICAL_METRICS
    assert matrix["evaluation"]["primary_outcomes"] == [
        "reduction_rate",
        "success_at_0_85",
    ]
    assert matrix["protocol"]["fairness"] == {
        name: True for name in FAIRNESS_FIELDS
    }

    raw_fields = load("raw_episode_schema.yaml")["fields"]
    validated_fields = load("validated_long_table_schema.yaml")["fields"]
    raw_by_name = {field["name"]: field for field in raw_fields}
    validated_by_name = {field["name"]: field for field in validated_fields}
    assert len(raw_by_name) == len(raw_fields)
    assert len(validated_by_name) == len(validated_fields)
    for name, (field_type, unit, _category) in CANONICAL_METRICS.items():
        assert raw_by_name[name]["type"] == field_type
        assert raw_by_name[name]["unit"] == unit
        assert validated_by_name[name]["type"] == field_type
        assert validated_by_name[name]["unit"] == unit
    assert set(validated_by_name) == set(raw_by_name) | {
        "validation_status",
        "source_row_reference",
    }
    for name, raw_field in raw_by_name.items():
        assert validated_by_name[name] == raw_field


def test_primary_method_family_scale_and_seed_protocol_are_exact() -> None:
    matrix = load("experiment_matrix.yaml")
    assert matrix["methods"] == [
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    ]
    assert matrix["scales"] == {
        "g20x20_d2": {"max_physical_decision_steps": 150},
        "g20x30_d3": {"max_physical_decision_steps": 180},
        "g20x40_d3": {"max_physical_decision_steps": 220},
        "g30x30_d3": {"max_physical_decision_steps": 220},
        "g30x40_d4": {"max_physical_decision_steps": 280},
        "g30x50_d4": {"max_physical_decision_steps": 350},
    }
    manifest = load("scenario_seed_manifest.yaml")
    assert manifest["partitions"]["training"]["seeds"] == [42, 123, 2024, 3407, 7919]
    assert manifest["partitions"]["validation"] == {
        "start": 20000,
        "end": 20049,
        "purpose": "checkpoint_selection_and_algorithm_tuning",
        "tuning_allowed": True,
    }
    assert manifest["partitions"]["sealed_test"]["tuning_allowed"] is False


def test_pending_external_sources_expose_lookup_fields() -> None:
    ledger = load("literature_source_ledger.yaml")
    pending_sources = [
        source for source in ledger["sources"]
        if source["verification_status"] == "pending"
    ]
    assert pending_sources
    for source in pending_sources:
        assert "database" in source
        assert "authoritative_page" in source


def test_sealed_test_is_locked_once_at_g7() -> None:
    lock = load("sealed_test_lock.yaml")
    assert lock["status"] == "locked"
    assert lock["unlock_gate"] == "G7"
    assert lock.get("maximum_unlock_count") == 1
    assert lock.get("actual_unlock_count") == 0
    assert "unlock_count" not in lock
    assert lock["tuning_allowed_before_unlock"] is False


def test_parameter_registry_defines_executable_service_and_request_contracts() -> None:
    registry = load("parameter_registry.yaml")
    parameters = {record["id"]: record for record in registry["parameters"]}
    parameter_ids = set(parameters)
    assert "service.transfer_cap" in parameter_ids
    assert "service.request_safety_margin" in parameter_ids
    assert parameters["service.transfer_cap"]["unit"] == "L"
    assert parameters["service.transfer_cap"]["value"] > 0
    assert parameters["service.request_safety_margin"]["unit"] == "s"
    assert parameters["service.request_safety_margin"]["value"] >= 0
    assert registry.get("service_transfer_contract") == {
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
    assert registry.get("request_trigger_contract") == {
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


def test_artifact_schema_requires_non_null_execution_provenance_for_results() -> None:
    schema = load("artifact_manifest_schema.yaml")
    result_statuses = ["validated", "locked_summary"]
    provenance_types = {
        "generator_commit": "git_commit_or_null",
        "created_at": "utc_datetime_or_null",
        "generator_sha256": "sha256_or_null",
        "generator_version": "string_or_null",
        "output_sha256": "sha256_or_null",
    }
    for field, field_type in provenance_types.items():
        assert field in schema["required_fields"]
        assert schema["record_schema"].get(field) == {
            "type": field_type,
            "required": True,
            "non_null_when": result_statuses,
        }


def test_job_identity_is_canonical_and_ordered() -> None:
    assert build_job_identity(
        "sr_mappo_mobile", "g20x20_d2", 42, "abc123", "deadbeef"
    ) == "sr_mappo_mobile|g20x20_d2|42|abc123|deadbeef"


def _mutate_unknown_source(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"][0]["source_id"] = "SRC-UNKNOWN"
    write("parameter_registry.yaml", root, data)


def _mutate_inverted_range(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"][0]["min"] = data["parameters"][0]["value"] + 1
    write("parameter_registry.yaml", root, data)


def _mutate_one_field_raw_schema(root: Path) -> None:
    data = load("raw_episode_schema.yaml", root)
    data["fields"] = data["fields"][:1]
    write("raw_episode_schema.yaml", root, data)


def _mutate_job_state(root: Path) -> None:
    data = load("job_identity_contract.yaml", root)
    data["states"] = ["queued", "done"]
    write("job_identity_contract.yaml", root, data)


def _mutate_job_hash(root: Path) -> None:
    data = load("job_identity_contract.yaml", root)
    data["serialization"]["hash_algorithm"] = "MD5"
    write("job_identity_contract.yaml", root, data)


def _mutate_removed_output_guards(root: Path) -> None:
    data = load("output_root_contract.yaml", root)
    data.pop("forbidden_roots", None)
    data.pop("source_inputs", None)
    data.pop("derived_road_cache_required_metadata", None)
    write("output_root_contract.yaml", root, data)


def _mutate_m2_wording(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"][0]["meaning"] = "M2 implementation verified"
    write("parameter_registry.yaml", root, data)


def _mutate_metric_mismatch(root: Path) -> None:
    data = load("raw_episode_schema.yaml", root)
    target = next(item for item in data["fields"] if item["name"] == "reduction_rate")
    target["unit"] = "%"
    write("raw_episode_schema.yaml", root, data)


def _mutate_incomplete_fairness(root: Path) -> None:
    data = load("experiment_matrix.yaml", root)
    data["protocol"]["fairness"] = {name: True for name in FAIRNESS_FIELDS[:-1]}
    write("experiment_matrix.yaml", root, data)


def _mutate_non_boolean_fairness(root: Path) -> None:
    data = load("experiment_matrix.yaml", root)
    data["protocol"]["fairness"] = {name: True for name in FAIRNESS_FIELDS}
    data["protocol"]["fairness"][FAIRNESS_FIELDS[0]] = 1
    write("experiment_matrix.yaml", root, data)


def _mutate_registry_id(root: Path) -> None:
    data = load("raw_episode_schema.yaml", root)
    data["registry_id"] = "G1-WRONG"
    write("raw_episode_schema.yaml", root, data)


def _mutate_empty_required_string(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"][0]["name"] = "   "
    write("parameter_registry.yaml", root, data)


def _mutate_parameter_enum(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"][0]["source_type"] = "unreviewed_blog"
    write("parameter_registry.yaml", root, data)


def _mutate_support_mismatch(root: Path) -> None:
    data = load("literature_source_ledger.yaml", root)
    data["sources"][0]["supports"] = data["sources"][0]["supports"][:-1]
    write("literature_source_ledger.yaml", root, data)


def _mutate_duplicate_schema_field(root: Path) -> None:
    data = load("raw_episode_schema.yaml", root)
    data["fields"].append(copy.deepcopy(data["fields"][-1]))
    write("raw_episode_schema.yaml", root, data)


def _mutate_artifact_schema(root: Path) -> None:
    data = load("artifact_manifest_schema.yaml", root)
    data["required_fields"] = ["artifact_id"]
    data["record_schema"] = {"artifact_id": data["record_schema"]["artifact_id"]}
    write("artifact_manifest_schema.yaml", root, data)


def _mutate_missing_service_cap_contract(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data["parameters"] = [
        record for record in data["parameters"]
        if record["id"] != "service.transfer_cap"
    ]
    data.pop("service_transfer_contract", None)
    write("parameter_registry.yaml", root, data)

    ledger = load("literature_source_ledger.yaml", root)
    for source in ledger["sources"]:
        source["supports"] = [
            support for support in source["supports"]
            if support["parameter_id"] != "service.transfer_cap"
        ]
    write("literature_source_ledger.yaml", root, ledger)


def _mutate_missing_request_trigger_contract(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    data.pop("request_trigger_contract", None)
    write("parameter_registry.yaml", root, data)


def _mutate_ambiguous_sealed_unlock_state(root: Path) -> None:
    data = load("sealed_test_lock.yaml", root)
    data.pop("maximum_unlock_count", None)
    data.pop("actual_unlock_count", None)
    data["unlock_count"] = 1
    write("sealed_test_lock.yaml", root, data)


def _mutate_result_artifact_provenance_to_nullable(root: Path) -> None:
    data = load("artifact_manifest_schema.yaml", root)
    for field in (
        "generator_commit",
        "created_at",
        "generator_sha256",
        "generator_version",
        "output_sha256",
    ):
        record = data["record_schema"].get(field)
        if isinstance(record, dict):
            record.pop("non_null_when", None)
    write("artifact_manifest_schema.yaml", root, data)


def _mutate_validation_tuning_to_forbidden(root: Path) -> None:
    data = load("scenario_seed_manifest.yaml", root)
    data["partitions"]["validation"] = {
        "start": 20000,
        "end": 20049,
        "purpose": "fixed_scenario_validation",
        "tuning_allowed": False,
    }
    write("scenario_seed_manifest.yaml", root, data)


def _mutate_nonpositive_service_cap_lower_bound(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    record = next(
        item for item in data["parameters"]
        if item["id"] == "service.transfer_cap"
    )
    record["min"] = 0.0
    write("parameter_registry.yaml", root, data)


def _mutate_negative_request_safety_margin_lower_bound(root: Path) -> None:
    data = load("parameter_registry.yaml", root)
    record = next(
        item for item in data["parameters"]
        if item["id"] == "service.request_safety_margin"
    )
    record["min"] = -1.0
    write("parameter_registry.yaml", root, data)


NEGATIVE_CASES: tuple[tuple[str, Callable[[Path], None], str], ...] = (
    ("unknown source ID", _mutate_unknown_source, "unknown source"),
    ("inverted parameter range", _mutate_inverted_range, "range"),
    ("one-field raw schema", _mutate_one_field_raw_schema, "raw episode schema"),
    ("invalid job states", _mutate_job_state, "job states"),
    ("invalid identity hash", _mutate_job_hash, "SHA-256"),
    ("removed output guards", _mutate_removed_output_guards, "output guard"),
    ("M2 wording", _mutate_m2_wording, "maturity"),
    ("metric mismatch", _mutate_metric_mismatch, "metric"),
    ("incomplete fairness", _mutate_incomplete_fairness, "fairness"),
    ("non-boolean fairness", _mutate_non_boolean_fairness, "boolean"),
    ("wrong registry ID", _mutate_registry_id, "registry ID"),
    ("empty required string", _mutate_empty_required_string, "nonempty"),
    ("invalid parameter enum", _mutate_parameter_enum, "source_type"),
    ("two-way support mismatch", _mutate_support_mismatch, "support"),
    ("duplicate schema field", _mutate_duplicate_schema_field, "duplicate"),
    ("incomplete artifact schema", _mutate_artifact_schema, "artifact schema"),
    ("missing service-cap contract", _mutate_missing_service_cap_contract, "service cap"),
    ("missing request-trigger contract", _mutate_missing_request_trigger_contract, "request trigger"),
    ("ambiguous sealed unlock state", _mutate_ambiguous_sealed_unlock_state, "unlock"),
    (
        "nullable result-artifact provenance",
        _mutate_result_artifact_provenance_to_nullable,
        "provenance",
    ),
    ("validation tuning forbidden", _mutate_validation_tuning_to_forbidden, "validation"),
    (
        "nonpositive service-cap lower bound",
        _mutate_nonpositive_service_cap_lower_bound,
        "service cap",
    ),
    (
        "negative request-safety-margin lower bound",
        _mutate_negative_request_safety_margin_lower_bound,
        "safety-margin",
    ),
)


@pytest.mark.parametrize(
    ("case", "mutator", "expected_error"),
    NEGATIVE_CASES,
    ids=[case[0] for case in NEGATIVE_CASES],
)
def test_validator_rejects_semantically_invalid_registry_data(
    tmp_path: Path,
    case: str,
    mutator: Callable[[Path], None],
    expected_error: str,
) -> None:
    candidate = copy_registry_tree(tmp_path)
    mutator(candidate)
    result = validate_registries(candidate)
    assert result["status"] == "fail", case
    assert any(expected_error.lower() in error.lower() for error in result["errors"]), (
        case,
        result["errors"],
    )


@pytest.mark.parametrize(
    ("name", "key", "value"),
    (
        ("parameter_registry.yaml", "parameters", 7),
        ("experiment_matrix.yaml", "methods", 7),
        ("raw_episode_schema.yaml", "fields", {"name": "bad"}),
        ("artifact_manifest_schema.yaml", "record_schema", []),
        ("output_root_contract.yaml", "source_inputs", "read-write"),
    ),
)
def test_validator_returns_failure_instead_of_raising_for_malformed_types(
    tmp_path: Path, name: str, key: str, value: object
) -> None:
    candidate = copy_registry_tree(tmp_path)
    data = load(name, candidate)
    data[key] = value
    write(name, candidate, data)
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert result["errors"]


def test_validator_rejects_cross_file_sealed_range_mismatch(tmp_path: Path) -> None:
    candidate = copy_registry_tree(tmp_path)
    data = load("sealed_test_lock.yaml", candidate)
    data["scenario_range"]["start"] = 30001
    write("sealed_test_lock.yaml", candidate, data)
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert any("sealed" in error.lower() and "range" in error.lower() for error in result["errors"])


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    (
        ("battery_activation", True, "battery activation"),
        ("battery_replenishment_enabled", True, "battery activation"),
        ("battery_replenishment", "active", "battery replenishment"),
        ("resource_replenishment", "battery_and_pesticide", "resource replenishment"),
    ),
)
def test_validator_rejects_resource_activation_keys_in_any_registry_record(
    tmp_path: Path,
    field: str,
    value: object,
    expected_error: str,
) -> None:
    candidate = copy_registry_tree(tmp_path)
    data = load("parameter_registry.yaml", candidate)
    data["parameters"][0][field] = value
    write("parameter_registry.yaml", candidate, data)

    result = validate_registries(candidate)

    assert result["status"] == "fail"
    assert any(expected_error in error.lower() for error in result["errors"])


def test_validator_allows_legitimate_battery_retention_wording(tmp_path: Path) -> None:
    candidate = copy_registry_tree(tmp_path)
    data = load("parameter_registry.yaml", candidate)
    data["parameters"][0]["meaning"] = (
        "Battery state is retained for observation only; pesticide is the only "
        "replenished resource."
    )
    write("parameter_registry.yaml", candidate, data)

    result = validate_registries(candidate)

    assert result["status"] == "pass"
    assert result["errors"] == []


def test_validator_report_binds_inputs_validator_time_and_commit() -> None:
    result = validate_registries(REGISTRY_ROOT)
    assert result["status"] == "pass"
    assert result["errors"] == []
    provenance = result["provenance"]
    assert set(provenance["registry_sha256"]) == set(REGISTRY_NAMES)
    for name, digest in provenance["registry_sha256"].items():
        assert digest == hashlib.sha256((REGISTRY_ROOT / name).read_bytes()).hexdigest()
    assert provenance["validator"]["version"]
    assert re.fullmatch(r"[0-9a-f]{64}", provenance["validator"]["sha256"])
    assert provenance["generated_at_utc"].endswith("+00:00")
    expected_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout.strip()
    assert provenance["repository_commit"] == expected_commit
