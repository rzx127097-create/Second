from pathlib import Path
import shutil

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


def load(name: str) -> dict:
    with (REGISTRY_ROOT / name).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    assert isinstance(value, dict)
    return value


def test_all_g1_registries_exist_and_are_frozen() -> None:
    for name in REGISTRY_NAMES:
        registry = load(name)
        assert registry["schema_version"] == "g1.v1"
        assert registry["registry_id"].startswith("G1-")
        if name != "sealed_test_lock.yaml":
            assert registry["status"] == "design_frozen"


def test_primary_method_family_and_scale_protocol_are_complete() -> None:
    matrix = load("experiment_matrix.yaml")
    assert matrix["methods"] == [
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    ]
    assert matrix["scales"]["g30x50_d4"]["max_physical_decision_steps"] == 350


def test_seed_partitions_do_not_overlap() -> None:
    manifest = load("scenario_seed_manifest.yaml")
    partitions = manifest["partitions"]
    training = set(partitions["training"]["seeds"])
    validation = set(range(partitions["validation"]["start"], partitions["validation"]["end"] + 1))
    sealed = set(range(partitions["sealed_test"]["start"], partitions["sealed_test"]["end"] + 1))
    assert not training & validation
    assert not training & sealed
    assert not validation & sealed


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
    assert lock["unlock_count"] == 1
    assert lock["tuning_allowed_before_unlock"] is False


def copy_registry_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "g1"
    shutil.copytree(REGISTRY_ROOT, destination)
    return destination


def test_job_identity_is_canonical_and_ordered() -> None:
    assert build_job_identity(
        "sr_mappo_mobile", "g20x20_d2", 42, "abc123", "deadbeef"
    ) == "sr_mappo_mobile|g20x20_d2|42|abc123|deadbeef"


def test_validator_accepts_frozen_g1_registries() -> None:
    result = validate_registries(REGISTRY_ROOT)
    assert result["status"] == "pass"
    assert result["errors"] == []


def test_validator_rejects_forbidden_algorithm_name(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "experiment_matrix.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["methods"].append("happpo")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert any("forbidden algorithm" in error for error in result["errors"])


def test_validator_rejects_sealed_test_tuning(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "sealed_test_lock.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["tuning_allowed_before_unlock"] = True
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert any("sealed-test tuning" in error for error in result["errors"])


def test_validator_rejects_battery_activation_and_wrong_output_root(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    lock_path = candidate / "sealed_test_lock.yaml"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    lock["battery_replenishment"] = "active"
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    output_path = candidate / "output_root_contract.yaml"
    output = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    output["root"] = "outputs/sr_mappo_paper_v1"
    output_path.write_text(yaml.safe_dump(output, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert any("battery replenishment" in error for error in result["errors"])
    assert any("output root" in error for error in result["errors"])


def test_validator_fails_closed_for_malformed_scale_record(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "experiment_matrix.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["scales"]["g20x20_d2"] = "malformed"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert result["errors"]


def test_validator_fails_closed_for_malformed_validation_seed_bounds(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "scenario_seed_manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["partitions"]["validation"] = "malformed"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert any("validation partition must be a mapping" in error for error in result["errors"])


def test_validator_fails_closed_for_malformed_job_serialization(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "job_identity_contract.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["serialization"] = "malformed"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert any("serialization must be a mapping" in error for error in result["errors"])


def test_validator_fails_closed_for_malformed_sealed_scenario_range(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "sealed_test_lock.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["scenario_range"] = "malformed"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert result["status"] == "fail"
    assert any("scenario_range must be a mapping" in error for error in result["errors"])
