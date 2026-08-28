from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from problem2.ecology import dynamics
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.pesticide import AcceptedSpray, PesticideEffectField
from problem2.ecology.scenario import DynamicWind, WindState, generate_dynamic_scenario
from problem2.ecology.system import DynamicEcologySystem, EcologyTransition


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def _scenario() -> object:
    return generate_dynamic_scenario(
        "development", 10000, "g20x20_d2", (20, 20), CONFIG
    )


def _sprays(step: int) -> tuple[AcceptedSpray, ...]:
    return (
        AcceptedSpray((step * 3) % 20, (step * 5 + 1) % 20, 0.125),
    ) if step % 2 == 0 else ()


def _assert_state_equal(left: object, right: object) -> None:
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        assert isinstance(left, np.ndarray) and isinstance(right, np.ndarray)
        assert left.dtype == right.dtype
        assert np.array_equal(left, right)
        return
    if isinstance(left, dict) or isinstance(right, dict):
        assert isinstance(left, dict) and isinstance(right, dict)
        assert left.keys() == right.keys()
        for key in left:
            _assert_state_equal(left[key], right[key])
        return
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        assert type(left) is type(right)
        assert len(left) == len(right)  # type: ignore[arg-type]
        for left_item, right_item in zip(left, right):  # type: ignore[arg-type]
            _assert_state_equal(left_item, right_item)
        return
    assert left == right


def test_step_uses_the_approved_dependency_order(monkeypatch: pytest.MonkeyPatch) -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    calls: list[str] = []

    def deposit(self: PesticideEffectField, spray: AcceptedSpray, reference_volume_l: float) -> None:
        calls.append("deposit")

    def update(self: DynamicWind) -> WindState:
        calls.append("wind")
        self.state = WindState(0.0, 0.5, self.state.step_count + 1)
        return self.state

    def mortality(self: PesticideEffectField, prey: np.ndarray, predator: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        calls.append("mortality")
        return prey.copy(), predator.copy()

    def substep(
        prey: np.ndarray,
        predator: np.ndarray,
        wind: tuple[float, float],
        config: DynamicEcologyConfig,
    ) -> tuple[np.ndarray, np.ndarray]:
        calls.append(f"substep-{len([item for item in calls if item.startswith('substep-')]) + 1}")
        return prey + 0.001, predator + 0.001

    def decay(self: PesticideEffectField) -> None:
        calls.append("decay")

    monkeypatch.setattr(PesticideEffectField, "deposit", deposit)
    monkeypatch.setattr(DynamicWind, "update", update)
    monkeypatch.setattr(PesticideEffectField, "apply_mortality", mortality)
    monkeypatch.setattr(dynamics, "holling_tanner_substep", substep)
    monkeypatch.setattr(PesticideEffectField, "decay", decay)

    transition = system.step((AcceptedSpray(2, 2, 0.25),))

    assert calls == [
        "deposit", "wind", "mortality", "substep-1", "substep-2", "substep-3", "decay"
    ]
    assert transition.deposited_effect == pytest.approx(CONFIG.effect_amount)
    assert transition.step_count == 1


def test_no_spray_still_advances_a_non_equilibrium_ecology() -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    prey_before = system.prey
    predator_before = system.predator

    system.step(())

    assert not np.array_equal(system.prey, prey_before)
    assert not np.array_equal(system.predator, predator_before)


def test_transition_reports_cumulative_deposited_center_effect() -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)

    first = system.step((AcceptedSpray(2, 2, 0.25),))
    second = system.step((AcceptedSpray(3, 3, 0.125),))

    assert first.deposited_effect == pytest.approx(0.85)
    assert second.deposited_effect == pytest.approx(0.85 + 0.425)


def test_global_summary_and_local_context_have_frozen_dimensions() -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)

    summary = system.global_summary()
    context = system.local_context(0, 0)

    assert isinstance(summary, tuple)
    assert len(summary) == 17
    assert len(context) == 6
    assert all(np.isfinite(summary))
    assert all(np.isfinite(context))


def test_snapshot_restores_exact_continuation_and_canonical_digest() -> None:
    left = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    for step in range(4):
        left.step(_sprays(step))
    snapshot = left.state_dict()
    right = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    right.load_state_dict(snapshot)

    _assert_state_equal(right.state_dict(), snapshot)
    for step in range(4, 14):
        assert left.step(_sprays(step)) == right.step(_sprays(step))
        _assert_state_equal(left.state_dict(), right.state_dict())
    assert left.prey.tobytes() == right.prey.tobytes()
    assert left.predator.tobytes() == right.predator.tobytes()
    assert left.wind_state == right.wind_state
    assert left.rng_state == right.rng_state


def test_public_arrays_are_detached_from_the_live_system() -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    prey = system.prey
    concentration = system.concentration
    prey[0, 0] = 99.0
    concentration[0, 0] = 99.0

    assert system.prey[0, 0] != 99.0
    assert system.concentration[0, 0] != 99.0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda state: state.update(config_hash="0" * 64), "config_hash"),
        (lambda state: state["prey"].__setitem__((0, 0), np.nan), "prey"),
        (lambda state: state["predator"].__setitem__((0, 0), -1.0), "predator"),
        (lambda state: state["pesticide"]["concentration"].__setitem__((0, 0), 2.0), "concentration"),
        (lambda state: state.update(prey=state["prey"].astype(np.float32)), "prey"),
        (lambda state: state["wind"].update(bit_generator="MT19937"), "bit-generator"),
    ],
)
def test_state_restore_rejects_drift_invalid_values_and_unsupported_rng(
    mutation: object, message: str
) -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    snapshot = system.state_dict()
    mutation(snapshot)

    with pytest.raises(ValueError, match=message):
        system.load_state_dict(snapshot)


def test_state_restore_rejects_config_object_drift() -> None:
    system = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)
    changed = replace(CONFIG, beta=1.4)
    restored = DynamicEcologySystem.from_scenario(_scenario(), CONFIG, 0.25)

    with pytest.raises(ValueError, match="config_hash"):
        restored.load_state_dict(system.state_dict(), config=changed)


def test_transition_has_the_declared_fields() -> None:
    assert EcologyTransition.__dataclass_fields__.keys() == {
        "prey_before_total",
        "prey_after_total",
        "predator_before_total",
        "predator_after_total",
        "deposited_effect",
        "wind_vector",
        "step_count",
    }
