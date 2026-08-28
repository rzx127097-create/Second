from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import DynamicWind, WindState


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def test_wind_state_is_immutable_and_exposes_cartesian_vector() -> None:
    state = WindState(direction=np.pi / 2.0, strength=0.5, step_count=3)

    assert state.vector == pytest.approx((0.0, 0.5))
    with pytest.raises(AttributeError):
        state.direction = 0.0  # type: ignore[misc]


def test_dynamic_wind_same_seed_replays_and_different_seed_diverges() -> None:
    left = DynamicWind.initialize(np.random.default_rng(20000), CONFIG)
    right = DynamicWind.initialize(np.random.default_rng(20000), CONFIG)
    other = DynamicWind.initialize(np.random.default_rng(20001), CONFIG)

    assert [left.update() for _ in range(8)] == [right.update() for _ in range(8)]
    assert left.state != other.state
    assert 0.0 <= left.state.strength <= 0.5


def test_wind_initialization_and_update_match_independent_generator_reference() -> None:
    seed = 77
    reference_rng = np.random.default_rng(seed)
    expected_direction = float(reference_rng.uniform(0.0, 2.0 * np.pi))
    expected_strength = float(reference_rng.uniform(0.0, 0.5))
    wind = DynamicWind.initialize(np.random.default_rng(seed), CONFIG)

    assert wind.state == WindState(expected_direction, expected_strength, 0)

    for step in range(1, 4):
        expected_direction = (
            expected_direction
            + float(reference_rng.normal(0.0, 0.1))
            + 0.005 * np.sin(step / 50.0)
        ) % (2.0 * np.pi)
        expected_strength = float(
            np.clip(expected_strength + reference_rng.normal(0.0, 0.05), 0.0, 0.5)
        )
        assert wind.update() == WindState(expected_direction, expected_strength, step)


def test_state_round_trip_restores_wind_and_bit_generator_state_exactly() -> None:
    wind = DynamicWind.initialize(np.random.default_rng(1234), CONFIG)
    for _ in range(5):
        wind.update()
    snapshot = wind.state_dict()
    restored = DynamicWind.from_state_dict(snapshot, CONFIG)

    assert snapshot["bit_generator"] == "PCG64"
    assert restored.state == wind.state
    assert restored.state_dict() == snapshot
    assert [wind.update() for _ in range(10)] == [restored.update() for _ in range(10)]


def test_dynamic_wind_owns_a_deep_copied_generator_state() -> None:
    source = np.random.default_rng(8)
    wind = DynamicWind.initialize(source, CONFIG)
    snapshot = wind.state_dict()
    snapshot["rng_state"]["state"]["state"] += 1

    assert wind.state_dict()["rng_state"] != snapshot["rng_state"]
