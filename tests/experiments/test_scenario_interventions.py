from __future__ import annotations

from pathlib import Path

import numpy as np

from problem2.scenarios.factory import build_synthetic_scenario
from problem2.scenarios.interventions import ScenarioIntervention


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"


def _legal_step(bundle, *, spray: bool = False):
    snapshot = bundle._snapshot(events=())
    actions = {}
    for agent_id, observation in snapshot.role_observations.items():
        desired = "spray" if spray and observation["role"] == "uav" else "hold"
        actions[agent_id] = desired if desired in snapshot.action_masks[agent_id].valid_actions else snapshot.action_masks[agent_id].valid_actions[0]
    return bundle.step(actions)


def test_parameter_intervention_is_typed_bounded_and_recorded() -> None:
    intervention = ScenarioIntervention(
        condition_id="sensitivity-probe",
        parameter_overrides=(
            ("uav_initial_pesticide_ratio", 0.5),
            ("vehicle_speed", 2.0),
            ("service_setup_time", 20.0),
            ("rendezvous_radius", 10.0),
        ),
    )
    bundle = build_synthetic_scenario("s1", 5, config_dir=CONFIG_DIR, intervention=intervention)

    assert bundle.intervention_id == "sensitivity-probe"
    assert len(bundle.intervention_hash) == 64
    assert bundle.adapter.vehicle_speed_mps == 2.0
    assert bundle.adapter.service_setup_s == 20.0
    assert bundle.adapter.rendezvous_radius_m == 10.0
    assert all(state.onboard_l == 0.5 * state.capacity_l for state in bundle.resources.uavs.values())


def test_unlimited_diagnostic_removes_onboard_bottleneck_without_breaking_conservation() -> None:
    intervention = ScenarioIntervention(condition_id="unlimited", pesticide_mode="unlimited")
    bundle = build_synthetic_scenario("s1", 7, config_dir=CONFIG_DIR, intervention=intervention)
    base = build_synthetic_scenario("s1", 7, config_dir=CONFIG_DIR)

    assert bundle.resources.uav("uav-1").capacity_l > base.resources.uav("uav-1").capacity_l
    assert bundle.resources.uav("uav-1").onboard_l >= (
        bundle.resources.uav("uav-1").spray_flow_l_s * bundle.max_steps
    )
    for _ in range(3):
        _legal_step(bundle, spray=True)
    assert bundle.resources.assert_conservation() is None
    assert not any(event["event_type"] == "request_created" for event in bundle.adapter.state.events)


def test_disabled_support_keeps_inventory_stranded_and_closes_vehicle_slots() -> None:
    intervention = ScenarioIntervention(
        condition_id="no-support",
        support_mode="disabled",
        parameter_overrides=(("uav_initial_pesticide_ratio", 0.1),),
    )
    bundle = build_synthetic_scenario("s1", 11, config_dir=CONFIG_DIR, intervention=intervention)
    initial_inventory = bundle.resources.vehicle("vehicle-1").inventory_l

    stepped = _legal_step(bundle, spray=True)

    assert any(event["event_type"] == "request_created" for event in stepped.events)
    assert stepped.action_masks["vehicle-1"].valid_actions == ("hold",)
    assert bundle.resources.vehicle("vehicle-1").inventory_l == initial_inventory


def test_fixed_support_exposes_only_routes_ending_at_the_frozen_support_node() -> None:
    intervention = ScenarioIntervention(
        condition_id="fixed",
        support_mode="fixed",
        parameter_overrides=(
            ("uav_initial_pesticide_ratio", 0.1),
            ("rendezvous_radius", 30.0),
        ),
    )
    bundle = build_synthetic_scenario("s1", 13, config_dir=CONFIG_DIR, intervention=intervention)
    support_node = bundle.adapter.initial_vehicle_nodes["vehicle-1"]
    bundle.adapter.uav_positions["uav-1"] = bundle.adapter.road_node_to_uav_cell(support_node)

    stepped = _legal_step(bundle, spray=True)

    routes = bundle.adapter._candidate_routes["vehicle-1"]
    assert routes
    assert {route[-1] for route in routes.values()} == {support_node}
    assert any(action.startswith("slot-") for action in stepped.action_masks["vehicle-1"].valid_actions)


