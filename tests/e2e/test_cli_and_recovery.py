from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.job_identity import GitProvenance, capture_git_commit, make_job_identity
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


def _train_module():
    source = ROOT / "scripts" / "train.py"
    spec = importlib.util.spec_from_file_location("problem2_train_recovery_cli", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checkpoint_step(path: Path) -> int:
    torch = pytest.importorskip("torch")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    return int(payload["step"])


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
    assert {
        "job_id", "config_hash", "git_commit", "source_tree_hash", "git_dirty",
        "status", "attempts", "checkpoint_path", "checkpoint_sha256",
        "checkpoint_step", "error",
    } <= job.keys()
    assert job["status"] == "completed"
    assert Path(str(job["checkpoint_path"])).is_file()
    assert {
        "run_id", "method", "scale", "training_seed", "scenario_id", "config_hash",
        "git_commit", "source_tree_hash", "checkpoint_sha256", "checkpoint_step",
        "reduction_rate", "success", "transferred_l",
    } <= row.keys()
    assert row["method"] == "sr_mappo_mobile"
    assert len(str(job["source_tree_hash"])) == 64
    assert len(str(job["checkpoint_sha256"])) == 64
    checkpoint_payload = pytest.importorskip("torch").load(
        Path(str(job["checkpoint_path"])), map_location="cpu", weights_only=False,
    )
    assert checkpoint_payload["provenance"]["job_id"] == job["job_id"]
    assert checkpoint_payload["provenance"]["source_tree_hash"] == job["source_tree_hash"]

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
    assert evaluation_row["checkpoint_sha256"] == job["checkpoint_sha256"]
    assert evaluation_row["source_tree_hash"] == job["source_tree_hash"]


def test_train_cli_commits_each_update_and_resumes_after_mid_job_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    module = _train_module()
    original_train_policy = module.train_policy
    calls = 0

    def fail_on_second_update(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected failure after first committed update")
        return original_train_policy(*args, **kwargs)

    monkeypatch.setattr(module, "train_policy", fail_on_second_update)
    arguments = [
        "--config-dir", str(ROOT / "configs"),
        "--scale", "s1", "--seed", "0", "--updates", "2",
        "--output-root", str(tmp_path), "--smoke",
    ]

    assert module.main(arguments) == 1
    job_path = next((tmp_path / "jobs").glob("*.json"))
    failed = load_job_record(job_path)
    assert failed.status == "failed"
    assert failed.checkpoint_path is not None
    assert _checkpoint_step(failed.checkpoint_path) == 1
    raw_path = tmp_path / "raw" / f"{failed.job_id}.jsonl"
    assert len(raw_path.read_text(encoding="utf-8").splitlines()) == 1

    monkeypatch.setattr(module, "train_policy", original_train_policy)
    assert module.main(arguments) == 0
    completed = load_job_record(job_path)
    assert completed.status == "completed"
    assert completed.attempts == 2
    assert completed.job_id == failed.job_id
    assert _checkpoint_step(completed.checkpoint_path) == 2
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    assert [row["update"] for row in rows] == [1, 2]
    assert len({row["run_id"] for row in rows}) == 2


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


def test_evaluate_cli_rejects_checkpoint_without_persisted_job_identity(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoints" / "orphan.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"not-a-valid-checkpoint")
    result = _cli(
        "evaluate.py", "--config-dir", "configs", "--checkpoint", str(checkpoint),
        "--split", "validation", "--scenario", "val_001", "--smoke",
    )

    assert result.returncode != 0
    assert "job record" in str(_json_output(result)["error"])


def test_completed_job_rejects_corrupt_checkpoint_before_worker(tmp_path: Path) -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 0, {"lr": 0.001}, git_commit="abc123")
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"corrupt")
    calls: list[str] = []
    runner = JobRunner(
        lambda record: calls.append(record.job_id),
        checkpoint_validator=lambda path: (_ for _ in ()).throw(ValueError("invalid evaluation checkpoint")),
    )

    result = runner.run(JobRecord(identity=identity, status="completed", checkpoint_path=checkpoint))

    assert result.status == "failed"
    assert "invalid evaluation checkpoint" in str(result.error)
    assert calls == []


def test_completed_job_without_checkpoint_becomes_failed_and_persists_diagnostic(tmp_path: Path) -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 0, {"lr": 0.001}, git_commit="abc123")
    record_path = tmp_path / "jobs" / "missing.json"
    runner = JobRunner(
        lambda _: pytest.fail("completed job without checkpoint must not rerun worker"),
        record_path=record_path,
        checkpoint_validator=lambda _: None,
    )
    result = runner.run(JobRecord(identity=identity, status="completed"))

    assert result.status == "failed"
    assert "checkpoint" in str(result.error).lower()
    assert load_job_record(record_path).status == "failed"
    assert "checkpoint" in str(load_job_record(record_path).error).lower()


def test_matrix_dry_run_is_json_and_does_not_create_execution_outputs(tmp_path: Path) -> None:
    result = _cli("run_matrix.py", "--config-dir", "configs", "--output-root", str(tmp_path), "--dry-run")

    assert result.returncode == 0, result.stderr
    payload = _json_output(result)
    assert payload["status"] == "dry_run"
    assert payload["provisional"] is True
    assert payload["job_count"] == 150
    assert all(job["method"] != "sr_mappo_rolling_astar" for job in payload["jobs"])
    assert list(tmp_path.iterdir()) == []


