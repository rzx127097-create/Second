"""Fail-closed audit for the G3 heterogeneous SR-MAPPO gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import torch

from problem2.config import G3Config, load_g3_config


class G3AuditError(RuntimeError):
    """Raised when a G3 acceptance or provenance requirement fails."""


ACCEPTANCE_TESTS = {
    "gradient_isolation": "tests/g3/test_training_and_checkpoint.py::test_actor_optimizer_parameter_sets_are_gradient_isolated",
    "masked_log_prob_replay": "tests/g3/test_training_and_checkpoint.py::test_algorithm_act_replays_from_exact_masks_and_policy_inputs",
    "zero_invalid_action_probability": "tests/g3/test_common_math_and_rollout.py::test_masked_categorical_has_exact_zero_probability_for_invalid_actions",
    "team_gae_gold": "tests/g3/test_common_math_and_rollout.py::test_compute_gae_bootstraps_truncation_but_cuts_termination_and_trace",
    "valid_advantage_normalization": "tests/g3/test_common_math_and_rollout.py::test_rollout_advantage_normalization_uses_only_valid_team_samples",
    "configured_update_counts": "tests/g3/test_training_and_checkpoint.py::test_trainer_updates_roles_with_isolated_optimizers_and_counts",
    "evaluation_normalizer_freeze": "tests/g3/test_training_and_checkpoint.py::test_deterministic_evaluation_freezes_normalizers_byte_identically",
    "checkpoint_roundtrip": "tests/g3/test_training_and_checkpoint.py::test_checkpoint_roundtrip_restores_policy_trainer_normalizers_and_rng",
    "actor_information_boundary": "tests/g3/test_role_interfaces.py::test_actor_interfaces_accept_only_role_observation",
    "configuration_diff": "tests/g3/test_training_and_checkpoint.py::test_configuration_diff_only_allows_declared_stability_flags",
    "g2_mask_conversion": "tests/g3/test_role_interfaces.py::test_g2_masks_convert_to_role_masks_without_action_replacement",
    "development_training_smoke": "tests/g3/test_training_smoke.py::test_training_smoke_writes_finite_provenance_bound_artifacts",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise G3AuditError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise G3AuditError(f"{label} must be a JSON object")
    return payload


def _child(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise G3AuditError(f"artifact escapes output root: {relative}") from exc
    return path


def _run_acceptance_tests(root: Path) -> dict[str, Any]:
    nodeids = list(ACCEPTANCE_TESTS.values())
    command = [sys.executable, "-m", "pytest", *nodeids, "-q"]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    summary = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    if completed.returncode != 0:
        raise G3AuditError(
            "G3 acceptance tests failed: "
            f"{summary or completed.stderr.strip()[-500:]}"
        )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "summary": summary,
        "tests": {name: True for name in ACCEPTANCE_TESTS},
    }


def _audit_smoke(
    config: G3Config,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_log = _child(output_root, "training-smoke.jsonl")
    provenance_path = _child(output_root, "provenance.json")
    checkpoint = _child(output_root, "checkpoints/g3-smoke.pt")
    for path, label in (
        (raw_log, "raw development log"),
        (provenance_path, "provenance report"),
        (checkpoint, "checkpoint"),
    ):
        if not path.is_file() or path.stat().st_size == 0:
            raise G3AuditError(f"missing or empty {label}: {path}")

    provenance = _load_json(provenance_path, "provenance report")
    if provenance.get("config_hash") != config.config_hash:
        raise G3AuditError("provenance config hash does not match G3 config hash")
    if provenance.get("training_partition") != "development":
        raise G3AuditError("smoke provenance is not development-only")
    if provenance.get("sealed_test_accessed") is not False:
        raise G3AuditError("sealed test access is not false in provenance")
    if provenance.get("validation_scenarios_accessed") is not False:
        raise G3AuditError("validation scenario access is not false in provenance")
    if provenance.get("battery_replenishment_enabled") is not False:
        raise G3AuditError("battery replenishment is not disabled in provenance")
    updates = provenance.get("updates")
    if isinstance(updates, bool) or not isinstance(updates, int) or updates <= 0:
        raise G3AuditError("provenance updates must be a positive integer")
    if provenance.get("finite_loss_checks") is not True:
        raise G3AuditError("smoke finite-loss check did not pass")

    lines = raw_log.read_text(encoding="utf-8").splitlines()
    if len(lines) != updates:
        raise G3AuditError("raw development log update count disagrees with provenance")
    for line_number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise G3AuditError(f"invalid raw log JSON at line {line_number}") from exc
        if record.get("config_hash") != config.config_hash:
            raise G3AuditError(f"raw log config hash mismatch at line {line_number}")
        if record.get("sealed_test_accessed") is not False:
            raise G3AuditError(f"sealed access flag is not false at line {line_number}")
        if record.get("finite_losses") is not True:
            raise G3AuditError(f"finite-loss flag is not true at line {line_number}")
        if not isinstance(record.get("metrics"), dict):
            raise G3AuditError(f"missing metrics at line {line_number}")
        for key, value in record["metrics"].items():
            if isinstance(value, (int, float)) and not np.isfinite(value):
                raise G3AuditError(f"non-finite metric {key} at line {line_number}")

    try:
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    except Exception as exc:
        raise G3AuditError(f"cannot load smoke checkpoint: {exc}") from exc
    if payload.get("format_version") != "g3-checkpoint-v1":
        raise G3AuditError("checkpoint format version is not g3-checkpoint-v1")
    checkpoint_provenance = payload.get("provenance") or {}
    if checkpoint_provenance.get("config_hash") != config.config_hash:
        raise G3AuditError("checkpoint config hash does not match G3 config hash")
    if checkpoint_provenance.get("sealed_test_accessed") is not False:
        raise G3AuditError("checkpoint sealed access flag is not false")

    artifacts = {
        "raw_log": {
            "path": str(raw_log),
            "sha256": _sha256(raw_log),
            "bytes": raw_log.stat().st_size,
        },
        "provenance": {
            "path": str(provenance_path),
            "sha256": _sha256(provenance_path),
            "bytes": provenance_path.stat().st_size,
        },
        "checkpoint": {
            "path": str(checkpoint),
            "sha256": _sha256(checkpoint),
            "bytes": checkpoint.stat().st_size,
        },
    }
    smoke = {
        "raw_log": str(raw_log),
        "provenance": str(provenance_path),
        "checkpoint": str(checkpoint),
        "updates": updates,
        "finite_loss_checks": True,
        "sealed_test_accessed": False,
        "validation_scenarios_accessed": False,
        "config_hash": config.config_hash,
        "source_tree_commit": provenance.get("source_tree_commit"),
    }
    return smoke, artifacts


def audit_g3(
    config_path: str | Path,
    output_root: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    config = load_g3_config(config_path)
    root = Path(output_root).resolve()
    if not root.is_dir():
        raise G3AuditError(f"G3 output root does not exist: {root}")
    smoke, artifacts = _audit_smoke(config, root)
    test_result = _run_acceptance_tests(Path(__file__).resolve().parents[1])
    report = {
        "schema_version": "g3-audit.v1",
        "status": "pass",
        "gate": "G3",
        "maturity": "M2",
        "algorithm_name": config.algorithm_name,
        "config_hash": config.config_hash,
        "acceptance": {
            "required": len(ACCEPTANCE_TESTS),
            "passed": len(ACCEPTANCE_TESTS),
            "tests": test_result["tests"],
            "command": test_result["command"],
            "summary": test_result["summary"],
        },
        "training_smoke": smoke,
        "artifacts": artifacts,
        "boundaries": {
            "formal_jobs": False,
            "validation_tuning": False,
            "sealed_test_accessed": False,
            "battery_replenishment_enabled": False,
            "endpoint_claim_permitted": False,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the G3 SR-MAPPO gate.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_g3(args.config, args.output_root, args.report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
