from pathlib import Path

from problem2.config import config_identity, load_config_bundle


ROOT = Path(__file__).resolve().parents[2]


def test_config_bundle_loads_and_has_stable_identity() -> None:
    bundle = load_config_bundle(ROOT / "configs")
    assert bundle.environment["primary_vehicle_count"] == 1
    assert bundle.algorithm["name"] == "SR-MAPPO"
    assert bundle.parameters["status"] == "provisional"
    first = config_identity(bundle)
    second = config_identity(load_config_bundle(ROOT / "configs"))
    assert first == second
    assert len(first) == 64


def test_formal_matrix_separates_training_validation_and_sealed_test() -> None:
    bundle = load_config_bundle(ROOT / "configs")
    matrix = bundle.experiments
    assert set(matrix["splits"]) == {"train", "validation", "sealed_test"}
    assert not (set(matrix["train_scenarios"]) & set(matrix["sealed_test_scenarios"]))
