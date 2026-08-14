from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _run(*arguments: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_matrix.py"), *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout)


def test_five_method_smoke_matrix_runs_and_resumes_without_retraining(tmp_path: Path) -> None:
    """Every registered comparison requires a real worker and stable recovery identity."""
    arguments = (
        "--config-dir", "configs",
        "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison",
        "--output-root", str(tmp_path),
        "--smoke", "--max-jobs", "5",
    )
    first_result, first = _run(*arguments)
    assert first_result.returncode == 0, first_result.stderr
    assert first["status"] == "partial"
    assert {job["method"] for job in first["jobs"]} == {
        "sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar",
        "mappo_mobile", "sr_mappo_two_stage",
    }
    assert all(job["status"] == "completed" for job in first["jobs"])
    attempts = {
        job["job_id"]: json.loads(Path(job["output"]["job_file"]).read_text(encoding="utf-8"))["attempts"]
        for job in first["jobs"]
    }

    for job in first["jobs"]:
        checkpoint = job["output"]["checkpoint_path"]
        evaluation = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts" / "evaluate.py"),
                "--config-dir", "configs",
                "--protocol", "configs/experiments/chapter4_5.yaml",
                "--checkpoint", str(checkpoint),
                "--split", "validation", "--scenario", "val_001", "--smoke",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        assert evaluation.returncode == 0, evaluation.stderr or evaluation.stdout
        payload = json.loads(evaluation.stdout)
        row = json.loads(Path(payload["raw_path"]).read_text(encoding="utf-8").splitlines()[0])
        assert row["method"] == job["method"]
        assert row["family"] == "main_comparison"
        assert row["condition_id"] == job["condition_id"]
        assert row["protocol_hash"] == job["protocol_hash"]

    second_result, second = _run(*arguments)
    assert second_result.returncode == 0, second_result.stderr
    assert all(job["status"] == "completed" for job in second["jobs"])
    assert {
        job["job_id"]: json.loads(Path(job["output"]["job_file"]).read_text(encoding="utf-8"))["attempts"]
        for job in second["jobs"]
    } == attempts


def test_nonmain_family_dry_run_is_side_effect_free(tmp_path: Path) -> None:
    result, payload = _run(
        "--config-dir", "configs",
        "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "mechanism",
        "--output-root", str(tmp_path),
        "--dry-run",
    )

    assert result.returncode == 0
    assert payload["job_count"] == 90
    assert payload["family"] == "mechanism"
    assert list(tmp_path.iterdir()) == []
