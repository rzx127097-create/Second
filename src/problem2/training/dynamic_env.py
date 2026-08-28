"""Physical Problem-2 environment coupled to the dynamic pest ecology."""

from __future__ import annotations

from dataclasses import replace
import math
from numbers import Real
from typing import Any, Mapping

import numpy as np

from problem2.domain import (
    EpisodeState,
    Event,
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleMode,
    VehicleState,
)
from problem2.ecology.config import DYNAMIC_ECOLOGY_VERSION
from problem2.ecology.pesticide import AcceptedSpray
from problem2.ecology.system import DynamicEcologySystem
from problem2.resources.ledger import ResourceLedger


STATE_SCHEMA_VERSION = "problem2.dynamic-pest-environment.v1"


def _detached_view(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _detached_view(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_detached_view(item) for item in value)
    if isinstance(value, list):
        return [_detached_view(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.copy()
    return value


def _metrics_to_state(metrics: Any) -> dict[str, object]:
    return {
        "tolerance": metrics.tolerance,
        "created": dict(metrics._created),
        "requested": dict(metrics._requested),
        "started": dict(metrics._started),
        "rendezvous_distance_m": metrics._rendezvous_distance_m,
        "vehicle_service_travel_m": metrics._vehicle_service_travel_m,
        "pesticide_disabled_steps": metrics._pesticide_disabled_steps,
        "return_steps": metrics._return_steps,
        "effective_spray_steps": metrics._effective_spray_steps,
        "service_completed_count": metrics._service_completed_count,
        "partial_service_count": metrics._partial_service_count,
        "zero_transfer_count": metrics._zero_transfer_count,
        "transferred_pesticide_l": metrics._transferred_pesticide_l,
        "decision_runtime_s": metrics._decision_runtime_s,
        "initial_total_l": metrics._initial_total_l,
    }


def _load_metrics_state(metrics: Any, state: Mapping[str, object]) -> None:
    expected = {
        "tolerance", "created", "requested", "started", "rendezvous_distance_m",
        "vehicle_service_travel_m", "pesticide_disabled_steps", "return_steps",
        "effective_spray_steps", "service_completed_count", "partial_service_count",
        "zero_transfer_count", "transferred_pesticide_l", "decision_runtime_s",
        "initial_total_l",
    }
    if set(state) != expected:
        raise ValueError("physical metric state is incomplete")
    if float(state["tolerance"]) != float(metrics.tolerance) or float(state["initial_total_l"]) != float(metrics._initial_total_l):
        raise ValueError("physical metric identity drifted")
    metrics._created = {str(key): int(value) for key, value in dict(state["created"]).items()}
    metrics._requested = {str(key): float(value) for key, value in dict(state["requested"]).items()}
    metrics._started = {str(key): int(value) for key, value in dict(state["started"]).items()}
    for name in expected - {"tolerance", "created", "requested", "started", "initial_total_l"}:
        setattr(metrics, "_" + name, float(state[name]) if name in {
            "rendezvous_distance_m", "vehicle_service_travel_m", "transferred_pesticide_l", "decision_runtime_s"
        } else int(state[name]))


def _event_to_state(event: Event) -> dict[str, object]:
    return {
        "step": event.step,
        "phase": event.phase,
        "kind": event.kind,
        "entity_id": event.entity_id,
        "payload": [[key, value] for key, value in event.payload],
    }


def _event_from_state(state: Mapping[str, object]) -> Event:
    if set(state) != {"step", "phase", "kind", "entity_id", "payload"}:
        raise ValueError("physical event state is incomplete")
    payload = state["payload"]
    if not isinstance(payload, list):
        raise ValueError("physical event payload is invalid")
    return Event(
        int(state["step"]),
        str(state["phase"]),
        str(state["kind"]),
        str(state["entity_id"]),
        tuple((str(item[0]), item[1]) for item in payload),
    )


def _uav_to_state(uav: UavState) -> dict[str, object]:
    return {
        "uav_id": uav.uav_id,
        "x_m": uav.x_m,
        "y_m": uav.y_m,
        "pesticide_l": uav.pesticide_l,
        "active_request_id": uav.active_request_id,
        "service_locked": uav.service_locked,
    }


def _uav_from_state(state: Mapping[str, object]) -> UavState:
    return UavState(**dict(state))  # type: ignore[arg-type]


def _vehicle_to_state(vehicle: VehicleState) -> dict[str, object]:
    return {
        "vehicle_id": vehicle.vehicle_id,
        "current_node": vehicle.current_node,
        "x_m": vehicle.x_m,
        "y_m": vehicle.y_m,
        "inventory_l": vehicle.inventory_l,
        "inventory_depleted": vehicle.inventory_depleted,
        "mode": vehicle.mode.value,
        "target_node": vehicle.target_node,
        "direction": None if vehicle.direction is None else int(vehicle.direction),
        "edge_progress_m": vehicle.edge_progress_m,
        "route_distance_m": vehicle.route_distance_m,
        "active_request_id": vehicle.active_request_id,
        "service_steps_elapsed": vehicle.service_steps_elapsed,
        "service_steps_required": vehicle.service_steps_required,
        "planned_transfer_l": vehicle.planned_transfer_l,
    }


def _vehicle_from_state(state: Mapping[str, object]) -> VehicleState:
    from problem2.domain import Action

    values = dict(state)
    values["mode"] = VehicleMode(str(values["mode"]))
    values["direction"] = None if values["direction"] is None else Action(int(values["direction"]))
    return VehicleState(**values)  # type: ignore[arg-type]


def _request_to_state(request: ServiceRequest) -> dict[str, object]:
    return {
        "request_id": request.request_id,
        "uav_id": request.uav_id,
        "created_step": request.created_step,
        "requested_l": request.requested_l,
        "status": request.status.value,
        "reserved_vehicle_id": request.reserved_vehicle_id,
    }


def _request_from_state(state: Mapping[str, object]) -> ServiceRequest:
    values = dict(state)
    values["status"] = RequestStatus(str(values["status"]))
    return ServiceRequest(**values)  # type: ignore[arg-type]


def _ledger_to_state(ledger: ResourceLedger) -> dict[str, object]:
    return {
        "initial_total_l": ledger.initial_total_l,
        "cumulative_sprayed_l": ledger.cumulative_sprayed_l,
        "cumulative_transferred_l": ledger.cumulative_transferred_l,
        "events": [_event_to_state(event) for event in ledger.events],
    }


def _ledger_from_state(state: Mapping[str, object]) -> ResourceLedger:
    return ResourceLedger(
        initial_total_l=float(state["initial_total_l"]),
        cumulative_sprayed_l=float(state["cumulative_sprayed_l"]),
        cumulative_transferred_l=float(state["cumulative_transferred_l"]),
        events=tuple(_event_from_state(item) for item in state["events"]),  # type: ignore[arg-type]
    )


def _episode_state_to_state(state: EpisodeState) -> dict[str, object]:
    return {
        "step": state.step,
        "uavs": [_uav_to_state(uav) for uav in state.uavs],
        "vehicle": _vehicle_to_state(state.vehicle),
        "requests": [_request_to_state(request) for request in state.requests],
        "ledger": _ledger_to_state(state.ledger),
        "last_step_events": [_event_to_state(event) for event in state.last_step_events],
        "terminated": state.terminated,
    }


def _episode_state_from_state(state: Mapping[str, object]) -> EpisodeState:
    return EpisodeState(
        step=int(state["step"]),
        uavs=tuple(_uav_from_state(item) for item in state["uavs"]),  # type: ignore[arg-type]
        vehicle=_vehicle_from_state(state["vehicle"]),  # type: ignore[arg-type]
        requests=tuple(_request_from_state(item) for item in state["requests"]),  # type: ignore[arg-type]
        ledger=_ledger_from_state(state["ledger"]),  # type: ignore[arg-type]
        last_step_events=tuple(_event_from_state(item) for item in state["last_step_events"]),  # type: ignore[arg-type]
        terminated=bool(state["terminated"]),
    )


class DynamicPestEnvironment:
    """Couple accepted physical spray events to one ecology decision step."""

    ecology_mode = "dynamic"
    primary_eligible = True

    def __init__(
        self,
        physical_environment: Any,
        ecology: DynamicEcologySystem,
        *,
        partition: str,
        source_provenance: Mapping[str, Any],
    ) -> None:
        if not isinstance(ecology, DynamicEcologySystem):
            raise TypeError("ecology must be a DynamicEcologySystem")
        if partition != ecology.scenario.partition:
            raise ValueError("environment partition must match ecology scenario")
        if int(physical_environment.scenario_id) != ecology.scenario.scenario_id:
            raise ValueError("physical and ecology scenario IDs must match")
        self.physical = physical_environment
        self.ecology = ecology
        self.partition = partition
        self.source_provenance = dict(source_provenance)
        self.source_provenance.update(
            {
                "ecology_version": ecology.config.version,
                "ecology_implementation_version": DYNAMIC_ECOLOGY_VERSION,
                "ecology_config_sha256": ecology.config.contract_sha256,
                "ecology_scenario_sha256": ecology.scenario.scenario_sha256,
                "ecology_source_commit": ecology.scenario.source_commit,
            }
        )
        self.replenished_resource = "pesticide"
        self.battery_replenishment_enabled = False
        self._scenario_id = ecology.scenario.scenario_id
        self._scenario_sha256 = ecology.scenario.scenario_sha256
        self._reference_spray_l = float(ecology.state_dict()["reference_spray_l"])
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self._last_sampled_actions: dict[str, np.ndarray] = {}
        self._current_view: dict[str, Any] | None = None
        self.ecology_global_context_before = ecology.global_summary()
        self._set_diagnostics()

    @property
    def state(self) -> EpisodeState:
        return self.physical.state

    @property
    def scenario_id(self) -> int:
        return self._scenario_id

    @property
    def initial_prey(self) -> np.ndarray:
        return self.ecology.scenario.initial_prey.copy()

    @property
    def prey(self) -> np.ndarray:
        return self.ecology.prey

    @property
    def initial_predator(self) -> np.ndarray:
        return self.ecology.scenario.initial_predator.copy()

    @property
    def predator(self) -> np.ndarray:
        return self.ecology.predator

    @property
    def initial_pest(self) -> np.ndarray:
        """Compatibility alias for historical diagnostic callers."""

        return self.initial_prey

    @property
    def pest(self) -> np.ndarray:
        """Compatibility alias for historical diagnostic callers."""

        return self.prey

    @property
    def field_summary(self) -> tuple[float, ...]:
        return tuple(self.physical.field_summary)

    def _set_diagnostics(self) -> None:
        prey = self.prey
        initial = self.initial_prey
        field_summary = (
            float(np.mean(prey)),
            float(np.max(prey)),
            float(np.min(prey)),
            float(np.count_nonzero(prey < initial) / prey.size),
        )
        self.physical.initial_total_pest = float(np.sum(self.initial_prey))
        self.physical.final_total_pest = float(np.sum(self.prey))
        self.physical.field_summary = field_summary
        self.physical.ecology_global_context = self.ecology.global_summary()
        self.physical.uav_ecology_context = {
            uav.uav_id: self.ecology.local_context(*self._cell_for_position(uav.x_m, uav.y_m))
            for uav in self.physical.state.uavs
        }

    def _cell_for_position(self, x_m: float, y_m: float) -> tuple[int, int]:
        x0, y0, x1, y1 = self.physical.graph.aoi_bounds_m
        x_fraction = 0.0 if x1 <= x0 else (x_m - x0) / (x1 - x0)
        y_fraction = 0.0 if y1 <= y0 else (y_m - y0) / (y1 - y0)
        width = self.ecology.shape[1]
        height = self.ecology.shape[0]
        col = min(width - 1, max(0, int(round(x_fraction * (width - 1)))))
        row = min(height - 1, max(0, int(round(y_fraction * (height - 1)))))
        return row, col

    def _cell_for_event(self, event: Event) -> tuple[int, int]:
        values = dict(event.payload)
        x_m = values.get("x_m")
        y_m = values.get("y_m")
        if isinstance(x_m, Real) and isinstance(y_m, Real) and math.isfinite(float(x_m)) and math.isfinite(float(y_m)):
            return self._cell_for_position(float(x_m), float(y_m))
        uav = next(item for item in self.physical.state.uavs if item.uav_id == event.entity_id)
        return self._cell_for_position(uav.x_m, uav.y_m)

    def _accepted_sprays(self, events: tuple[Event, ...]) -> tuple[AcceptedSpray, ...]:
        accepted: list[AcceptedSpray] = []
        for event in events:
            if event.kind != "spray":
                continue
            delta_l = dict(event.payload).get("delta_l")
            if isinstance(delta_l, bool) or not isinstance(delta_l, Real) or not math.isfinite(float(delta_l)) or float(delta_l) <= 0.0:
                continue
            row, col = self._cell_for_event(event)
            accepted.append(AcceptedSpray(row, col, float(delta_l)))
        return tuple(accepted)

    def _decorate_view(self, physical_view: Mapping[str, Any], transition: Any, before_total: float) -> dict[str, Any]:
        view = self.physical._make_view(events=tuple(physical_view.get("events", ())))
        if self._last_sampled_actions:
            view["sampled_actions"] = {role: values.copy() for role, values in self._last_sampled_actions.items()}
        view.update(
            {
                "pest_total_before": before_total,
                "pest_total": float(transition.prey_after_total),
                "initial_total_pest": float(np.sum(self.initial_prey)),
                "final_total_pest": float(transition.prey_after_total),
                "team_reward": (before_total - float(transition.prey_after_total)) / float(np.sum(self.initial_prey)),
                "metric_source": "dynamic_ecology_environment",
                "ecology_version": self.ecology.config.version,
                "ecology_config_sha256": self.ecology.config.contract_sha256,
                "ecology_scenario_sha256": self.ecology.scenario.scenario_sha256,
                "ecology_global_context": self.ecology.global_summary(),
                "ecology_global_context_before": self.ecology_global_context_before,
                "predator_total_before": transition.predator_before_total,
                "predator_total": transition.predator_after_total,
                "initial_predator_total": float(np.sum(self.initial_predator)),
                "concentration_mean": float(np.mean(self.ecology.concentration)),
                "concentration_max": float(np.max(self.ecology.concentration)),
                "wind_direction": float(math.atan2(transition.wind_vector[1], transition.wind_vector[0])),
                "wind_strength": float(math.hypot(*transition.wind_vector)),
                "dynamic_step_count": transition.step_count,
                "ecology_dynamic_step_count": transition.step_count,
                "cumulative_deposited_effect": self.ecology.deposited_effect,
                "spray_action_count": self.spray_action_count,
                "sprayed_pesticide_l": self.sprayed_pesticide_l,
            }
        )
        self._set_diagnostics()
        self._current_view = view
        return view

    def reset(self, *, scenario_id: int | None = None) -> dict[str, Any]:
        requested = self._scenario_id if scenario_id is None else scenario_id
        if requested != self._scenario_id:
            raise ValueError("wrapped scenario identity is immutable")
        reset_ecology = DynamicEcologySystem.from_scenario(
            self.ecology.scenario, self.ecology.config, self._reference_spray_l
        )
        self.ecology.load_state_dict(reset_ecology.state_dict())
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self._last_sampled_actions = {}
        self.physical.reset(scenario_id=requested)
        self._set_diagnostics()
        view = self.physical._make_view()
        self._current_view = view
        return view

    def step(self, action_result: Any, **kwargs: Any) -> dict[str, Any]:
        if self.physical.scenario_id != self._scenario_id:
            raise ValueError("wrapped scenario identity changed")
        before_total = float(np.sum(self.prey))
        self.ecology_global_context_before = self.ecology.global_summary()
        physical_view = self.physical.step(action_result, **kwargs)
        events = tuple(physical_view.get("events", ()))
        accepted = self._accepted_sprays(events)
        self.spray_action_count += len(accepted)
        self.sprayed_pesticide_l += math.fsum(spray.delta_l for spray in accepted)
        self._last_sampled_actions = {
            role: np.asarray(values).copy() for role, values in physical_view.get("sampled_actions", {}).items()
        }
        transition = self.ecology.step(accepted)
        self._set_diagnostics()
        self._current_view = self._decorate_view(physical_view, transition, before_total)
        return self._current_view

    def state_dict(self) -> dict[str, object]:
        dispatch = self.physical._dispatch
        dispatch_state = None if dispatch is None else {
            "request_id": dispatch.request_id,
            "sampled_slot": dispatch.sampled_slot,
            "candidate_mapping": list(dispatch.candidate_mapping),
            "selected_service_node": dispatch.selected_service_node,
            "route_length_m": dispatch.route_length_m,
        }
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "partition": self.partition,
            "scenario_id": self._scenario_id,
            "scenario_sha256": self._scenario_sha256,
            "scale_id": self.ecology.scenario.scale_id,
            "ecology_config_sha256": self.ecology.config.contract_sha256,
            "ecology": self.ecology.state_dict(),
            "physical_state": _episode_state_to_state(self.physical.state),
            "physical_metrics": _metrics_to_state(self.physical._metrics),
            "dispatch": dispatch_state,
            "candidate_nodes": {key: list(value) for key, value in self.physical._candidate_nodes.items()},
            "spray_action_count": self.spray_action_count,
            "sprayed_pesticide_l": self.sprayed_pesticide_l,
            "last_sampled_actions": {role: values.copy() for role, values in self._last_sampled_actions.items()},
            "ecology_global_context_before": self.ecology_global_context_before,
            "current_view": _detached_view(self._current_view),
        }

    def load_state_dict(self, state: Mapping[str, object]) -> None:
        expected = {
            "schema_version", "partition", "scenario_id", "scenario_sha256", "scale_id",
            "ecology_config_sha256", "ecology", "physical_state", "physical_metrics", "dispatch", "candidate_nodes",
            "spray_action_count", "sprayed_pesticide_l", "last_sampled_actions", "ecology_global_context_before", "current_view",
        }
        if not isinstance(state, Mapping) or set(state) != expected:
            raise ValueError("dynamic environment state keys are incomplete")
        if (
            state["schema_version"] != STATE_SCHEMA_VERSION
            or state["partition"] != self.partition
            or state["scenario_id"] != self._scenario_id
            or state["scenario_sha256"] != self._scenario_sha256
            or state["scale_id"] != self.ecology.scenario.scale_id
            or state["ecology_config_sha256"] != self.ecology.config.contract_sha256
        ):
            raise ValueError("dynamic environment scenario identity drifted")
        physical_state = _episode_state_from_state(state["physical_state"])  # type: ignore[arg-type]
        if physical_state.step > self.physical.max_steps:
            raise ValueError("physical state step exceeds environment horizon")
        self.ecology.load_state_dict(state["ecology"])  # type: ignore[arg-type]
        self.physical._state = physical_state
        _load_metrics_state(self.physical._metrics, state["physical_metrics"])  # type: ignore[arg-type]
        dispatch = state["dispatch"]
        if dispatch is None:
            self.physical._dispatch = None
        else:
            from .cooperative_env import _Dispatch

            self.physical._dispatch = _Dispatch(
                str(dispatch["request_id"]),
                int(dispatch["sampled_slot"]),
                tuple(dispatch["candidate_mapping"]),
                int(dispatch["selected_service_node"]),
                float(dispatch["route_length_m"]),
            )
        self.physical._candidate_nodes = {
            str(key): (int(value[0]), float(value[1]))
            for key, value in dict(state["candidate_nodes"]).items()
        }
        self.spray_action_count = int(state["spray_action_count"])
        self.sprayed_pesticide_l = float(state["sprayed_pesticide_l"])
        self._last_sampled_actions = {
            str(role): np.asarray(values).copy()
            for role, values in dict(state["last_sampled_actions"]).items()
        }
        self.ecology_global_context_before = tuple(state["ecology_global_context_before"])  # type: ignore[arg-type]
        self._set_diagnostics()
        current_view = state["current_view"]
        if current_view is None:
            self.physical._current_view = None
            self._current_view = None
        else:
            if not isinstance(current_view, Mapping):
                raise ValueError("dynamic environment current view is invalid")
            self.physical._make_view(events=tuple(current_view.get("events", ())))
            self._current_view = _detached_view(current_view)

    def episode_record(self) -> Any:
        return self.physical.episode_record()


__all__ = ["DynamicPestEnvironment", "STATE_SCHEMA_VERSION"]
