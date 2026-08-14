from __future__ import annotations

import json
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


def test_complete_project_smoke_resume_evaluate_and_build_artifacts(tmp_path: Path) -> None:
    runbook = ROOT / "docs" / "verification" / "complete-project-runbook.md"
    assert runbook.is_file()
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

    # Model an interrupted persisted job so the next invocation exercises the
    # real checkpoint loader and optimizer continuation path.
    identity["status"] = "failed"
    identity["error"] = "simulated interruption"
    job_file.write_text(json.dumps(identity, ensure_ascii=False), encoding="utf-8")
    resumed = _run(
        "train.py",
        "--config-dir",
        "configs",
        "--scale",
        "s1",
        "--seed",
        "0",
        "--updates",
        "1",
        "--output-root",
        str(output_root),
        "--smoke",
    )
    assert resumed["status"] == "completed"
    assert resumed["job_id"] == job["job_id"]
    assert Path(str(resumed["checkpoint_path"])).resolve() == checkpoint.resolve()
    assert _checkpoint_step(checkpoint) == 2

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

    artifacts = _run(
        "build_artifacts.py",
        str(validation_raw),
        "--output",
        str(tmp_path / "artifacts"),
        "--manifest",
        str(tmp_path / "artifacts" / "manifest.json"),
    )
    paths = {name: Path(path) for name, path in artifacts["paths"].items()}
    assert paths["validated_csv"].is_file()
    assert paths["summary_json"].is_file()
    assert paths["manifest_json"].is_file()
    manifest = json.loads(paths["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["input"]["path"] == str(validation_raw)
    assert manifest["identity"]["method"] == ["sr_mappo_mobile"]
    assert manifest["identity"]["split"] == ["validation"]
