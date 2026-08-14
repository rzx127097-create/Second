"""Evaluate one checkpoint on an explicitly isolated scenario split."""

from __future__ import annotations

import argparse
import hashlib
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
from problem2.experiments.freeze import (
    commit_sealed_access,
    release_sealed_access,
    reserve_sealed_access,
)
from problem2.experiments.job_identity import (
    assert_clean_formal_source,
    capture_git_provenance,
)
from problem2.experiments.methods import method_profile
from problem2.experiments.orchestrator import resolve_condition_intervention
from problem2.experiments.policy_protocol import AlgorithmPolicyAdapter
from problem2.experiments.recovery import load_job_record
from problem2.experiments.runner import JobRecord, traceable_episode_rows
from problem2.scenarios.factory import build_synthetic_scenario
from problem2.experiments.specification import load_experiment_spec, protocol_identity
from problem2.baselines import make_policy


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _assert_evaluation_source(job: JobRecord, *, smoke: bool) -> None:
    if job.identity.execution_profile == "smoke":
        return
    provenance = capture_git_provenance(str(ROOT))
    assert_clean_formal_source(provenance)
    if (
        provenance.commit != job.identity.git_commit
        or provenance.source_tree_hash != job.identity.source_tree_hash
        or job.identity.git_dirty
    ):
        raise ValueError("evaluation source tree does not match the frozen training job")


def _assert_evaluation_mode(job: JobRecord, *, split: str, smoke: bool) -> None:
    checkpoint_is_smoke = job.identity.execution_profile == "smoke"
    if bool(smoke) != checkpoint_is_smoke:
        raise ValueError("evaluation mode must match the checkpoint execution profile")
    if split == "sealed_test" and smoke:
        raise ValueError("sealed_test cannot use a smoke checkpoint or smoke evaluation mode")


