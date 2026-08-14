from __future__ import annotations

from pathlib import Path

import pytest

from problem2.config import load_config_bundle
from problem2.experiments.specification import load_experiment_spec


ROOT = Path(__file__).resolve().parents[2]


def _verified_protocol_copy(tmp_path: Path) -> Path:
    path = tmp_path / "chapter4_5.yaml"
    text = (ROOT / "configs" / "experiments" / "chapter4_5.yaml").read_text(encoding="utf-8")
    path.write_text(text.replace("status: provisional", "status: verified", 1), encoding="utf-8")
    return path


def test_chapter45_protocol_expands_every_registered_experiment_family() -> None:
    """Removing a Chapter 4.5 family or a canonical method breaks executable coverage."""
    config = load_config_bundle(ROOT / "configs")
    spec = load_experiment_spec(
        ROOT / "configs" / "experiments" / "chapter4_5.yaml",
        config,
    )

    assert spec.status == "provisional"
    assert spec.main_methods == (
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    )
    assert set(spec.families) == {
        "mechanism",
        "main_comparison",
        "sensitivity",
        "adaptation",
        "ablation",
    }
    assert {condition.condition_id for condition in spec.expand("mechanism")} == {
        "unlimited_supply",
        "finite_no_support",
        "matched_fixed",
        "teleport_diagnostic",
        "rolling_astar_mobile",
        "sr_mappo_mobile",
    }
    assert {condition.factor for condition in spec.expand("sensitivity")} == {
        "uav_initial_pesticide_ratio",
        "vehicle_speed",
        "service_setup_time",
        "rendezvous_radius",
    }
    assert len(spec.expand("main_comparison")) == 5 * 6 * 5
    assert spec.statistics["bootstrap_draws"] >= 2000
    assert spec.statistics["pairing_unit"] == "training_seed_then_shared_scenario"


def test_protocol_rejects_duplicate_condition_ids(tmp_path: Path) -> None:
    """Duplicate IDs would overwrite evidence and therefore must fail closed."""
    source = (ROOT / "configs" / "experiments" / "chapter4_5.yaml").read_text(encoding="utf-8")
    duplicate = source.replace(
        "  adaptation:\n",
        "  adaptation:\n    - id: finite_no_support\n      kind: road_blockage\n      levels: [0.1]\n",
        1,
    )
    path = tmp_path / "duplicate.yaml"
    path.write_text(duplicate, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate experiment condition id"):
        load_experiment_spec(path, load_config_bundle(ROOT / "configs"))


def test_protocol_rejects_diagnostic_as_main_method(tmp_path: Path) -> None:
    """Diagnostic upper bounds cannot enter the ordinary algorithm ranking."""
    source = (ROOT / "configs" / "experiments" / "chapter4_5.yaml").read_text(encoding="utf-8")
    invalid = source.replace(
        "    - sr_mappo_two_stage\n",
        "    - sr_mappo_two_stage\n    - teleport_diagnostic\n",
        1,
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="main methods"):
        load_experiment_spec(path, load_config_bundle(ROOT / "configs"))


def test_verified_protocol_requires_finite_justified_equivalence_margin(tmp_path: Path) -> None:
    config = load_config_bundle(ROOT / "configs")
    protocol = _verified_protocol_copy(tmp_path)

    with pytest.raises(ValueError, match="practical_equivalence_margin"):
        load_experiment_spec(protocol, config)

    text = protocol.read_text(encoding="utf-8").replace(
        "practical_equivalence_margin: null",
        "practical_equivalence_margin: 0.02",
    )
    protocol.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="practical_equivalence_basis"):
        load_experiment_spec(protocol, config)
