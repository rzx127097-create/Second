from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


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


def _run_script(script: str, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    payload = json.loads(result.stdout) if result.stdout else {}
    return result, payload


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


@pytest.mark.parametrize(
    ("family", "expected_count"),
    [
        ("main_comparison", 150),
        ("mechanism", 90),
        ("sensitivity", 120),
        ("adaptation", 120),
        ("ablation", 60),
    ],
)
def test_every_chapter45_family_dry_run_has_frozen_job_count(
    tmp_path: Path, family: str, expected_count: int,
) -> None:
    result, payload = _run(
        "--config-dir", "configs",
        "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", family,
        "--output-root", str(tmp_path),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "dry_run"
    assert payload["family"] == family
    assert payload["job_count"] == expected_count
    assert payload["provisional"] is True
    assert list(tmp_path.iterdir()) == []


def test_matrix_evaluation_runs_all_shared_scale_scenarios_and_reuses_outputs(
    tmp_path: Path,
) -> None:
    train_result, train_payload = _run(
        "--config-dir", "configs",
        "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison",
        "--output-root", str(tmp_path),
        "--smoke", "--max-jobs", "1",
    )
    assert train_result.returncode == 0, train_result.stderr
    assert train_payload["jobs"][0]["status"] == "completed"

    arguments = (
        "--config-dir", "configs",
        "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison",
        "--output-root", str(tmp_path),
        "--split", "validation",
        "--smoke", "--max-jobs", "1",
    )
    first_result, first = _run_script("evaluate_matrix.py", *arguments)
    assert first_result.returncode == 0, first_result.stderr or first_result.stdout
    assert first["status"] == "partial"
    assert first["selected_job_count"] == 1
    assert first["evaluation_count"] == 2
    assert {item["scenario"] for item in first["evaluations"]} == {"val_001", "val_s1_002"}
    assert all(item["status"] == "completed" for item in first["evaluations"])
    raw_paths = [Path(str(item["raw_path"])) for item in first["evaluations"]]
    assert all(path.is_file() for path in raw_paths)
    rows = [json.loads(path.read_text(encoding="utf-8").splitlines()[0]) for path in raw_paths]
    assert {row["scenario_id"] for row in rows} == {"val_001", "val_s1_002"}
    assert len({row["run_id"] for row in rows}) == 2

    second_result, second = _run_script("evaluate_matrix.py", *arguments)
    assert second_result.returncode == 0, second_result.stderr or second_result.stdout
    assert all(item["reused"] is True for item in second["evaluations"])


def test_matrix_evaluation_rejects_conflicting_simulation_and_smoke(
    tmp_path: Path,
) -> None:
    result, payload = _run_script(
        "evaluate_matrix.py",
        "--config-dir", "configs",
        "--output-root", str(tmp_path),
        "--split", "validation",
        "--simulation", "--smoke",
    )

    assert result.returncode != 0
    assert "cannot be combined" in str(payload["error"])


def test_sealed_matrix_reruns_evaluation_when_existing_raw_has_no_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    source = ROOT / "scripts" / "evaluate_matrix.py"
    module_spec = importlib.util.spec_from_file_location("problem2_sealed_recovery", source)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    identity = SimpleNamespace(
        job_id="job-1",
        method="sr_mappo_mobile",
        scale="s1",
        training_seed=0,
        config_hash="c" * 64,
        git_commit="d" * 40,
        family="main_comparison",
        condition_id="direct",
        protocol_hash="p" * 64,
        source_tree_hash="s" * 64,
    )
    planned = SimpleNamespace(identity=identity)
    job = SimpleNamespace(
        identity=identity,
        status="completed",
        checkpoint_path=tmp_path / "checkpoint.pt",
        checkpoint_sha256="h" * 64,
        checkpoint_step=10,
    )

    class FakeOrchestrator:
        def __init__(self, *_args, **_kwargs) -> None:
            self.config = SimpleNamespace(
                experiments={"sealed_test_scenarios": ["test_001"]},
                scenarios={"test_001": {"scale": "s1"}},
            )
            self.spec = SimpleNamespace(status="verified")
            self.protocol_path = ROOT / "configs" / "experiments" / "chapter4_5.yaml"
            self.protocol_hash = "p" * 64

        def plan(self, *_args, **_kwargs):
            return (planned,)

    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / "job-1.json").write_text("{}", encoding="utf-8")
    raw_path = tmp_path / "raw" / "evaluation-job-1-test_001.jsonl"
    raw_path.parent.mkdir()
    row = {
        "run_id": "job-1:0:test_001",
        "job_id": "job-1",
        "method": "sr_mappo_mobile",
        "scale": "s1",
        "training_seed": 0,
        "scenario_id": "test_001",
        "split": "sealed_test",
        "config_hash": "c" * 64,
        "git_commit": "d" * 40,
        "family": "main_comparison",
        "condition_id": "direct",
        "protocol_hash": "p" * 64,
        "source_tree_hash": "s" * 64,
        "checkpoint_sha256": "h" * 64,
        "checkpoint_step": 10,
    }
    raw_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    verification_calls = 0
    commit_calls = 0
    child_calls = 0

    def verify(*_args, **_kwargs):
        nonlocal verification_calls
        verification_calls += 1
        raise ValueError("sealed evidence has no consumed unlock receipt")

    def commit(*_args, **_kwargs):
        nonlocal commit_calls
        commit_calls += 1
        return {"access_key": "job-1:test_001"}

    def run_child(*_args, **_kwargs):
        nonlocal child_calls
        child_calls += 1
        return {
            "returncode": 0,
            "payload": {
                "status": "completed",
                "raw_path": str(raw_path),
            },
        }

    monkeypatch.setattr(module, "Chapter45Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(module, "_is_provisional", lambda _: False)
    monkeypatch.setattr(module, "load_job_record", lambda _: job)
    monkeypatch.setattr(module, "verify_sealed_evidence", verify, raising=False)
    monkeypatch.setattr(
        module, "reserve_sealed_access",
        lambda *_args, **_kwargs: {"reservation_id": "recovery-1"},
        raising=False,
    )
    monkeypatch.setattr(module, "commit_sealed_access", commit, raising=False)
    monkeypatch.setattr(module, "release_sealed_access", lambda *_args, **_kwargs: True, raising=False)
    monkeypatch.setattr(module, "run_utf8_json_child", run_child)

    assert module.main([
        "--config-dir", str(ROOT / "configs"),
        "--output-root", str(tmp_path),
        "--split", "sealed_test",
        "--max-jobs", "1",
        "--freeze-manifest", str(tmp_path / "freeze.json"),
        "--sealed-unlock", str(tmp_path / "unlock.json"),
    ]) == 0
    assert verification_calls == 1
    assert child_calls == 1
    assert commit_calls == 0
