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


def test_provisional_scenario_blocks_formal_use_and_reset_restores_spray_state() -> None:
    bundle = build_synthetic_scenario("s1", seed=3, config_dir=CONFIG_DIR)
    initial = bundle.reset()
    spray_actions = {
        agent_id: ("spray" if agent_id.startswith("uav-") and "spray" in mask.valid_actions else mask.valid_actions[0])
        for agent_id, mask in initial.action_masks.items()
    }
    stepped = bundle.step(spray_actions)
    assert any(event["event_type"] == "spray_applied" for event in stepped.events)
    assert bundle.resources.total_pesticide_l < float(initial.critic_state["resource_totals"][-1])
    bundle.resources.assert_conservation()
    reset = bundle.reset()
    assert reset.critic_state["resource_totals"][-1] == initial.critic_state["resource_totals"][-1]
    try:
        bundle.assert_formal_ready()
    except ValueError as exc:
        assert "provisional" in str(exc)
    else:
        raise AssertionError("provisional scenario must not be accepted as formal evidence")


def test_snapshot_exposes_candidate_mapping_from_adapter() -> None:
    bundle = build_synthetic_scenario("s1", seed=5, config_dir=CONFIG_DIR)
    snapshot = bundle.reset()
    assert snapshot.candidate_mapping
    assert bundle.adapter.state.candidate_mapping == snapshot.candidate_mapping


def test_request_and_service_state_reach_all_section_4_4_inputs() -> None:
    bundle = build_synthetic_scenario("s1", seed=23, config_dir=CONFIG_DIR)
    initial = bundle.reset()
    bundle.resources.spray("uav-1", 0.85)
    actions = {
        agent_id: "hold"
        for agent_id in initial.role_observations
    }

    snapshot = bundle.step(actions)

    requests = bundle.request_manager.active_requests()
    assert len(requests) == 1
    request = requests[0]
    assert snapshot.role_observations["uav-1"]["request_remaining_l"] == request.remaining_l
    vehicle = snapshot.role_observations["vehicle-1"]
    assert vehicle["slot_mapping"][0] == request.request_id
    assert vehicle["request_slot_mask"][0] == 1
    assert snapshot.critic_state["requests"].shape[0] == bundle.adapter.max_candidate_slots
    assert snapshot.critic_state["requests"][0, 0] == request.remaining_l
    assert snapshot.critic_state["service"][0] == 0.0
    candidate_mapping = snapshot.candidate_mapping["vehicle-1"]
    assert candidate_mapping
    assert vehicle["candidate_slot_mapping"][0] == candidate_mapping[0][1]
    assert vehicle["candidate_slot_mask"][0] == 1
    assert np.isfinite(vehicle["candidate_features"]).all()


def test_snapshot_uses_grid_coordinates_for_both_actor_roles_and_critic() -> None:
    bundle = build_synthetic_scenario("s1", seed=29, config_dir=CONFIG_DIR)
    bundle.reset()
    node = str((0, 1))
    bundle.adapter.executors["vehicle-1"].current_node = node
    bundle.adapter._refresh_state(events=[])

    snapshot = bundle._snapshot(events=())

    assert snapshot.role_observations["vehicle-1"]["position"] == (0.0, 1.0)
    np.testing.assert_allclose(snapshot.critic_state["vehicles"][0, :2], [0.0, 1.0])
