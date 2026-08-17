"""Evidence and formal-experiment readiness audits.

The audits in this module are deliberately conservative.  They validate the
shape and provenance of evidence; they do not decide whether an equipment
manual or field study is scientifically applicable to a particular farm.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from problem2.road.graphml import load_graphml


REQUIRED_PARAMETER_NAMES = (
    "decision_dt",
    "rendezvous_radius",
    "service_setup_time",
    "uav_onboard_pesticide",
    "uav_spray_flow",
    "uav_speed",
    "uav_usable_fraction",
    "vehicle_inventory",
    "vehicle_service_capacity",
    "request_safety_margin",
    "vehicle_speed",
    "vehicle_transfer_rate",
)
ALLOWED_SOURCE_TYPES = {
    "manual",
    "standard",
    "field-study",
    "peer-reviewed-study",
    "expert",
    "assumption",
}


@dataclass(frozen=True)
class AuditIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class AuditReport:
    name: str
    status: str
    ready: bool
    issues: tuple[AuditIssue, ...] = ()
    evidence_paths: tuple[str, ...] = ()
    missing_parameters: tuple[str, ...] = ()
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "ready": self.ready,
            "issues": [issue.to_dict() for issue in self.issues],
            "evidence_paths": list(self.evidence_paths),
            "missing_parameters": list(self.missing_parameters),
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True)
class ReadinessReport:
    """Repository-level formal gate with explicit blockers and provenance."""

    formal_ready: bool
    highest_gate: str
    gates: tuple[dict[str, object], ...]
    blockers: tuple[str, ...]
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "formal_ready": self.formal_ready,
            "highest_gate": self.highest_gate,
            "gates": [dict(gate) for gate in self.gates],
            "blockers": list(self.blockers),
            "details": dict(self.details),
        }


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def audit_parameter_registry(document: Mapping[str, Any]) -> AuditReport:
    """Audit engineering parameter provenance, ranges and unit conversion.

    Assumption records are accepted for smoke/pilot execution but remain
    blocking for formal evidence.  A record marked ``verified`` must carry a
    non-placeholder source, source value/unit and reproducible conversion.
    """

    status = str(document.get("status", ""))
    parameters = document.get("parameters", {})
    issues: list[AuditIssue] = []
    if not isinstance(parameters, Mapping):
        return AuditReport(
            name="parameters",
            status=status,
            ready=False,
            issues=(AuditIssue("invalid_registry", "parameters", "parameters must be a mapping"),),
            missing_parameters=REQUIRED_PARAMETER_NAMES,
        )

    missing = tuple(name for name in REQUIRED_PARAMETER_NAMES if name not in parameters)
    for name in missing:
        issues.append(AuditIssue("missing_parameter", f"parameters.{name}", "required engineering parameter is absent"))

    for name, raw in parameters.items():
        path = f"parameters.{name}"
        if not isinstance(raw, Mapping):
            issues.append(AuditIssue("invalid_record", path, "parameter record must be a mapping"))
            continue
        value = raw.get("value")
        lower = raw.get("min")
        upper = raw.get("max")
        if not _finite_number(value):
            issues.append(AuditIssue("invalid_value", f"{path}.value", "value must be finite numeric"))
        if not _finite_number(lower) or not _finite_number(upper) or float(lower) > float(upper):
            issues.append(AuditIssue("invalid_range", path, "min/max must be finite and min <= max"))
        elif _finite_number(value) and not float(lower) <= float(value) <= float(upper):
            issues.append(AuditIssue("value_out_of_range", f"{path}.value", "value lies outside declared engineering range"))

        source_type = str(raw.get("source_type", ""))
        source_id = str(raw.get("source_id", ""))
        source_value = raw.get("source_value")
        source_unit = raw.get("source_unit")
        conversion = raw.get("conversion")
        if source_type not in ALLOWED_SOURCE_TYPES:
            issues.append(AuditIssue("invalid_source_type", f"{path}.source_type", "unsupported source_type"))
        if not str(raw.get("unit", "")).strip():
            issues.append(AuditIssue("missing_unit", f"{path}.unit", "simulation unit is required"))
        if source_type == "assumption" or not source_id or source_id.startswith("pending-"):
            issues.append(AuditIssue("unverified_source", path, "parameter is an assumption or has a placeholder source"))
        if status == "verified" and source_type == "assumption":
            issues.append(AuditIssue("verified_assumption", path, "verified registry cannot contain assumption records"))
        if source_type != "assumption":
            if not _finite_number(source_value):
                issues.append(AuditIssue("missing_source_value", f"{path}.source_value", "source_value is required for sourced parameters"))
            if not str(source_unit or "").strip():
                issues.append(AuditIssue("missing_source_unit", f"{path}.source_unit", "source_unit is required for sourced parameters"))
            if not isinstance(conversion, str) or not conversion.strip():
                issues.append(AuditIssue("missing_conversion", f"{path}.conversion", "conversion formula is required"))
            if str(source_unit or "").strip() != str(raw.get("unit", "")).strip() and conversion == "value = source_value":
                issues.append(AuditIssue("unit_mismatch", f"{path}.conversion", "different source/simulation units need an explicit conversion"))
        if not str(raw.get("scope", "")).strip():
            issues.append(AuditIssue("missing_scope", f"{path}.scope", "scope must identify main, sensitivity or extension use"))

    blocking = tuple(issues)
    ready = status == "verified" and not blocking and not missing
    return AuditReport(
        name="parameters",
        status=status,
        ready=ready,
        issues=blocking,
        missing_parameters=missing,
    )


def audit_parameter_file(path: str | Path) -> AuditReport:
    """Load YAML/JSON-like parameter registry and return its audit report."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, Mapping):
        return AuditReport(
            name="parameters",
            status="",
            ready=False,
            issues=(AuditIssue("invalid_registry", str(source), "registry root must be a mapping"),),
        )
    return audit_parameter_registry(document)


