from pathlib import Path

from problem2.config import config_identity, load_config_bundle


ROOT = Path(__file__).resolve().parents[2]


def test_config_bundle_loads_and_has_stable_identity() -> None:
    bundle = load_config_bundle(ROOT / "configs")
    assert bundle.environment["primary_vehicle_count"] == 1
    assert bundle.algorithm["name"] == "SR-MAPPO"
    assert bundle.algorithm["ppo_epochs"] >= 1
    assert bundle.algorithm["max_grad_norm"] > 0
    assert bundle.parameters["status"] == "provisional"
    first = config_identity(bundle)
    second = config_identity(load_config_bundle(ROOT / "configs"))
    assert first == second
    assert len(first) == 64
    assert bundle.scenario_status == "provisional"


def test_scenario_registry_status_is_part_of_config_identity(tmp_path) -> None:
    import shutil

    config_dir = tmp_path / "configs"
    shutil.copytree(ROOT / "configs", config_dir)
    original = load_config_bundle(config_dir)
    scenario_file = config_dir / "scenarios.yaml"
    scenario_file.write_text(
        scenario_file.read_text(encoding="utf-8").replace("status: provisional", "status: verified", 1),
        encoding="utf-8",
    )
    changed = load_config_bundle(config_dir)
    assert original.scenario_status == "provisional"
    assert changed.scenario_status == "verified"
    assert config_identity(original) != config_identity(changed)


def test_formal_matrix_separates_training_validation_and_sealed_test() -> None:
    bundle = load_config_bundle(ROOT / "configs")
    matrix = bundle.experiments
    assert set(matrix["splits"]) == {"train", "validation", "sealed_test"}
    assert not (set(matrix["train_scenarios"]) & set(matrix["sealed_test_scenarios"]))
