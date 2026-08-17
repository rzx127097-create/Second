"""Deterministic provisional scenarios and the common decision interface.

The factory deliberately keeps physical state in the existing domain and
section-4.2 adapter.  This module only assembles a small rectangular smoke
scenario and translates that state into the observation/critic contract used
by later training and evaluation tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from problem2.config import config_identity, load_config_bundle
from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.environment.action_masks import ActionMask
from problem2.environment.observations import (
    SlotMapping,
    build_observations,
    build_structured_critic_state,
    stable_slot_mapping,
)
from problem2.environment.rewards import compute_reward
from problem2.field.pest_dynamics import PestDynamics
from problem2.field.pesticide_field import PesticideField
from problem2.field.wind_field import WindField
from problem2.road.graph import RoadGraph
from problem2.road.graphml import load_graphml
from problem2.section4_2.adapter import HeterogeneousDecisionAdapter
from problem2.scenarios.interventions import ScenarioIntervention, baseline_intervention
from problem2.experiments.simulation_preflight import audit_simulation_preflight, load_simulation_profile


NORMALIZATION_VERSION = "provisional-v1"


@dataclass(frozen=True)
class DecisionSnapshot:
    """All inputs required by a role policy at one decision boundary."""

    role_observations: dict[str, dict[str, Any]]
    critic_state: dict[str, Any]
    action_masks: dict[str, ActionMask]
    candidate_mapping: dict[str, Any]
    episode_id: str
    step: int
    normalization_version: str
    events: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class StepSnapshot(DecisionSnapshot):
    """Decision snapshot returned after applying one joint action."""

    reward: float = 0.0
    reward_components: dict[str, float] = field(default_factory=dict)
    terminated: bool = False
    truncated: bool = False
    info: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioBundle:
    """A deterministic, resettable synthetic air-ground scenario."""

    scale_id: str
    seed: int
    max_steps: int
    grid_shape: tuple[int, int]
    resources: PesticideResources
    road_graph: RoadGraph
    adapter: HeterogeneousDecisionAdapter
    initial_density: np.ndarray
    pest_density: np.ndarray
    pest_dynamics: PestDynamics
    pesticide_field: PesticideField
    candidate_mapping: dict[str, Any]
    episode_id: str
    scenario_id: str
    success_reduction_threshold: float = 0.85
    physical_extent_m: tuple[float, float] = (1.0, 1.0)
    cell_size_m: tuple[float, float] = (1.0, 1.0)
    normalization_version: str = NORMALIZATION_VERSION
    parameter_status: str = "provisional"
    intervention_id: str = "baseline"
    intervention_hash: str = ""
    support_mode: str = "mobile"
    ablation_flags: tuple[str, ...] = ()
    include_air_ground_observation: bool = True
    scenario_source_kind: str = "synthetic_smoke"
    dynamics_kind: str = "smoke_local_removal"
    source_metadata_hash: str = ""
    config_hash: str = ""
    simulation_profile_sha256: str = ""
    evidence_mode: str = "controlled_simulation"
    simulation_preflight_ready: bool = True
    simulation_preflight_errors: tuple[dict[str, object], ...] = ()
    simulation_preflight_warnings: tuple[dict[str, object], ...] = ()
    step_count: int = 0
    last_termination_reason: str | None = None
    _slot_mapping: SlotMapping | None = field(default=None, init=False, repr=False)

    @property
    def request_manager(self):
        return self.adapter.request_manager

    @property
    def service(self):
        return self.adapter.service

    def reset(self) -> DecisionSnapshot:
        """Restore all physical state and return the initial decision."""

        self.pest_density = self.initial_density.copy()
        self.pesticide_field.active.fill(0.0)
        self.step_count = 0
        self.last_termination_reason = None
        self.adapter.reset(seed=self.seed)
        return self._snapshot(events=())

    def assert_formal_ready(self) -> None:
        """Guard formal evidence generation until engineering values are verified."""

        if self.parameter_status != "verified":
            raise ValueError(
                "scenario parameters are provisional; formal training/evaluation is blocked"
            )
        if self.scenario_source_kind != "frozen_gis":
            raise ValueError(
                f"scenario source {self.scenario_source_kind!r} is not a frozen GIS source"
            )
        if self.dynamics_kind != "calibrated_reaction_diffusion_advection":
            raise ValueError(
                f"scenario dynamics {self.dynamics_kind!r} are not calibrated formal dynamics"
            )
        if len(self.source_metadata_hash) != 64:
            raise ValueError("formal scenario source metadata must have a SHA-256 identity")

    def assert_simulation_ready(self) -> None:
        """Guard controlled-simulation evidence against technical drift.

        Provisional engineering and ecological values are allowed here, but
        the mechanistic model, frozen road identity, and preflight result must
        still be internally consistent.
        """

        if self.simulation_preflight_ready is not True:
            details = "; ".join(
                str(issue.get("message", issue))
                for issue in self.simulation_preflight_errors
            )
            raise ValueError(f"simulation preflight failed: {details or 'technical error'}")
        if self.scenario_source_kind != "frozen_gis":
            raise ValueError(
                f"simulation scenario source {self.scenario_source_kind!r} is not frozen GIS"
            )
        if self.dynamics_kind != "reaction_diffusion_advection_exposure":
            raise ValueError(
                f"simulation dynamics {self.dynamics_kind!r} are not mechanistic"
            )
        if len(self.source_metadata_hash) != 64:
            raise ValueError("simulation scenario source metadata must have a SHA-256 identity")
        if len(self.config_hash) != 64:
            raise ValueError("simulation scenario configuration must have a SHA-256 identity")
        if len(self.simulation_profile_sha256) != 64:
            raise ValueError("simulation profile must have a SHA-256 identity")
        if not self.road_graph.nodes or not self.road_graph.adjacency:
            raise ValueError("simulation road graph must contain nodes and adjacency")

    def step(self, actions: Mapping[str, str]) -> StepSnapshot:
        """Apply one validated joint action and update the pest field."""

        if self.step_count >= self.max_steps:
            raise RuntimeError("scenario horizon has been exhausted; call reset")
        previous_mean = float(np.mean(self.pest_density))
        state = self.adapter.step(actions)
        self.step_count += 1

        # Apply deposited liquid to the exposure field, then advance the
        # mechanistic reaction-diffusion-advection model.  The physical liquid
        # ledger remains owned by Resources; the field stores exposure units.
        for event in state.events:
            if event.get("event_type") != "spray_applied":
                continue
            uav_id = str(event.get("uav_id"))
            position = self.adapter.uav_positions[uav_id]
            amount = float(event.get("amount_l", 0.0))
            self.pesticide_field.deposit(position, amount)
        self.pest_density = self.pest_dynamics.step(
            self.pest_density,
            self.pesticide_field,
            self.adapter.decision_dt_s,
            cell_size_m=self.cell_size_m,
        )
        self.pesticide_field.step(self.adapter.decision_dt_s, cell_size_m=self.cell_size_m)
        current_mean = float(np.mean(self.pest_density))
        reward = compute_reward(
            previous_mean,
            current_mean,
            events=state.events,
            vehicle_distance_m=sum(
                float(event.get("travelled_distance_m", 0.0))
                for event in state.events
                if event.get("event_type") == "movement_applied"
            ),
        )
        reduction = max(0.0, 1.0 - current_mean / max(float(np.mean(self.initial_density)), 1e-12))
        terminated = reduction >= self.success_reduction_threshold
        truncated = self.step_count >= self.max_steps and not terminated
        self.last_termination_reason = "success" if terminated else ("max_steps" if truncated else None)
        info = {
            "scale_id": self.scale_id,
            "seed": self.seed,
            "step": self.step_count,
            "pesticide_total_l": self.resources.total_pesticide_l,
            "pest_mean": current_mean,
            "pesticide_exposure_total": float(np.sum(self.pesticide_field.active)),
            "reduction_rate": reduction,
            "termination_reason": self.last_termination_reason,
        }
        self.resources.assert_conservation()
        snapshot = self._snapshot(events=tuple(state.events))
        return StepSnapshot(
            **snapshot.__dict__,
            reward=reward.total,
            reward_components=dict(reward.components),
            terminated=terminated,
            truncated=truncated,
            info=info,
        )

    def _snapshot(self, *, events: tuple[dict[str, object], ...]) -> DecisionSnapshot:
        vehicle_positions = {
            vehicle_id: self.adapter.road_node_to_uav_cell(node)
            for vehicle_id, node in self.adapter.state.vehicle_nodes.items()
        }
        positions = {
            **{uav_id: position for uav_id, position in self.adapter.uav_positions.items()},
            **vehicle_positions,
        }
        active_requests = self.request_manager.active_requests()
        self._slot_mapping = stable_slot_mapping(
            self.resources.uavs,
            self.resources.vehicles,
            active_requests,
            max_request_slots=self.adapter.max_candidate_slots,
        )
        observations = build_observations(
            resources=self.resources,
            positions=positions,
            vehicle_positions=vehicle_positions,
            pest_density=self.pest_density,
            mapping=self._slot_mapping,
            requests=active_requests,
            service_locked_uav_id=self.service.locked_uav_id,
            service_phase=self.service.phase,
            active_request_id=self.service.request_id,
            max_request_slots=self.adapter.max_candidate_slots,
            candidate_features_by_vehicle=self.adapter.state.candidate_features,
            max_candidate_slots=self.adapter.max_candidate_slots,
            step=self.step_count,
            max_steps=self.max_steps,
            include_air_ground_observation=self.include_air_ground_observation,
        )
        critic = build_structured_critic_state(
            self.resources,
            positions=positions,
            vehicle_positions=vehicle_positions,
            pest_density=self.pest_density,
            mapping=self._slot_mapping,
            requests=active_requests,
            service=self.service,
            step=self.step_count,
            max_steps=self.max_steps,
        )
        critic["field"] = self.pest_density.copy()
        critic["resource_totals"] = np.asarray(
            [
                sum(state.onboard_l for state in self.resources.uavs.values()),
                sum(state.inventory_l for state in self.resources.vehicles.values()),
                self.resources.total_pesticide_l,
            ],
            dtype=float,
        )
        self.candidate_mapping = self.adapter.state.candidate_mapping
        return DecisionSnapshot(
            role_observations=observations,
            critic_state=critic,
            action_masks=dict(self.adapter.state.action_masks),
            candidate_mapping=self.candidate_mapping,
            episode_id=self.episode_id,
            step=self.step_count,
            normalization_version=self.normalization_version,
            events=events,
        )


def _scale_record(config_dir: str | Path, scale_id: str) -> dict[str, Any]:
    bundle = load_config_bundle(config_dir)
    records = bundle.scales.get("scales", [])
    for record in records:
        if str(record.get("id")) == scale_id:
            return dict(record)
    raise ValueError(f"unknown scale_id: {scale_id}")


def _serviceable_support_node(
    graph: RoadGraph,
    *,
    grid_shape: tuple[int, int],
    cell_size_m: tuple[float, float],
    rendezvous_radius_m: float,
    anchor_m: tuple[float, float],
) -> str:
    """Choose the nearest road node whose mapped UAV cell is serviceable."""

    rows, cols = grid_shape
    row_size_m, col_size_m = cell_size_m
    radius_sq = float(rendezvous_radius_m) ** 2
    serviceable: list[str] = []
    for node_id, (x_m, y_m) in graph.nodes.items():
        row = min(max(int(round(float(y_m) / row_size_m)), 0), rows - 1)
        col = min(max(int(round(float(x_m) / col_size_m)), 0), cols - 1)
        target_x = float(col) * col_size_m
        target_y = float(row) * row_size_m
        if (float(x_m) - target_x) ** 2 + (float(y_m) - target_y) ** 2 <= radius_sq + 1e-12:
            serviceable.append(str(node_id))
    if not serviceable:
        raise ValueError(
            "road graph has no UAV-serviceable node within rendezvous_radius_m"
        )
    anchor_x, anchor_y = anchor_m
    return min(
        serviceable,
        key=lambda node_id: (
            (float(graph.nodes[node_id][0]) - anchor_x) ** 2
            + (float(graph.nodes[node_id][1]) - anchor_y) ** 2,
            node_id,
        ),
    )


def build_synthetic_scenario(
    scale_id: str,
    seed: int,
    *,
    config_dir: str | Path,
    scenario_id: str | None = None,
    intervention: ScenarioIntervention | None = None,
) -> ScenarioBundle:
    """Build one deterministic rectangular provisional scenario.

    Values come from the provisional parameter registry and are suitable only
    for interface/smoke tests until the project parameter status is verified.
    """

    config = load_config_bundle(config_dir)
    simulation_profile = load_simulation_profile(config_dir)
    simulation_preflight = audit_simulation_preflight(config_dir)
    intervention = intervention or baseline_intervention()
    scenario_registry = config.scenarios
    requested_id = str(scenario_id or scale_id)
    if requested_id in scenario_registry:
        scenario_record = dict(scenario_registry[requested_id])
        scale_id = str(scenario_record["scale"])
        seed = int(seed) + int(scenario_record.get("seed_offset", 0))
    else:
        scenario_record = {"split": "smoke"}
    scale = _scale_record(config_dir, scale_id)
    rows, cols = (int(scale["grid"][0]), int(scale["grid"][1]))
    uav_count = int(scale["uav_count"])
    parameters = config.parameters.get("parameters", {})
    rated_capacity = float(parameters["uav_onboard_pesticide"]["value"])
    usable_fraction = float(parameters.get("uav_usable_fraction", {}).get("value", 1.0))
    if not 0.0 < usable_fraction <= 1.0:
        raise ValueError("uav_usable_fraction must lie in (0, 1]")
    capacity = rated_capacity * usable_fraction
    spray_flow = float(parameters["uav_spray_flow"]["value"])
    vehicle_inventory = float(parameters["vehicle_inventory"]["value"])
    vehicle_service_capacity = float(parameters["vehicle_service_capacity"]["value"])
    if vehicle_service_capacity <= 0 or vehicle_service_capacity > vehicle_inventory:
        raise ValueError("vehicle_service_capacity must be positive and no greater than vehicle_inventory")
    transfer_rate = float(parameters["vehicle_transfer_rate"]["value"])
    decision_dt_s = float(
        parameters.get("decision_dt", {}).get(
            "value", config.scales.get("decision_dt_s", 1.0)
        )
    )
    field_parameters = config.field_dynamics.get("parameters", {})

    def field_value(name: str, default: float) -> float:
        record = field_parameters.get(name, {})
        if not isinstance(record, Mapping):
            return float(default)
        return float(record.get("value", default))

    field_wind = WindField(
        vx_m_s=field_value("wind_vx_m_s", 0.0),
        vy_m_s=field_value("wind_vy_m_s", 0.0),
    )
    pest_dynamics = PestDynamics(
        growth_rate_s=field_value("pest_growth_rate_s", 0.0),
        carrying_capacity=field_value("pest_carrying_capacity", 1.0),
        mortality_per_exposure=field_value("pest_mortality_per_exposure", 0.02),
        diffusion_rate_m2_s=field_value("pest_diffusion_rate_m2_s", 0.0),
        wind=field_wind,
    )
    hotspot_separation = intervention.adaptations.get("hotspot_road_separation")
    cells = _road_cells((rows, cols), hotspot_separation)

    parameter_overrides = intervention.parameters
    initial_ratio = float(parameter_overrides.get("uav_initial_pesticide_ratio", 1.0))
    if intervention.pesticide_mode == "unlimited":
        capacity = max(capacity, spray_flow * int(scale["max_steps"]) * decision_dt_s * 1.01)

    uavs = {
        f"uav-{index + 1}": UAVState(
            uav_id=f"uav-{index + 1}",
            onboard_l=capacity * initial_ratio,
            capacity_l=capacity,
            spray_flow_l_s=spray_flow,
        )
        for index in range(uav_count)
    }
    vehicles = {
        "vehicle-1": VehicleState(
            "vehicle-1", vehicle_inventory, vehicle_inventory, transfer_rate, vehicle_service_capacity
        )
    }
    resources = PesticideResources(uavs=uavs, vehicles=vehicles)
    extent = tuple(float(value) for value in config.scales.get("physical_extent_m", [cols, rows]))
    cell_size_m = (extent[0] / rows, extent[1] / cols)
    pesticide_field = PesticideField(
        np.zeros((rows, cols), dtype=float),
        decay_rate_s=field_value("pesticide_decay_rate_s", 0.0),
        efficacy_per_l=field_value("pesticide_efficacy_per_l", 1.0),
        diffusion_rate_m2_s=field_value("pesticide_diffusion_rate_m2_s", 0.0),
        wind=field_wind,
    )
    environment = config.environment
    road_config = environment.get("road", {})
    if isinstance(road_config, dict) and str(road_config.get("source")) == "frozen_gis":
        origin = road_config.get("origin_lonlat")
        if not isinstance(origin, (list, tuple)) or len(origin) != 2:
            raise ValueError("frozen_gis road source requires origin_lonlat")
        graphml_source = Path(str(road_config.get("graphml_path")))
        if not graphml_source.is_absolute():
            graphml_source = Path(config_dir).resolve().parent / graphml_source
        road_graph, road_metadata = load_graphml(
            graphml_source,
            coordinate_mode=str(road_config.get("coordinate_mode", "lonlat")),
            origin_lonlat=(float(origin[0]), float(origin[1])),
            directed_policy=str(road_config.get("directed_policy", "undirected")),
            bbox_lonlat=tuple(road_config["bbox_lonlat"]) if road_config.get("bbox_lonlat") else None,
        )
        min_x = min(float(xy[0]) for xy in road_graph.nodes.values())
        min_y = min(float(xy[1]) for xy in road_graph.nodes.values())
        max_x = max(float(xy[0]) for xy in road_graph.nodes.values())
        max_y = max(float(xy[1]) for xy in road_graph.nodes.values())
        if min_x < -1e-6 or min_y < -1e-6 or max_x > extent[1] + 1e-6 or max_y > extent[0] + 1e-6:
            raise ValueError("frozen_gis road graph exceeds the declared physical extent; set a metric crop/bbox")
    else:
        road_graph = RoadGraph.from_grid(cells, cell_size_m=cell_size_m)
        road_metadata = {}
    if hotspot_separation is not None and str(road_config.get("source")) == "frozen_gis":
        cells = [
            (
                min(max(int(round(y / cell_size_m[0])), 0), rows - 1),
                min(max(int(round(x / cell_size_m[1])), 0), cols - 1),
            )
            for x, y in road_graph.nodes.values()
        ]
    density = _density_field(
        np.random.default_rng(int(seed)),
        (rows, cols),
        intervention.adaptations.get("demand_dispersion"),
        road_cells=cells,
        hotspot_separation=hotspot_separation,
    )
    # Scenario registry seeds also freeze a small, deterministic road-condition
    # variant.  Connectivity and metric units remain unchanged, while sealed
    # scenarios no longer differ only by an identifier label.
    road_factor = 1.0 + 0.005 * (int(seed) % 7)
    for node, neighbours in road_graph.adjacency.items():
        for neighbour in list(neighbours):
            neighbours[neighbour] *= road_factor
    blockage = float(intervention.adaptations.get("road_blockage", 0.0))
    if blockage > 0:
        _apply_connected_road_blockage(road_graph, blockage, int(seed))
    parameter_values = {key: value.get("value") for key, value in parameters.items() if isinstance(value, dict)}
    for key in (
        "vehicle_speed",
        "service_setup_time",
        "request_safety_margin",
        "rendezvous_radius",
    ):
        if key in parameter_overrides:
            record = parameters[key]
            value = float(parameter_overrides[key])
            if not float(record["min"]) <= value <= float(record["max"]):
                raise ValueError(f"{key} override is outside the registered engineering range")
            parameter_values[key] = value
    support_node = _serviceable_support_node(
        road_graph,
        grid_shape=(rows, cols),
        cell_size_m=cell_size_m,
        rendezvous_radius_m=float(parameter_values.get("rendezvous_radius", 5.0)),
        anchor_m=(0.0, 0.0),
    )
    simultaneous_level = intervention.adaptations.get("simultaneous_requests")
    request_release_steps = _request_release_steps(tuple(uavs), simultaneous_level)
    ablations = set(intervention.ablation_flags)
    adapter = HeterogeneousDecisionAdapter(
        resources,
        road_graph,
        uav_slots=tuple(uavs),
        vehicle_slots=tuple(vehicles),
        vehicle_speed_mps=float(parameter_values.get("vehicle_speed", 1.0)),
        decision_dt_s=decision_dt_s,
        uav_grid_shape=(rows, cols),
        uav_cell_size_m=cell_size_m,
        uav_speed_mps=float(parameter_values.get("uav_speed", max(cell_size_m) / decision_dt_s)),
        request_threshold_ratio=float(environment.get("request_threshold_ratio", 0.20)),
        dynamic_request_enabled="remove_endurance_prediction" not in ablations,
        request_safety_margin_s=float(parameter_values.get("request_safety_margin", 10.0)),
        service_setup_s=float(parameter_values.get("service_setup_time", 10.0)),
        rendezvous_radius_m=float(parameter_values.get("rendezvous_radius", 5.0)),
        max_candidate_slots=int(environment.get("max_candidate_slots", 4)),
        support_mode=intervention.support_mode,
        initial_vehicle_nodes={"vehicle-1": support_node},
        request_release_steps=request_release_steps,
        endurance_prediction_enabled="remove_endurance_prediction" not in ablations,
        joint_demand_rendezvous_enabled="remove_joint_demand_rendezvous" not in ablations,
    )
    bundle = ScenarioBundle(
        scale_id=scale_id,
        seed=int(seed),
        max_steps=int(scale["max_steps"]),
        grid_shape=(rows, cols),
        resources=resources,
        road_graph=road_graph,
        adapter=adapter,
        initial_density=density,
        pest_density=density.copy(),
        pest_dynamics=pest_dynamics,
        pesticide_field=pesticide_field,
        candidate_mapping={},
        episode_id=f"{requested_id}-seed-{int(seed)}",
        scenario_id=requested_id,
        success_reduction_threshold=float(environment.get("termination", {}).get("success_reduction_threshold", 0.85)),
        physical_extent_m=extent,
        cell_size_m=cell_size_m,
        parameter_status=str(config.parameters.get("status", "provisional")),
        intervention_id=intervention.condition_id,
        intervention_hash=intervention.identity_hash,
        support_mode=intervention.support_mode,
        ablation_flags=tuple(sorted(ablations)),
        include_air_ground_observation="remove_air_ground_observation" not in ablations,
        scenario_source_kind=config.scenario_source_kind or "synthetic_smoke",
        dynamics_kind=config.scenario_dynamics_kind or "smoke_local_removal",
        source_metadata_hash=config.source_metadata_hash or str(road_metadata.get("source_sha256", "")),
        config_hash=config_identity(config),
        simulation_profile_sha256=simulation_profile.sha256,
        simulation_preflight_ready=simulation_preflight.ready,
        simulation_preflight_errors=tuple(issue.to_dict() for issue in simulation_preflight.errors),
        simulation_preflight_warnings=tuple(issue.to_dict() for issue in simulation_preflight.warnings),
    )
    bundle.reset()
    return bundle


def _road_cells(shape: tuple[int, int], hotspot_separation: object | None) -> list[tuple[int, int]]:
    rows, cols = shape
    if hotspot_separation is None:
        return [(row, col) for row in range(rows) for col in range(cols)]
    center_row, center_col = rows // 2, cols // 2
    return sorted(
        {(center_row, col) for col in range(cols)}
        | {(row, center_col) for row in range(rows)}
    )


def _density_field(
    rng: np.random.Generator,
    shape: tuple[int, int],
    dispersion: object | None,
    *,
    road_cells: list[tuple[int, int]],
    hotspot_separation: object | None,
) -> np.ndarray:
    if hotspot_separation is not None:
        return _hotspot_distance_field(rng, shape, road_cells, str(hotspot_separation))
    if dispersion is None:
        return rng.uniform(0.6, 1.0, size=shape).astype(float)
    rows, cols = shape
    row_axis, col_axis = np.mgrid[0:rows, 0:cols]
    counts = {"clustered": 1, "moderate": 2, "dispersed": 4}
    if str(dispersion) not in counts:
        raise ValueError("demand_dispersion must be clustered, moderate or dispersed")
    field = np.full(shape, 0.35, dtype=float)
    sigma = max(1.0, min(rows, cols) / (3.0 + counts[str(dispersion)]))
    for _ in range(counts[str(dispersion)]):
        center_row = int(rng.integers(0, rows))
        center_col = int(rng.integers(0, cols))
        field += 0.65 * np.exp(
            -((row_axis - center_row) ** 2 + (col_axis - center_col) ** 2) / (2.0 * sigma**2)
        )
    return np.clip(field, 0.0, 1.0)


def _hotspot_distance_field(
    rng: np.random.Generator,
    shape: tuple[int, int],
    road_cells: list[tuple[int, int]],
    level: str,
) -> np.ndarray:
    rows, cols = shape
    row_axis, col_axis = np.mgrid[0:rows, 0:cols]
    road = np.asarray(road_cells, dtype=float)
    grid = np.column_stack((row_axis.reshape(-1), col_axis.reshape(-1))).astype(float)
    distances = np.sqrt(((grid[:, None, :] - road[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    max_distance = float(distances.max())
    target = {"near": 0.0, "medium": max_distance * 0.5, "far": max_distance}[level]
    error = np.abs(distances - target)
    choices = np.flatnonzero(error <= error.min() + 1e-12)
    center_index = int(choices[int(rng.integers(0, len(choices)))])
    center_row, center_col = grid[center_index]
    sigma = max(0.75, min(rows, cols) / 14.0)
    field = 0.01 + 0.99 * np.exp(
        -((row_axis - center_row) ** 2 + (col_axis - center_col) ** 2) / (2.0 * sigma**2)
    )
    return np.clip(field, 0.0, 1.0)


def _request_release_steps(
    uav_ids: tuple[str, ...], level: object | None
) -> dict[str, int]:
    if level is None or str(level) == "high":
        offsets = [1] * len(uav_ids)
    elif str(level) == "medium":
        offsets = [1 + index // 2 for index in range(len(uav_ids))]
    elif str(level) == "low":
        offsets = [1 + index for index in range(len(uav_ids))]
    else:
        raise ValueError("simultaneous_requests must be low, medium or high")
    return dict(zip(sorted(uav_ids), offsets))


def _apply_connected_road_blockage(graph: RoadGraph, fraction: float, seed: int) -> None:
    edges = sorted(
        (left, right, weight)
        for left, neighbours in graph.adjacency.items()
        for right, weight in neighbours.items()
        if left < right
    )
    rng = np.random.default_rng(int(seed) + 7919)
    order = rng.permutation(len(edges)).tolist()
    target = int(round(len(edges) * fraction))
    removed = 0
    root = min(graph.nodes)
    for index in order:
        if removed >= target:
            break
        left, right, weight = edges[index]
        graph.adjacency[left].pop(right, None)
        graph.adjacency[right].pop(left, None)
        if len(graph.component(root)) == len(graph.nodes):
            removed += 1
        else:
            graph.adjacency[left][right] = weight
            graph.adjacency[right][left] = weight
    if removed < target:
        raise ValueError("requested road blockage cannot preserve graph connectivity")


__all__ = [
    "DecisionSnapshot",
    "StepSnapshot",
    "ScenarioBundle",
    "build_synthetic_scenario",
]
