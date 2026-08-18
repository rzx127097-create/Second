from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from problem2.experiments.job_identity import JobIdentity
from problem2.experiments.recovery import save_job_record
from problem2.experiments.runner import JobRecord


def _identity(job: Mapping[str, object]) -> JobIdentity:
    return JobIdentity(
        method=str(job["method"]),
        scale=str(job["scale"]),
        training_seed=int(job["training_seed"]),
        config_hash=str(job["config_hash"]),
        git_commit=str(job["git_commit"]),
        execution_profile=str(job["execution_profile"]),
        target_updates=int(job["target_updates"]),
        rollout_horizon=int(job["rollout_horizon"]),
        family=str(job["family"]),
        condition_id=str(job["condition_id"]),
        scenario_split=str(job["scenario_split"]),
        protocol_hash=str(job["protocol_hash"]),
        source_tree_hash=str(job["source_tree_hash"]),
        git_dirty=bool(job["git_dirty"]),
    )


def materialize_complete_m3_evidence(
    manifest: Mapping[str, object],
    run_root: Path,
) -> list[Path]:
    run_root.mkdir(parents=True, exist_ok=True)
    jobs = {str(row["job_id"]): row for row in manifest["jobs"]}
    checkpoint_hashes: dict[str, str] = {}
    for job_id, row in jobs.items():
        checkpoint = run_root / str(row["checkpoint_path"])
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(f"checkpoint:{job_id}".encode("ascii"))
        checkpoint_hashes[job_id] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        record = JobRecord(
            identity=_identity(row),
            status="completed",
            attempts=1,
            checkpoint_path=checkpoint.resolve(),
            checkpoint_sha256=checkpoint_hashes[job_id],
            checkpoint_step=int(row["target_updates"]),
        )
        save_job_record(run_root / str(row["job_record_path"]), record)

    evaluation_paths: list[Path] = []
    for index, expected in enumerate(manifest["evaluations"]):
        job = jobs[str(expected["job_id"])]
        row = {
            "run_id": expected["run_id"],
            "job_id": expected["job_id"],
            "method": expected["method"],
            "scale": expected["scale"],
            "training_seed": expected["training_seed"],
            "scenario_id": expected["scenario_id"],
            "split": "validation",
            "config_hash": job["config_hash"],
            "git_commit": job["git_commit"],
            "git_dirty": False,
            "source_tree_hash": job["source_tree_hash"],
            "execution_profile": "simulation",
            "target_updates": job["target_updates"],
            "rollout_horizon": job["rollout_horizon"],
            "checkpoint_sha256": checkpoint_hashes[str(expected["job_id"])],
            "checkpoint_step": job["target_updates"],
            "family": expected["family"],
            "condition_id": expected["condition_id"],
            "protocol_hash": job["protocol_hash"],
            "provisional": True,
            "reduction_rate": 0.80 + 0.001 * (index % 10),
            "success": index % 3 != 0,
            "transferred_l": 1.0,
            "request_count": 2.0,
            "request_completion_rate": 1.0,
            "requested_l": 1.0,
            "request_wait_mean_s": 2.0,
            "request_wait_p90_s": 3.0,
            "wait_s": 4.0,
            "pesticide_disabled_s": 1.0,
            "effective_spray_s": 30.0,
            "service_s": 5.0,
            "rendezvous_road_distance_m": 40.0,
            "uav_rendezvous_distance_m": 10.0,
            "vehicle_distance_m": 60.0,
            "vehicle_idle_s": 6.0,
            "vehicle_inventory_initial_l": 40.0,
            "vehicle_inventory_final_l": 20.0,
            "vehicle_inventory_utilization": 0.5,
            "decision_time_mean_ms": 2.0,
        }
        path = run_root / str(expected["raw_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
        evaluation_paths.append(path)
    return evaluation_paths


__all__ = ["materialize_complete_m3_evidence"]
