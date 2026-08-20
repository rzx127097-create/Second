"""Conversions from G2 legal masks to the frozen G3 role action spaces."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def _bool_vector(values: Iterable[bool], width: int, name: str) -> np.ndarray:
    result = np.asarray(list(values), dtype=bool).reshape(-1)
    if result.shape != (width,):
        raise ValueError(f"{name} must contain exactly {width} actions")
    if not result.any():
        raise ValueError(f"{name} must retain at least one legal action")
    return result


def convert_g2_uav_mask(mask: Iterable[bool]) -> np.ndarray:
    """Reorder G2 ``stay,up,down,left,right,spray`` to G3 action order."""

    g2 = _bool_vector(mask, 6, "G2 UAV mask")
    return g2[[1, 2, 3, 4, 0, 5]]


def convert_g2_vehicle_mask(
    mask: Iterable[bool], candidate_slot_mask: Iterable[bool]
) -> np.ndarray:
    """Map G2 hold legality plus frozen candidate-slot legality to G3."""

    g2 = _bool_vector(mask, 5, "G2 vehicle mask")
    candidates = _bool_vector(candidate_slot_mask, 4, "candidate slot mask")
    return np.concatenate([g2[[0]], candidates])


def convert_g2_masks_to_roles(
    *,
    uav_mask: Iterable[bool],
    vehicle_mask: Iterable[bool],
    candidate_slot_mask: Iterable[bool],
) -> tuple[np.ndarray, np.ndarray]:
    """Convert legal masks without replacing an illegal sampled action."""

    return convert_g2_uav_mask(uav_mask), convert_g2_vehicle_mask(
        vehicle_mask, candidate_slot_mask
    )


__all__ = [
    "convert_g2_masks_to_roles",
    "convert_g2_uav_mask",
    "convert_g2_vehicle_mask",
]
