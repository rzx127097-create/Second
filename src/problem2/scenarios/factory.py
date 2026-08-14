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

from problem2.config import load_config_bundle
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
from problem2.road.graph import RoadGraph
from problem2.section4_2.adapter import HeterogeneousDecisionAdapter


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
    candidate_mapping: dict[str, Any]
    episode_id: str
    scenario_id: str
    success_reduction_threshold: float = 0.85
    physical_extent_m: tuple[float, float] = (1.0, 1.0)
    cell_size_m: tuple[float, float] = (1.0, 1.0)
    normalization_version: str = NORMALIZATION_VERSION
    parameter_status: str = "provisional"
    step_count: int = 0
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
        self.step_count = 0
        self.adapter.reset(seed=self.seed)
        self._install_candidate_routes()
        return self._snapshot(events=())

    def assert_formal_ready(self) -> None:
        """Guard formal evidence generation until engineering values are verified."""

        if self.parameter_status != "verified":
            raise ValueError(
                "scenario parameters are provisional; formal training/evaluation is blocked"
            )

    def step(self, actions: Mapping[str, str]) -> StepSnapshot:
        """Apply one validated joint action and update the pest field."""

        if self.step_count >= self.max_steps:
            raise RuntimeError("scenario horizon has been exhausted; call reset")
        previous_mean = float(np.mean(self.pest_density))
        state = self.adapter.step(actions)
        self.step_count += 1

        # Provisional smoke dynamics: each spray event removes a bounded local
        # amount.  The physical pesticide ledger remains owned by Resources.
        for event in state.events:
            if event.get("event_type") != "spray_applied":
                continue
            uav_id = str(event.get("uav_id"))
            position = self.adapter.uav_positions[uav_id]
            amount = float(event.get("amount_l", 0.0))
            row, col = position
            self.pest_density[row, col] = max(
                0.0, self.pest_density[row, col] - min(0.25, amount)
            )
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
        info = {
            "scale_id": self.scale_id,
            "seed": self.seed,
            "step": self.step_count,
            "pesticide_total_l": self.resources.total_pesticide_l,
            "pest_mean": current_mean,
            "reduction_rate": reduction,
            "termination_reason": "success" if terminated else ("max_steps" if truncated else None),
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

    def _install_candidate_routes(self) -> None:
        start = self.adapter.executors[next(iter(self.adapter.vehicle_slots))].current_node
        neighbours = [node for node, _ in self.road_graph.neighbors(start)]
        routes: dict[str, tuple[str, ...]] = {}
        for index, node in enumerate(neighbours[:4]):
            routes[f"slot-{index}"] = (start, node)
        self.candidate_mapping = {
            vehicle_id: tuple(sorted(routes.items()))
            for vehicle_id in self.adapter.vehicle_slots
        }
        for vehicle_id in self.adapter.vehicle_slots:
            self.adapter.set_candidate_routes(vehicle_id, routes)

    def _snapshot(self, *, events: tuple[dict[str, object], ...]) -> DecisionSnapshot:
        vehicle_positions = {
            vehicle_id: self.road_graph.nodes[node]
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
            service_locked=self.service.locked_uav_id is not None,
            service_phase=self.service.phase,
            active_request_id=self.service.request_id,
            max_request_slots=self.adapter.max_candidate_slots,
            step=self.step_count,
            max_steps=self.max_steps,
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


def build_synthetic_scenario(
    scale_id: str,
    seed: int,
    *,
    config_dir: str | Path,
    scenario_id: str | None = None,
) -> ScenarioBundle:
    """Build one deterministic rectangular provisional scenario.

    Values come from the provisional parameter registry and are suitable only
    for interface/smoke tests until the project parameter status is verified.
    """

    config = load_config_bundle(config_dir)
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
    capacity = float(parameters["uav_onboard_pesticide"]["value"])
    spray_flow = float(parameters["uav_spray_flow"]["value"])
    vehicle_inventory = float(parameters["vehicle_inventory"]["value"])
    transfer_rate = float(parameters["vehicle_transfer_rate"]["value"])
    rng = np.random.default_rng(int(seed))
    density = rng.uniform(0.6, 1.0, size=(rows, cols)).astype(float)

    uavs = {
        f"uav-{index + 1}": UAVState(
            f"uav-{index + 1}", capacity, capacity, spray_flow
        )
        for index in range(uav_count)
    }
    vehicles = {
        "vehicle-1": VehicleState(
            "vehicle-1", vehicle_inventory, vehicle_inventory, transfer_rate, vehicle_inventory
        )
    }
    resources = PesticideResources(uavs=uavs, vehicles=vehicles)
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    extent = tuple(float(value) for value in config.scales.get("physical_extent_m", [cols, rows]))
    cell_size_m = (extent[1] / rows, extent[0] / cols)
    road_graph = RoadGraph.from_grid(cells, cell_size_m=cell_size_m)
    # Scenario registry seeds also freeze a small, deterministic road-condition
    # variant.  Connectivity and metric units remain unchanged, while sealed
    # scenarios no longer differ only by an identifier label.
    road_factor = 1.0 + 0.005 * (int(seed) % 7)
    for node, neighbours in road_graph.adjacency.items():
        for neighbour in list(neighbours):
            neighbours[neighbour] *= road_factor
    environment = config.environment
    parameter_values = {key: value.get("value") for key, value in parameters.items() if isinstance(value, dict)}
    adapter = HeterogeneousDecisionAdapter(
        resources,
        road_graph,
        uav_slots=tuple(uavs),
        vehicle_slots=tuple(vehicles),
        vehicle_speed_mps=float(parameter_values.get("vehicle_speed", 1.0)),
        decision_dt_s=float(config.scales.get("decision_dt_s", 1.0)),
        uav_grid_shape=(rows, cols),
        request_threshold_ratio=float(environment.get("request_threshold_ratio", 0.20)),
        service_setup_s=float(parameter_values.get("service_setup_time", 10.0)),
        rendezvous_radius_m=float(parameter_values.get("rendezvous_radius", 5.0)),
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
        candidate_mapping={},
        episode_id=f"{requested_id}-seed-{int(seed)}",
        scenario_id=requested_id,
        success_reduction_threshold=float(environment.get("termination", {}).get("success_reduction_threshold", 0.85)),
        physical_extent_m=extent,
        cell_size_m=cell_size_m,
        parameter_status=str(config.parameters.get("status", "provisional")),
    )
    bundle.reset()
    return bundle


__all__ = [
    "DecisionSnapshot",
    "StepSnapshot",
    "ScenarioBundle",
    "build_synthetic_scenario",
]
