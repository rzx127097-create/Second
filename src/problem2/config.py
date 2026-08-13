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


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return value


def load_config_bundle(config_dir: str | Path) -> ConfigBundle:
    root = Path(config_dir)
    bundle = ConfigBundle(
        parameters=_load(root / "parameter_registry.yaml"),
        scales=_load(root / "scales.yaml"),
        environment=_load(root / "environment.yaml"),
        algorithm=_load(root / "algorithms" / "sr_mappo.yaml"),
        experiments=_load(root / "experiments" / "formal_matrix.yaml"),
    )
    _validate(bundle)
    return bundle


def _validate(bundle: ConfigBundle) -> None:
    if bundle.algorithm.get("name") != "SR-MAPPO":
        raise ValueError("the flagship algorithm name must remain SR-MAPPO")
    if bundle.environment.get("primary_vehicle_count") != 1:
        raise ValueError("the primary experiment must use one vehicle")
    if bundle.parameters.get("status") not in {"provisional", "verified"}:
        raise ValueError("parameter registry status must be provisional or verified")
    required_splits = {"train", "validation", "sealed_test"}
    if set(bundle.experiments.get("splits", [])) != required_splits:
        raise ValueError("formal matrix must declare train, validation and sealed_test")


def _canonical(bundle: ConfigBundle) -> bytes:
    payload = {
        "parameters": bundle.parameters,
        "scales": bundle.scales,
        "environment": bundle.environment,
        "algorithm": bundle.algorithm,
        "experiments": bundle.experiments,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def config_identity(bundle: ConfigBundle) -> str:
    """Return the SHA-256 identity of the canonical configuration bundle."""

    return hashlib.sha256(_canonical(bundle)).hexdigest()
