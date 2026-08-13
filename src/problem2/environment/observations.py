"""Role-local observations and structured centralized state.

The builders deliberately return small dictionaries as well as a numeric
``vector``.  The dictionaries keep the evidence ledger readable while the
vectors give actors and critics a deterministic input contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable, Mapping

import numpy as np

from problem2.domain.resources import PesticideResources


@dataclass(frozen=True)
class SlotMapping:
    """Deterministic entity-to-slot mapping shared by rollout and replay."""

    uav_ids: tuple[str, ...]
    vehicle_ids: tuple[str, ...]
    request_ids: tuple[str, ...] = ()
    max_request_slots: int = 0

    def request_slot_ids(self) -> tuple[str | None, ...]:
        return tuple(self.request_ids[: self.max_request_slots]) + (None,) * max(
            0, self.max_request_slots - len(self.request_ids)
        )


def _ids(values: Mapping[str, Any] | Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, Mapping):
        values = values.keys()
    return tuple(sorted(str(value) for value in values))


def _request_id(request: Any) -> str:
    return str(request.get("request_id", "")) if isinstance(request, Mapping) else str(getattr(request, "request_id", ""))


def stable_slot_mapping(
    uavs: Mapping[str, Any] | Iterable[Any],
    vehicles: Mapping[str, Any] | Iterable[Any],
    requests: Iterable[Any] | None = None,
    *,
    max_request_slots: int | None = None,
) -> SlotMapping:
    """Build a mapping whose order does not depend on dictionary insertion order."""

    request_ids = tuple(sorted({_request_id(item) for item in (requests or ()) if _request_id(item)}))
    slot_count = len(request_ids) if max_request_slots is None else max(0, int(max_request_slots))
    return SlotMapping(_ids(uavs), _ids(vehicles), request_ids, slot_count)


def _position(value: Any) -> tuple[float, float]:
    if value is None:
        return (0.0, 0.0)
    return (float(value[0]), float(value[1]))


def _request_value(request: Any, key: str, default: Any = 0.0) -> Any:
    if isinstance(request, Mapping):
        return request.get(key, default)
    return getattr(request, key, default)


def _phase_code(value: Any) -> float:
    text = getattr(value, "value", value)
    return {"idle": 0.0, "preparing": 1.0, "transferring": 2.0, "reserved": 1.0}.get(str(text), 0.0)


def _shape_from_density(pest_density: Any) -> tuple[int, int] | None:
    if pest_density is None:
        return None
    shape = np.asarray(pest_density).shape
    return (int(shape[0]), int(shape[1])) if len(shape) >= 2 else None


def _norm_position(position: tuple[float, float], shape: tuple[int, int] | None) -> tuple[float, float]:
    if shape is None:
        return position
    rows, cols = shape
    return (
        position[0] / max(1.0, rows - 1),
        position[1] / max(1.0, cols - 1),
    )


def _local_field(pest_density: Any, position: tuple[float, float]) -> np.ndarray:
    """Encode local field information without exposing the full global field."""

    if pest_density is None:
        return np.zeros(4, dtype=float)
    field = np.asarray(pest_density, dtype=float)
    if field.ndim < 2 or field.size == 0:
        value = float(field.reshape(-1)[0]) if field.size else 0.0
        return np.array([value, value, value, 0.0], dtype=float)
    row, col = int(round(position[0])), int(round(position[1]))
    row = min(max(row, 0), field.shape[0] - 1)
    col = min(max(col, 0), field.shape[1] - 1)
    r0, r1 = max(0, row - 1), min(field.shape[0], row + 2)
    c0, c1 = max(0, col - 1), min(field.shape[1], col + 2)
    patch = field[r0:r1, c0:c1]
    value = float(field[row, col])
    return np.array([value, float(np.mean(patch)), float(np.max(patch)), float(np.min(patch))], dtype=float)


def _as_array(parts: Iterable[Any]) -> np.ndarray:
    flattened: list[float] = []
    for part in parts:
        flattened.extend(np.asarray(part, dtype=float).reshape(-1).tolist())
    return np.asarray(flattened, dtype=float)


def _find_request(requests: Iterable[Any], uav_id: str) -> Any | None:
    for request in requests:
        if str(_request_value(request, "uav_id", "")) == uav_id:
            return request
    return None


def build_uav_observation(
    uav_id: str,
    resources: PesticideResources,
    positions: Mapping[str, Any] | None = None,
    vehicle_positions: Mapping[str, Any] | None = None,
    pest_density: Any = None,
    *,
    mapping: SlotMapping | None = None,
    requests: Iterable[Any] | None = None,
    service_locked: bool = False,
    service_phase: Any = "idle",
    step: int = 0,
    max_steps: int = 1,
    **_: Any,
) -> dict[str, Any]:
    """Build one decentralized UAV observation.

    Only local field summaries and current coordination messages are included;
    the complete pest field and structured critic state are intentionally absent.
    """

    positions = positions or {}
    vehicle_positions = vehicle_positions or {}
    requests_list = list(requests or ())
    mapping = mapping or stable_slot_mapping(resources.uavs, resources.vehicles, requests_list)
    if uav_id not in resources.uavs:
        raise KeyError(uav_id)
    state = resources.uav(uav_id)
    own_position = _position(positions.get(uav_id))
    shape = _shape_from_density(pest_density)
    own_norm = _norm_position(own_position, shape)
    own_request = _find_request(requests_list, uav_id)
    request_remaining = float(_request_value(own_request, "remaining_l", 0.0)) if own_request else 0.0
    request_active = 1.0 if own_request is not None else 0.0

    # Relative peer and vehicle summaries use fixed IDs, so actor dimensions are stable.
    peer_features: list[float] = []
    for peer_id in mapping.uav_ids:
        peer = resources.uav(peer_id)
        peer_pos = _position(positions.get(peer_id))
        if peer_id == uav_id:
            peer_features.extend((0.0, 0.0, peer.onboard_l / max(peer.capacity_l, 1e-12)))
        else:
            peer_features.extend((peer_pos[0] - own_position[0], peer_pos[1] - own_position[1], peer.onboard_l / max(peer.capacity_l, 1e-12)))
    vehicle_features: list[float] = []
    for vehicle_id in mapping.vehicle_ids:
        vehicle = resources.vehicle(vehicle_id)
        vehicle_pos = _position(vehicle_positions.get(vehicle_id))
        vehicle_features.extend(
            (
                vehicle_pos[0] - own_position[0],
                vehicle_pos[1] - own_position[1],
                vehicle.inventory_l / max(vehicle.capacity_l, 1e-12),
                1.0 if service_locked and vehicle_id in mapping.vehicle_ids else 0.0,
            )
        )
    vector = _as_array(
        (
            own_norm,
            (state.onboard_l / max(state.capacity_l, 1e-12), state.spray_flow_l_s, request_remaining, request_active),
            (float(service_locked), _phase_code(service_phase), step / max(1, max_steps)),
            _local_field(pest_density, own_position),
            peer_features,
            vehicle_features,
        )
    )
    return {
        "role": "uav",
        "agent_id": uav_id,
        "position": own_position,
        "onboard_l": float(state.onboard_l),
        "capacity_l": float(state.capacity_l),
        "spray_flow_l_s": float(state.spray_flow_l_s),
        "service_locked": bool(service_locked),
        "request_remaining_l": request_remaining,
        "local_field": _local_field(pest_density, own_position),
        "vector": vector,
    }


def build_vehicle_observation(
    vehicle_id: str,
    resources: PesticideResources,
    positions: Mapping[str, Any] | None = None,
    vehicle_positions: Mapping[str, Any] | None = None,
    requests: Iterable[Any] | None = None,
    *,
    mapping: SlotMapping | None = None,
    service_phase: Any = "idle",
    active_request_id: str | None = None,
    step: int = 0,
    max_steps: int = 1,
    max_request_slots: int | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Build a fixed-slot vehicle observation from current requests."""

    positions = positions or {}
    vehicle_positions = vehicle_positions or {}
    requests_list = sorted(list(requests or ()), key=lambda item: (_request_value(item, "created_step", 0), _request_id(item)))
    mapping = mapping or stable_slot_mapping(resources.uavs, resources.vehicles, requests_list, max_request_slots=max_request_slots)
    if not mapping.request_ids and requests_list:
        # A caller may freeze the entity slots before requests exist.  Keep its
        # configured capacity while filling request IDs deterministically once
        # the first request batch arrives.
        mapping = SlotMapping(
            mapping.uav_ids,
            mapping.vehicle_ids,
            tuple(sorted(_request_id(item) for item in requests_list if _request_id(item)))[: mapping.max_request_slots],
            mapping.max_request_slots,
        )
    if vehicle_id not in resources.vehicles:
        raise KeyError(vehicle_id)
    vehicle = resources.vehicle(vehicle_id)
    slot_count = mapping.max_request_slots
    slot_ids = mapping.request_slot_ids()
    by_id = {_request_id(request): request for request in requests_list}
    request_slots = np.zeros(slot_count, dtype=float)
    request_mask = np.zeros(slot_count, dtype=np.int8)
    request_features = np.zeros((slot_count, 5), dtype=float)
    own_position = _position(vehicle_positions.get(vehicle_id))
    for index, request_id in enumerate(slot_ids):
        if request_id is None or request_id not in by_id:
            continue
        request = by_id[request_id]
        uav_id = str(_request_value(request, "uav_id", ""))
        request_slots[index] = float(_request_value(request, "remaining_l", 0.0))
        request_mask[index] = 1
        uav_position = _position(positions.get(uav_id))
        request_features[index] = (
            request_slots[index],
            float(_request_value(request, "urgency", 0.0)),
            hypot(uav_position[0] - own_position[0], uav_position[1] - own_position[1]),
            1.0 if _request_value(request, "reserved_vehicle_id", None) is None else 0.0,
            1.0 if str(_request_value(request, "status", "open")) in {"open", "RequestStatus.OPEN"} else 0.0,
        )
    norm_position = own_position
    phase = _phase_code(service_phase)
    vector = _as_array(
        (
            norm_position,
            (vehicle.inventory_l / max(vehicle.capacity_l, 1e-12), vehicle.transfer_rate_l_s, vehicle.service_cap_l, phase),
            (1.0 if active_request_id else 0.0, step / max(1, max_steps)),
            request_features,
        )
    )
    return {
        "role": "vehicle",
        "agent_id": vehicle_id,
        "position": own_position,
        "inventory_l": float(vehicle.inventory_l),
        "capacity_l": float(vehicle.capacity_l),
        "service_phase": getattr(service_phase, "value", service_phase),
        "active_request_id": active_request_id,
        "request_slots": request_slots,
        "request_slot_mask": request_mask,
        "slot_mapping": slot_ids,
        "vector": vector,
    }


