"""Run one immutable SR-MAPPO training job through the real ScenarioBundle path."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
import random
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.config import config_identity, load_config_bundle
from problem2.experiments.evaluation import load_evaluation_checkpoint
from problem2.experiments.job_identity import capture_git_commit, make_job_identity
from problem2.experiments.methods import PRIMARY_METHODS, method_profile
from problem2.experiments.specification import load_experiment_spec, protocol_identity
from problem2.experiments.recovery import load_job_record
from problem2.experiments.rollout_runner import train_policy
from problem2.experiments.runner import JobRecord, JobRunner, traceable_episode_rows
from problem2.scenarios.factory import build_synthetic_scenario
from problem2.scenarios.interventions import ScenarioIntervention


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    import numpy as np
    np.random.seed(int(seed))
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _is_provisional(bundle: Any) -> bool:
    return any(section.get("status") != "verified" for section in (bundle.parameters, bundle.scales, bundle.environment, bundle.algorithm, bundle.experiments)) or bundle.scenario_status != "verified"


def _write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.replace(temporary, path)


def _synchronize_raw_with_checkpoint(path: Path, *, checkpoint_step: int, expected_job_id: str) -> list[dict[str, Any]]:
    """Make raw evidence agree with the last committed checkpoint update."""
    if checkpoint_step < 0:
        raise ValueError("checkpoint step must be non-negative")
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank raw JSONL line at {line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("raw JSONL rows must be objects")
            rows.append(value)
    run_ids = [str(row.get("run_id", "")) for row in rows]
    if any(not run_id.startswith(f"{expected_job_id}:") for run_id in run_ids):
        raise ValueError("raw row does not belong to the expected job identity")
    updates = [int(row.get("update", 0)) for row in rows]
    if updates != list(range(1, len(rows) + 1)):
        raise ValueError("raw update sequence must be contiguous from one")
    if len(rows) < int(checkpoint_step):
        raise ValueError("checkpoint step exceeds raw evidence")
    if len(rows) > int(checkpoint_step):
        rows = rows[: int(checkpoint_step)]
        _write_jsonl_rows(path, rows)
    return rows


def _merge_jsonl_rows(path: Path, rows: list[dict[str, Any]], *, expected_job_id: str) -> Path:
    """Append rows atomically while preserving one immutable job identity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank raw JSONL line at {line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("raw JSONL rows must be objects")
            existing.append(value)
    combined = existing + [dict(row) for row in rows]
    run_ids = [str(row.get("run_id", "")) for row in combined]
    if any(not run_id.startswith(f"{expected_job_id}:") for run_id in run_ids):
        raise ValueError("raw row does not belong to the expected job identity")
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate run_id in raw JSONL")
    updates = [int(row.get("update", index + 1)) for index, row in enumerate(combined)]
    if updates != sorted(updates) or any(right <= left for left, right in zip(updates, updates[1:])):
        raise ValueError("raw update sequence must be strictly increasing")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in combined), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _algorithm_factory(
    config_dir: Path,
    scale: str,
    seed: int,
    hidden_dim: int,
    algorithm_config: dict[str, Any] | float,
    profile: Any | None = None,
    intervention: ScenarioIntervention | None = None,
    device: str = "cpu",
):
    if not isinstance(algorithm_config, dict):
        loaded = dict(load_config_bundle(config_dir).algorithm)
        loaded["learning_rate"] = float(algorithm_config)
        algorithm_config = loaded
    profile = profile or method_profile("sr_mappo_mobile", algorithm_config)
    intervention = intervention or ScenarioIntervention("direct")
    def factory() -> SRMAPPOAlgorithm:
        _seed_everything(seed)
        snapshot = build_synthetic_scenario(
            scale, seed, config_dir=config_dir, intervention=intervention,
        ).reset()
        algorithm = SRMAPPOAlgorithm(
            uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
            vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
            state_dim=len(snapshot.critic_state["vector"]),
            uav_action_dim=len(snapshot.action_masks["uav-1"]),
            vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
            hidden_dim=hidden_dim,
            device=device,
            stability_components=profile.stability_components,
        )
        algorithm.training_seed = int(seed)
        SRMAPPOTrainer(
            algorithm,
            learning_rate=float(algorithm_config["learning_rate"]),
            value_coef=float(algorithm_config.get("value_loss_coef", 0.5)),
            entropy_coef=float(algorithm_config.get("entropy_coef", 0.01)),
            max_grad_norm=float(algorithm_config.get("max_grad_norm", 0.5)),
        )
        return algorithm

    return factory


