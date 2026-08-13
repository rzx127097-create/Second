from __future__ import annotations

import pytest

from problem2.environment.rewards import (
    RewardWeights,
    compute_reward,
    reduction_rate,
    success,
)


def test_service_reward_uses_actual_transferred_amount_not_refill_count() -> None:
    weights = RewardWeights(service_per_l=2.0, completion_bonus=3.0)
    partial = compute_reward(
        previous_density=1.0,
        current_density=0.9,
        transferred_l=0.1,
        request_completed=False,
        weights=weights,
    )
    complete = compute_reward(
        previous_density=1.0,
        current_density=0.9,
        transferred_l=0.4,
        request_completed=True,
        weights=weights,
    )
    assert partial.components["service"] == pytest.approx(0.2)
    assert complete.components["service"] == pytest.approx(3.8)
    assert complete.total > partial.total


def test_reward_components_are_auditable_and_invalid_is_separate() -> None:
    result = compute_reward(
        previous_density=1.0,
        current_density=0.8,
        transferred_l=0.0,
        waiting_s=2.0,
        invalid_count=1,
        weights=RewardWeights(control_per_density=1.0, coordination_per_wait_s=0.5, invalid_cost=4.0),
    )
    assert set(result.components) == {"control", "service", "coordination", "invalid"}
    assert result.total == pytest.approx(0.2 - 1.0 - 4.0)
    assert result.components["invalid"] == pytest.approx(4.0)


def test_reduction_and_success_use_the_85_percent_threshold() -> None:
    assert reduction_rate(100.0, 15.0) == pytest.approx(0.85)
    assert success(100.0, 15.0)
    assert not success(100.0, 15.0001)
    assert reduction_rate(0.0, 0.0) == 0.0

