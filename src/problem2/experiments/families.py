from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


SCALES = (
    "g20x20_d2", "g20x30_d3", "g20x40_d3",
    "g30x30_d3", "g30x40_d4", "g30x50_d4",
)
LEARNING_METHODS = (
    "sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile",
)
FORMAL_SEEDS = (42, 123, 2024, 3407, 7919)
REQUIRED_CONDITIONS = (
    "sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage",
)
HEURISTIC_CONDITIONS = ("sr_mappo_nearest", "sr_mappo_urgency")


@dataclass(frozen=True)
class FamilyDefinition:
    family: str
    conditions: tuple[str, ...]
    scales: tuple[str, ...]
    seeds: tuple[int, ...]
    purpose: str


FAMILY_DEFINITIONS: Mapping[str, FamilyDefinition] = {
    "algorithm_convergence": FamilyDefinition(
        "algorithm_convergence", LEARNING_METHODS, SCALES, FORMAL_SEEDS,
        "equal interaction-budget convergence references",
    ),
    "algorithm_scale": FamilyDefinition(
        "algorithm_scale", LEARNING_METHODS, SCALES, FORMAL_SEEDS,
        "six-scale endpoint training matrix",
    ),
    "problem2_required": FamilyDefinition(
        "problem2_required", REQUIRED_CONDITIONS, SCALES, FORMAL_SEEDS,
        "required Problem-2 condition references and training",
    ),
    "vehicle_heuristics": FamilyDefinition(
        "vehicle_heuristics", HEURISTIC_CONDITIONS, SCALES, FORMAL_SEEDS,
        "classical vehicle-control hybrid training",
    ),
    "sr_mappo_ablation": FamilyDefinition(
        "sr_mappo_ablation", ("sr_mappo_mobile",), ("g30x30_d3",), FORMAL_SEEDS,
        "remove-one SR-MAPPO stability groups",
    ),
    "sr_mappo_sensitivity": FamilyDefinition(
        "sr_mappo_sensitivity", ("sr_mappo_mobile",), ("g30x30_d3",), FORMAL_SEEDS,
        "noncenter one-factor algorithmic sensitivity",
    ),
}


__all__ = [
    "FamilyDefinition", "FAMILY_DEFINITIONS", "SCALES", "LEARNING_METHODS", "FORMAL_SEEDS",
    "REQUIRED_CONDITIONS", "HEURISTIC_CONDITIONS",
]
