"""Fail-closed ecology and output-root policy for Problem 2 experiments."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re
from typing import Any, Mapping


class EcologyMode(str, Enum):
    """Ecology modes exposed to experiment entrypoints."""

    DYNAMIC = "dynamic"
    STATIC_DIAGNOSTIC = "static_diagnostic"


DYNAMIC_OUTPUT_ROOT = Path("outputs/problem2_sr_mappo_v1/dynamic_pest_v1")
STATIC_DIAGNOSTIC_OUTPUT_ROOT = Path(
    "outputs/problem2_sr_mappo_v1/diagnostics/static_ecology"
)
HISTORICAL_OUTPUT_ROOT = Path("outputs/problem2_sr_mappo_v1/g5")
DEFAULT_PRIMARY_ECOLOGY_MODE = EcologyMode.DYNAMIC
_PRIMARY_PARTITIONS = frozenset({"development", "validation", "formal", "sealed_test"})
_GATES = frozenset({"g3", "g4", "g5", "g6", "g7", "g8"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _mode(value: EcologyMode | str) -> EcologyMode:
    try:
        return value if isinstance(value, EcologyMode) else EcologyMode(str(value))
    except ValueError as exc:
        raise ValueError(f"unsupported ecology mode: {value!r}") from exc


def _gate(value: str) -> str:
    normalized = str(value).lower()
    if normalized not in _GATES:
        raise ValueError(f"unsupported experiment gate: {value!r}")
    return normalized


def _resolved_candidate(repository_root: Path, requested_root: Path | str | None) -> Path | None:
    if requested_root is None:
        return None
    candidate = Path(requested_root)
    return (repository_root / candidate if not candidate.is_absolute() else candidate).resolve()


def _reject_parent_traversal(requested_root: Path | str | None, label: str) -> None:
    if requested_root is not None and ".." in Path(requested_root).parts:
        raise ValueError(f"canonical {label} cannot contain parent traversal")


def _remap_or_accept(
    candidate: Path | None,
    *,
    target_root: Path,
    legacy_roots: tuple[Path, ...],
    label: str,
) -> Path:
    if candidate is None:
        return target_root
    try:
        candidate.relative_to(target_root)
    except ValueError:
        pass
    else:
        return candidate
    for legacy_root in legacy_roots:
        try:
            suffix = candidate.relative_to(legacy_root)
        except ValueError:
            continue
        return target_root / suffix
    raise ValueError(
        f"canonical {label} must be under {target_root} or a historical gate root for migration"
    )


def resolve_output_root(
    repository_root: Path | str,
    gate: str,
    requested_root: Path | str | None,
    *,
    primary: bool,
    partition: str,
    ecology_mode: EcologyMode | str = DEFAULT_PRIMARY_ECOLOGY_MODE,
) -> Path:
    """Resolve an experiment output root without rewriting historical evidence.

    Historical G5 paths are accepted only as an input spelling that is mapped
    into the dynamic namespace. New files are never returned below that path.
    """

    root = Path(repository_root).resolve()
    gate_name = _gate(gate)
    mode = _mode(ecology_mode)
    partition_name = str(partition)
    _reject_parent_traversal(requested_root, "output root")
    candidate = _resolved_candidate(root, requested_root)

    if primary:
        if mode is not EcologyMode.DYNAMIC:
            raise ValueError("primary experiments require dynamic ecology")
        if partition_name not in _PRIMARY_PARTITIONS:
            raise ValueError(f"primary experiment partition is invalid: {partition_name!r}")
        target = root / DYNAMIC_OUTPUT_ROOT / gate_name
        return _remap_or_accept(
            candidate,
            target_root=target,
            legacy_roots=(
                root / HISTORICAL_OUTPUT_ROOT,
                root / Path("outputs/problem2_sr_mappo_v1") / gate_name,
            ),
            label="primary output root",
        )

    if mode is not EcologyMode.STATIC_DIAGNOSTIC:
        raise ValueError("non-primary runs require static_diagnostic ecology mode")
    if partition_name != "development":
        raise ValueError("static diagnostics are restricted to the development partition")
    target = root / STATIC_DIAGNOSTIC_OUTPUT_ROOT / gate_name
    return _remap_or_accept(
        candidate,
        target_root=target,
        legacy_roots=(root / STATIC_DIAGNOSTIC_OUTPUT_ROOT,),
        label="static diagnostic output root",
    )


def resolve_frozen_g5_manifest(repository_root: Path | str, filename: str) -> Path:
    """Locate a frozen G5 input, preferring dynamic evidence and reading history only as fallback.

    This helper is intentionally read-only. Callers may consume a historical
    candidate or budget manifest while rebuilding dynamic development outputs,
    but no caller receives a historical path as a destination.
    """

    root = Path(repository_root).resolve()
    name = Path(filename)
    if name.is_absolute() or name.name != filename or filename in {"", ".", ".."}:
        raise ValueError("frozen G5 manifest filename must be a simple file name")
    dynamic = root / DYNAMIC_OUTPUT_ROOT / "g5" / "manifests" / name
    historical = root / HISTORICAL_OUTPUT_ROOT / "manifests" / name
    if dynamic.is_file():
        return dynamic
    if historical.is_file():
        return historical
    return dynamic


def assert_dynamic_primary_environment(environment: Any, *, partition: str) -> None:
    """Reject a primary run unless its environment carries dynamic provenance."""

    if getattr(environment, "ecology_mode", None) != EcologyMode.DYNAMIC.value:
        raise ValueError("primary environment must use dynamic ecology")
    if getattr(environment, "primary_eligible", None) is not True:
        raise ValueError("environment is not eligible for primary experiments")
    if getattr(environment, "partition", None) != str(partition):
        raise ValueError("environment partition does not match the requested partition")
    if getattr(environment, "replenished_resource", None) != "pesticide":
        raise ValueError("primary environment must replenish pesticide only")
    if getattr(environment, "battery_replenishment_enabled", None) is not False:
        raise ValueError("battery replenishment must remain disabled")
    provenance = getattr(environment, "source_provenance", None)
    if not isinstance(provenance, Mapping):
        raise ValueError("dynamic environment provenance is missing")
    required = (
        "ecology_version",
        "ecology_config_sha256",
        "ecology_scenario_sha256",
        "ecology_source_commit",
        "ecology_implementation_version",
    )
    if any(not isinstance(provenance.get(field), str) or not provenance[field] for field in required):
        raise ValueError("dynamic environment provenance is incomplete")
    if not _SHA256.fullmatch(provenance["ecology_config_sha256"]):
        raise ValueError("dynamic ecology config hash is invalid")
    if not _SHA256.fullmatch(provenance["ecology_scenario_sha256"]):
        raise ValueError("dynamic ecology scenario hash is invalid")
    if not _COMMIT.fullmatch(provenance["ecology_source_commit"]):
        raise ValueError("dynamic ecology source commit is invalid")


__all__ = [
    "DEFAULT_PRIMARY_ECOLOGY_MODE",
    "DYNAMIC_OUTPUT_ROOT",
    "EcologyMode",
    "HISTORICAL_OUTPUT_ROOT",
    "STATIC_DIAGNOSTIC_OUTPUT_ROOT",
    "assert_dynamic_primary_environment",
    "resolve_frozen_g5_manifest",
    "resolve_output_root",
]
