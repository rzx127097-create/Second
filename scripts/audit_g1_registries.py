"""Fail-closed validation for the frozen G1 evidence registries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

import yaml


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
FORBIDDEN_TEXT = re.compile(
    r"(?:\bhappo\b|\bhapppo\b|ag[-_ ]?sr[-_ ]?mappo|\bM3\b|\bM4\b)",
    re.IGNORECASE,
)
PREMATURE_WORDING = re.compile(
    r"(?:proves?|significantly\s+outperforms?|formal\s+experiments?\s+show|"
    r"real\s+deployment\s+verified|universally\s+optimal)",
    re.IGNORECASE,
)


def load_yaml(path: Path) -> object:
    """Load YAML using the safe loader, allowing the caller to fail closed."""
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


def _mapping(value: object, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must have a mapping root")
        return None
    return value


def _required(data: dict[str, Any], fields: Sequence[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in data:
            errors.append(f"{label} missing required field: {field}")


def _check_common(name: str, data: dict[str, Any], errors: list[str]) -> None:
    _required(data, ("schema_version", "registry_id", "status"), name, errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{name} has wrong schema version")
    expected_status = "locked" if name == "sealed_test_lock.yaml" else FROZEN_STATUS
    if data.get("status") != expected_status:
        errors.append(f"{name} must have status {expected_status}")


def _iter_text(value: object) -> list[str]:
    if isinstance(value, dict):
        return [part for pair in value.items() for part in _iter_text(pair)]
    if isinstance(value, (list, tuple)):
        return [part for item in value for part in _iter_text(item)]
    return [str(value)] if isinstance(value, str) else []


def _check_text(name: str, data: dict[str, Any], errors: list[str]) -> None:
    text = "\n".join(_iter_text(data))
    if FORBIDDEN_TEXT.search(text):
        errors.append(f"{name} contains forbidden algorithm or maturity wording")
    if PREMATURE_WORDING.search(text):
        errors.append(f"{name} contains premature formal-result wording")


def _check_records(data: dict[str, Any], key: str, fields: Sequence[str], errors: list[str]) -> None:
    records = data.get(key)
    if not isinstance(records, list):
        errors.append(f"{key} must be a list")
        return
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"{key}[{index}] must be a mapping")
            continue
        _required(record, fields, f"{key}[{index}]", errors)


def _check_parameters(data: dict[str, Any], errors: list[str]) -> None:
    _check_records(
        data,
        "parameters",
        ("id", "name", "symbol", "meaning", "value", "unit", "min", "max", "source_type", "source_id", "source_value", "source_unit", "conversion", "status", "scope"),
        errors,
    )


def _check_sources(data: dict[str, Any], errors: list[str]) -> None:
    _check_records(data, "sources", ("id", "source_type", "title", "authority", "verification_status"), errors)
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return
    for source in sources:
        if isinstance(source, dict) and source.get("verification_status") == "pending":
            _required(source, ("database", "authoritative_page"), "pending source", errors)


def _check_matrix(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("methods") != PRIMARY_METHODS:
        errors.append("experiment_matrix.yaml must use the exact primary method family")
    scales = data.get("scales")
    if not isinstance(scales, dict) or set(scales) != set(SCALE_HORIZONS):
        errors.append("experiment_matrix.yaml must define the exact six scales")
    else:
        for scale, horizon in SCALE_HORIZONS.items():
            record = scales[scale]
            if not isinstance(record, dict) or record.get("max_physical_decision_steps") != horizon:
                errors.append(f"{scale} has the wrong maximum horizon")
    _required(data, ("methods", "scales", "evaluation", "protocol"), "experiment_matrix.yaml", errors)


def _check_seeds(data: dict[str, Any], errors: list[str]) -> None:
    partitions = data.get("partitions")
    if not isinstance(partitions, dict):
        errors.append("scenario_seed_manifest.yaml missing partitions")
        return
    training = partitions.get("training", {})
    validation = partitions.get("validation", {})
    sealed = partitions.get("sealed_test", {})
    for label, record in (("training", training), ("validation", validation), ("sealed_test", sealed)):
        if not isinstance(record, dict):
            errors.append(f"{label} partition must be a mapping")
    if not isinstance(training, dict):
        training = {}
    if not isinstance(validation, dict):
        validation = {}
    if not isinstance(sealed, dict):
        sealed = {}
    if training.get("seeds") != TRAINING_SEEDS:
        errors.append("training seeds do not match the exact protocol")
    ranges = [("validation", validation, 20000, 20049), ("sealed_test", sealed, 30000, 30099)]
    sets: list[set[int]] = []
    for label, record, start, end in ranges:
        if not isinstance(record, dict):
            record = {}
        actual_start = record.get("start")
        actual_end = record.get("end")
        if actual_start != start or actual_end != end:
            errors.append(f"{label} seed range is not exact")
        if isinstance(actual_start, int) and isinstance(actual_end, int) and actual_start <= actual_end:
            sets.append(set(range(actual_start, actual_end + 1)))
        else:
            sets.append(set())
    training_seeds = training.get("seeds") if isinstance(training, dict) else []
    sets.insert(0, set(training_seeds) if isinstance(training_seeds, list) else set())
    if any(left & right for index, left in enumerate(sets) for right in sets[index + 1:]):
        errors.append("seed partitions overlap")


def _check_identity(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("identity_fields") != ["method", "scale", "training_seed", "config_hash", "git_commit"]:
        errors.append("job identity fields are not exact")
    serialization = data.get("serialization", {})
    if not isinstance(serialization, dict):
        errors.append("job identity serialization must be a mapping")
        serialization = {}
    if serialization.get("separator") != "|" or serialization.get("format") != "method|scale|training_seed|config_hash|git_commit":
        errors.append("job identity serialization is not exact")
    _required(data, ("identity_fields", "serialization", "states", "required_recovery_fields", "sealed_test_creation_gate"), "job_identity_contract.yaml", errors)


def _check_fields_schema(data: dict[str, Any], key: str, errors: list[str]) -> None:
    fields = data.get(key)
    if not isinstance(fields, list) or not fields:
        errors.append(f"{key} must be a non-empty list")
        return
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            errors.append(f"{key}[{index}] must be a mapping")
        else:
            _required(field, ("name", "type", "required"), f"{key}[{index}]", errors)


def _check_sealed(data: dict[str, Any], errors: list[str]) -> None:
    _required(data, ("scenario_range", "unlock_gate", "unlock_count", "tuning_allowed_before_unlock", "resource_replenishment", "battery_replenishment"), "sealed_test_lock.yaml", errors)
    scenario = data.get("scenario_range", {})
    if not isinstance(scenario, dict):
        errors.append("sealed-test scenario_range must be a mapping")
        scenario = {}
    if scenario.get("start") != 30000 or scenario.get("end") != 30099:
        errors.append("sealed-test scenario range is not exact")
    if data.get("unlock_gate") != "G7" or data.get("unlock_count") != 1:
        errors.append("sealed-test unlock policy must be one-time at G7")
    if data.get("tuning_allowed_before_unlock") is not False:
        errors.append("sealed-test tuning is forbidden before unlock")
    if data.get("resource_replenishment") != "pesticide_only":
        errors.append("resource replenishment must be pesticide-only")
    if data.get("battery_replenishment") != "inactive":
        errors.append("battery replenishment must remain inactive")


def _check_resource_scope(data: dict[str, Any], name: str, errors: list[str]) -> None:
    def visit(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "resource_replenishment" and child != "pesticide_only":
                    errors.append(f"{name} resource replenishment must be pesticide-only")
                if key == "battery_replenishment" and child != "inactive":
                    errors.append(f"{name} battery replenishment must remain inactive")
                if key in {"battery_activation", "battery_replenishment_enabled"} and child is not False:
                    errors.append(f"{name} battery activation is forbidden")
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(data, name)


def validate_registries(registry_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked_files: list[str] = []
    registries: dict[str, dict[str, Any]] = {}
    for name in REGISTRY_NAMES:
        path = registry_root / name
        if not path.is_file():
            errors.append(f"missing registry file: {name}")
            continue
        checked_files.append(name)
        try:
            value = load_yaml(path)
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"could not load {name}: {exc}")
            continue
        data = _mapping(value, name, errors)
        if data is None:
            continue
        registries[name] = data
        _check_common(name, data, errors)
        _check_text(name, data, errors)
        _check_resource_scope(data, name, errors)

    for name, key, fields in (
        ("parameter_registry.yaml", "parameters", ("id",)),
        ("literature_source_ledger.yaml", "sources", ("id",)),
    ):
        records = registries.get(name, {}).get(key, [])
        ids = [record.get("id") for record in records if isinstance(record, dict)]
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate {key[:-1]} IDs")
        if name in registries:
            _check_parameters(registries[name], errors) if key == "parameters" else _check_sources(registries[name], errors)

    if "experiment_matrix.yaml" in registries:
        matrix = registries["experiment_matrix.yaml"]
        _check_matrix(matrix, errors)
        methods = matrix.get("methods", [])
        if len(methods) != len(set(methods)):
            errors.append("duplicate method IDs")
    if "scenario_seed_manifest.yaml" in registries:
        _check_seeds(registries["scenario_seed_manifest.yaml"], errors)
    if "job_identity_contract.yaml" in registries:
        _check_identity(registries["job_identity_contract.yaml"], errors)
    for name, key in (("raw_episode_schema.yaml", "fields"), ("validated_long_table_schema.yaml", "fields")):
        if name in registries:
            _check_fields_schema(registries[name], key, errors)
    if "artifact_manifest_schema.yaml" in registries:
        artifact = registries["artifact_manifest_schema.yaml"]
        _required(artifact, ("required_fields", "record_schema"), "artifact_manifest_schema.yaml", errors)
    if "sealed_test_lock.yaml" in registries:
        _check_sealed(registries["sealed_test_lock.yaml"], errors)
    if "output_root_contract.yaml" in registries:
        output = registries["output_root_contract.yaml"]
        if output.get("root") != "outputs/problem2_sr_mappo_v1":
            errors.append("output root must be outputs/problem2_sr_mappo_v1")
        if output.get("allowed_descendants_only") is not True:
            errors.append("output root must allow descendants only")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "checked_files": checked_files,
        "counts": {"expected_files": len(REGISTRY_NAMES), "checked_files": len(checked_files), "errors": len(errors)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_registries(args.root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