def test_teleport_diagnostic_transfers_real_inventory_without_vehicle_travel() -> None:
    intervention = ScenarioIntervention(
        condition_id="teleport",
        support_mode="teleport",
        parameter_overrides=(("uav_initial_pesticide_ratio", 0.1),),
    )
    bundle = build_synthetic_scenario("s1", 17, config_dir=CONFIG_DIR, intervention=intervention)
    inventory_before = bundle.resources.vehicle("vehicle-1").inventory_l

    stepped = _legal_step(bundle, spray=True)

    transfers = [event for event in stepped.events if event["event_type"] == "pesticide_transfer"]
    assert transfers and transfers[0]["mode"] == "teleport_diagnostic"
    assert bundle.resources.vehicle("vehicle-1").inventory_l < inventory_before
    assert sum(float(event.get("travelled_distance_m", 0.0)) for event in stepped.events) == 0.0
    assert bundle.resources.assert_conservation() is None


def test_adaptation_variants_are_seed_deterministic_and_change_the_declared_state() -> None:
    blocked = ScenarioIntervention(
        condition_id="blocked",
        adaptation_overrides=(("road_blockage", 0.10),),
    )
    first = build_synthetic_scenario("s2", 19, config_dir=CONFIG_DIR, intervention=blocked)
    second = build_synthetic_scenario("s2", 19, config_dir=CONFIG_DIR, intervention=blocked)
    base = build_synthetic_scenario("s2", 19, config_dir=CONFIG_DIR)

    first_edges = sum(len(value) for value in first.road_graph.adjacency.values()) // 2
    second_edges = sum(len(value) for value in second.road_graph.adjacency.values()) // 2
    base_edges = sum(len(value) for value in base.road_graph.adjacency.values()) // 2
    assert first_edges == second_edges < base_edges
    assert len(first.road_graph.component(next(iter(first.road_graph.nodes)))) == len(first.road_graph.nodes)

    dispersed = ScenarioIntervention(
        condition_id="dispersed",
        adaptation_overrides=(("demand_dispersion", "dispersed"),),
    )
    clustered = ScenarioIntervention(
        condition_id="clustered",
        adaptation_overrides=(("demand_dispersion", "clustered"),),
    )
    dispersed_bundle = build_synthetic_scenario("s2", 19, config_dir=CONFIG_DIR, intervention=dispersed)
    clustered_bundle = build_synthetic_scenario("s2", 19, config_dir=CONFIG_DIR, intervention=clustered)
    assert not np.array_equal(dispersed_bundle.initial_density, clustered_bundle.initial_density)


