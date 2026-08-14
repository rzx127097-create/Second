from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from problem2.experiments.job_identity import make_job_identity
from problem2.experiments.recovery import load_job_record, retry_failed_job, save_job_record
from problem2.experiments.runner import JobRecord, JobRunner


ROOT = Path(__file__).resolve().parents[2]


def _cli(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *arguments],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _json_output(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_train_cli_runs_real_smoke_job_and_writes_traceable_raw_rows(tmp_path: Path) -> None:
    """Removing real rollout execution or identity enrichment breaks this boundary."""
    result = _cli(
        "train.py",
        "--config-dir", "configs",
        "--scale", "s1",
        "--seed", "0",
        "--updates", "1",
        "--output-root", str(tmp_path),
        "--smoke",
    )

    assert result.returncode == 0, result.stderr
    payload = _json_output(result)
    assert payload["status"] == "completed"
    job_file = Path(str(payload["job_file"]))
    raw_path = Path(str(payload["raw_path"]))
    job = json.loads(job_file.read_text(encoding="utf-8"))
    row = json.loads(raw_path.read_text(encoding="utf-8").splitlines()[0])
    assert {"job_id", "config_hash", "git_commit", "status", "attempts", "checkpoint_path", "error"} <= job.keys()
    assert job["status"] == "completed"
    assert Path(str(job["checkpoint_path"])).is_file()
    assert {
        "run_id", "method", "scale", "training_seed", "scenario_id", "config_hash",
        "git_commit", "reduction_rate", "success", "transferred_l",
    } <= row.keys()
    assert row["method"] == "sr_mappo_mobile"

    evaluated = _cli(
        "evaluate.py", "--config-dir", "configs", "--checkpoint", str(job["checkpoint_path"]),
        "--split", "validation", "--scenario", "val_001", "--smoke",
    )
    assert evaluated.returncode == 0, evaluated.stderr
    evaluation = _json_output(evaluated)
    assert evaluation["status"] == "completed"
    evaluation_row = json.loads(Path(str(evaluation["raw_path"])).read_text(encoding="utf-8").splitlines()[0])
    assert evaluation_row["split"] == "validation"
    assert evaluation_row["scenario_id"] == "val_001"


def test_train_cli_blocks_provisional_formal_execution(tmp_path: Path) -> None:
    result = _cli(
        "train.py", "--config-dir", "configs", "--scale", "s1", "--seed", "0",
        "--updates", "1", "--output-root", str(tmp_path),
    )

    assert result.returncode != 0
    payload = _json_output(result)
    assert payload["status"] == "rejected"
    assert "provisional" in str(payload["error"])


def test_evaluate_cli_checks_checkpoint_and_split_isolation(tmp_path: Path) -> None:
    missing = _cli(
        "evaluate.py", "--config-dir", "configs", "--checkpoint", str(tmp_path / "missing.pt"),
        "--split", "validation", "--scenario", "val_001", "--smoke",
    )
    assert missing.returncode != 0
    assert "checkpoint" in str(_json_output(missing)["error"])

    wrong_split = _cli(
        "evaluate.py", "--config-dir", "configs", "--checkpoint", str(tmp_path / "missing.pt"),
        "--split", "validation", "--scenario", "train_001", "--smoke",
    )
    assert wrong_split.returncode != 0
    assert "does not belong" in str(_json_output(wrong_split)["error"])


def test_matrix_dry_run_is_json_and_does_not_create_execution_outputs(tmp_path: Path) -> None:
    result = _cli("run_matrix.py", "--config-dir", "configs", "--output-root", str(tmp_path), "--dry-run")

    assert result.returncode == 0, result.stderr
    payload = _json_output(result)
    assert payload["status"] == "dry_run"
    assert payload["provisional"] is True
    assert payload["job_count"] == 150
    assert all(job["method"] != "sr_mappo_rolling_astar" for job in payload["jobs"])
    assert list(tmp_path.iterdir()) == []


def test_failed_job_retries_only_its_identity_and_persists_full_error(tmp_path: Path) -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 0, {"lr": 0.001}, git_commit="abc123")
    record_path = tmp_path / "jobs" / "job.json"
    calls: list[str] = []

    def fail_once(record: JobRecord) -> dict[str, object]:
        calls.append(record.job_id)
        if len(calls) == 1:
            raise RuntimeError("simulated worker failure")
        checkpoint = tmp_path / "checkpoint.pt"
        checkpoint.write_bytes(b"checkpoint")
        return {"checkpoint_path": str(checkpoint)}

    runner = JobRunner(fail_once, max_attempts=2, record_path=record_path)
    first = runner.run(JobRecord(identity=identity, checkpoint_path=tmp_path / "checkpoint.pt"))
    assert first.status == "failed"
    assert "RuntimeError: simulated worker failure" in str(first.error)
    assert load_job_record(record_path).attempts == 1

    resumed = retry_failed_job(load_job_record(record_path), runner)
    assert resumed.status == "completed"
    assert resumed.job_id == first.job_id
    assert calls == [first.job_id, first.job_id]
    assert load_job_record(record_path).attempts == 2
    with pytest.raises(ValueError, match="only failed jobs"):
        retry_failed_job(resumed, runner)

    saved = save_job_record(record_path, resumed)
    assert saved == record_path
