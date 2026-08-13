from __future__ import annotations

import numpy as np

from problem2.scenarios.factory import build_synthetic_scenario


CONFIG_DIR = "configs"


def _snapshot_signature(snapshot):
    positions = {
        agent_id: tuple(observation["position"])
        for agent_id, observation in snapshot.role_observations.items()
    }
    density = np.asarray(snapshot.critic_state["eco"], dtype=float)
    return (
        positions,
        tuple(np.asarray(snapshot.critic_state["field"], dtype=float).reshape(-1)),
        tuple(np.asarray(snapshot.critic_state["resource_totals"], dtype=float).reshape(-1)),
        density.tolist(),
    )


def test_synthetic_scenario_is_deterministic_and_completes_a_legal_step() -> None:
    first = build_synthetic_scenario("s1", seed=17, config_dir=CONFIG_DIR)
    second = build_synthetic_scenario("s1", seed=17, config_dir=CONFIG_DIR)

    first_initial = first.reset()
    second_initial = second.reset()
    assert _snapshot_signature(first_initial) == _snapshot_signature(second_initial)
    assert _snapshot_signature(first.reset()) == _snapshot_signature(first_initial)
    assert first_initial.episode_id == second_initial.episode_id
    assert first_initial.step == 0
    assert first_initial.normalization_version

    actions = {
        agent_id: mask.valid_actions[0]
        for agent_id, mask in first_initial.action_masks.items()
    }
    stepped = first.step(actions)
    assert stepped.step == 1
    assert [event["event_type"] for event in stepped.events] == [
        "actions_validated",
        "movement_applied",
        "field_updated",
    ]
    first.resources.assert_conservation()