def _density_weighted_distance_to_road(bundle) -> float:
    road_cells = np.asarray(
        [bundle.adapter.road_node_to_uav_cell(node_id) for node_id in bundle.road_graph.nodes],
        dtype=float,
    )
    rows, cols = np.indices(bundle.grid_shape)
    cells = np.column_stack((rows.reshape(-1), cols.reshape(-1))).astype(float)
    distances = np.sqrt(((cells[:, None, :] - road_cells[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    weights = bundle.initial_density.reshape(-1)
    return float(np.average(distances, weights=weights))


def test_hotspot_road_separation_changes_hotspot_distance_without_changing_road() -> None:
    near = ScenarioIntervention(
        condition_id="hotspot-near",
        adaptation_overrides=(("hotspot_road_separation", "near"),),
    )
    far = ScenarioIntervention(
        condition_id="hotspot-far",
        adaptation_overrides=(("hotspot_road_separation", "far"),),
    )

    near_bundle = build_synthetic_scenario("s3", 23, config_dir=CONFIG_DIR, intervention=near)
    far_bundle = build_synthetic_scenario("s3", 23, config_dir=CONFIG_DIR, intervention=far)

    assert near_bundle.road_graph.nodes == far_bundle.road_graph.nodes
    assert far_bundle.initial_density.shape == near_bundle.initial_density.shape
    assert _density_weighted_distance_to_road(far_bundle) > (
        _density_weighted_distance_to_road(near_bundle) + 1.0
    )


def test_simultaneous_request_level_changes_same_step_arrival_count() -> None:
    common_parameters = (("uav_initial_pesticide_ratio", 0.1),)
    low = ScenarioIntervention(
        condition_id="requests-low",
        parameter_overrides=common_parameters,
        adaptation_overrides=(("simultaneous_requests", "low"),),
    )
    high = ScenarioIntervention(
        condition_id="requests-high",
        parameter_overrides=common_parameters,
        adaptation_overrides=(("simultaneous_requests", "high"),),
    )
    low_bundle = build_synthetic_scenario("s5", 29, config_dir=CONFIG_DIR, intervention=low)
    high_bundle = build_synthetic_scenario("s5", 29, config_dir=CONFIG_DIR, intervention=high)

    low_step = _legal_step(low_bundle)
    high_step = _legal_step(high_bundle)
    low_requests = [event for event in low_step.events if event["event_type"] == "request_created"]
    high_requests = [event for event in high_step.events if event["event_type"] == "request_created"]

    assert len(low_requests) == 1
    assert len(high_requests) == len(high_bundle.resources.uavs)


def _request_step(bundle):
    bundle.reset()
    bundle.resources.spray("uav-1", 0.85)
    bundle.resources.spray("uav-2", 1.0)
    return _legal_step(bundle)


def test_remove_air_ground_observation_zeroes_cross_role_features_only() -> None:
    full = build_synthetic_scenario(
        "s1",
        31,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention("full", ablation_flags=("full",)),
    )
    removed = build_synthetic_scenario(
        "s1",
        31,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention(
            "no-air-ground",
            ablation_flags=("remove_air_ground_observation",),
        ),
    )

    full_snapshot = _request_step(full)
    removed_snapshot = _request_step(removed)
    full_vehicle = full_snapshot.role_observations["vehicle-1"]
    removed_vehicle = removed_snapshot.role_observations["vehicle-1"]

    assert full_vehicle["vector"].shape == removed_vehicle["vector"].shape
    assert np.any(full_vehicle["request_slots"] > 0.0)
    assert np.all(removed_vehicle["request_slots"] == 0.0)
    assert np.any(full_vehicle["candidate_features"] != 0.0)
    assert np.all(removed_vehicle["candidate_features"] == 0.0)


def test_remove_endurance_prediction_removes_exhaustion_signal_from_candidates() -> None:
    full = build_synthetic_scenario(
        "s1",
        37,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention("full", ablation_flags=("full",)),
    )
    removed = build_synthetic_scenario(
        "s1",
        37,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention(
            "no-endurance",
            ablation_flags=("remove_endurance_prediction",),
        ),
    )

    full_snapshot = _request_step(full)
    removed_snapshot = _request_step(removed)
    full_candidates = full_snapshot.role_observations["vehicle-1"]["candidate_features"]
    removed_candidates = removed_snapshot.role_observations["vehicle-1"]["candidate_features"]

    assert np.any(full_candidates[:, 9] == 1.0)
    assert np.all(removed_candidates[:, 9] == 0.0)
    assert np.isfinite(removed_candidates).all()


def test_remove_joint_demand_rendezvous_uses_fifo_instead_of_urgency_order() -> None:
    full = build_synthetic_scenario(
        "s1",
        41,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention("full", ablation_flags=("full",)),
    )
    removed = build_synthetic_scenario(
        "s1",
        41,
        config_dir=CONFIG_DIR,
        intervention=ScenarioIntervention(
            "no-joint-rendezvous",
            ablation_flags=("remove_joint_demand_rendezvous",),
        ),
    )

    full_snapshot = _request_step(full)
    removed_snapshot = _request_step(removed)
    full_first = dict(full_snapshot.candidate_mapping["vehicle-1"])["slot-0"]
    removed_first = dict(removed_snapshot.candidate_mapping["vehicle-1"])["slot-0"]

    assert full_first.split(":", 1)[0] != removed_first.split(":", 1)[0]
    assert removed_first.split(":", 1)[0].endswith("000001")
