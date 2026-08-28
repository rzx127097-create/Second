from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.pesticide import AcceptedSpray, PesticideEffectField


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def test_one_full_accepted_spray_deposits_the_approved_radial_profile() -> None:
    field = PesticideEffectField.empty((11, 11), CONFIG)

    field.deposit(AcceptedSpray(5, 5, 0.25), reference_volume_l=0.25)

    assert field.concentration[5, 5] == pytest.approx(0.85)
    assert field.concentration[5, 9] == pytest.approx(0.17)
    assert field.concentration[5, 10] == 0.0
    assert field.duration[5, 5] == 15
    assert field.spray_count[5, 5] == 1
    assert int(np.count_nonzero(field.spray_count)) == 1


def test_partial_spray_receives_only_proportional_effect() -> None:
    field = PesticideEffectField.empty((3, 3), CONFIG)

    field.deposit(AcceptedSpray(1, 1, 0.125), reference_volume_l=0.25)

    assert field.concentration[1, 1] == pytest.approx(0.425)


def test_overlapping_deposits_cap_concentration_and_extend_duration() -> None:
    field = PesticideEffectField.empty((11, 11), CONFIG)
    field.deposit(AcceptedSpray(5, 5, 0.25), reference_volume_l=0.25)
    field.decay()
    field.deposit(AcceptedSpray(5, 5, 0.25), reference_volume_l=0.25)

    assert field.concentration[5, 5] == 1.0
    assert field.duration[5, 5] == 15
    assert field.spray_count[5, 5] == 2


def test_mortality_uses_capped_prey_and_predator_kill_rates() -> None:
    field = PesticideEffectField.empty((1, 3), CONFIG)
    field.concentration[0] = np.array([0.2, 0.8, 4.0], dtype=np.float32)
    prey = np.ones((1, 3), dtype=np.float64)
    predator = np.ones((1, 3), dtype=np.float64)

    prey_after, predator_after = field.apply_mortality(prey, predator)

    assert np.allclose(prey_after, [[0.6, 0.02, 0.02]])
    assert np.allclose(predator_after, [[0.98, 0.92, 0.7]])
    assert np.array_equal(prey, np.ones((1, 3)))
    assert np.array_equal(predator, np.ones((1, 3)))


def test_decay_decrements_duration_before_expiration_and_clears_tiny_effects() -> None:
    field = PesticideEffectField.empty((1, 2), CONFIG)
    field.concentration[0] = np.array([0.5, 5.0e-7], dtype=np.float32)
    field.duration[0] = np.array([2.0, 4.0], dtype=np.float32)

    field.decay()
    assert field.duration.tolist() == [[1.0, 3.0]]
    assert field.concentration[0, 0] == pytest.approx(0.46)
    assert field.concentration[0, 1] == 0.0

    field.decay()
    assert field.duration[0, 0] == 0.0
    assert field.concentration[0, 0] == 0.0


@pytest.mark.parametrize(
    ("spray", "reference"),
    [
        (AcceptedSpray(0, 0, 0.0), 0.25),
        (AcceptedSpray(0, 0, -0.1), 0.25),
        (AcceptedSpray(0, 0, float("nan")), 0.25),
        (AcceptedSpray(0, 0, float("inf")), 0.25),
        (AcceptedSpray(0, 0, 0.25), 0.0),
        (AcceptedSpray(0, 0, 0.25), float("nan")),
    ],
)
def test_deposit_rejects_invalid_spray_or_reference_volume(
    spray: AcceptedSpray, reference: float
) -> None:
    field = PesticideEffectField.empty((3, 3), CONFIG)

    with pytest.raises(ValueError):
        field.deposit(spray, reference_volume_l=reference)

    assert np.count_nonzero(field.concentration) == 0
    assert np.count_nonzero(field.duration) == 0
    assert np.count_nonzero(field.spray_count) == 0


@pytest.mark.parametrize("row,col", [(-1, 0), (0, -1), (3, 0), (0, 3)])
def test_deposit_rejects_out_of_bounds_centers(row: int, col: int) -> None:
    field = PesticideEffectField.empty((3, 3), CONFIG)

    with pytest.raises(ValueError):
        field.deposit(AcceptedSpray(row, col, 0.25), reference_volume_l=0.25)


def test_state_round_trip_restores_arrays_and_keeps_physical_litres_out() -> None:
    field = PesticideEffectField.empty((5, 6), CONFIG)
    field.deposit(AcceptedSpray(2, 3, 0.125), reference_volume_l=0.25)
    field.decay()
    snapshot = field.state_dict()
    restored = PesticideEffectField.from_state_dict(snapshot, CONFIG)

    assert snapshot.keys() == {"shape", "concentration", "duration", "spray_count"}
    assert restored.concentration.dtype == np.float32
    assert restored.duration.dtype == np.float32
    assert restored.spray_count.dtype == np.int32
    assert np.array_equal(restored.concentration, field.concentration)
    assert np.array_equal(restored.duration, field.duration)
    assert np.array_equal(restored.spray_count, field.spray_count)
    assert "litre" not in repr(snapshot).lower()

    snapshot["concentration"][2, 3] = 0.0
    assert restored.concentration[2, 3] != 0.0


@pytest.mark.parametrize(
    ("array_name", "value"),
    [
        ("concentration", -0.01),
        ("concentration", CONFIG.concentration_cap + 0.01),
        ("duration", -1.0),
        ("duration", float(CONFIG.effect_duration + 1)),
        ("duration", 1.5),
        ("spray_count", -1),
    ],
)
def test_state_restore_rejects_values_outside_ecological_domains(
    array_name: str, value: float
) -> None:
    field = PesticideEffectField.empty((3, 3), CONFIG)
    snapshot = field.state_dict()
    snapshot[array_name][1, 1] = value

    with pytest.raises(ValueError, match=array_name):
        PesticideEffectField.from_state_dict(snapshot, CONFIG)


@pytest.mark.parametrize("population_name", ["prey", "predator"])
def test_mortality_rejects_negative_population(
    population_name: str,
) -> None:
    field = PesticideEffectField.empty((2, 2), CONFIG)
    prey = np.ones((2, 2), dtype=np.float64)
    predator = np.ones((2, 2), dtype=np.float64)
    population = prey if population_name == "prey" else predator
    population[0, 0] = -0.1

    with pytest.raises(ValueError, match=population_name):
        field.apply_mortality(prey, predator)
