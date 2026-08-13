"""Role-specific legal movement primitives."""

from __future__ import annotations

from typing import Iterable


UAV_ACTIONS = ("up", "down", "left", "right", "hold", "spray")
VEHICLE_ACTIONS = ("hold", "next_request_slot")
_DELTAS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def legal_uav_position(
    position: tuple[int, int], action: str, shape: tuple[int, int], *, locked: bool = False
) -> tuple[int, int]:
    """Apply a legal grid move; spray/hold/locked actions preserve position."""
    if action not in UAV_ACTIONS:
        raise ValueError(f"unknown UAV action: {action}")
    if locked or action in {"hold", "spray"}:
        return position
    dr, dc = _DELTAS[action]
    candidate = (position[0] + dr, position[1] + dc)
    rows, cols = shape
    if 0 <= candidate[0] < rows and 0 <= candidate[1] < cols:
        return candidate
    return position


def move_vehicle_towards(
    position: tuple[int, int], target: tuple[int, int] | None, shape: tuple[int, int]
) -> tuple[int, int]:
    """Fallback Manhattan-grid vehicle step, replaced by a road executor in Task 4."""
    if target is None or position == target:
        return position
    row, col = position
    tr, tc = target
    if row != tr:
        row += 1 if tr > row else -1
    elif col != tc:
        col += 1 if tc > col else -1
    rows, cols = shape
    return (min(max(row, 0), rows - 1), min(max(col, 0), cols - 1))
