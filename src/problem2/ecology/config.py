"""Immutable, versioned contracts for the Problem-2 dynamic ecology."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml


DYNAMIC_ECOLOGY_VERSION = "problem2-dynamic-pest-v1"


class DynamicEcologyConfigError(ValueError):
    """Raised when a frozen dynamic-ecology contract is invalid or drifts."""


_CONFIG_KEYS = frozenset(
    {
        "schema_version",
        "version",
        "assumption_status",
        "dynamic_wind",
        "replenished_resource",
        "battery_replenishment_enabled",
        "beta",
        "m",
        "s",
        "d1",
        "d2",
        "integration_interval",
        "substeps",
        "reaction_clip_bounds",
        "prey_extinction_threshold",
        "predator_low_prey_decay",
        "prey_advection_multiplier",
        "predator_advection_multiplier",
        "wind_strength_range",
        "wind_direction_noise_std",
        "wind_strength_noise_std",
        "wind_slow_direction_amplitude",
        "wind_slow_direction_period",
        "effect_amount",
        "effect_duration",
        "decay_rate",
        "spray_radius",
        "concentration_cap",
        "prey_mortality_scale",
        "prey_mortality_cap",
        "predator_sensitivity",
        "predator_mortality_cap",
    }
)
_LINEAGE_KEYS = frozenset(
    {
        "schema_version",
        "repository_path",
        "source_commit",
        "read_only",
        "runtime_import_allowed",
        "checkpoint_import_allowed",
        "output_or_result_import_allowed",
        "sources",
    }
)
_LINEAGE_SOURCE_KEYS = frozenset({"path", "blob_id", "adopted_design"})
_SHA1_RE = re.compile(r"[0-9a-f]{40}$")
_EXACT_NUMBERS = {
    "beta": 1.5,
    "m": 2.0,
    "s": 0.25,
    "d1": 0.3,
    "d2": 0.3,
    "integration_interval": 0.005,
    "prey_extinction_threshold": 1.0e-6,
    "predator_low_prey_decay": 0.1,
    "prey_advection_multiplier": 0.05,
    "predator_advection_multiplier": 0.01,
    "wind_direction_noise_std": 0.1,
    "wind_strength_noise_std": 0.05,
    "wind_slow_direction_amplitude": 0.005,
    "effect_amount": 0.85,
    "decay_rate": 0.92,
    "concentration_cap": 1.0,
    "prey_mortality_scale": 2.0,
    "prey_mortality_cap": 0.98,
    "predator_sensitivity": 0.1,
    "predator_mortality_cap": 0.3,
}
_EXACT_INTEGERS = {
    "substeps": 3,
    "wind_slow_direction_period": 50,
    "effect_duration": 15,
    "spray_radius": 4,
}
_APPROVED_LINEAGE = {
    "source/locust_rl_selected/models/holling_tanner.py": "3cd829a907d6931206a4045c3436a941bc1cacfc",
    "source/locust_rl_selected/models/subsystems.py": "245e9c46cb977629e3e22e09841693be7095db38",
    "source/locust_rl_selected/envs/locust_env.py": "dcc1527be19667daca41e310c69dde8775b6eb83",
    "source/locust_rl_selected/config/settings.py": "25bbd3afb90b5be1e0d267d3aabf938526ef5ae2",
}
_APPROVED_SOURCE_COMMIT = "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.Node
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise DynamicEcologyConfigError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise DynamicEcologyConfigError(f"cannot load YAML contract: {exc}") from exc
    if not isinstance(payload, dict):
        raise DynamicEcologyConfigError("contract root must be a mapping")
    return payload


def _require_keys(payload: dict[str, Any], expected: frozenset[str], name: str) -> None:
    unknown = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if unknown:
        raise DynamicEcologyConfigError(f"{name} contains unknown keys: {', '.join(unknown)}")
    if missing:
        raise DynamicEcologyConfigError(f"{name} is missing keys: {', '.join(missing)}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DynamicEcologyConfigError(f"{name} must be non-empty text")
    return value.strip()


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DynamicEcologyConfigError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise DynamicEcologyConfigError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise DynamicEcologyConfigError(f"{name} must be positive")
    return result


def _integer(value: Any, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DynamicEcologyConfigError(f"{name} must be an integer")
    if positive and value <= 0:
        raise DynamicEcologyConfigError(f"{name} must be positive")
    return value


def _strict_bool(value: Any, name: str, expected: bool) -> bool:
    if value is not expected:
        rendered = "true" if expected else "false"
        raise DynamicEcologyConfigError(f"{name} must be {rendered}")
    return expected


def _pair(value: Any, name: str, *, positive_upper: bool = False) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise DynamicEcologyConfigError(f"{name} must contain exactly two values")
    lower = _number(value[0], f"{name}[0]")
    upper = _number(value[1], f"{name}[1]")
    if lower >= upper:
        raise DynamicEcologyConfigError(f"{name} bounds must be increasing")
    if positive_upper and upper <= 0.0:
        raise DynamicEcologyConfigError(f"{name}[1] must be positive")
    return lower, upper


def _canonical_json_sha256(payload: dict[str, object]) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DynamicEcologyConfigError("contract cannot be canonically serialized") from exc
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DynamicEcologyConfig:
    """Validated normalized parameters for the versioned dynamic ecology."""

    schema_version: str
    version: str
    assumption_status: str
    dynamic_wind: bool
    replenished_resource: str
    battery_replenishment_enabled: bool
    beta: float
    m: float
    s: float
    d1: float
    d2: float
    integration_interval: float
    substeps: int
    reaction_clip_bounds: tuple[float, float]
    prey_extinction_threshold: float
    predator_low_prey_decay: float
    prey_advection_multiplier: float
    predator_advection_multiplier: float
    wind_strength_range: tuple[float, float]
    wind_direction_noise_std: float
    wind_strength_noise_std: float
    wind_slow_direction_amplitude: float
    wind_slow_direction_period: int
    effect_amount: float
    effect_duration: int
    decay_rate: float
    spray_radius: int
    concentration_cap: float
    prey_mortality_scale: float
    prey_mortality_cap: float
    predator_sensitivity: float
    predator_mortality_cap: float

    @classmethod
    def from_yaml(cls, path: Path) -> DynamicEcologyConfig:
        """Load the exact approved ecology contract from a YAML record."""

        payload = _load_yaml(Path(path))
        _require_keys(payload, _CONFIG_KEYS, "dynamic ecology configuration")
        schema_version = _text(payload["schema_version"], "schema_version")
        if schema_version != "problem2.dynamic-ecology.v1":
            raise DynamicEcologyConfigError("schema_version drifted")
        version = _text(payload["version"], "version")
        if version != DYNAMIC_ECOLOGY_VERSION:
            raise DynamicEcologyConfigError("version must preserve the dynamic ecology identity")
        assumption_status = _text(payload["assumption_status"], "assumption_status")
        if assumption_status != "provisional_normalized_simulation":
            raise DynamicEcologyConfigError("assumption_status drifted")
        dynamic_wind = _strict_bool(payload["dynamic_wind"], "dynamic_wind", True)
        replenished_resource = _text(
            payload["replenished_resource"], "replenished_resource"
        )
        if replenished_resource != "pesticide":
            raise DynamicEcologyConfigError("replenished_resource must be pesticide")
        battery_replenishment_enabled = _strict_bool(
            payload["battery_replenishment_enabled"],
            "battery replenishment",
            False,
        )

        numbers = {
            name: _number(payload[name], name, positive=True)
            for name in _EXACT_NUMBERS
        }
        for name, expected in _EXACT_NUMBERS.items():
            if numbers[name] != expected:
                raise DynamicEcologyConfigError(f"{name} drifted from the approved value")
        integers = {
            name: _integer(payload[name], name, positive=True)
            for name in _EXACT_INTEGERS
        }
        for name, expected in _EXACT_INTEGERS.items():
            if integers[name] != expected:
                raise DynamicEcologyConfigError(f"{name} drifted from the approved value")

        reaction_clip_bounds = _pair(payload["reaction_clip_bounds"], "reaction_clip_bounds")
        if reaction_clip_bounds != (-0.5, 0.5):
            raise DynamicEcologyConfigError("reaction_clip_bounds drifted")
        wind_strength_range = _pair(
            payload["wind_strength_range"], "wind_strength_range", positive_upper=True
        )
        if wind_strength_range != (0.0, 0.5):
            raise DynamicEcologyConfigError("wind_strength_range drifted")

        return cls(
            schema_version=schema_version,
            version=version,
            assumption_status=assumption_status,
            dynamic_wind=dynamic_wind,
            replenished_resource=replenished_resource,
            battery_replenishment_enabled=battery_replenishment_enabled,
            beta=numbers["beta"],
            m=numbers["m"],
            s=numbers["s"],
            d1=numbers["d1"],
            d2=numbers["d2"],
            integration_interval=numbers["integration_interval"],
            substeps=integers["substeps"],
            reaction_clip_bounds=reaction_clip_bounds,
            prey_extinction_threshold=numbers["prey_extinction_threshold"],
            predator_low_prey_decay=numbers["predator_low_prey_decay"],
            prey_advection_multiplier=numbers["prey_advection_multiplier"],
            predator_advection_multiplier=numbers["predator_advection_multiplier"],
            wind_strength_range=wind_strength_range,
            wind_direction_noise_std=numbers["wind_direction_noise_std"],
            wind_strength_noise_std=numbers["wind_strength_noise_std"],
            wind_slow_direction_amplitude=numbers["wind_slow_direction_amplitude"],
            wind_slow_direction_period=integers["wind_slow_direction_period"],
            effect_amount=numbers["effect_amount"],
            effect_duration=integers["effect_duration"],
            decay_rate=numbers["decay_rate"],
            spray_radius=integers["spray_radius"],
            concentration_cap=numbers["concentration_cap"],
            prey_mortality_scale=numbers["prey_mortality_scale"],
            prey_mortality_cap=numbers["prey_mortality_cap"],
            predator_sensitivity=numbers["predator_sensitivity"],
            predator_mortality_cap=numbers["predator_mortality_cap"],
        )

    def canonical_payload(self) -> dict[str, object]:
        """Return the canonical, JSON-safe contract representation."""

        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "assumption_status": self.assumption_status,
            "dynamic_wind": self.dynamic_wind,
            "replenished_resource": self.replenished_resource,
            "battery_replenishment_enabled": self.battery_replenishment_enabled,
            "beta": self.beta,
            "m": self.m,
            "s": self.s,
            "d1": self.d1,
            "d2": self.d2,
            "integration_interval": self.integration_interval,
            "substeps": self.substeps,
            "reaction_clip_bounds": list(self.reaction_clip_bounds),
            "prey_extinction_threshold": self.prey_extinction_threshold,
            "predator_low_prey_decay": self.predator_low_prey_decay,
            "prey_advection_multiplier": self.prey_advection_multiplier,
            "predator_advection_multiplier": self.predator_advection_multiplier,
            "wind_strength_range": list(self.wind_strength_range),
            "wind_direction_noise_std": self.wind_direction_noise_std,
            "wind_strength_noise_std": self.wind_strength_noise_std,
            "wind_slow_direction_amplitude": self.wind_slow_direction_amplitude,
            "wind_slow_direction_period": self.wind_slow_direction_period,
            "effect_amount": self.effect_amount,
            "effect_duration": self.effect_duration,
            "decay_rate": self.decay_rate,
            "spray_radius": self.spray_radius,
            "concentration_cap": self.concentration_cap,
            "prey_mortality_scale": self.prey_mortality_scale,
            "prey_mortality_cap": self.prey_mortality_cap,
            "predator_sensitivity": self.predator_sensitivity,
            "predator_mortality_cap": self.predator_mortality_cap,
        }

    @property
    def contract_sha256(self) -> str:
        return _canonical_json_sha256(self.canonical_payload())


def _git_text(repository: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise DynamicEcologyConfigError("Git is unavailable for Problem-1 lineage resolution") from exc
    if completed.returncode != 0:
        raise DynamicEcologyConfigError(f"Problem-1 lineage resolution failed: {' '.join(args)}")
    return completed.stdout.strip()


def verify_problem1_lineage(path: Path, *, resolve_git: bool = True) -> dict[str, str]:
    """Validate the frozen read-only Problem-1 source lineage registry."""

    payload = _load_yaml(Path(path))
    _require_keys(payload, _LINEAGE_KEYS, "Problem-1 lineage")
    if _text(payload["schema_version"], "schema_version") != "problem2.dynamic-pest-lineage.v1":
        raise DynamicEcologyConfigError("Problem-1 lineage schema_version drifted")
    repository_path = _text(payload["repository_path"], "repository_path")
    source_commit = _text(payload["source_commit"], "source commit")
    if source_commit != _APPROVED_SOURCE_COMMIT:
        raise DynamicEcologyConfigError("Problem-1 source commit drifted")
    _strict_bool(payload["read_only"], "Problem-1 read-only", True)
    _strict_bool(payload["runtime_import_allowed"], "Problem-1 runtime import", False)
    _strict_bool(payload["checkpoint_import_allowed"], "Problem-1 checkpoint import", False)
    _strict_bool(payload["output_or_result_import_allowed"], "Problem-1 output import", False)

    sources = payload["sources"]
    if not isinstance(sources, list) or len(sources) != len(_APPROVED_LINEAGE):
        raise DynamicEcologyConfigError("Problem-1 lineage must contain exactly four sources")
    observed: dict[str, str] = {}
    for index, raw_source in enumerate(sources):
        if not isinstance(raw_source, dict):
            raise DynamicEcologyConfigError(f"Problem-1 sources[{index}] must be a mapping")
        _require_keys(raw_source, _LINEAGE_SOURCE_KEYS, f"Problem-1 sources[{index}]")
        source_path = _text(raw_source["path"], f"Problem-1 sources[{index}].path")
        blob_id = _text(raw_source["blob_id"], f"Problem-1 sources[{index}].blob_id")
        if not _SHA1_RE.fullmatch(blob_id):
            raise DynamicEcologyConfigError(f"Problem-1 blob ID is invalid: {source_path}")
        if source_path in observed:
            raise DynamicEcologyConfigError(f"duplicate Problem-1 lineage path: {source_path}")
        observed[source_path] = blob_id
        _text(raw_source["adopted_design"], f"Problem-1 sources[{index}].adopted_design")
    if observed != _APPROVED_LINEAGE:
        raise DynamicEcologyConfigError("Problem-1 source blob lineage drifted")

    if resolve_git:
        repository = Path(repository_path)
        if not repository.is_dir():
            raise DynamicEcologyConfigError("Problem-1 repository path is unavailable")
        resolved_commit = _git_text(repository, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
        if resolved_commit != source_commit:
            raise DynamicEcologyConfigError("Problem-1 source commit is unresolved")
        for source_path, blob_id in observed.items():
            listing = _git_text(repository, "ls-tree", source_commit, "--", source_path)
            parts = listing.split(maxsplit=3)
            if len(parts) != 4 or parts[1] != "blob" or parts[2] != blob_id:
                raise DynamicEcologyConfigError(f"Problem-1 blob does not resolve: {source_path}")

    return {
        "repository_path": repository_path,
        "source_commit": source_commit,
        "read_only": "true",
        "runtime_import_allowed": "false",
        "checkpoint_import_allowed": "false",
        "output_or_result_import_allowed": "false",
    }


__all__ = [
    "DYNAMIC_ECOLOGY_VERSION",
    "DynamicEcologyConfig",
    "DynamicEcologyConfigError",
    "verify_problem1_lineage",
]
