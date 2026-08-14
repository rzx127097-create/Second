"""Single-source Chapter 4.5 summary, figures, tables and evidence manifest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.specification import (
    Chapter45Spec,
    ExperimentCondition,
    load_experiment_spec,
    protocol_identity,
)
from problem2.experiments.freeze import verify_sealed_evidence

from .evidence_manifest import write_chapter45_evidence_manifest
from .figures import build_chapter45_figures
from .summarize import hierarchical_paired_summary, summarize_metric_groups
from .tables import build_chapter45_tables
from .validate_logs import read_jsonl, validate_episode_records


FAMILIES = ("main_comparison", "mechanism", "sensitivity", "adaptation", "ablation")
METRICS = (
    "reduction_rate",
    "success",
    "transferred_l",
    "request_count",
    "request_completion_rate",
    "requested_l",
    "request_wait_mean_s",
    "request_wait_p90_s",
    "wait_s",
    "pesticide_disabled_s",
    "effective_spray_s",
    "service_s",
    "rendezvous_road_distance_m",
    "uav_rendezvous_distance_m",
    "vehicle_distance_m",
    "vehicle_idle_s",
    "vehicle_inventory_utilization",
    "decision_time_mean_ms",
)
METRIC_DEFINITIONS = {
    "reduction_rate": "1 - final total pest / initial total pest",
    "success": "reduction_rate >= 0.85",
    "transferred_l": "event-ledger pesticide transfer volume (L)",
    "request_count": "unique replenishment requests created",
    "request_completion_rate": "completed requests / created requests",
    "requested_l": "requested pesticide volume (L)",
    "request_wait_mean_s": "mean request creation-to-service/censoring time (s)",
    "request_wait_p90_s": "90th percentile request creation-to-service/censoring time (s)",
    "wait_s": "event-ledger rendezvous and service waiting time (s)",
    "pesticide_disabled_s": "UAV time unable to spray due to replenishment state (s)",
    "effective_spray_s": "positive pesticide-application UAV time (s)",
    "service_s": "active setup and transfer service time (s)",
    "rendezvous_road_distance_m": "planned vehicle road distance at reservation (m)",
    "uav_rendezvous_distance_m": "UAV movement committed to rendezvous (m)",
    "vehicle_distance_m": "actual support-vehicle road travel (m)",
    "vehicle_idle_s": "zero-travel non-service vehicle time (s)",
    "vehicle_inventory_utilization": "used initial vehicle inventory / initial inventory",
    "decision_time_mean_ms": "mean policy/controller decision wall time (ms)",
}


@dataclass(frozen=True)
class Chapter45ArtifactBundle:
    paths: dict[str, Path]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _algorithm_method(condition: ExperimentCondition) -> str:
    if condition.family != "ablation":
        return condition.method
    if condition.kind == "same_source_mappo":
        return "mappo_mobile"
    if condition.kind == "two_stage_training":
        return "sr_mappo_two_stage"
    return "sr_mappo_mobile"


def _condition_lookup(spec: Chapter45Spec) -> dict[tuple[str, str], ExperimentCondition]:
    return {
        (family, condition.condition_id): condition
        for family in FAMILIES
        for condition in spec.expand(family)
    }


def _read_records(input_paths: Sequence[Path]) -> list[dict[str, Any]]:
    paths = [Path(path).resolve() for path in input_paths]
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Chapter 4.5 inputs must be unique and non-empty")
    records = [row for path in paths for row in read_jsonl(path)]
    return validate_episode_records(records, strict=True)


def _validate_identity(
    records: list[dict[str, Any]], *, expected_config_hash: str, expected_protocol_hash: str
) -> None:
    config_hashes = {str(row.get("config_hash", "")) for row in records}
    if config_hashes != {expected_config_hash}:
        raise ValueError(
            f"episode config hash does not match current configuration: {sorted(config_hashes)}"
        )
    protocol_hashes = {str(row.get("protocol_hash", "")) for row in records}
    if protocol_hashes != {expected_protocol_hash}:
        raise ValueError(
            f"episode protocol hash does not match supplied protocol: {sorted(protocol_hashes)}"
        )
    if len({str(row.get("git_commit", "")) for row in records}) != 1:
        raise ValueError("mixed Git commits in one locked Chapter 4.5 package")
    source_tree_hashes = {str(row.get("source_tree_hash", "")) for row in records}
    if (
        len(source_tree_hashes) != 1
        or any(len(value) != 64 for value in source_tree_hashes)
    ):
        raise ValueError("Chapter 4.5 records require one valid source-tree SHA-256")
    job_provenance: dict[str, tuple[object, ...]] = {}
    for row in records:
        job_id = str(row.get("job_id", ""))
        checkpoint_hash = str(row.get("checkpoint_sha256", ""))
        checkpoint_step = row.get("checkpoint_step")
        if not job_id or len(checkpoint_hash) != 64 or type(checkpoint_step) is not int:
            raise ValueError("Chapter 4.5 records require job/checkpoint provenance")
        identity = (
            checkpoint_hash,
            checkpoint_step,
            str(row.get("source_tree_hash", "")),
            str(row.get("config_hash", "")),
            str(row.get("protocol_hash", "")),
        )
        previous = job_provenance.setdefault(job_id, identity)
        if previous != identity:
            raise ValueError("one job_id maps to multiple checkpoint identities")
    splits = {str(row.get("split", "")) for row in records}
    if len(splits) != 1 or not splits <= {"validation", "sealed_test"}:
        raise ValueError("Chapter 4.5 artifacts require one evaluation split")


def _validate_conditions(
    records: list[dict[str, Any]], spec: Chapter45Spec
) -> None:
    lookup = _condition_lookup(spec)
    for row in records:
        family = str(row.get("family", ""))
        condition_id = str(row.get("condition_id", ""))
        condition = lookup.get((family, condition_id))
        if condition is None:
            raise ValueError(f"unregistered Chapter 4.5 condition: {family}/{condition_id}")
        scale = str(row["scale"])
        training_seed = int(row["training_seed"])
        if family == "main_comparison":
            if (
                scale != condition.scale
                or training_seed != condition.training_seed
                or str(row["method"]) != condition.method
            ):
                raise ValueError("main-comparison row contradicts its condition identity")
        else:
            scope = spec.family_scopes[family]
            if scale not in scope["scales"] or training_seed not in scope["training_seeds"]:
                raise ValueError(f"row lies outside the declared {family} scope")
            if str(row["method"]) != _algorithm_method(condition):
                raise ValueError(f"row method contradicts registered {family} condition")


def _formal_expected_keys(config: Any, spec: Chapter45Spec, split: str) -> set[tuple[object, ...]]:
    scenario_ids = [str(value) for value in config.experiments[f"{split}_scenarios"]]
    scenarios_by_scale = {
        scale: tuple(
            scenario for scenario in scenario_ids
            if str(config.scenarios[scenario]["scale"]) == str(scale)
        )
        for scale in spec.scales
    }
    expected: set[tuple[object, ...]] = set()
    for condition in spec.expand("main_comparison"):
        for scenario in scenarios_by_scale[str(condition.scale)]:
            expected.add((
                "main_comparison", condition.condition_id, condition.method,
                condition.scale, condition.training_seed, scenario,
            ))
    for family in FAMILIES[1:]:
        scope = spec.family_scopes[family]
        for condition in spec.expand(family):
            method = _algorithm_method(condition)
            for scale in scope["scales"]:
                for training_seed in scope["training_seeds"]:
                    for scenario in scenarios_by_scale[str(scale)]:
                        expected.add((
                            family, condition.condition_id, method, str(scale),
                            int(training_seed), scenario,
                        ))
    return expected


def _assert_formal_complete(records: list[dict[str, Any]], config: Any, spec: Chapter45Spec) -> None:
    statuses = [
        config.parameters, config.scales, config.environment,
        config.algorithm, config.experiments,
    ]
    if (
        spec.status != "verified"
        or config.scenario_status != "verified"
        or any(section.get("status") != "verified" for section in statuses)
        or any(bool(row.get("provisional", True)) for row in records)
        or any(bool(row.get("git_dirty", True)) for row in records)
    ):
        raise ValueError("formal Chapter 4.5 artifacts are blocked by provisional evidence")
    split = str(records[0]["split"])
    if split != "sealed_test":
        raise ValueError("formal Chapter 4.5 artifacts require the sealed_test split")
    observed = {
        (
            str(row["family"]), str(row["condition_id"]), str(row["method"]),
            str(row["scale"]), int(row["training_seed"]), str(row["scenario_id"]),
        )
        for row in records
    }
    expected = _formal_expected_keys(config, spec, split)
    if observed != expected:
        raise ValueError(
            "formal Chapter 4.5 evaluation matrix is incomplete or contains extra rows; "
            f"missing={len(expected - observed)}, extra={len(observed - expected)}"
        )


def _assert_present_families_complete(
    records: list[dict[str, Any]], config: Any, spec: Chapter45Spec
) -> None:
    split = str(records[0]["split"])
    present = {str(row["family"]) for row in records}
    observed = {
        (
            str(row["family"]), str(row["condition_id"]), str(row["method"]),
            str(row["scale"]), int(row["training_seed"]), str(row["scenario_id"]),
        )
        for row in records
    }
    expected = {
        key for key in _formal_expected_keys(config, spec, split)
        if str(key[0]) in present
    }
    if observed != expected:
        raise ValueError(
            "Chapter 4.5 present families are incomplete or contain extra rows; "
            f"missing={len(expected - observed)}, extra={len(observed - expected)}"
        )


def _analysis_records(
    records: list[dict[str, Any]], spec: Chapter45Spec
) -> list[dict[str, Any]]:
    lookup = _condition_lookup(spec)
    prepared: list[dict[str, Any]] = []
    for source in records:
        row = dict(source)
        family = str(row["family"])
        condition = lookup[(family, str(row["condition_id"]))]
        if family == "main_comparison":
            row["analysis_group"] = str(row["method"])
            row["factor"] = "method"
            row["level"] = str(row["method"])
        else:
            row["analysis_group"] = str(row["condition_id"])
            row["factor"] = str(condition.factor or condition.kind or family)
            row["level"] = str(condition.level if condition.level is not None else condition.condition_id)
        prepared.append(row)
    return prepared


def _paired(
    rows: list[dict[str, Any]],
    *,
    reference: str,
    metric: str,
    group_field: str,
    draws: int,
    confidence_level: float,
    margin: float | None,
    confirmatory: bool,
) -> list[dict[str, object]]:
    values = {str(row[group_field]) for row in rows}
    if reference not in values or len(values) < 2:
        return []
    return hierarchical_paired_summary(
        rows,
        reference=reference,
        metric=metric,
        draws=draws,
        seed=0,
        confidence_level=confidence_level,
        practical_equivalence_margin=margin,
        confirmatory=confirmatory,
        group_field=group_field,
    )


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in records for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(records)
    os.replace(temporary, path)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_chapter45_artifacts(
    input_paths: Sequence[Path],
    output_root: Path,
    *,
    config_dir: Path,
    protocol_path: Path,
    allow_partial: bool = False,
    freeze_path: Path | None = None,
    unlock_path: Path | None = None,
) -> Chapter45ArtifactBundle:
    """Build every Chapter 4.5 artifact from validated evaluation records."""

    inputs = [Path(path).resolve() for path in input_paths]
    config_dir = Path(config_dir).resolve()
    protocol_path = Path(protocol_path).resolve()
    config = load_config_bundle(config_dir)
    spec = load_experiment_spec(protocol_path, config)
    expected_config_hash = config_identity(config)
    expected_protocol_hash = protocol_identity(protocol_path)
    records = _read_records(inputs)
    _validate_identity(
        records,
        expected_config_hash=expected_config_hash,
        expected_protocol_hash=expected_protocol_hash,
    )
    _validate_conditions(records, spec)
    if not allow_partial:
        _assert_formal_complete(records, config, spec)
        if freeze_path is None or unlock_path is None:
            raise ValueError(
                "formal Chapter 4.5 artifacts require validation freeze and sealed unlock records"
            )
        sealed_verification = verify_sealed_evidence(
            records,
            evidence_paths=inputs,
            freeze_path=Path(freeze_path),
            unlock_path=Path(unlock_path),
        )
    else:
        _assert_present_families_complete(records, config, spec)
        sealed_verification = None

    prepared = _analysis_records(records, spec)
    draws = int(spec.statistics["bootstrap_draws"])
    confidence_level = float(spec.statistics.get("confidence_level", 0.95))
    margin_raw = spec.statistics.get("practical_equivalence_margin")
    margin = None if margin_raw is None else float(margin_raw)
    summaries = summarize_metric_groups(
        prepared,
        group_fields=("family", "analysis_group", "method", "scale", "factor", "level"),
        metrics=METRICS,
        draws=draws,
        seed=0,
        confidence_level=confidence_level,
    )
    families = {
        family: [row for row in summaries if str(row["family"]) == family]
        for family in FAMILIES
    }
    if not allow_partial and any(not rows for rows in families.values()):
        missing = [family for family, rows in families.items() if not rows]
        raise ValueError(f"Chapter 4.5 artifact families are missing: {missing}")

    main_rows = [row for row in prepared if row["family"] == "main_comparison"]
    mechanism_rows = [row for row in prepared if row["family"] == "mechanism"]
    ablation_rows = [row for row in prepared if row["family"] == "ablation"]
    confirmatory = not allow_partial
    paired = {
        "main_reduction": _paired(
            main_rows, reference="sr_mappo_mobile", metric="reduction_rate",
            group_field="method", draws=draws, confidence_level=confidence_level,
            margin=margin, confirmatory=confirmatory,
        ),
        "main_success": _paired(
            main_rows, reference="sr_mappo_mobile", metric="success",
            group_field="method", draws=draws, confidence_level=confidence_level,
            margin=margin, confirmatory=confirmatory,
        ),
        "mechanism_reduction": _paired(
            mechanism_rows, reference="sr_mappo_mobile", metric="reduction_rate",
            group_field="condition_id", draws=draws, confidence_level=confidence_level,
            margin=margin, confirmatory=confirmatory,
        ),
        "ablation_reduction": _paired(
            ablation_rows, reference="full_sr_mappo", metric="reduction_rate",
            group_field="condition_id", draws=draws, confidence_level=confidence_level,
            margin=margin, confirmatory=confirmatory,
        ),
    }
    maturity = "provisional_smoke" if allow_partial or any(bool(row["provisional"]) for row in records) else "formal_sealed"
    uncertainty = {
        "absolute_summary": "scenario mean within training seed, percentile bootstrap across training seeds",
        "paired_summary": "hierarchical paired bootstrap: training seed first, shared scenario second",
        "pairing_unit": str(spec.statistics["pairing_unit"]),
        "bootstrap_draws": draws,
        "confidence_level": confidence_level,
        "multiplicity": str(spec.statistics["multiplicity"]),
        "practical_equivalence_margin": margin,
    }
    locked_summary: dict[str, object] = {
        "schema_version": 1,
        "locked": True,
        "maturity": maturity,
        "record_count": len(records),
        "source_inputs": [
            {"path": str(path), "sha256": _sha256(path)} for path in inputs
        ],
        "identity": {
            "config_hash": expected_config_hash,
            "protocol_hash": expected_protocol_hash,
            "git_commit": sorted({str(row["git_commit"]) for row in records}),
            "split": sorted({str(row["split"]) for row in records}),
            "source_tree_hash": sorted({str(row.get("source_tree_hash", "")) for row in records}),
            "checkpoint_sha256": sorted({str(row.get("checkpoint_sha256", "")) for row in records}),
        },
        "sealed_verification": sealed_verification,
        "uncertainty": uncertainty,
        "metric_definitions": METRIC_DEFINITIONS,
        "families": families,
        "paired": paired,
    }

    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    validated_csv = root / "validated_chapter45.csv"
    locked_summary_path = root / "locked_summary.json"
    _write_csv(validated_csv, records)
    _write_json(locked_summary_path, locked_summary)
    consumed_summary = json.loads(locked_summary_path.read_text(encoding="utf-8"))
    outputs: dict[str, Path] = {
        "validated_csv": validated_csv,
        "locked_summary_json": locked_summary_path,
    }
    outputs.update(
        build_chapter45_figures(
            consumed_summary, root / "figures", allow_partial=allow_partial,
        )
    )
    outputs.update(
        build_chapter45_tables(
            consumed_summary, root / "tables", allow_partial=allow_partial,
        )
    )
    manifest_path = root / "artifact_manifest.json"
    write_chapter45_evidence_manifest(
        manifest_path,
        input_paths=inputs,
        protocol_path=protocol_path,
        output_paths=outputs,
        records=records,
        maturity=maturity,
        uncertainty=uncertainty,
        metric_definitions=METRIC_DEFINITIONS,
    )
    outputs["manifest_json"] = manifest_path
    return Chapter45ArtifactBundle(paths=outputs)


__all__ = ["Chapter45ArtifactBundle", "build_chapter45_artifacts"]