def _resolve_intervention(
    *,
    config: Any,
    protocol_path: Path,
    family: str,
    condition_id: str | None,
    profile: Any,
) -> tuple[ScenarioIntervention, str]:
    if condition_id is None:
        return ScenarioIntervention("direct", support_mode=profile.environment_mode), "direct"
    spec = load_experiment_spec(protocol_path, config)
    matches = [condition for condition in spec.expand(family) if condition.condition_id == condition_id]
    if len(matches) != 1:
        raise ValueError(f"condition_id {condition_id!r} is not unique in family {family!r}")
    condition = matches[0]
    if condition.method != profile.name and not (
        family == "ablation"
        and (
            (condition.kind == "same_source_mappo" and profile.name == "mappo_mobile")
            or (condition.kind == "two_stage_training" and profile.name == "sr_mappo_two_stage")
            or (condition.kind not in {"same_source_mappo", "two_stage_training"} and profile.name == "sr_mappo_mobile")
        )
    ):
        raise ValueError("condition method does not match the requested training method")
    if family == "main_comparison":
        intervention = ScenarioIntervention(condition_id, support_mode=profile.environment_mode)
    else:
        intervention = ScenarioIntervention.from_condition(condition)
        if profile.environment_mode == "fixed" and intervention.support_mode == "mobile":
            intervention = replace(intervention, support_mode="fixed")
    return intervention, condition_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", default="SR-MAPPO", choices=["SR-MAPPO"])
    parser.add_argument("--method", default="sr_mappo_mobile", choices=list(PRIMARY_METHODS))
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--protocol")
    parser.add_argument(
        "--family", default="main_comparison",
        choices=["main_comparison", "mechanism", "sensitivity", "adaptation", "ablation"],
    )
    parser.add_argument("--condition-id")
    parser.add_argument("--scale", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--updates", type=int, required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    args = parser.parse_args(argv)
    try:
        config_dir = Path(args.config_dir)
        config = load_config_bundle(config_dir)
        _seed_everything(args.seed)
        if _is_provisional(config) and not args.smoke:
            _emit({"status": "rejected", "error": "formal training is blocked because a configuration status is provisional"})
            return 2
        if args.updates < 1:
            raise ValueError("updates must be positive")
        output_root = Path(args.output_root).resolve()
        algorithm_config = config.algorithm
        profile = method_profile(args.method, algorithm_config)
        protocol_path = Path(args.protocol or (config_dir / "experiments" / "chapter4_5.yaml"))
        intervention, condition_id = _resolve_intervention(
            config=config,
            protocol_path=protocol_path,
            family=args.family,
            condition_id=args.condition_id,
            profile=profile,
        )
        device = "cpu" if args.smoke or args.device == "cpu" else args.device
        if device == "auto":
            try:
                import torch
            except ImportError:
                device = "cpu"
            else:
                device = "cuda" if torch.cuda.is_available() else "cpu"
        hidden_dim = 16 if args.smoke else int(algorithm_config["hidden_dim"])
        horizon = 3 if args.smoke else int(algorithm_config["rollout_horizon"])
        identity = make_job_identity(
            args.method, args.scale, args.seed, config_identity(config),
            config_hash=config_identity(config), git_commit=capture_git_commit(str(ROOT)),
            execution_profile="smoke" if args.smoke else "formal",
            target_updates=args.updates,
            rollout_horizon=horizon,
            family=args.family,
            condition_id=condition_id,
            scenario_split="train",
            protocol_hash=protocol_identity(protocol_path),
        )
        checkpoint_path = output_root / "checkpoints" / f"{identity.job_id}.pt"
        record_path = output_root / "jobs" / f"{identity.job_id}.json"
        raw_path = output_root / "raw" / f"{identity.job_id}.jsonl"
        record = load_job_record(record_path) if record_path.exists() else JobRecord(identity=identity, checkpoint_path=checkpoint_path)
        if record.identity != identity:
            raise ValueError("persisted job identity does not match requested immutable identity")
        algorithm_factory = _algorithm_factory(
            config_dir,
            args.scale,
            args.seed,
            hidden_dim,
            algorithm_config,
            profile,
            intervention,
            device,
        )
        scenario_ids = [
            scenario_id for scenario_id in config.experiments.get("train_scenarios", [])
            if str(config.scenarios.get(scenario_id, {}).get("scale")) == str(args.scale)
        ]
        if not scenario_ids:
            raise ValueError(f"no train scenarios registered for scale {args.scale}")
        scenario_cursor = {"index": 0}

        def worker(job: JobRecord) -> dict[str, Any]:
            start_update = 0
            if job.checkpoint_path is not None and job.checkpoint_path.exists():
                algorithm, metadata = load_checkpoint(job.checkpoint_path, algorithm_factory)
                start_update = int(metadata["step"])
            else:
                algorithm = algorithm_factory()
            if start_update > int(args.updates):
                raise ValueError("checkpoint step exceeds requested target updates")
            existing_rows = _synchronize_raw_with_checkpoint(
                raw_path, checkpoint_step=start_update, expected_job_id=job.job_id,
            )
            existing_count = len(existing_rows)
            scenario_cursor["index"] = start_update
            remaining_updates = int(args.updates) - int(start_update)
            if remaining_updates <= 0:
                return {"checkpoint_path": str(checkpoint_path), "raw_path": str(raw_path), "episode_count": existing_count, "resume": "target_already_reached"}
            def make_bundle():
                scenario_id = scenario_ids[scenario_cursor["index"] % len(scenario_ids)]
                scenario_cursor["index"] += 1
                return build_synthetic_scenario(
                    args.scale,
                    args.seed,
                    config_dir=config_dir,
                    scenario_id=scenario_id,
                    intervention=intervention,
                )
            records = train_policy(
                make_bundle,
                algorithm,
                algorithm._trainer,
                updates=remaining_updates,
                rollout_horizon=horizon,
                checkpoint_path=None,
                start_update=start_update,
                total_updates=args.updates,
                algorithm_config=algorithm_config,
                method_profile=profile,
            )
            rows = traceable_episode_rows(records, job, split="train", index_offset=start_update)
            _merge_jsonl_rows(raw_path, rows, expected_job_id=job.job_id)
            final_step = start_update + len(records)
            save_checkpoint(checkpoint_path, algorithm, step=final_step)
            return {"checkpoint_path": str(checkpoint_path), "raw_path": str(raw_path), "episode_count": existing_count + len(rows)}

        completed = JobRunner(
            worker,
            max_attempts=args.max_attempts,
            record_path=record_path,
            checkpoint_validator=lambda path: load_evaluation_checkpoint(path, algorithm_factory),
        ).run(record)
        payload = {
            **completed.to_dict(),
            "job_file": str(record_path),
            "raw_path": str(raw_path),
            "smoke": bool(args.smoke),
            "device": device,
            "intervention": intervention.to_dict(),
            "intervention_hash": intervention.identity_hash,
        }
        _emit(payload)
        return 0 if completed.status == "completed" else 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary must preserve diagnostics as JSON
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
