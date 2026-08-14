"""Configuration loading and immutable experiment identity helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ConfigBundle:
    parameters: dict[str, Any]
    scales: dict[str, Any]
    environment: dict[str, Any]
    algorithm: dict[str, Any]
    experiments: dict[str, Any]
    scenarios: dict[str, Any]
    scenario_status: str


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return value


def load_config_bundle(config_dir: str | Path) -> ConfigBundle:
    root = Path(config_dir)
    scenario_doc = _load(root / "scenarios.yaml")
    bundle = ConfigBundle(
        parameters=_load(root / "parameter_registry.yaml"),
        scales=_load(root / "scales.yaml"),
        environment=_load(root / "environment.yaml"),
        algorithm=_load(root / "algorithms" / "sr_mappo.yaml"),
        experiments=_load(root / "experiments" / "formal_matrix.yaml"),
        scenarios=dict(scenario_doc.get("scenarios", {})),
        scenario_status=str(scenario_doc.get("status", "")),
    )
    _validate(bundle)
    return bundle


def _validate(bundle: ConfigBundle) -> None:
    if bundle.algorithm.get("name") != "SR-MAPPO":
        raise ValueError("the flagship algorithm name must remain SR-MAPPO")
    total_updates = bundle.algorithm.get("total_updates")
    if type(total_updates) is not int or total_updates < 1:
        raise ValueError("algorithm total_updates must be a positive integer")
    rollout_horizon = bundle.algorithm.get("rollout_horizon")
    if type(rollout_horizon) is not int or rollout_horizon < 1:
        raise ValueError("algorithm rollout_horizon must be a positive integer")
    if bundle.environment.get("primary_vehicle_count") != 1:
        raise ValueError("the primary experiment must use one vehicle")
    max_candidate_slots = bundle.environment.get("max_candidate_slots")
    if type(max_candidate_slots) is not int or max_candidate_slots < 1:
        raise ValueError("max_candidate_slots must be a positive integer")
    expected_vehicle_actions = [
        "hold",
        *[f"slot-{index}" for index in range(max_candidate_slots)],
    ]
    if list(bundle.environment.get("vehicle_action_names", ())) != expected_vehicle_actions:
        raise ValueError("vehicle_action_names must match max_candidate_slots")
    if bundle.parameters.get("status") not in {"provisional", "verified"}:
        raise ValueError("parameter registry status must be provisional or verified")
    if bundle.scenario_status not in {"provisional", "verified"}:
        raise ValueError("scenario registry status must be provisional or verified")
    required_splits = {"train", "validation", "sealed_test"}
    if set(bundle.experiments.get("splits", [])) != required_splits:
        raise ValueError("formal matrix must declare train, validation and sealed_test")
    scenarios = bundle.scenarios
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("scenario registry must contain named scenarios")
    split_ids = {split: set() for split in required_splits}
    for scenario_id, record in scenarios.items():
        if not isinstance(record, dict) or record.get("split") not in required_splits:
            raise ValueError(f"scenario {scenario_id!r} must declare a valid split")
        if record.get("scale") not in {item.get("id") for item in bundle.scales.get("scales", [])}:
            raise ValueError(f"scenario {scenario_id!r} references an unknown scale")
        if type(record.get("seed_offset")) is not int:
            raise ValueError(f"scenario {scenario_id!r} seed_offset must be an integer")
        split_ids[str(record["split"])].add(str(scenario_id))
    if any(not values for values in split_ids.values()):
        raise ValueError("each train/validation/sealed_test split needs at least one scenario")
    for split, key in (("train", "train_scenarios"), ("validation", "validation_scenarios"), ("sealed_test", "sealed_test_scenarios")):
        declared = tuple(str(value) for value in bundle.experiments.get(key, ()))
        if set(declared) != split_ids[split] or len(declared) != len(set(declared)):
            raise ValueError(f"{key} must exactly match the frozen scenario registry")
    methods = tuple(bundle.experiments.get("methods", ()))
    canonical = ("sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage")
    if methods != canonical:
        forbidden = {"happo", "ag-sr-mappo", "AG-SR-MAPPO"}
        if any(str(method) in forbidden for method in methods):
            raise ValueError("HAPPO and AG-SR-MAPPO are forbidden method names")
        prefix = "no sr_mappo_mobile jobs; " if "sr_mappo_mobile" not in methods else ""
        raise ValueError(f"{prefix}formal matrix methods must equal canonical registry: {canonical}")


def _canonical(bundle: ConfigBundle) -> bytes:
    payload = {
        "parameters": bundle.parameters,
        "scales": bundle.scales,
        "environment": bundle.environment,
        "algorithm": bundle.algorithm,
        "experiments": bundle.experiments,
        "scenarios": bundle.scenarios,
        "scenario_status": bundle.scenario_status,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def config_identity(bundle: ConfigBundle) -> str:
    """Return the SHA-256 identity of the canonical configuration bundle."""

    return hashlib.sha256(_canonical(bundle)).hexdigest()
