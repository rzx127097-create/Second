"""Deterministic air-ground cooperative spraying environment core."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from problem2.domain.events import ResourceEvent
from problem2.domain.requests import RequestManager, RequestStatus
from problem2.domain.resources import PesticideResources
from problem2.field.pesticide_field import PesticideField
from problem2.field.pest_dynamics import PestDynamics
from .movement import legal_uav_position, move_vehicle_towards
from .service_state_machine import ServicePhase, ServiceStateMachine
from .transition import event_dict, reduction_rate


@dataclass
class EnvironmentConfig:
    decision_dt_s: float = 1.0
    max_steps: int = 100
    success_reduction_threshold: float = 0.85
    request_threshold_ratio: float = 0.20
    service_setup_s: float = 10.0
    grid_shape: tuple[int, int] = (10, 20)
    pest_growth_rate_s: float = 0.0
    pesticide_decay_rate_s: float = 0.0
    pesticide_efficacy_per_l: float = 1.0
    pest_mortality_per_exposure: float = 0.02
    reward_spray_cost: float = 0.01
    reward_invalid_cost: float = 0.02


class AirGroundEnv:
    """Minimal deterministic environment following the frozen Section 4.2 order."""

    def __init__(self, pest_density: np.ndarray, resources: PesticideResources, config: EnvironmentConfig | None = None):
        self.config = config or EnvironmentConfig(grid_shape=tuple(pest_density.shape))
        self._initial_density = np.asarray(pest_density, dtype=float).copy()
        if self._initial_density.shape != self.config.grid_shape:
            raise ValueError("grid_shape must match pest_density")
        self._initial_uavs = {key: vars(value).copy() for key, value in resources.uavs.items()}
        self._initial_vehicles = {key: vars(value).copy() for key, value in resources.vehicles.items()}
        self.resources = resources
        self._initial_total_l = resources.total_pesticide_l
        self.request_manager = RequestManager()
        self.service = ServiceStateMachine()
        self.pest_dynamics = PestDynamics(
            growth_rate_s=self.config.pest_growth_rate_s,
            mortality_per_exposure=self.config.pest_mortality_per_exposure,
        )
        self.step_count = 0
        self.pest_density = self._initial_density.copy()
        self.pesticide = PesticideField(
            np.zeros_like(self.pest_density),
            decay_rate_s=self.config.pesticide_decay_rate_s,
            efficacy_per_l=self.config.pesticide_efficacy_per_l,
        )
        self.uav_positions: dict[str, tuple[int, int]] = {}
        self.vehicle_positions: dict[str, tuple[int, int]] = {}
        self._last_events: list[dict[str, object]] = []

    def reset(self, seed: int | None = None) -> dict[str, dict[str, object]]:
        if seed is not None:
            np.random.default_rng(seed)  # explicit seed hook; scenarios remain deterministic
        for key, state in self._initial_uavs.items():
            self.resources.uavs[key].onboard_l = state["onboard_l"]
        for key, state in self._initial_vehicles.items():
            self.resources.vehicles[key].inventory_l = state["inventory_l"]
        self.resources._initial_total_l = self._initial_total_l
        self.resources._cumulative_sprayed_l = 0.0
        self.request_manager = RequestManager()
        self.service = ServiceStateMachine()
        self.step_count = 0
        self.pest_density = self._initial_density.copy()
        self.pesticide.active.fill(0.0)
        self.uav_positions = {uav_id: (0, index) for index, uav_id in enumerate(self.resources.uavs)}
        self.vehicle_positions = {vehicle_id: (0, 0) for vehicle_id in self.resources.vehicles}
        self._last_events = []
        return self._observations()

    def step(self, actions: dict[str, str]):
        events: list[dict[str, object]] = []
        self.step_count += 1
        self._last_events = events
        active_request = self.request_manager.get(self.service.request_id) if self.service.request_id else None
        # 1) Sampled actions are already supplied by the caller; apply legal movement.
        for uav_id, position in list(self.uav_positions.items()):
            action = actions.get(uav_id, "hold")
            locked = active_request is not None and active_request.uav_id == uav_id
            new_position = legal_uav_position(position, action, self.config.grid_shape, locked=locked)
            self.uav_positions[uav_id] = new_position
            if action == "spray" and not locked:
                sprayed = self.resources.spray_step(uav_id, self.config.decision_dt_s)
                self.pesticide.deposit(new_position, sprayed.amount_l)
                events.append(event_dict(ResourceEvent("spray", self.step_count, uav_id=uav_id, amount_l=sprayed.amount_l)))

        # 2) Move the road vehicle one grid edge toward its active rendezvous hook.
        for vehicle_id, position in list(self.vehicle_positions.items()):
            target = self.uav_positions.get(active_request.uav_id) if active_request else None
            if target is not None and self.service.phase is ServicePhase.PREPARING:
                self.vehicle_positions[vehicle_id] = move_vehicle_towards(position, target, self.config.grid_shape)

        # 3) Generate at most one request per UAV after resource use.
        for uav_id, state in self.resources.uavs.items():
            if state.onboard_l <= state.capacity_l * self.config.request_threshold_ratio + 1e-12:
                request = self.request_manager.create_request(
                    uav_id, state.capacity_l - state.onboard_l, self.step_count
                )
                if request.created_step == self.step_count:
                    events.append(event_dict(ResourceEvent("request_created", self.step_count, uav_id=uav_id, request_id=request.request_id, amount_l=request.remaining_l)))

        # 4) Reserve and advance the explicit service state machine.
        vehicle_action = next((actions.get(key) for key in self.vehicle_positions), "hold")
        reserved_this_step = False
        if vehicle_action == "next_request_slot" and self.service.phase is ServicePhase.IDLE:
            reserved = self.service.reserve(self.request_manager, next(iter(self.vehicle_positions)), self.step_count, self.config.service_setup_s)
            if reserved:
                reserved_this_step = True
                events.append(event_dict(ResourceEvent("request_reserved", self.step_count, vehicle_id=next(iter(self.vehicle_positions)), uav_id=reserved.uav_id, request_id=reserved.request_id)))
        transfer_l = 0.0
        # A reservation is a discrete event.  Preparation begins at the next
        # decision boundary, so the same step cannot also transfer pesticide.
        if not reserved_this_step:
            transfer_l = self.service.tick(
                self.request_manager,
                self.resources,
                next(iter(self.vehicle_positions)),
                self.config.decision_dt_s,
                self.step_count,
            )
        if transfer_l > 0:
            events.append(event_dict(ResourceEvent("pesticide_transfer", self.step_count, vehicle_id=next(iter(self.vehicle_positions)), uav_id=active_request.uav_id if active_request else None, request_id=active_request.request_id if active_request else None, amount_l=transfer_l)))

        # 5) Update pesticide and pest dynamics, then compute reward and termination.
        self.pesticide.step(self.config.decision_dt_s)
        previous_mean = float(np.mean(self.pest_density))
        self.pest_density = self.pest_dynamics.step(self.pest_density, self.pesticide, self.config.decision_dt_s)
        current_mean = float(np.mean(self.pest_density))
        events.append(event_dict(ResourceEvent("field_update", self.step_count, amount_l=max(0.0, previous_mean - current_mean))))
        self.resources.assert_conservation()
        reduction = reduction_rate(float(np.mean(self._initial_density)), current_mean)
        reward = (previous_mean - current_mean) - self.config.reward_spray_cost * sum(
            event["amount_l"] for event in events if event["event_type"] == "spray"
        )
        terminated = reduction >= self.config.success_reduction_threshold
        truncated = self.step_count >= self.config.max_steps and not terminated
        reason = "success" if terminated else ("max_steps" if truncated else None)
        return self._observations(), float(reward), terminated, truncated, {
            "step": self.step_count,
            "events": events,
            "service_phase": self.service.phase.value,
            "service_transfer_l": transfer_l,
            "reduction_rate": reduction,
            "termination_reason": reason,
        }

    def _observations(self) -> dict[str, dict[str, object]]:
        observations: dict[str, dict[str, object]] = {}
        for uav_id, state in self.resources.uavs.items():
            observations[uav_id] = {
                "role": "uav",
                "position": self.uav_positions.get(uav_id, (0, 0)),
                "onboard_l": state.onboard_l,
                "pest_density": self.pest_density.copy(),
                "service_locked": self.service.locked_uav_id == uav_id,
            }
        for vehicle_id, state in self.resources.vehicles.items():
            observations[vehicle_id] = {
                "role": "vehicle",
                "position": self.vehicle_positions.get(vehicle_id, (0, 0)),
                "inventory_l": state.inventory_l,
                "service_phase": self.service.phase.value,
                "active_request_id": self.service.request_id,
            }
        return observations
