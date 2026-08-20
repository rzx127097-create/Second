"""Deterministic role-local observations and centralized critic state.

The builders accept a small mapping snapshot so the G3 learning interface can
be tested independently of a particular environment wrapper.  Only fields
declared in the current snapshot are used by actors; the critic has its own
explicit global-state builder.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


UAV_BASE_DIM = 43
UAV_PER_AGENT_DIM = 68
VEHICLE_OBS_DIM = 28
CRITIC_BASE_DIM = 45
CRITIC_PER_AGENT_DIM = 70


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if np.isfinite(result) else float(default)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(snapshot: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = snapshot.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [_mapping(row) for row in value]


def _pad(values: Sequence[float], width: int) -> np.ndarray:
    result = np.zeros(width, dtype=np.float32)
    clipped = np.asarray(list(values)[:width], dtype=np.float32)
    if clipped.size:
        result[: clipped.size] = clipped
    return result


def _mode_code(value: Any) -> float:
    text = getattr(value, "value", value)
    return {
        "idle": 0.0,
        "transit": 1.0,
        "serving": 2.0,
        "reserved": 3.0,
    }.get(str(text).lower(), 0.0)


def _uav_rows(snapshot: Mapping[str, Any], uav_count: int) -> list[Mapping[str, Any]]:
    rows = sorted(_rows(snapshot, "uavs"), key=lambda row: str(row.get("id", "")))
    rows = rows[:uav_count]
    while len(rows) < uav_count:
        rows.append({"id": f"uav-{len(rows)}"})
    return rows


def _vehicle_row(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(snapshot.get("vehicle"))


def _requests_for_uav(
    snapshot: Mapping[str, Any], uav_id: str
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in _rows(snapshot, "requests")
        if str(row.get("uav_id", "")) == uav_id
    ]


def _candidate_rows(
    snapshot: Mapping[str, Any], max_candidate_slots: int
) -> list[Mapping[str, Any]]:
    rows = sorted(
        _rows(snapshot, "candidate_slots"),
        key=lambda row: int(_number(row.get("slot"), 0.0)),
    )
    by_slot = {
        int(_number(row.get("slot"), index)): row
        for index, row in enumerate(rows)
    }
    return [by_slot.get(index, {}) for index in range(max_candidate_slots)]


def _field_summary(snapshot: Mapping[str, Any]) -> np.ndarray:
    return _pad(snapshot.get("field_summary", ()), 8)


def _step_norm(snapshot: Mapping[str, Any]) -> float:
    return _number(snapshot.get("step"), 0.0) / max(
        1.0, _number(snapshot.get("max_steps"), 1.0)
    )


def _vehicle_mode_features(vehicle: Mapping[str, Any]) -> list[float]:
    return [
        _number(vehicle.get("x")),
        _number(vehicle.get("y")),
        _number(vehicle.get("inventory_l"))
        / max(1.0e-8, _number(vehicle.get("capacity_l"), 1.0)),
        _mode_code(vehicle.get("mode")),
        float(bool(vehicle.get("active_request_id"))),
    ]


def _request_aggregate(
    snapshot: Mapping[str, Any], max_candidate_slots: int
) -> list[float]:
    requests = _rows(snapshot, "requests")
    candidates = _candidate_rows(snapshot, max_candidate_slots)
    remaining = [_number(row.get("remaining_l")) for row in requests]
    urgency = [_number(row.get("urgency")) for row in requests]
    road_distance = [_number(row.get("road_distance_m")) for row in requests]
    return [
        float(len(requests)),
        min(remaining, default=0.0),
        float(np.mean(urgency)) if urgency else 0.0,
        min(road_distance, default=0.0),
        float(sum(bool(row.get("valid", False)) for row in candidates)),
    ]


def build_role_observations(
    snapshot: Mapping[str, Any],
    uav_count: int,
    max_candidate_slots: int,
) -> dict[str, np.ndarray]:
    """Return fixed-shape UAV and vehicle policy inputs.

    UAV rows contain only local state, current service/request information,
    current vehicle summary, local ecological summary, and same-time peer
    summaries.  Critic-only fields are intentionally ignored.
    """

    if uav_count <= 0 or max_candidate_slots <= 0:
        raise ValueError("uav_count and max_candidate_slots must be positive")
    uavs = _uav_rows(snapshot, uav_count)
    vehicle = _vehicle_row(snapshot)
    field = _field_summary(snapshot)
    step_norm = _step_norm(snapshot)
    request_aggregate = _request_aggregate(snapshot, max_candidate_slots)

    uav_observations: list[np.ndarray] = []
    for index, uav in enumerate(uavs):
        uav_id = str(uav.get("id", f"uav-{index}"))
        requests = _requests_for_uav(snapshot, uav_id)
        request = requests[0] if requests else {}
        own_x = _number(uav.get("x"))
        own_y = _number(uav.get("y"))
        own_capacity = max(1.0e-8, _number(uav.get("capacity_l"), 1.0))
        own = [
            own_x,
            own_y,
            _number(uav.get("pesticide_l")) / own_capacity,
            float(bool(uav.get("service_locked"))),
            float(bool(uav.get("active_request_id"))),
            _number(uav.get("request_remaining_l", request.get("remaining_l"))),
            step_norm,
        ]
        vehicle_features = _vehicle_mode_features(vehicle)
        if vehicle:
            vehicle_features[0] -= own_x
            vehicle_features[1] -= own_y
        base = own + vehicle_features + field.tolist() + request_aggregate
        base_vector = _pad(base, UAV_BASE_DIM)

        peer_blocks: list[float] = []
        for peer_index, peer in enumerate(uavs):
            peer_id = str(peer.get("id", f"uav-{peer_index}"))
            peer_requests = _requests_for_uav(snapshot, peer_id)
            peer_request = peer_requests[0] if peer_requests else {}
            peer_capacity = max(1.0e-8, _number(peer.get("capacity_l"), 1.0))
            peer_block = [
                _number(peer.get("x")) - own_x,
                _number(peer.get("y")) - own_y,
                _number(peer.get("pesticide_l")) / peer_capacity,
                float(bool(peer.get("service_locked"))),
                float(bool(peer.get("active_request_id"))),
                _number(peer.get("request_remaining_l", peer_request.get("remaining_l"))),
                float(peer_index == index),
            ]
            peer_blocks.extend(peer_block)
        uav_observations.append(
            np.concatenate(
                [base_vector, _pad(peer_blocks, UAV_PER_AGENT_DIM * uav_count)],
                dtype=np.float32,
            )
        )

    candidates = _candidate_rows(snapshot, max_candidate_slots)
    vehicle_base = [
        _number(vehicle.get("x")),
        _number(vehicle.get("y")),
        _number(vehicle.get("inventory_l"))
        / max(1.0e-8, _number(vehicle.get("capacity_l"), 1.0)),
        _mode_code(vehicle.get("mode")),
        float(bool(vehicle.get("active_request_id"))),
        step_norm,
        float(len(_rows(snapshot, "requests"))),
        float(sum(bool(row.get("valid", False)) for row in candidates)),
    ]
    candidate_features: list[float] = []
    for row in candidates:
        candidate_features.extend(
            [
                _number(row.get("remaining_l")),
                _number(row.get("urgency")),
                _number(row.get("road_distance_m")),
                float(bool(row.get("valid", False))),
                float(bool(row.get("uav_id"))),
            ]
        )
    vehicle_observation = np.concatenate(
        [_pad(vehicle_base, 8), _pad(candidate_features, 5 * max_candidate_slots)],
        dtype=np.float32,
    )

    uav_array = np.asarray(uav_observations, dtype=np.float32)
    if uav_array.shape != (uav_count, UAV_BASE_DIM + UAV_PER_AGENT_DIM * uav_count):
        raise AssertionError("UAV observation contract construction drifted")
    if vehicle_observation.shape != (VEHICLE_OBS_DIM,):
        raise AssertionError("vehicle observation contract construction drifted")
    return {"uav": uav_array, "vehicle": vehicle_observation.reshape(1, -1)}


def build_structured_critic_state(
    snapshot: Mapping[str, Any],
    uav_count: int,
    max_candidate_slots: int,
) -> np.ndarray:
    """Return the fixed structured centralized team-state vector."""

    if uav_count <= 0 or max_candidate_slots <= 0:
        raise ValueError("uav_count and max_candidate_slots must be positive")
    uavs = _uav_rows(snapshot, uav_count)
    vehicle = _vehicle_row(snapshot)
    candidates = _candidate_rows(snapshot, max_candidate_slots)
    field = _field_summary(snapshot)
    requests = _rows(snapshot, "requests")
    critic_only = _pad(snapshot.get("critic_only", ()), 3)

    base = field.tolist()
    base.extend(
        [
            *_vehicle_mode_features(vehicle),
            _number(vehicle.get("capacity_l")),
            _number(vehicle.get("inventory_l")),
            float(len(requests)),
            float(sum(bool(row.get("valid", False)) for row in candidates)),
            _step_norm(snapshot),
            _number(snapshot.get("step")),
            _number(snapshot.get("max_steps"), 1.0),
            _number(snapshot.get("episode_return")),
        ]
    )
    base.extend(_request_aggregate(snapshot, max_candidate_slots))
    base.extend(critic_only.tolist())
    base_vector = _pad(base, CRITIC_BASE_DIM)

    agent_blocks: list[float] = []
    for index, uav in enumerate(uavs):
        uav_id = str(uav.get("id", f"uav-{index}"))
        requests_for_uav = _requests_for_uav(snapshot, uav_id)
        request = requests_for_uav[0] if requests_for_uav else {}
        capacity = max(1.0e-8, _number(uav.get("capacity_l"), 1.0))
        block = [
            _number(uav.get("x")),
            _number(uav.get("y")),
            _number(uav.get("pesticide_l")) / capacity,
            float(bool(uav.get("service_locked"))),
            float(bool(uav.get("active_request_id"))),
            _number(uav.get("request_remaining_l", request.get("remaining_l"))),
            _number(uav.get("spray_flow_lps")),
            _number(uav.get("capacity_l")),
            float(index),
        ]
        agent_blocks.extend(_pad(block, CRITIC_PER_AGENT_DIM).tolist())

    state = np.concatenate(
        [base_vector, _pad(agent_blocks, CRITIC_PER_AGENT_DIM * uav_count)],
        dtype=np.float32,
    )
    expected = CRITIC_BASE_DIM + CRITIC_PER_AGENT_DIM * uav_count
    if state.shape != (expected,):
        raise AssertionError("critic state contract construction drifted")
    return state


__all__ = [
    "CRITIC_BASE_DIM",
    "CRITIC_PER_AGENT_DIM",
    "UAV_BASE_DIM",
    "UAV_PER_AGENT_DIM",
    "VEHICLE_OBS_DIM",
    "build_role_observations",
    "build_structured_critic_state",
]
