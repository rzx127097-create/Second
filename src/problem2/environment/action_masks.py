"""Legal action masks shared by behavior sampling, logs and PPO replay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .movement import UAV_ACTIONS as _UAV_ACTIONS

UAV_ACTIONS = tuple(_UAV_ACTIONS)
# This is the environment's legacy high-level vehicle action vocabulary.  When
# candidate slots are supplied, ``vehicle_action_mask`` expands it to hold plus
# fixed ``slot-*`` actions without changing the legacy constant.
VEHICLE_ACTIONS = ("hold", "next_request_slot")
_DELTAS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


@dataclass(frozen=True)
class ActionMask:
    mask: np.ndarray
    actions: tuple[str, ...]
    fallback_hold: bool = False
    events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = np.asarray(self.mask, dtype=np.int8).reshape(-1)
        if values.size != len(self.actions):
            raise ValueError("mask and action dimensions must match")
        if not values.any():
            raise ValueError("an action mask must retain at least one action")
        values.setflags(write=False)
        object.__setattr__(self, "mask", values)

    def __len__(self) -> int:
        return len(self.mask)

    def __getitem__(self, index: int) -> int:
        return int(self.mask[index])

    def __iter__(self):
        return iter(self.mask.tolist())

    def tolist(self) -> list[int]:
        return self.mask.tolist()

    @property
    def valid_actions(self) -> tuple[str, ...]:
        return tuple(action for action, valid in zip(self.actions, self.mask) if valid)

    def __array__(self, dtype: Any = None) -> np.ndarray:
        return np.asarray(self.mask, dtype=dtype)


def _candidate_is_valid(candidate: Any, *, inventory_l: float | None = None) -> bool:
    if candidate is None:
        return False
    if isinstance(candidate, dict):
        if candidate.get("valid", True) is False or candidate.get("reachable", True) is False:
            return False
        if candidate.get("inventory_l", inventory_l if inventory_l is not None else 1.0) <= 0:
            return False
        if candidate.get("remaining_l", 1.0) <= 0:
            return False
        return True
    return bool(getattr(candidate, "reachable", True))


def uav_action_mask(
    position: tuple[int, int],
    shape: tuple[int, int],
    *,
    onboard_l: float,
    spray_flow_l_s: float,
    locked: bool = False,
    rendezvous_target: tuple[int, int] | None = None,
    must_approach: bool = False,
    valid_cells: set[tuple[int, int]] | None = None,
    minimum_spray_l: float = 1e-12,
) -> ActionMask:
    """Return six-action UAV mask, including the explicit ``fallback_hold`` rule."""

    actions = UAV_ACTIONS
    if locked:
        return ActionMask(np.array([0, 0, 0, 0, 1, 0], dtype=np.int8), actions)
    mask = np.zeros(len(actions), dtype=np.int8)
    rows, cols = shape
    distances: dict[str, int] = {}
    current_distance = None
    if rendezvous_target is not None:
        current_distance = abs(position[0] - rendezvous_target[0]) + abs(position[1] - rendezvous_target[1])
    for index, action in enumerate(actions):
        if action == "hold":
            mask[index] = 1
        elif action == "spray":
            mask[index] = int(onboard_l >= minimum_spray_l and spray_flow_l_s > 0)
        else:
            delta = _DELTAS[action]
            candidate = (position[0] + delta[0], position[1] + delta[1])
            legal = 0 <= candidate[0] < rows and 0 <= candidate[1] < cols
            if valid_cells is not None:
                legal = legal and candidate in valid_cells
            if legal and must_approach and rendezvous_target is not None:
                candidate_distance = abs(candidate[0] - rendezvous_target[0]) + abs(candidate[1] - rendezvous_target[1])
                distances[action] = candidate_distance
                legal = candidate_distance < current_distance
            mask[index] = int(legal)
    events: tuple[str, ...] = ()
    fallback = False
    if must_approach and rendezvous_target is not None:
        # Once a service commitment is active, the UAV must first shorten the
        # rendezvous distance; spraying while en route violates that protocol.
        if current_distance and current_distance > 0:
            mask[actions.index("spray")] = 0
        improving = [idx for action, idx in ((name, i) for i, name in enumerate(actions)) if action in _DELTAS and mask[idx]]
        if current_distance == 0 or not improving:
            # A hold at the rendezvous point or when all improving moves are
            # blocked is a protocol fallback, never an unconstrained move.
            mask[:] = 0
            mask[actions.index("hold")] = 1
            fallback = True
            events = ("fallback_hold",)
        else:
            mask[actions.index("hold")] = 0
    if not mask.any():
        mask[actions.index("hold")] = 1
    return ActionMask(mask, actions, fallback_hold=fallback, events=events)


def vehicle_action_mask(
    *,
    locked: bool = False,
    candidate_slots: Iterable[Any] | None = None,
    max_slots: int | None = None,
    inventory_l: float | None = None,
    service_cap_l: float | None = None,
) -> ActionMask:
    """Return a fixed hold-plus-candidate-slot vehicle mask.

    With no candidate collection this preserves the current environment's
    two-action ``hold/next_request_slot`` interface.
    """

    candidates = list(candidate_slots or ())
    if candidate_slots is None and max_slots is None:
        actions = VEHICLE_ACTIONS
        return ActionMask(np.array([1, 0 if locked else 1], dtype=np.int8), actions)
    slot_count = max(0, int(max_slots if max_slots is not None else len(candidates)))
    candidates = candidates[:slot_count]
    actions = ("hold",) + tuple(f"slot-{index}" for index in range(slot_count))
    mask = np.zeros(1 + slot_count, dtype=np.int8)
    mask[0] = 1
    if not locked and (inventory_l is None or inventory_l > 0) and (service_cap_l is None or service_cap_l > 0):
        for index, candidate in enumerate(candidates):
            mask[index + 1] = int(_candidate_is_valid(candidate, inventory_l=inventory_l))
    return ActionMask(mask, actions)


__all__ = ["ActionMask", "UAV_ACTIONS", "VEHICLE_ACTIONS", "uav_action_mask", "vehicle_action_mask"]