def _is_provisional(config: Any) -> bool:
    return any(section.get("status") != "verified" for section in (config.parameters, config.scales, config.environment, config.algorithm, config.experiments)) or config.scenario_status != "verified"


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
    parser.add_argument("--protocol")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", choices=["train", "validation", "sealed_test"], required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--freeze-manifest")
    parser.add_argument("--sealed-unlock")
    args = parser.parse_args(argv)
    try:
        config_dir = Path(args.config_dir)
        config = load_config_bundle(config_dir)
        protocol_path = Path(args.protocol or (config_dir / "experiments" / "chapter4_5.yaml"))
        spec = load_experiment_spec(protocol_path, config)
        scenarios = [str(value) for value in config.experiments[f"{args.split}_scenarios"]]
        if args.scenario not in scenarios:
            raise ValueError(f"scenario {args.scenario!r} does not belong to split {args.split!r}")
        if args.split == "sealed_test" and _is_provisional(config):
            raise ValueError("sealed_test is blocked because a configuration status is provisional")
        if args.split == "sealed_test" and (not args.freeze_manifest or not args.sealed_unlock):
            raise ValueError("sealed_test requires a validation freeze manifest and sealed unlock record")
        if _is_provisional(config) and not args.smoke:
            raise ValueError("formal evaluation is blocked because a configuration status is provisional")
        checkpoint = Path(args.checkpoint).resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(f"checkpoint does not exist: {checkpoint}")
        job = _checkpoint_record(checkpoint)
        _assert_evaluation_mode(job, split=args.split, smoke=bool(args.smoke))
        if job.identity.config_hash != config_identity(config):
            raise ValueError("checkpoint job config hash does not match the requested configuration")
        if job.identity.protocol_hash and job.identity.protocol_hash != protocol_identity(protocol_path):
            raise ValueError("checkpoint job protocol hash does not match the requested protocol")
        checkpoint_sha256 = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        if job.checkpoint_sha256 != checkpoint_sha256:
            raise ValueError("checkpoint SHA-256 does not match its persisted job record")
        _assert_evaluation_source(job, smoke=bool(args.smoke))
        physical_scale = job.identity.scale
        scenario_scale = str(config.scenarios[args.scenario]["scale"])
        if scenario_scale != physical_scale:
            raise ValueError("evaluation scenario scale does not match checkpoint scale")
        sealed_reservation = None
        if args.split == "sealed_test":
            sealed_reservation = reserve_sealed_access(
                args.sealed_unlock,
                freeze_path=args.freeze_manifest,
                job_id=job.job_id,
                scenario_id=args.scenario,
            )
        raw_path = checkpoint.parent.parent / "raw" / f"evaluation-{job.job_id}-{args.scenario}.jsonl"
        sealed_receipt = None
        try:
            profile = method_profile(job.identity.method, config.algorithm)
            intervention = resolve_condition_intervention(
                spec,
                config.algorithm,
                family=job.identity.family,
                condition_id=job.identity.condition_id,
                method=job.identity.method,
            )
            snapshot = build_synthetic_scenario(
                physical_scale,
                job.identity.training_seed,
                config_dir=config_dir,
                scenario_id=args.scenario,
                intervention=intervention,
            ).reset()

            def algorithm_factory() -> SRMAPPOAlgorithm:
                algorithm = SRMAPPOAlgorithm(
                    uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
                    vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
                    state_dim=len(snapshot.critic_state["vector"]),
                    uav_action_dim=len(snapshot.action_masks["uav-1"]),
                    vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
                    hidden_dim=16 if args.smoke else int(config.algorithm["hidden_dim"]),
                    device="cpu",
                    stability_components=profile.stability_components,
                )
                SRMAPPOTrainer(
                    algorithm,
                    learning_rate=float(config.algorithm["learning_rate"]),
                    value_coef=float(config.algorithm.get("value_loss_coef", 0.5)),
                    entropy_coef=float(config.algorithm.get("entropy_coef", 0.01)),
                    max_grad_norm=float(config.algorithm.get("max_grad_norm", 0.5)),
                )
                return algorithm

            algorithm, checkpoint_metadata = load_evaluation_checkpoint(checkpoint, algorithm_factory)
            expected_provenance = {"job_id": job.job_id, **job.identity.to_dict()}
            if checkpoint_metadata.get("provenance") != expected_provenance:
                raise ValueError("checkpoint payload provenance does not match its persisted job")
            if job.checkpoint_step != int(checkpoint_metadata["step"]):
                raise ValueError("checkpoint step does not match its persisted job record")

            def scenario_factory(scenario_id: str):
                return build_synthetic_scenario(
                    physical_scale,
                    job.identity.training_seed,
                    config_dir=config_dir,
                    scenario_id=scenario_id,
                    intervention=intervention,
                )

            inner_split = args.split if args.split == "sealed_test" else ("smoke" if args.smoke else args.split)
            if job.identity.method in {"sr_mappo_fixed", "sr_mappo_astar"}:
                policy = make_policy(job.identity.method, checkpoint=checkpoint)
                policy._algorithm = algorithm
                policy.smoke_only = False
                policy.formal_ready = True
            else:
                policy = AlgorithmPolicyAdapter(algorithm, name=job.identity.method)
            records = evaluate_policy(
                policy, scenario_factory,
                scenarios=[args.scenario], split=inner_split, deterministic=True,
            )
            rows = traceable_episode_rows(records, job, split=args.split)
            _write_jsonl(raw_path, rows)
            if sealed_reservation is not None:
                sealed_receipt = commit_sealed_access(
                    args.sealed_unlock,
                    freeze_path=args.freeze_manifest,
                    reservation_id=str(sealed_reservation["reservation_id"]),
                    evidence_path=raw_path,
                )
        except Exception:
            if sealed_reservation is not None:
                release_sealed_access(
                    args.sealed_unlock,
                    freeze_path=args.freeze_manifest,
                    reservation_id=str(sealed_reservation["reservation_id"]),
                )
            raise
        _emit({"status": "completed", "split": args.split, "scenario": args.scenario, "raw_path": str(raw_path), "smoke": bool(args.smoke), "sealed_receipt": sealed_receipt})
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary must preserve diagnostics as JSON
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