def build_structured_critic_state(
    resources: PesticideResources,
    positions: Mapping[str, Any] | None = None,
    vehicle_positions: Mapping[str, Any] | None = None,
    pest_density: Any = None,
    *,
    mapping: SlotMapping | None = None,
    requests: Iterable[Any] | None = None,
    service: Any = None,
    step: int = 0,
    max_steps: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build semantic global state blocks for the centralized critic."""

    positions = positions or {}
    vehicle_positions = vehicle_positions or {}
    requests_list = list(requests or ())
    mapping = mapping or stable_slot_mapping(resources.uavs, resources.vehicles, requests_list)
    field = np.asarray(pest_density, dtype=float) if pest_density is not None else np.zeros(1, dtype=float)
    eco = np.asarray([float(np.mean(field)), float(np.max(field)) if field.size else 0.0, float(np.mean(field)) if field.size else 0.0], dtype=float)
    uav_rows = []
    for uav_id in mapping.uav_ids:
        state = resources.uav(uav_id)
        uav_rows.append((*_position(positions.get(uav_id)), state.onboard_l, state.capacity_l, state.spray_flow_l_s))
    vehicle_rows = []
    for vehicle_id in mapping.vehicle_ids:
        state = resources.vehicle(vehicle_id)
        vehicle_rows.append((*_position(vehicle_positions.get(vehicle_id)), state.inventory_l, state.capacity_l, state.transfer_rate_l_s, state.service_cap_l))
    request_rows = []
    for request_id in mapping.request_slot_ids():
        request = next((item for item in requests_list if _request_id(item) == request_id), None)
        request_rows.append((
            float(_request_value(request, "remaining_l", 0.0)),
            float(_request_value(request, "created_step", 0.0)),
            float(_request_value(request, "urgency", 0.0)),
            1.0 if request is not None else 0.0,
        ))
    service_obj = service if service is not None else kwargs
    service_block = np.asarray(
        [
            _phase_code(getattr(service_obj, "phase", kwargs.get("service_phase", "idle"))),
            1.0 if getattr(service_obj, "request_id", kwargs.get("active_request_id")) else 0.0,
            1.0 if getattr(service_obj, "locked_uav_id", kwargs.get("locked_uav_id")) else 0.0,
            float(getattr(service_obj, "setup_remaining_s", kwargs.get("setup_remaining_s", 0.0))),
        ],
        dtype=float,
    )
    time_block = np.asarray([float(step), float(step) / max(1, max_steps)], dtype=float)
    blocks: dict[str, Any] = {
        "eco": eco,
        "uavs": np.asarray(uav_rows, dtype=float).reshape(len(mapping.uav_ids), -1),
        "vehicles": np.asarray(vehicle_rows, dtype=float).reshape(len(mapping.vehicle_ids), -1),
        "requests": np.asarray(request_rows, dtype=float).reshape(mapping.max_request_slots, -1) if mapping.max_request_slots else np.zeros((0, 4), dtype=float),
        "service": service_block,
        "time": time_block,
    }
    blocks["vector"] = _as_array(blocks.values())
    return blocks


def build_observations(*args: Any, **kwargs: Any) -> dict[str, dict[str, Any]]:
    """Convenience builder for all agents using one shared slot mapping."""

    resources: PesticideResources = kwargs.pop("resources", args[0] if args else None)
    if resources is None:
        raise TypeError("resources is required")
    mapping = kwargs.pop("mapping", None) or stable_slot_mapping(resources.uavs, resources.vehicles, kwargs.get("requests", ()))
    result: dict[str, dict[str, Any]] = {}
    for uav_id in mapping.uav_ids:
        result[uav_id] = build_uav_observation(uav_id, resources, mapping=mapping, **kwargs)
    for vehicle_id in mapping.vehicle_ids:
        result[vehicle_id] = build_vehicle_observation(vehicle_id, resources, mapping=mapping, **kwargs)
    return result


__all__ = [
    "SlotMapping",
    "stable_slot_mapping",
    "build_uav_observation",
    "build_vehicle_observation",
    "build_structured_critic_state",
    "build_observations",
]
