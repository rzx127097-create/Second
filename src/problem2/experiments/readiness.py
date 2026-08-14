"""Evidence and formal-experiment readiness audits.

The audits in this module are deliberately conservative.  They validate the
shape and provenance of evidence; they do not decide whether an equipment
manual or field study is scientifically applicable to a particular farm.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

import yaml


REQUIRED_PARAMETER_NAMES = (
    "decision_dt",
    "rendezvous_radius",
    "service_setup_time",
    "uav_onboard_pesticide",
    "uav_spray_flow",
    "uav_speed",
    "uav_usable_fraction",
    "vehicle_inventory",
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


__all__ = [
    "ALLOWED_SOURCE_TYPES",
    "AuditIssue",
    "AuditReport",
    "REQUIRED_PARAMETER_NAMES",
    "audit_parameter_file",
    "audit_parameter_registry",
    "audit_scenario_registry",
]
