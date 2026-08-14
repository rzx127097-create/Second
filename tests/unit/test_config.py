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


def test_vehicle_action_names_match_configured_candidate_slots(tmp_path) -> None:
    import shutil

    config_dir = tmp_path / "configs"
    shutil.copytree(ROOT / "configs", config_dir)
    environment_file = config_dir / "environment.yaml"
    environment_file.write_text(
        environment_file.read_text(encoding="utf-8").replace(
            "vehicle_action_names: [hold, slot-0, slot-1, slot-2, slot-3]",
            "vehicle_action_names: [hold, slot-0]",
        ),
        encoding="utf-8",
    )
    try:
        load_config_bundle(config_dir)
    except ValueError as exc:
        assert "vehicle_action_names" in str(exc)
    else:
        raise AssertionError("mismatched vehicle action names must be rejected")