def audit_scenario_registry(
    scenarios_document: Mapping[str, Any],
    scales_document: Mapping[str, Any],
    matrix_document: Mapping[str, Any],
) -> AuditReport:
    """Audit scenario split isolation and physical-scale consistency."""

    issues: list[AuditIssue] = []
    scenarios = scenarios_document.get("scenarios", {})
    scale_records = scales_document.get("scales", [])
    if not isinstance(scenarios, Mapping):
        return AuditReport(
            name="scenarios",
            status=str(scenarios_document.get("status", "")),
            ready=False,
            issues=(AuditIssue("invalid_registry", "scenarios", "scenarios must be a mapping"),),
        )
    if not isinstance(scale_records, list) or not scale_records:
        return AuditReport(
            name="scenarios",
            status=str(scenarios_document.get("status", "")),
            ready=False,
            issues=(AuditIssue("invalid_scale_registry", "scales", "scales must be a non-empty list"),),
        )
    if str(scenarios_document.get("status", "")) != "verified" or str(scales_document.get("status", "")) != "verified" or str(matrix_document.get("status", "")) != "verified":
        issues.append(AuditIssue("registry_provisional", "status", "scenario, scale and matrix registries must all be verified"))
    source_hash = str(scenarios_document.get("source_metadata_hash", ""))
    if (
        not str(scenarios_document.get("source_kind", "")).strip()
        or not str(scenarios_document.get("dynamics_kind", "")).strip()
        or len(source_hash) != 64
    ):
        issues.append(AuditIssue("missing_source_metadata", "scenarios", "source_kind, dynamics_kind and a SHA-256 source_metadata_hash are required"))

    known_scales: dict[str, Mapping[str, Any]] = {}
    physical_extent = scales_document.get("physical_extent_m")
    if not isinstance(physical_extent, (list, tuple)) or len(physical_extent) != 2 or any(not _finite_number(value) or float(value) <= 0 for value in physical_extent):
        issues.append(AuditIssue("invalid_physical_extent", "physical_extent_m", "physical_extent_m must contain two positive numbers"))
        extent = (0.0, 0.0)
    else:
        extent = (float(physical_extent[0]), float(physical_extent[1]))
    cell_sizes: dict[str, list[float]] = {}
    for item in scale_records:
        if not isinstance(item, Mapping):
            issues.append(AuditIssue("invalid_scale", "scales", "scale record must be a mapping"))
            continue
        scale_id = str(item.get("id", ""))
        grid = item.get("grid")
        if not scale_id or not isinstance(grid, (list, tuple)) or len(grid) != 2 or any(type(value) is not int or value <= 0 for value in grid):
            issues.append(AuditIssue("invalid_scale", f"scales.{scale_id or '<missing>'}", "grid must contain two positive integers and id is required"))
            continue
        if scale_id in known_scales:
            issues.append(AuditIssue("duplicate_scale_id", f"scales.{scale_id}", "scale id is duplicated"))
        known_scales[scale_id] = item
        if extent[0] > 0 and extent[1] > 0:
            cell_sizes[scale_id] = [extent[0] / int(grid[0]), extent[1] / int(grid[1])]

    split_ids: dict[str, set[str]] = {"train": set(), "validation": set(), "sealed_test": set()}
    offsets: dict[int, str] = {}
    declared_ids: set[str] = set()
    for scenario_key, raw in scenarios.items():
        key = str(scenario_key)
        if not isinstance(raw, Mapping):
            issues.append(AuditIssue("invalid_scenario", f"scenarios.{key}", "scenario record must be a mapping"))
            continue
        declared_id = str(raw.get("scenario_id", key))
        if declared_id in declared_ids:
            issues.append(AuditIssue("duplicate_scenario_id", f"scenarios.{key}", "scenario_id is duplicated"))
        declared_ids.add(declared_id)
        split = str(raw.get("split", ""))
        scale = str(raw.get("scale", ""))
        offset = raw.get("seed_offset")
        if split not in split_ids:
            issues.append(AuditIssue("invalid_split", f"scenarios.{key}.split", "split must be train, validation or sealed_test"))
        else:
            split_ids[split].add(key)
        if scale not in known_scales:
            issues.append(AuditIssue("unknown_scale", f"scenarios.{key}.scale", "scenario references an unknown scale"))
        if type(offset) is not int:
            issues.append(AuditIssue("invalid_seed_offset", f"scenarios.{key}.seed_offset", "seed_offset must be an integer"))
        elif offset in offsets:
            issues.append(AuditIssue("duplicate_seed_offset", f"scenarios.{key}.seed_offset", f"seed_offset is already used by {offsets[offset]}"))
        else:
            offsets[offset] = key

    if set().union(*split_ids.values()) != set(scenarios):
        issues.append(AuditIssue("split_overlap", "scenarios", "every scenario must belong to exactly one registered split"))
    for split, key in (("train", "train_scenarios"), ("validation", "validation_scenarios"), ("sealed_test", "sealed_test_scenarios")):
        declared = tuple(str(value) for value in matrix_document.get(key, ()))
        if set(declared) != split_ids[split] or len(declared) != len(set(declared)):
            issues.append(AuditIssue("matrix_split_mismatch", key, "formal matrix split list must exactly match scenario registry"))
    scale_coverage = {
        split: {scale: sum(1 for scenario_id in ids if str(scenarios[scenario_id].get("scale")) == scale) for scale in known_scales}
        for split, ids in split_ids.items()
    }
    for split, counts in scale_coverage.items():
        for scale, count in counts.items():
            if count < 1:
                issues.append(AuditIssue("missing_scale_coverage", f"{split}.{scale}", "each split needs at least one independent scenario per scale"))
    details = {
        "split_counts": {split: len(ids) for split, ids in split_ids.items()},
        "scale_coverage": scale_coverage,
        "cell_size_m": cell_sizes,
        "seed_offset_count": len(offsets),
        "scale_ids": sorted(known_scales),
    }
    return AuditReport(
        name="scenarios",
        status=str(scenarios_document.get("status", "")),
        ready=not issues,
        issues=tuple(issues),
        details=details,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return dict(value)


def audit_repository_readiness(
    config_dir: str | Path,
    *,
    resource_report: Mapping[str, object] | None = None,
) -> ReadinessReport:
    """Run the shared formal gate used by training and sealed-test tooling."""

    root = Path(config_dir).resolve()
    parameters = _load_yaml(root / "parameter_registry.yaml")
    scenarios = _load_yaml(root / "scenarios.yaml")
    scales = _load_yaml(root / "scales.yaml")
    environment = _load_yaml(root / "environment.yaml")
    algorithm = _load_yaml(root / "algorithms" / "sr_mappo.yaml")
    matrix = _load_yaml(root / "experiments" / "formal_matrix.yaml")
    protocol = _load_yaml(root / "experiments" / "chapter4_5.yaml")
    field_dynamics = _load_yaml(root / "field_dynamics.yaml")

    parameter_report = audit_parameter_registry(parameters)
    scenario_report = audit_scenario_registry(scenarios, scales, matrix)
    gates: list[dict[str, object]] = [
        {"name": "parameters", "ready": parameter_report.ready, "status": parameter_report.status, "issues": [issue.to_dict() for issue in parameter_report.issues]},
        {"name": "scenarios", "ready": scenario_report.ready, "status": scenario_report.status, "issues": [issue.to_dict() for issue in scenario_report.issues]},
    ]

    road = environment.get("road", {})
    road_ready = False
    road_issues: list[dict[str, str]] = []
    road_metadata: dict[str, object] = {}
    if not isinstance(road, Mapping):
        road_issues.append({"code": "invalid_road_config", "message": "environment.road must be a mapping"})
    elif str(road.get("source")) != "frozen_gis":
        road_issues.append({"code": "road_not_frozen", "message": "road source is not declared as frozen_gis"})
    else:
        graphml_path = road.get("graphml_path")
        origin = road.get("origin_lonlat")
        if not graphml_path:
            road_issues.append({"code": "missing_graphml_path", "message": "frozen_gis requires graphml_path"})
        if not isinstance(origin, (list, tuple)) or len(origin) != 2:
            road_issues.append({"code": "missing_projection_origin", "message": "frozen_gis requires origin_lonlat"})
        if graphml_path and isinstance(origin, (list, tuple)) and len(origin) == 2:
            try:
                graphml_source = Path(str(graphml_path))
                if not graphml_source.is_absolute():
                    graphml_source = root.parent / graphml_source
                _graph, road_metadata = load_graphml(
                    graphml_source,
                    coordinate_mode=str(road.get("coordinate_mode", "lonlat")),
                    origin_lonlat=(float(origin[0]), float(origin[1])),
                    directed_policy=str(road.get("directed_policy", "undirected")),
                )
                expected_hash = str(road.get("source_sha256", ""))
                if expected_hash != road_metadata["source_sha256"]:
                    road_issues.append({"code": "source_hash_mismatch", "message": "configured road source_sha256 does not match the read-only file"})
                metadata_path = road.get("cache_metadata_path")
                metadata_file = Path(str(metadata_path)) if metadata_path else None
                if metadata_file is not None and not metadata_file.is_absolute():
                    metadata_file = root.parent / metadata_file
                if metadata_file is None or not metadata_file.is_file():
                    road_issues.append({"code": "missing_road_metadata", "message": "cache_metadata_path must point to the audited metadata JSON"})
                else:
                    metadata_hash = hashlib.sha256(metadata_file.read_bytes()).hexdigest()
                    expected_metadata_hash = str(road.get("source_metadata_sha256", ""))
                    if expected_metadata_hash and expected_metadata_hash != metadata_hash:
                        road_issues.append({"code": "metadata_hash_mismatch", "message": "source_metadata_sha256 does not match the audited metadata JSON"})
                    try:
                        frozen_payload = json.loads(metadata_file.read_text(encoding="utf-8"))
                        derived_hash = str(frozen_payload.get("derived", {}).get("sha256", ""))
                        if derived_hash and derived_hash != road_metadata.get("source_sha256"):
                            road_issues.append({"code": "derived_hash_mismatch", "message": "road metadata derived hash does not match the configured GraphML"})
                        if frozen_payload.get("ready") is not True:
                            road_issues.append({"code": "road_derivation_not_ready", "message": "frozen road derivation metadata is not marked ready"})
                    except (OSError, json.JSONDecodeError, AttributeError) as exc:
                        road_issues.append({"code": "invalid_road_metadata", "message": str(exc)})
            except Exception as exc:  # noqa: BLE001 - preserve exact source failure in report
                road_issues.append({"code": type(exc).__name__, "message": str(exc)})
    road_ready = not road_issues
    gates.append({"name": "road_source", "ready": road_ready, "status": str(road.get("source_status", "")) if isinstance(road, Mapping) else "", "issues": road_issues})

    algorithm_issues: list[dict[str, str]] = []
    if algorithm.get("name") != "SR-MAPPO":
        algorithm_issues.append({"code": "algorithm_name", "message": "flagship algorithm must remain SR-MAPPO"})
    if str(algorithm.get("status", "")) != "verified":
        algorithm_issues.append({"code": "registry_provisional", "message": "SR-MAPPO algorithm configuration is provisional"})
    gates.append({"name": "algorithm", "ready": not algorithm_issues, "status": str(algorithm.get("status", "")), "issues": algorithm_issues})

    dynamics_issues: list[dict[str, str]] = []
    if str(field_dynamics.get("model", "")) != "reaction_diffusion_advection_exposure":
        dynamics_issues.append({"code": "dynamics_model", "message": "field dynamics must be the declared reaction-diffusion-advection-exposure model"})
    if str(field_dynamics.get("status", "")) != "verified":
        dynamics_issues.append({"code": "dynamics_provisional", "message": "field dynamics parameters require crop-, wind- and pesticide-specific calibration"})
    dynamics_parameters = field_dynamics.get("parameters", {})
    required_dynamics = {
        "pest_growth_rate_s", "pest_carrying_capacity", "pest_diffusion_rate_m2_s",
        "wind_vx_m_s", "wind_vy_m_s", "pesticide_decay_rate_s",
        "pesticide_diffusion_rate_m2_s", "pesticide_efficacy_per_l",
        "pest_mortality_per_exposure",
    }
    if not isinstance(dynamics_parameters, Mapping) or not required_dynamics.issubset(dynamics_parameters):
        dynamics_issues.append({"code": "dynamics_parameters", "message": "all reaction, diffusion, advection and exposure parameters are required"})
    gates.append({"name": "field_dynamics", "ready": not dynamics_issues, "status": str(field_dynamics.get("status", "")), "issues": dynamics_issues})

    protocol_issues: list[dict[str, str]] = []
    if str(protocol.get("status", "")) != "verified" or str(matrix.get("status", "")) != "verified":
        protocol_issues.append({"code": "registry_provisional", "message": "Chapter 4.5 protocol and formal matrix must be verified"})
    statistics = protocol.get("statistics", {})
    margin = statistics.get("practical_equivalence_margin") if isinstance(statistics, Mapping) else None
    basis = statistics.get("practical_equivalence_basis") if isinstance(statistics, Mapping) else None
    if not isinstance(margin, (int, float)) or isinstance(margin, bool) or not math.isfinite(float(margin)) or float(margin) <= 0:
        protocol_issues.append({"code": "missing_equivalence_margin", "message": "a positive practical equivalence margin is required"})
    if not isinstance(basis, str) or not basis.strip():
        protocol_issues.append({"code": "missing_equivalence_basis", "message": "the practical equivalence basis is required"})
    gates.append({"name": "protocol", "ready": not protocol_issues, "status": str(protocol.get("status", "")), "issues": protocol_issues})

    resource_ready = bool(resource_report and resource_report.get("activated") is True)
    resource_issues = [] if resource_ready else [{"code": "resource_activation_pending", "message": "resource counterfactual pilot has not established an active bottleneck"}]
    gates.append({"name": "resource_activation", "ready": resource_ready, "status": "observed" if resource_report else "pending", "issues": resource_issues})

    blockers = tuple(
        f"{gate['name']}: {issue.get('message', issue.get('code', 'unresolved'))}"
        for gate in gates
        if not gate["ready"]
        for issue in gate.get("issues", [])
    )
    formal_names = {"parameters", "scenarios", "road_source", "algorithm", "field_dynamics", "protocol", "resource_activation"}
    formal_ready = all(bool(gate["ready"]) for gate in gates if gate["name"] in formal_names)
    return ReadinessReport(
        formal_ready=formal_ready,
        highest_gate="M2",
        gates=tuple(gates),
        blockers=blockers,
        details={
            "config_dir": str(root),
            "road_metadata": road_metadata,
            "scenario": scenario_report.details or {},
            "field_dynamics": field_dynamics,
        },
    )


__all__ = [
    "ALLOWED_SOURCE_TYPES",
    "AuditIssue",
    "AuditReport",
    "ReadinessReport",
    "REQUIRED_PARAMETER_NAMES",
    "audit_parameter_file",
    "audit_parameter_registry",
    "audit_scenario_registry",
    "audit_repository_readiness",
]