def test_matrix_smoke_executes_each_registered_method(tmp_path: Path) -> None:
    result = _cli(
        "run_matrix.py", "--config-dir", "configs", "--output-root", str(tmp_path),
        "--smoke", "--max-jobs", "5",
    )

    assert result.returncode == 0, result.stderr
    payload = _json_output(result)
    assert payload["status"] == "partial"
    outputs = payload["jobs"]
    methods = {item["method"] for item in outputs}
    assert methods == {"sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage"}
    assert all(item["status"] == "completed" for item in outputs)


def test_matrix_default_max_jobs_reports_partial_execution(tmp_path: Path) -> None:
    result = _cli("run_matrix.py", "--config-dir", "configs", "--output-root", str(tmp_path), "--smoke")

    assert result.returncode == 0
    payload = _json_output(result)
    assert payload["status"] == "partial"
    assert payload["selected_count"] == 1
    assert payload["total_count"] == 150
    assert len(payload["jobs"]) == 1


def test_matrix_smoke_handles_unicode_output_root_without_decode_failure(tmp_path: Path) -> None:
    """The real Windows workspace contains Chinese path components."""
    output_root = tmp_path / "论文" / "第二问"
    result = _cli(
        "run_matrix.py", "--config-dir", "configs", "--output-root", str(output_root),
        "--smoke", "--max-jobs", "1",
    )

    assert result.returncode == 0, result.stderr
    payload = _json_output(result)
    assert payload["status"] == "partial"
    assert payload["jobs"][0]["status"] == "completed"


def test_matrix_smoke_rejects_matrix_without_mobile_method(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    shutil.copytree(ROOT / "configs", config_dir)
    formal = config_dir / "experiments" / "formal_matrix.yaml"
    formal.write_text(formal.read_text(encoding="utf-8").replace(
        "methods: [sr_mappo_mobile, sr_mappo_fixed, sr_mappo_astar, mappo_mobile, sr_mappo_two_stage]",
        "methods: [sr_mappo_fixed]",
    ), encoding="utf-8")
    result = _cli(
        "run_matrix.py", "--config-dir", str(config_dir), "--output-root", str(tmp_path / "runs"),
        "--smoke",
    )

    assert result.returncode != 0
    assert "no sr_mappo_mobile jobs" in str(_json_output(result)["error"])


def test_sealed_test_rejects_smoke_mode_for_formal_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    source = ROOT / "scripts" / "evaluate.py"
    spec = importlib.util.spec_from_file_location("problem2_evaluate_cli", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = load_config_bundle(ROOT / "configs")
    checkpoint = tmp_path / "checkpoints" / "sealed.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"placeholder-for-mocked-loader")
    identity = make_job_identity(
        "sr_mappo_mobile", "s1", 0, config_identity(config),
        config_hash=config_identity(config), git_commit=capture_git_commit(str(ROOT)),
    )
    save_job_record(
        tmp_path / "jobs" / "sealed.json",
        JobRecord(
            identity=identity,
            status="completed",
            checkpoint_path=checkpoint,
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            checkpoint_step=1,
        ),
    )
    seen: dict[str, object] = {}

    class Snapshot:
        role_observations = {"uav-1": {"vector": [0.0], "role": "uav"}, "vehicle-1": {"vector": [0.0], "role": "vehicle"}}
        critic_state = {"vector": [0.0]}
        action_masks = {"uav-1": [True], "vehicle-1": [True]}

    monkeypatch.setattr(module, "_is_provisional", lambda _: False)
    expected_provenance = {"job_id": identity.job_id, **identity.to_dict()}
    monkeypatch.setattr(module, "load_evaluation_checkpoint", lambda *_: (object(), {"step": 1, "format": 2, "provenance": expected_provenance}))
    monkeypatch.setattr(module, "build_synthetic_scenario", lambda *_args, **_kwargs: type("Bundle", (), {"reset": lambda self: Snapshot()})())
    monkeypatch.setattr(
        module,
        "reserve_sealed_access",
        lambda *_args, **_kwargs: {
            "reservation_id": "reservation-1",
            "access_key": f"{identity.job_id}:test_001",
        },
    )
    monkeypatch.setattr(
        module,
        "commit_sealed_access",
        lambda *_args, **_kwargs: {"access_key": f"{identity.job_id}:test_001"},
    )
    monkeypatch.setattr(module, "release_sealed_access", lambda *_args, **_kwargs: True)

    def fake_evaluate(policy, factory, *, scenarios, split, deterministic):
        seen.update(split=split, deterministic=deterministic)
        return []

    monkeypatch.setattr(module, "evaluate_policy", fake_evaluate)
    assert module.main([
        "--config-dir", str(ROOT / "configs"), "--checkpoint", str(checkpoint),
        "--split", "sealed_test", "--scenario", "test_001", "--smoke",
        "--freeze-manifest", str(tmp_path / "freeze.json"),
        "--sealed-unlock", str(tmp_path / "unlock.json"),
    ]) == 1
    assert seen == {}


def test_formal_evaluation_requires_the_exact_clean_training_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ROOT / "scripts" / "evaluate.py"
    spec = importlib.util.spec_from_file_location("problem2_evaluate_source_guard", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    identity = make_job_identity(
        "sr_mappo_mobile", "s1", 0, {"x": 1},
        git_commit="a" * 40,
        source_tree_hash="b" * 64,
        git_dirty=False,
    )
    job = JobRecord(identity=identity)
    monkeypatch.setattr(
        module,
        "capture_git_provenance",
        lambda *_: GitProvenance("a" * 40, "c" * 64, False),
    )

    with pytest.raises(ValueError, match="source tree"):
        module._assert_evaluation_source(job, smoke=False)

    with pytest.raises(ValueError, match="source tree"):
        module._assert_evaluation_source(job, smoke=True)


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

    runner = JobRunner(fail_once, max_attempts=2, record_path=record_path, checkpoint_validator=lambda _: None)
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
