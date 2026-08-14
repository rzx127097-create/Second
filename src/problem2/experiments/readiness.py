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

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "ready": self.ready,
            "issues": [issue.to_dict() for issue in self.issues],
            "evidence_paths": list(self.evidence_paths),
            "missing_parameters": list(self.missing_parameters),
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


__all__ = [
    "ALLOWED_SOURCE_TYPES",
    "AuditIssue",
    "AuditReport",
    "REQUIRED_PARAMETER_NAMES",
    "audit_parameter_file",
    "audit_parameter_registry",
]
