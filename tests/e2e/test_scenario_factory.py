from __future__ import annotations

import numpy as np
import pytest

from problem2.config import load_config_bundle
from problem2.scenarios.factory import build_synthetic_scenario
from problem2.scenarios.interventions import ScenarioIntervention


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
    event_types = [event["event_type"] for event in stepped.events]
    assert event_types[0] == "actions_validated"
    assert event_types[-1] == "field_updated"
    assert event_types.count("uav_movement_applied") == 2
    assert event_types.count("movement_applied") == 1
    first.resources.assert_conservation()


def test_scenario_uses_mechanistic_field_dynamics_instead_of_local_smoke_removal() -> None:
    bundle = build_synthetic_scenario("s1", seed=41, config_dir=CONFIG_DIR)

    assert bundle.dynamics_kind == "reaction_diffusion_advection_exposure"
    assert bundle.pest_dynamics.diffusion_rate_m2_s > 0.0
    assert bundle.pesticide_field.decay_rate_s > 0.0


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


def test_controlled_simulation_readiness_allows_provisional_mechanistic_scenario() -> None:
    bundle = build_synthetic_scenario("s1", seed=3, config_dir=CONFIG_DIR)

    bundle.assert_simulation_ready()
    with pytest.raises(ValueError, match="provisional"):
        bundle.assert_formal_ready()


def test_verified_status_cannot_promote_provisional_mechanistic_scenario_to_formal() -> None:
    bundle = build_synthetic_scenario("s1", seed=3, config_dir=CONFIG_DIR)
    bundle.parameter_status = "verified"

    with pytest.raises(ValueError, match="not calibrated formal dynamics"):
        bundle.assert_formal_ready()


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
    node = min(bundle.road_graph.nodes)
    bundle.adapter.executors["vehicle-1"].current_node = node
    bundle.adapter._refresh_state(events=[])

    snapshot = bundle._snapshot(events=())

    position = snapshot.role_observations["vehicle-1"]["position"]
    assert len(position) == 2
    assert all(np.isfinite(position))
    np.testing.assert_allclose(snapshot.critic_state["vehicles"][0, :2], position)


def test_vehicle_action_contract_is_configured_and_matches_runtime_slots() -> None:
    config = load_config_bundle(CONFIG_DIR)
    environment = config.environment
    slot_count = int(environment["max_candidate_slots"])
    expected_names = ["hold", *[f"slot-{index}" for index in range(slot_count)]]
    assert environment["vehicle_action_names"] == expected_names

    bundle = build_synthetic_scenario("s1", seed=31, config_dir=CONFIG_DIR)
    snapshot = bundle.reset()
    vehicle_mask = snapshot.action_masks["vehicle-1"]
    assert len(vehicle_mask.actions) == slot_count + 1
    assert list(vehicle_mask.actions) == expected_names


def test_request_candidate_and_service_transfer_share_one_runtime_path() -> None:
    bundle = build_synthetic_scenario("s1", seed=37, config_dir=CONFIG_DIR)
    snapshot = bundle.reset()
    bundle.resources.spray("uav-1", 0.85)
    snapshot = bundle.step({agent_id: "hold" for agent_id in snapshot.role_observations})
    assert any(event["event_type"] == "request_created" for event in snapshot.events)

    initial_total = bundle.resources.total_pesticide_l
    transfer_events: list[dict[str, object]] = []
    release_events: list[dict[str, object]] = []
    for _ in range(80):
        vehicle_id = "vehicle-1"
        vehicle_action = "slot-0" if "slot-0" in snapshot.action_masks[vehicle_id].valid_actions else "hold"
        actions = {
            agent_id: (vehicle_action if agent_id == vehicle_id else "hold")
            for agent_id in snapshot.role_observations
        }
        snapshot = bundle.step(actions)
        transfer_events.extend(
            event for event in snapshot.events if event["event_type"] == "pesticide_transfer"
        )
        release_events.extend(
            event for event in snapshot.events if event["event_type"] == "service_released"
        )
        if release_events:
            break

    assert transfer_events
    assert sum(float(event["amount_l"]) for event in transfer_events) > 0.0
    assert bundle.resources.total_pesticide_l == pytest.approx(initial_total)
    assert len(transfer_events) > 1
    assert release_events


@pytest.mark.parametrize("scale_id", ["s1", "s2", "s3", "s4", "s5", "s6"])
def test_fixed_support_has_a_serviceable_request_slot_at_every_scale(scale_id: str) -> None:
    bundle = build_synthetic_scenario(
        scale_id,
        seed=43,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention("matched_fixed", support_mode="fixed"),
    )
    snapshot = bundle.reset()
    bundle.resources.spray("uav-1", bundle.resources.uav("uav-1").onboard_l)

    snapshot = bundle.step({agent_id: "hold" for agent_id in snapshot.role_observations})

    assert any(
        action.startswith("slot-")
        for action in snapshot.action_masks["vehicle-1"].valid_actions
    )


def test_mobile_and_fixed_support_share_one_serviceable_entry_depot() -> None:
    nodes: list[str] = []
    for condition_id, support_mode in (
        ("sr_mappo_mobile", "mobile"),
        ("matched_fixed", "fixed"),
    ):
        bundle = build_synthetic_scenario(
            "s3",
            seed=47,
            config_dir=CONFIG_DIR,
            intervention=ScenarioIntervention(condition_id, support_mode=support_mode),
        )
        bundle.reset()
        node = bundle.adapter.initial_vehicle_nodes["vehicle-1"]
        nodes.append(node)
        x_m, y_m = bundle.road_graph.nodes[node]
        assert x_m**2 + y_m**2 <= 25.0
        assert bundle.adapter._rendezvous_points("uav-1")

    assert nodes[0] == nodes[1]
