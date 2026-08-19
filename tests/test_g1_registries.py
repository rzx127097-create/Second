from pathlib import Path

import yaml


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


def test_sealed_test_is_locked_once_at_g7() -> None:
    lock = load("sealed_test_lock.yaml")
    assert lock["status"] == "locked"
    assert lock["unlock_gate"] == "G7"
    assert lock["unlock_count"] == 1
    assert lock["tuning_allowed_before_unlock"] is False
