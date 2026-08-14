"""Run one immutable SR-MAPPO training job through the real ScenarioBundle path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.algorithms.common.checkpoint import load_checkpoint
from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.config import config_identity, load_config_bundle
from problem2.experiments.job_identity import capture_git_commit, make_job_identity
from problem2.experiments.recovery import load_job_record
from problem2.experiments.rollout_runner import train_policy
from problem2.experiments.runner import JobRecord, JobRunner, traceable_episode_rows
from problem2.scenarios.factory import build_synthetic_scenario


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _is_provisional(bundle: Any) -> bool:
    return bundle.parameters.get("status") != "verified" or bundle.experiments.get("status") != "verified"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _algorithm_factory(config_dir: Path, scale: str, seed: int, hidden_dim: int, learning_rate: float):
    def factory() -> SRMAPPOAlgorithm:
        snapshot = build_synthetic_scenario(scale, seed, config_dir=config_dir).reset()
        algorithm = SRMAPPOAlgorithm(
            uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
            vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
            state_dim=len(snapshot.critic_state["vector"]),
            uav_action_dim=len(snapshot.action_masks["uav-1"]),
            vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
            hidden_dim=hidden_dim,
            device="cpu",
        )
        SRMAPPOTrainer(algorithm, learning_rate=learning_rate)
        return algorithm

    return factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", default="SR-MAPPO", choices=["SR-MAPPO"])
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--scale", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--updates", type=int, required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        config_dir = Path(args.config_dir)
        config = load_config_bundle(config_dir)
        if _is_provisional(config) and not args.smoke:
            _emit({"status": "rejected", "error": "formal training is blocked because parameter or matrix status is provisional"})
            return 2
        if args.updates < 1:
            raise ValueError("updates must be positive")
        output_root = Path(args.output_root)
        identity = make_job_identity(
            "sr_mappo_mobile", args.scale, args.seed, config_identity(config),
            config_hash=config_identity(config), git_commit=capture_git_commit(str(ROOT)),
        )
        checkpoint_path = output_root / "checkpoints" / f"{identity.job_id}.pt"
        record_path = output_root / "jobs" / f"{identity.job_id}.json"
        raw_path = output_root / "raw" / f"{identity.job_id}.jsonl"
        record = load_job_record(record_path) if record_path.exists() else JobRecord(identity=identity, checkpoint_path=checkpoint_path)
        if record.identity != identity:
            raise ValueError("persisted job identity does not match requested immutable identity")
        algorithm_config = config.algorithm
        hidden_dim = 16 if args.smoke else int(algorithm_config["hidden_dim"])
        horizon = 3 if args.smoke else int(algorithm_config["rollout_horizon"])
        algorithm_factory = _algorithm_factory(config_dir, args.scale, args.seed, hidden_dim, float(algorithm_config["learning_rate"]))

        def worker(job: JobRecord) -> dict[str, Any]:
            start_update = 0
            if job.checkpoint_path is not None and job.checkpoint_path.exists():
                algorithm, metadata = load_checkpoint(job.checkpoint_path, algorithm_factory)
                start_update = int(metadata["step"])
            else:
                algorithm = algorithm_factory()
            records = train_policy(
                lambda: build_synthetic_scenario(args.scale, args.seed, config_dir=config_dir),
                algorithm,
                algorithm._trainer,
                updates=args.updates,
                rollout_horizon=horizon,
                checkpoint_path=checkpoint_path,
                start_update=start_update,
                total_updates=start_update + args.updates,
            )
            rows = traceable_episode_rows(records, job, split="train")
            _write_jsonl(raw_path, rows)
            return {"checkpoint_path": str(checkpoint_path), "raw_path": str(raw_path), "episode_count": len(rows)}

        completed = JobRunner(worker, max_attempts=args.max_attempts, record_path=record_path).run(record)
        payload = {**completed.to_dict(), "job_file": str(record_path), "raw_path": str(raw_path), "smoke": bool(args.smoke)}
        _emit(payload)
        return 0 if completed.status == "completed" else 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary must preserve diagnostics as JSON
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
