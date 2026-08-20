"""Conversions from G2 legal masks to the frozen G3 role action spaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Iterable
from typing import Any

import numpy as np


def _bool_vector(
    values: Iterable[bool],
    width: int,
    name: str,
    *,
    require_any: bool = True,
) -> np.ndarray:
    result = np.asarray(list(values), dtype=bool).reshape(-1)
    if result.shape != (width,):
        raise ValueError(f"{name} must contain exactly {width} actions")
    if require_any and not result.any():
        raise ValueError(f"{name} must retain at least one legal action")
    return result


def convert_g2_uav_mask(mask: Iterable[bool]) -> np.ndarray:
    """Reorder G2 ``stay,up,down,left,right,spray`` to G3 action order."""

    g2 = _bool_vector(mask, 6, "G2 UAV mask")
    return g2[[1, 2, 3, 4, 0, 5]]


def convert_g2_vehicle_mask(
    mask: Iterable[bool],
    candidate_slot_mask: Iterable[bool],
    *,
    candidate_mapping: Any = None,
) -> np.ndarray:
    """Map G2 hold legality plus frozen candidate-slot legality to G3."""

    g2 = _bool_vector(mask, 5, "G2 vehicle mask")
    candidates = _bool_vector(
        candidate_slot_mask,
        4,
        "candidate slot mask",
        require_any=False,
    )
    result = np.concatenate([g2[[0]], candidates])
    if not result.any():
        raise ValueError("vehicle mask must retain at least one legal action")
    if candidate_mapping is not None:
        validate_candidate_slot_mapping(candidate_mapping, candidates)
    return result


def _candidate_mapping_values(
    candidate_mapping: Any, max_candidate_slots: int
) -> list[str | None]:
    if isinstance(candidate_mapping, Mapping):
        values: list[Any] = []
        for index in range(max_candidate_slots):
            values.append(
                candidate_mapping.get(
                    index, candidate_mapping.get(f"slot-{index}")
                )
            )
    elif isinstance(candidate_mapping, (str, bytes)) or candidate_mapping is None:
        raise ValueError("candidate mapping must contain one value per slot")
    else:
        values = list(candidate_mapping)
    if len(values) != max_candidate_slots:
        raise ValueError(
            f"candidate mapping must contain exactly {max_candidate_slots} slots"
        )

    normalized: list[str | None] = []
    for value in values:
        if value is None:
            normalized.append(None)
            continue
        text = str(value).strip()
        normalized.append(text or None)
    return normalized


def validate_candidate_slot_mapping(
    candidate_mapping: Any,
    candidate_slot_mask: Iterable[bool],
    *,
    max_candidate_slots: int = 4,
) -> tuple[str | None, ...]:
    """Ensure legal slot bits and stored request identities agree exactly."""

    mask = _bool_vector(
        candidate_slot_mask,
        max_candidate_slots,
        "candidate slot mask",
        require_any=False,
    )
    values = _candidate_mapping_values(candidate_mapping, max_candidate_slots)
    active = [value for value in values if value is not None]
    if len(active) != len(set(active)):
        raise ValueError("candidate slot mapping contains duplicate identities")
    for index, (legal, value) in enumerate(zip(mask.tolist(), values)):
        if bool(legal) != (value is not None):
            raise ValueError(
                f"candidate slot {index} mask and identity do not agree"
            )
    return tuple(values)


def convert_g2_masks_to_roles(
    *,
    uav_mask: Iterable[bool],
    vehicle_mask: Iterable[bool],
    candidate_slot_mask: Iterable[bool],
    candidate_mapping: Any = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert legal masks without replacing an illegal sampled action."""

    return convert_g2_uav_mask(uav_mask), convert_g2_vehicle_mask(
        vehicle_mask,
        candidate_slot_mask,
        candidate_mapping=candidate_mapping,
    )


__all__ = [
    "convert_g2_masks_to_roles",
    "convert_g2_uav_mask",
    "convert_g2_vehicle_mask",
    "validate_candidate_slot_mapping",
]
