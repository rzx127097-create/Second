from __future__ import annotations

import json
import hashlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"{script} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    return json.loads(result.stdout)


def _checkpoint_step(path: Path) -> int:
    torch = pytest.importorskip("torch")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    return int(payload["step"])


def _train_module():
    source = ROOT / "scripts" / "train.py"
    spec = importlib.util.spec_from_file_location("problem2_train_cli", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_complete_project_smoke_resume_evaluate_and_build_artifacts(tmp_path: Path) -> None:
    runbook = ROOT / "docs" / "verification" / "complete-project-runbook.md"
    assert runbook.is_file()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    runbook_text = runbook.read_text(encoding="utf-8")
    assert 'pip install -e ".[dev,rl]"' in readme
    assert 'pip install -e ".[dev,rl]"' in runbook_text
    output_root = tmp_path / "runs"
    matrix = _run(
        "run_matrix.py",
        "--config-dir",
        "configs",
        "--output-root",
        str(output_root),
        "--smoke",
        "--max-jobs",
        "1",
    )
    assert matrix["status"] == "partial"
    job = matrix["jobs"][0]
    assert job["method"] == "sr_mappo_mobile"
    assert job["status"] == "completed"
    train_output = job["output"]
    job_file = Path(str(train_output["job_file"]))
    checkpoint = Path(str(train_output["checkpoint_path"]))
    train_raw = Path(str(train_output["raw_path"]))
    assert job_file.is_file() and checkpoint.is_file() and train_raw.is_file()
    identity = json.loads(job_file.read_text(encoding="utf-8"))
    assert identity["job_id"] == job["job_id"]
    assert identity["status"] == "completed"
    assert _checkpoint_step(checkpoint) == 1
    assert len(train_raw.read_text(encoding="utf-8").splitlines()) == 1

    # Exercise a deterministic worker failure, persisted diagnostic, retry,
    # and real checkpoint loader continuation under the same immutable identity.
    from problem2.algorithms.common.checkpoint import load_checkpoint
    from problem2.config import load_config_bundle
    from problem2.experiments.evaluation import load_evaluation_checkpoint
    from problem2.experiments.recovery import load_job_record, retry_failed_job
    from problem2.experiments.runner import JobRecord, JobRunner
    from problem2.scenarios.factory import build_synthetic_scenario

    train_module = _train_module()
    config = load_config_bundle(ROOT / "configs")
    algorithm_factory = train_module._algorithm_factory(ROOT / "configs", "s1", 0, 16, float(config.algorithm["learning_rate"]))
    recovery_record_path = output_root / "jobs" / "recovery.json"
    recovery_checkpoint = output_root / "checkpoints" / "recovery.pt"
    shutil.copy2(checkpoint, recovery_checkpoint)
    recovery_identity = JobRecord.from_dict(identity).identity
    recovery_record = JobRecord(identity=recovery_identity, checkpoint_path=recovery_checkpoint)
    calls = 0

    def worker(record: JobRecord) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("deterministic failure injection")
        algorithm, metadata = load_checkpoint(recovery_checkpoint, algorithm_factory)
        train_module.train_policy(
            lambda: build_synthetic_scenario("s1", 0, config_dir=ROOT / "configs"),
            algorithm,
            algorithm._trainer,
            updates=1,
            rollout_horizon=3,
            checkpoint_path=recovery_checkpoint,
            start_update=int(metadata["step"]),
            checkpoint_provenance={"job_id": record.job_id, **record.identity.to_dict()},
        )
        return {"checkpoint_path": str(recovery_checkpoint), "checkpoint_step": 2}

    runner = JobRunner(
        worker,
        max_attempts=2,
        record_path=recovery_record_path,
        checkpoint_validator=lambda path: load_evaluation_checkpoint(path, algorithm_factory),
    )
    failed = runner.run(recovery_record)
    assert failed.status == "failed"
    assert failed.attempts == 1
    assert "deterministic failure injection" in str(failed.error)
    persisted_failure = load_job_record(recovery_record_path)
    assert persisted_failure.error == failed.error
    resumed = retry_failed_job(persisted_failure, runner)
    assert resumed.status == "completed"
    assert resumed.attempts == 2
    assert resumed.job_id == job["job_id"]
    assert resumed.checkpoint_path is not None and resumed.checkpoint_path.resolve() == recovery_checkpoint.resolve()
    assert _checkpoint_step(recovery_checkpoint) == 2

    evaluation = _run(
        "evaluate.py",
        "--config-dir",
        "configs",
        "--checkpoint",
        str(checkpoint),
        "--split",
        "validation",
        "--scenario",
        "val_001",
        "--smoke",
    )
    validation_raw = Path(str(evaluation["raw_path"]))
    assert evaluation["status"] == "completed"
    assert evaluation["split"] == "validation"
    assert validation_raw.is_file()
    validation_row = json.loads(validation_raw.read_text(encoding="utf-8").splitlines()[0])
    assert validation_row["run_id"].startswith(f"{job['job_id']}:0")
    assert validation_row["split"] == "validation"
    assert "parameter_status" in validation_row
    assert "provisional" not in validation_row

    artifacts = _run(
        "build_artifacts.py",
        str(validation_raw),
        "--output",
        str(tmp_path / "artifacts"),
        "--manifest",
        str(tmp_path / "artifacts" / "manifest.json"),
    )
    paths = {name: Path(path) for name, path in artifacts["paths"].items()}
    expected_outputs = {
        "validated_csv", "summary_json", "table_tsv", "table_markdown",
        "figure_svg", "figure_png", "manifest_json",
    }
    assert set(paths) == expected_outputs
    assert all(path.is_file() for path in paths.values())
    manifest = json.loads(paths["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["input"]["path"] == str(validation_raw)
    assert manifest["input"]["sha256"] == hashlib.sha256(validation_raw.read_bytes()).hexdigest()
    assert manifest["identity"]["method"] == ["sr_mappo_mobile"]
    assert manifest["identity"]["split"] == ["validation"]
    assert set(manifest["outputs"]) == expected_outputs - {"manifest_json"}
    assert all(set(entry) == {"path", "sha256"} for entry in manifest["outputs"].values())
    assert all(len(entry["sha256"]) == 64 for entry in manifest["outputs"].values())
    for entry in manifest["outputs"].values():
        output_path = Path(entry["path"])
        assert entry["sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()
