from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml


class G4ContractError(ValueError):
    """Raised when a frozen G4 contract or probe manifest is invalid."""


@dataclass(frozen=True)
class G4Contract:
    source_path: Path | None
    scarcity_axis: str
    admissible_band: tuple[float, float]
    probe_scales: tuple[str, ...]
    probe_seeds: tuple[int, ...]
    comparator_pair: tuple[str, str]
    metrics: tuple[str, ...]
    output_root: Path
    permitted_claim_boundary: str


@dataclass(frozen=True)
class G4ProbeManifest:
    source_path: Path | None
    probe_scales: tuple[str, ...]
    probe_seeds: tuple[int, ...]
    horizon_by_scale: Mapping[str, int]
    validation_access_allowed: bool
    sealed_test_access_allowed: bool


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.Node
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise G4ContractError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise G4ContractError(f"{name} must be a mapping")
    return value


def _require_keys(mapping: dict[str, Any], expected: set[str], name: str) -> None:
    extra = sorted(set(mapping) - expected)
    missing = sorted(expected - set(mapping))
    if extra:
        raise G4ContractError(f"{name} contains unknown keys: {', '.join(extra)}")
    if missing:
        raise G4ContractError(f"{name} is missing keys: {', '.join(missing)}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise G4ContractError(f"{name} must be non-empty text")
    return value.strip()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise G4ContractError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise G4ContractError(f"{name} must be finite")
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise G4ContractError(f"{name} must be an integer")
    return value


def _text_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise G4ContractError(f"{name} must be a non-empty list")
    result = tuple(_text(item, f"{name}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise G4ContractError(f"{name} must not contain duplicates")
    return result


def _integer_tuple(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise G4ContractError(f"{name} must be a non-empty list")
    result = tuple(_integer(item, f"{name}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise G4ContractError(f"{name} must not contain duplicates")
    return result


def _load(path: Path, loader: type[yaml.SafeLoader]) -> Any:
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=loader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise G4ContractError(f"cannot load G4 YAML: {exc}") from exc


def load_g4_contract(path: Path | str) -> G4Contract:
    """Load the fail-closed G4 scarcity and counterfactual contract."""

    contract_path = Path(path)
    root = _mapping(_load(contract_path, _UniqueKeyLoader), "contract")
    _require_keys(
        root,
        {
            "schema_version", "registry_id", "status", "algorithm_name",
            "problem_description", "scarcity_axis", "scarcity_band",
            "probe_scales", "probe_seeds", "comparator_pair", "metrics",
            "output_root", "permitted_claim_boundary", "resources",
            "endpoint_evidence_roots",
        },
        "contract",
    )
    if root["schema_version"] != "g4.v1":
        raise G4ContractError("schema_version must be g4.v1")
    if root["registry_id"] != "G4-RESOURCE-SCARCITY-COUNTERFACTUAL":
        raise G4ContractError("registry_id must identify the G4 contract")
    if root["status"] != "design_frozen":
        raise G4ContractError("G4 contract must be design_frozen")
    if root["algorithm_name"] != "SR-MAPPO":
        raise G4ContractError("the public algorithm name must remain SR-MAPPO")
    if root["problem_description"] != "air_ground_heterogeneous_extension":
        raise G4ContractError("problem_description must remain the air-ground extension")

    band = _mapping(root["scarcity_band"], "scarcity_band")
    if "lower" not in band or "upper" not in band:
        raise G4ContractError("scarcity_band requires lower and upper bounds")
    _require_keys(band, {"lower", "upper", "unit"}, "scarcity_band")
    lower = _number(band["lower"], "scarcity_band.lower")
    upper = _number(band["upper"], "scarcity_band.upper")
    if lower >= upper:
        raise G4ContractError("scarcity_band lower must be less than upper")
    if _text(band["unit"], "scarcity_band.unit") != "L":
        raise G4ContractError("scarcity_band.unit must be L")

    scales = _text_tuple(root["probe_scales"], "probe_scales")
    seeds = _integer_tuple(root["probe_seeds"], "probe_seeds")
    if any(20000 <= seed <= 20049 or 30000 <= seed <= 30099 for seed in seeds):
        raise G4ContractError("validation and sealed probe seeds are forbidden")
    pair = _text_tuple(root["comparator_pair"], "comparator_pair")
    if pair != ("sr_mappo_fixed", "sr_mappo_mobile"):
        raise G4ContractError("comparator_pair must be fixed versus mobile SR-MAPPO")
    metrics = _text_tuple(root["metrics"], "metrics")
    output_root = Path(_text(root["output_root"], "output_root"))
    if output_root.as_posix() == "outputs/problem2_sr_mappo_v1/g3":
        raise G4ContractError("G3 output-root paths cannot be endpoint evidence")
    if output_root.as_posix() != "outputs/problem2_sr_mappo_v1/g4":
        raise G4ContractError("output_root must be the frozen G4 output root")
    endpoint_roots = _text_tuple(root["endpoint_evidence_roots"], "endpoint_evidence_roots")
    if any("/g3" in item or item.endswith("\\g3") for item in endpoint_roots):
        raise G4ContractError("G3 output-root paths cannot be endpoint evidence")
    resources = _mapping(root["resources"], "resources")
    _require_keys(resources, {"replenished_resource", "battery_replenishment_enabled"}, "resources")
    if _text(resources["replenished_resource"], "resources.replenished_resource") != "pesticide":
        raise G4ContractError("the replenished resource must be pesticide")
    if resources["battery_replenishment_enabled"] is not False:
        raise G4ContractError("battery replenishment must remain disabled")

    return G4Contract(
        source_path=contract_path,
        scarcity_axis=_text(root["scarcity_axis"], "scarcity_axis"),
        admissible_band=(lower, upper),
        probe_scales=scales,
        probe_seeds=seeds,
        comparator_pair=pair,
        metrics=metrics,
        output_root=output_root,
        permitted_claim_boundary=_text(root["permitted_claim_boundary"], "permitted_claim_boundary"),
    )


def load_g4_probe_manifest(path: Path | str) -> G4ProbeManifest:
    """Load the exact non-validation, non-sealed G4 probe subset."""

    manifest_path = Path(path)
    root = _mapping(_load(manifest_path, _UniqueKeyLoader), "probe manifest")
    _require_keys(
        root,
        {
            "schema_version", "manifest_id", "status", "probe_scales",
            "probe_seeds", "horizon_by_scale", "probe_partitions",
            "validation_access_allowed", "sealed_test_access_allowed",
        },
        "probe manifest",
    )
    if root["schema_version"] != "g4.v1":
        raise G4ContractError("probe manifest schema_version must be g4.v1")
    if root["manifest_id"] != "G4-PROBE-MANIFEST":
        raise G4ContractError("manifest_id must identify the G4 probe manifest")
    if root["status"] != "design_frozen":
        raise G4ContractError("G4 probe manifest must be design_frozen")
    scales = _text_tuple(root["probe_scales"], "probe manifest.probe_scales")
    seeds = _integer_tuple(root["probe_seeds"], "probe manifest.probe_seeds")
    if any(20000 <= seed <= 20049 or 30000 <= seed <= 30099 for seed in seeds):
        raise G4ContractError("validation and sealed probe seeds are forbidden")
    horizons = _mapping(root["horizon_by_scale"], "horizon_by_scale")
    if set(horizons) != set(scales):
        raise G4ContractError("horizon_by_scale must match the exact probe scales")
    horizon_by_scale = {key: _integer(value, f"horizon_by_scale.{key}") for key, value in horizons.items()}
    if any(value <= 0 for value in horizon_by_scale.values()):
        raise G4ContractError("probe horizons must be positive")
    partitions = _mapping(root["probe_partitions"], "probe_partitions")
    _require_keys(partitions, {"training", "validation", "sealed_test"}, "probe_partitions")
    if partitions["training"] != list(seeds):
        raise G4ContractError("training probe IDs must equal the frozen probe seeds")
    if partitions["validation"] or partitions["sealed_test"]:
        raise G4ContractError("validation and sealed probe IDs are forbidden")
    if root["validation_access_allowed"] is not False:
        raise G4ContractError("validation access must remain disabled")
    if root["sealed_test_access_allowed"] is not False:
        raise G4ContractError("sealed-test access must remain disabled")
    return G4ProbeManifest(
        source_path=manifest_path,
        probe_scales=scales,
        probe_seeds=seeds,
        horizon_by_scale=MappingProxyType(horizon_by_scale),
        validation_access_allowed=False,
        sealed_test_access_allowed=False,
    )
