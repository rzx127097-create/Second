"""Evaluate one checkpoint on an explicitly isolated scenario split."""

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

from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.config import config_identity, load_config_bundle
from problem2.experiments.evaluation import evaluate_policy, load_evaluation_checkpoint
from problem2.experiments.policy_protocol import AlgorithmPolicyAdapter
from problem2.experiments.recovery import load_job_record
from problem2.experiments.runner import JobRecord, traceable_episode_rows
from problem2.scenarios.factory import build_synthetic_scenario


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _is_provisional(config: Any) -> bool:
    return config.parameters.get("status") != "verified" or config.experiments.get("status") != "verified"


def _checkpoint_record(path: Path) -> JobRecord:
    candidate = path.parent.parent / "jobs" / f"{path.stem}.json"
    if not candidate.is_file():
        raise FileNotFoundError(f"persisted job record does not exist for checkpoint: {candidate}")
    record = load_job_record(candidate)
    if record.status != "completed":
        raise ValueError(f"job record is not completed: {candidate}")
    if record.checkpoint_path is None:
        raise ValueError(f"job record has no checkpoint path: {candidate}")
    if record.checkpoint_path.resolve() != path.resolve():
        raise ValueError("checkpoint path does not match its persisted job record")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", choices=["train", "validation", "sealed_test"], required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        config_dir = Path(args.config_dir)
        config = load_config_bundle(config_dir)
        scenarios = [str(value) for value in config.experiments[f"{args.split}_scenarios"]]
        if args.scenario not in scenarios:
            raise ValueError(f"scenario {args.scenario!r} does not belong to split {args.split!r}")
        if args.split == "sealed_test" and _is_provisional(config):
            raise ValueError("sealed_test is blocked because parameter or matrix status is provisional")
        if _is_provisional(config) and not args.smoke:
            raise ValueError("formal evaluation is blocked because parameter or matrix status is provisional")
        checkpoint = Path(args.checkpoint).resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(f"checkpoint does not exist: {checkpoint}")
        job = _checkpoint_record(checkpoint)
        if job.identity.config_hash != config_identity(config):
            raise ValueError("checkpoint job config hash does not match the requested configuration")
        physical_scale = job.identity.scale
        snapshot = build_synthetic_scenario(physical_scale, job.identity.training_seed, config_dir=config_dir).reset()

        def algorithm_factory() -> SRMAPPOAlgorithm:
            algorithm = SRMAPPOAlgorithm(
                uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
                vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
                state_dim=len(snapshot.critic_state["vector"]),
                uav_action_dim=len(snapshot.action_masks["uav-1"]),
                vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
                hidden_dim=16 if args.smoke else int(config.algorithm["hidden_dim"]),
                device="cpu",
            )
            SRMAPPOTrainer(algorithm, learning_rate=float(config.algorithm["learning_rate"]))
            return algorithm

        algorithm, _ = load_evaluation_checkpoint(checkpoint, algorithm_factory)

        def scenario_factory(scenario_id: str):
            bundle = build_synthetic_scenario(physical_scale, job.identity.training_seed, config_dir=config_dir)
            bundle.scale_id = scenario_id
            bundle.episode_id = f"{scenario_id}-seed-{job.identity.training_seed}"
            return bundle

        inner_split = args.split if args.split == "sealed_test" else ("smoke" if args.smoke else args.split)
        records = evaluate_policy(
            AlgorithmPolicyAdapter(algorithm, name="SR-MAPPO"), scenario_factory,
            scenarios=[args.scenario], split=inner_split, deterministic=True,
        )
        rows = traceable_episode_rows(records, job, split=args.split)
        raw_path = checkpoint.parent.parent / "raw" / f"evaluation-{job.job_id}-{args.scenario}.jsonl"
        _write_jsonl(raw_path, rows)
        _emit({"status": "completed", "split": args.split, "scenario": args.scenario, "raw_path": str(raw_path), "smoke": bool(args.smoke)})
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary must preserve diagnostics as JSON
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
