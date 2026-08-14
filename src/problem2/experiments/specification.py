"""Strict, executable specification for the Chapter 4.5 experiment families."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import math
from typing import Any, Mapping

import yaml

from problem2.config import ConfigBundle


CANONICAL_FAMILIES = (
    "mechanism",
    "main_comparison",
    "sensitivity",
    "adaptation",
    "ablation",
)
DIAGNOSTIC_METHOD_NAMES = {
    "unlimited_supply",
    "finite_no_support",
    "teleport_diagnostic",
}


@dataclass(frozen=True)
class ExperimentCondition:
    condition_id: str
    family: str
    method: str
    scale: str | None = None
    training_seed: int | None = None
    factor: str | None = None
    level: object | None = None
    kind: str = ""
    overrides: tuple[tuple[str, object], ...] = ()

    @property
    def override_map(self) -> dict[str, object]:
        return dict(self.overrides)


@dataclass(frozen=True)
class Chapter45Spec:
    schema_version: int
    status: str
    main_methods: tuple[str, ...]
    scales: tuple[str, ...]
    training_seeds: tuple[int, ...]
    declared_families: Mapping[str, tuple[Mapping[str, Any], ...]]
    statistics: Mapping[str, Any]
    execution: Mapping[str, Any]
    family_scopes: Mapping[str, Mapping[str, tuple[object, ...]]]

    @property
    def families(self) -> tuple[str, ...]:
        return CANONICAL_FAMILIES

    def expand(self, family: str) -> tuple[ExperimentCondition, ...]:
        family = str(family)
        if family not in CANONICAL_FAMILIES:
            raise ValueError(f"unknown experiment family: {family}")
        if family == "main_comparison":
            return tuple(
                ExperimentCondition(
                    condition_id=f"{method}__{scale}__seed-{seed}",
                    family=family,
                    method=method,
                    scale=scale,
                    training_seed=seed,
                    kind="main_comparison",
                )
                for method in self.main_methods
                for scale in self.scales
                for seed in self.training_seeds
            )
        records = self.declared_families[family]
        if family == "sensitivity":
            return tuple(
                ExperimentCondition(
                    condition_id=f"{record['id']}__{_level_id(level)}",
                    family=family,
                    method="sr_mappo_mobile",
                    factor=str(record["parameter"]),
                    level=level,
                    kind="parameter_sensitivity",
                    overrides=((str(record["parameter"]), level),),
                )
                for record in records
                for level in record["levels"]
            )
        if family == "adaptation":
            return tuple(
                ExperimentCondition(
                    condition_id=f"{record['id']}__{_level_id(level)}",
                    family=family,
                    method="sr_mappo_mobile",
                    factor=str(record["kind"]),
                    level=level,
                    kind=str(record["kind"]),
                    overrides=((str(record["kind"]), level),),
                )
                for record in records
                for level in record["levels"]
            )
        return tuple(
            ExperimentCondition(
                condition_id=str(record["id"]),
                family=family,
                method=str(record.get("method", "sr_mappo_mobile")),
                kind=str(record.get("kind", "")),
                overrides=tuple(sorted(dict(record.get("intervention", {})).items())),
            )
            for record in records
        )


def _level_id(value: object) -> str:
    if isinstance(value, float):
        return format(value, ".8g").replace(".", "p")
    return str(value).replace(" ", "-")


def _mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return value


def _records(value: object, context: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} must be a non-empty list")
    return tuple(_mapping(item, f"{context} item") for item in value)


def load_experiment_spec(path: str | Path, config: ConfigBundle) -> Chapter45Spec:
    """Load and cross-check the experiment protocol against the base config."""

    with Path(path).open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    root = _mapping(document, "Chapter 4.5 protocol")
    if root.get("schema_version") != 1:
        raise ValueError("unsupported Chapter 4.5 protocol schema_version")
    status = str(root.get("status", ""))
    if status not in {"provisional", "verified"}:
        raise ValueError("Chapter 4.5 protocol status must be provisional or verified")
    main = _mapping(root.get("main_comparison"), "main_comparison")
    methods = tuple(str(value) for value in main.get("methods", ()))
    canonical_methods = tuple(str(value) for value in config.experiments["methods"])
    if methods != canonical_methods or any(method in DIAGNOSTIC_METHOD_NAMES for method in methods):
        raise ValueError("main methods must exactly match the canonical non-diagnostic registry")
    scales = tuple(str(value) for value in main.get("scales", ()))
    known_scales = tuple(str(record["id"]) for record in config.scales["scales"])
    if scales != known_scales:
        raise ValueError("main comparison scales must match the base scale registry")
    seeds = tuple(int(value) for value in main.get("training_seeds", ()))
    if seeds != tuple(int(value) for value in config.experiments["training_seeds"]):
        raise ValueError("training seeds must match the formal matrix")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("training seeds must be unique and non-empty")

    family_root = _mapping(root.get("families"), "families")
    required = {"mechanism", "sensitivity", "adaptation", "ablation"}
    if set(family_root) != required:
        raise ValueError(f"families must exactly equal {sorted(required)}")
    declared = {name: _records(family_root[name], name) for name in sorted(required)}

    identifiers: list[str] = []
    for records in declared.values():
        for record in records:
            identifier = str(record.get("id", "")).strip()
            if not identifier:
                raise ValueError("experiment condition id must be non-empty")
            identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate experiment condition id")

    parameters = set(config.parameters.get("parameters", {})) | {"uav_initial_pesticide_ratio"}
    for record in declared["sensitivity"]:
        parameter = str(record.get("parameter", ""))
        levels = record.get("levels")
        if parameter not in parameters:
            raise ValueError(f"unknown sensitivity parameter: {parameter}")
        if not isinstance(levels, list) or len(levels) < 3 or len({_level_id(item) for item in levels}) != len(levels):
            raise ValueError(f"sensitivity factor {parameter} needs at least three unique levels")

    statistics = _mapping(root.get("statistics"), "statistics")
    if statistics.get("pairing_unit") != "training_seed_then_shared_scenario":
        raise ValueError("statistics must preserve the seed-then-scenario hierarchy")
    if int(statistics.get("bootstrap_draws", 0)) < 2000:
        raise ValueError("bootstrap_draws must be at least 2000")
    if status == "verified":
        margin = statistics.get("practical_equivalence_margin")
        if (
            isinstance(margin, bool)
            or not isinstance(margin, (int, float))
            or not math.isfinite(float(margin))
            or float(margin) <= 0.0
        ):
            raise ValueError(
                "a verified protocol requires a finite positive practical_equivalence_margin"
            )
        basis = statistics.get("practical_equivalence_basis")
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError(
                "a verified protocol requires a non-empty practical_equivalence_basis"
            )
    execution = _mapping(root.get("execution"), "execution")
    if int(execution.get("max_gpu_workers", 0)) != 1:
        raise ValueError("the current hardware contract permits one GPU worker")
    if type(execution.get("checkpoint_every_updates")) is not int or int(execution["checkpoint_every_updates"]) < 1:
        raise ValueError("checkpoint_every_updates must be a positive integer")
    if execution.get("checkpoint_selection_rule") != "final_update":
        raise ValueError("the current implementation requires checkpoint_selection_rule=final_update")
    scope_root = _mapping(root.get("family_scopes"), "family_scopes")
    if set(scope_root) != required:
        raise ValueError(f"family_scopes must exactly equal {sorted(required)}")
    family_scopes: dict[str, Mapping[str, tuple[object, ...]]] = {}
    for family in sorted(required):
        scope = _mapping(scope_root[family], f"family_scopes.{family}")
        scoped_scales = tuple(str(value) for value in scope.get("scales", ()))
        scoped_seeds = tuple(int(value) for value in scope.get("training_seeds", ()))
        if not scoped_scales or not set(scoped_scales) <= set(scales):
            raise ValueError(f"{family} scope references an unknown or empty scale set")
        if not scoped_seeds or not set(scoped_seeds) <= set(seeds):
            raise ValueError(f"{family} scope references an unknown or empty seed set")
        family_scopes[family] = {
            "scales": scoped_scales,
            "training_seeds": scoped_seeds,
        }

    return Chapter45Spec(
        schema_version=1,
        status=status,
        main_methods=methods,
        scales=scales,
        training_seeds=seeds,
        declared_families=declared,
        statistics=dict(statistics),
        execution=dict(execution),
        family_scopes=family_scopes,
    )


def protocol_identity(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__all__ = ["Chapter45Spec", "ExperimentCondition", "load_experiment_spec", "protocol_identity"]
