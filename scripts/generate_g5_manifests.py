from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from typing import Any

from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.matrix import build_training_graph


DEFAULT_OUTPUT = Path("outputs/problem2_sr_mappo_v1/g5/manifests")
SOURCE_SCOPE = (
    "src/problem2/experiments/identity.py",
    "src/problem2/experiments/families.py",
    "src/problem2/experiments/matrix.py",
    "src/problem2/experiments/ablation.py",
    "src/problem2/experiments/sensitivity.py",
    "src/problem2/experiments/g5_contract.py",
    "scripts/generate_g5_manifests.py",
    "configs/problem2/g5/families.yaml",
    "configs/problem2/g5/ablations.yaml",
    "configs/problem2/g5/sensitivity.yaml",
)


def _write(path: Path, payload: Any) -> str:
    raw = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _job_payload(job) -> dict[str, Any]:
    return {
        "canonical_training_identity": job.canonical_training_identity,
        "condition_id": job.condition_id,
        "config_hash": job.config_hash,
        "family": job.family,
        "git_commit": job.git_commit,
        "identity": job.identity,
        "method": job.method,
        "protocol_hash": job.protocol_hash,
        "scale": job.scale,
        "training_seed": job.training_seed,
        **({"ablation_group": job.ablation_group} if job.ablation_group else {}),
        **({"sensitivity_axis": job.sensitivity_axis, "sensitivity_value": job.sensitivity_value} if job.sensitivity_axis else {}),
    }


def _reference_payload(reference, job_index: int) -> dict[str, Any]:
    job = reference.job
    return {
        "experiment_identity": reference.experiment_identity,
        "family": reference.family,
        "condition_id": reference.condition_id,
        "canonical_training_identity": reference.canonical_training_identity,
        "job_index": job_index,
    }


def _source_tree_hash(repository_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_SCOPE:
        path = repository_root / relative
        if not path.is_file():
            raise RuntimeError(f"missing source file for provenance: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def generate_manifests(repository_root: Path, output_root: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    repository_root = Path(repository_root).resolve()
    output_root = Path(output_root)
    contract = load_g5_contract(repository_root)
    graph = build_training_graph(contract)
    source_tree_hash = _source_tree_hash(repository_root)
    job_indices = {job.canonical_training_identity: index for index, job in enumerate(graph.unique_jobs)}
    references = [
        _reference_payload(reference, job_indices[reference.canonical_training_identity])
        for reference in graph.references
    ]
    raw_reference_counts = dict(Counter(reference.family for reference in graph.references))
    provenance = {
        "source_commit": graph.source_commit,
        "source_tree_sha256": source_tree_hash,
        "source_tree_paths": list(SOURCE_SCOPE),
        "protocol_hash": graph.protocol_hash,
        "registry_hashes": dict(sorted(graph.registry_hashes.items())),
        "config_hashes": sorted({job.config_hash for job in graph.unique_jobs}),
    }
    files: dict[str, str] = {}

    files["development-smoke.json"] = _write(output_root / "development-smoke.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G5-DEVELOPMENT-SMOKE",
        "status": "planned",
        "partition": "development",
        "training_seeds": list(contract.partitions["development_training"]),
        "scenario_ids": list(contract.partitions["development_scenarios"]),
        "scales": ["g20x20_d2", "g30x50_d4"],
        "jobs": [],
        "sealed_accessed": False,
    })
    files["pilot-manifest.json"] = _write(output_root / "pilot-manifest.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G5-PILOT",
        "status": "planned",
        "partition": "development",
        "scenario_ids": list(contract.partitions["development_scenarios"]),
        "scales": ["g20x20_d2", "g30x50_d4"],
        "families": ["algorithm_convergence", "algorithm_scale", "problem2_required", "vehicle_heuristics", "sr_mappo_ablation", "sr_mappo_sensitivity"],
        "sealed_accessed": False,
    })
    files["g6-training-jobs.json"] = _write(output_root / "g6-training-jobs.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G6-TRAINING-JOBS",
        "status": "skeleton_unexecuted",
        "partition": "formal_training",
        "job_count": len(graph.unique_jobs),
        "jobs": [_job_payload(job) for job in graph.unique_jobs],
        "references": references,
        "reference_count": len(references),
        "raw_reference_counts": raw_reference_counts,
        "decomposition": {"algorithm_scale": 150, "problem2_required": 90, "vehicle_heuristics": 60, "sr_mappo_ablation": 25, "sr_mappo_sensitivity": 50, "total": 375},
        "provenance": provenance,
        "sealed_accessed": False,
    })
    files["g6-validation-evaluations.json"] = _write(output_root / "g6-validation-evaluations.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G6-VALIDATION-EVALUATIONS",
        "status": "skeleton_unexecuted",
        "partition": "validation",
        "scenario_payload": None,
        "sealed_accessed": False,
    })
    files["g7-sealed-evaluations.json"] = _write(output_root / "g7-sealed-evaluations.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G7-SEALED-EVALUATIONS",
        "status": "locked_skeleton",
        "partition": "sealed_test",
        "scenario_payload": None,
        "unlock_required": True,
        "sealed_accessed": False,
    })
    files["g7-analysis.json"] = _write(output_root / "g7-analysis.json", {
        "schema_version": "g5.v1",
        "manifest_id": "G7-ANALYSIS",
        "status": "locked_skeleton",
        "partition": "sealed_test",
        "inputs": [],
        "summaries": [],
        "sealed_accessed": False,
    })
    # Keep the summary independent of the caller's temporary/output path so
    # repeated generation is byte-identical across staging directories.
    summary = {
        "files": files,
        "job_count": len(graph.unique_jobs),
        "reference_count": len(references),
        "raw_reference_counts": raw_reference_counts,
        "decomposition": {"algorithm_scale": 150, "problem2_required": 90, "vehicle_heuristics": 60, "sr_mappo_ablation": 25, "sr_mappo_sensitivity": 50, "total": 375},
        "provenance": provenance,
    }
    _write(output_root / "manifest-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = generate_manifests(args.root, args.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
