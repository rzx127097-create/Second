from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import copy

import numpy as np
import pytest

from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import (
    DynamicPestScenario,
    WindState,
    generate_dynamic_scenario,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def test_dynamic_scenario_replays_byte_identically_for_every_paired_method() -> None:
    scenarios = [
        generate_dynamic_scenario(
            "validation", 20000, "g20x20_d2", (20, 20), CONFIG
        )
        for _ in range(5)
    ]

    assert len({scenario.scenario_sha256 for scenario in scenarios}) == 1
    assert all(
        scenario.initial_prey.tobytes() == scenarios[0].initial_prey.tobytes()
        for scenario in scenarios
    )
    assert all(
        scenario.initial_predator.tobytes() == scenarios[0].initial_predator.tobytes()
        for scenario in scenarios
    )
    assert all(
        scenario.initial_wind == scenarios[0].initial_wind
        for scenario in scenarios
    )


def test_scenario_hash_changes_for_material_ecology_change() -> None:
    baseline = generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), CONFIG
    )
    changed = generate_dynamic_scenario(
        "development",
        10000,
        "g20x20_d2",
        (20, 20),
        replace(CONFIG, beta=1.4),
    )

    assert baseline.scenario_sha256 != changed.scenario_sha256


def test_generation_does_not_touch_legacy_global_numpy_rng() -> None:
    np.random.seed(7123)
    before = copy.deepcopy(np.random.get_state())

    generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), CONFIG
    )

    after = np.random.get_state()
    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert before[2:] == after[2:]


@pytest.mark.parametrize(
    ("partition", "scenario_id"),
    [
        ("development", 9999),
        ("development", 10020),
        ("validation", 19999),
        ("validation", 20050),
        ("sealed_test", 29999),
        ("sealed_test", 30100),
    ],
)
def test_generation_rejects_ids_outside_their_strict_partition(
    partition: str, scenario_id: int
) -> None:
    with pytest.raises(ValueError, match="partition"):
        generate_dynamic_scenario(
            partition, scenario_id, "g20x20_d2", (20, 20), CONFIG
        )


def test_generation_rejects_unknown_partition_and_noncanonical_inputs() -> None:
    with pytest.raises(ValueError, match="partition"):
        generate_dynamic_scenario(
            "sealed", 30000, "g20x20_d2", (20, 20), CONFIG
        )
    with pytest.raises(ValueError, match="grid_shape"):
        generate_dynamic_scenario(
            "development", 10000, "g20x20_d2", (1, 20), CONFIG
        )


def test_scenario_state_round_trip_is_deep_copied_and_exact() -> None:
    scenario = generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), CONFIG
    )
    snapshot = scenario.state_dict()
    restored = DynamicPestScenario.from_state_dict(snapshot)

    assert restored.scenario_sha256 == scenario.scenario_sha256
    assert restored.initial_wind == scenario.initial_wind
    assert restored.rng_state == scenario.rng_state
    restored_snapshot = restored.state_dict()
    assert {
        key: value
        for key, value in restored_snapshot.items()
        if key not in {"initial_prey", "initial_predator", "initial_effect"}
    } == {
        key: value
        for key, value in snapshot.items()
        if key not in {"initial_prey", "initial_predator", "initial_effect"}
    }
    assert np.array_equal(restored_snapshot["initial_prey"], snapshot["initial_prey"])
    assert np.array_equal(
        restored_snapshot["initial_predator"], snapshot["initial_predator"]
    )
    for key in ("concentration", "duration", "spray_count"):
        assert np.array_equal(
            restored_snapshot["initial_effect"][key], snapshot["initial_effect"][key]
        )

    snapshot["initial_prey"][0, 0] += 1.0
    snapshot["initial_effect"]["concentration"][0, 0] = 1.0
    snapshot["rng_state"]["state"]["state"] += 1

    assert restored.initial_prey[0, 0] != snapshot["initial_prey"][0, 0]
    assert restored.initial_concentration[0, 0] == 0.0
    assert restored.rng_state != snapshot["rng_state"]


def test_scenario_state_restore_rejects_stale_hash_and_wrong_dtype() -> None:
    scenario = generate_dynamic_scenario(
        "validation", 20000, "g20x20_d2", (20, 20), CONFIG
    )
    snapshot = scenario.state_dict()

    snapshot["initial_prey"][0, 0] += 0.01
    with pytest.raises(ValueError, match="scenario_sha256"):
        DynamicPestScenario.from_state_dict(snapshot)

    snapshot = scenario.state_dict()
    snapshot["initial_prey"] = snapshot["initial_prey"].astype(np.float32)
    with pytest.raises(ValueError, match="initial_prey"):
        DynamicPestScenario.from_state_dict(snapshot)


def test_generated_fields_use_problem1_lineage_source_shape_and_bounds() -> None:
    scenario = generate_dynamic_scenario(
        "sealed_test", 30000, "g30x40_d4", (30, 40), CONFIG
    )

    assert scenario.initial_prey.shape == (30, 40)
    assert scenario.initial_predator.shape == (30, 40)
    assert scenario.initial_prey.dtype == np.dtype("<f8")
    assert scenario.initial_predator.dtype == np.dtype("<f8")
    assert np.all((scenario.initial_prey >= 0.0) & (scenario.initial_prey <= 0.5))
    assert np.all(scenario.initial_predator >= 0.0)
    assert scenario.initial_concentration.dtype == np.dtype("<f4")
    assert scenario.initial_duration.dtype == np.dtype("<f4")
    assert scenario.initial_spray_count.dtype == np.dtype("<i4")
    assert scenario.initial_wind.step_count == 0
    assert scenario.source_commit == "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"
    assert scenario.implementation_version == "problem2-dynamic-pest-v1"
