from __future__ import annotations

import os
import json
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from problem2.experiments.evaluation import evaluate_shared_scenarios
from problem2.experiments.job_identity import make_job_identity


def test_pid_liveness_probe_is_safe_for_current_and_missing_processes() -> None:
    from problem2.experiments.process_liveness import pid_is_alive

    assert pid_is_alive(os.getpid()) is True
    assert pid_is_alive(2_147_483_647) is False


def test_windows_pid_probe_uses_pointer_sized_handle_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from problem2.experiments import process_liveness

    class FakeFunction:
        def __init__(self, result: object) -> None:
            self.result = result
            self.argtypes = None
            self.restype = None

        def __call__(self, *_args):
            return self.result

    kernel32 = type("Kernel32", (), {})()
    kernel32.OpenProcess = FakeFunction(1 << 40)
    kernel32.CloseHandle = FakeFunction(True)
    monkeypatch.setattr(process_liveness.os, "name", "nt")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel32, raising=False)

    assert process_liveness.pid_is_alive(987_654) is True
    assert kernel32.OpenProcess.argtypes == [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    assert kernel32.OpenProcess.restype is wintypes.HANDLE
    assert kernel32.CloseHandle.argtypes == [wintypes.HANDLE]
    assert kernel32.CloseHandle.restype is wintypes.BOOL


from problem2.experiments.recovery import atomic_checkpoint, load_checkpoint, retry_failed_job
from problem2.experiments.runner import JobRecord, JobRunner


def test_job_identity_is_immutable_and_contains_config_and_commit() -> None:
    identity = make_job_identity(
        "sr_mappo_mobile",
        "s1",
        3,
        {"lr": 0.001},
        git_commit="abc123",
        source_tree_hash="1" * 64,
        git_dirty=True,
    )
    assert identity.method == "sr_mappo_mobile"
    assert identity.scale == "s1"
    assert identity.training_seed == 3
    assert identity.config_hash
    assert identity.git_commit == "abc123"
    assert identity.source_tree_hash == "1" * 64
    assert identity.git_dirty is True
    assert str(identity).startswith("sr_mappo_mobile+s1+3+")


def test_source_tree_hash_is_part_of_immutable_job_identity() -> None:
    common = dict(
        method="sr_mappo_mobile",
        scale="s1",
        training_seed=3,
        config={"lr": 0.001},
        git_commit="abc123",
    )
    first = make_job_identity(**common, source_tree_hash="1" * 64)
    second = make_job_identity(**common, source_tree_hash="2" * 64)

    assert first.job_id != second.job_id


def test_atomic_checkpoint_and_failed_retry_preserve_job_identity(tmp_path: Path) -> None:
    path = tmp_path / "job.json"
    identity = make_job_identity("fixed_support", "s1", 0, {"x": 1}, git_commit="abc")
    atomic_checkpoint(path, {"identity": str(identity), "episode": 4})
    assert load_checkpoint(path)["episode"] == 4

    calls = []
    record = JobRecord(identity=identity, status="failed", attempts=1)
    runner = JobRunner(lambda job: calls.append(job.identity) or {"episode": 5})
    result = retry_failed_job(record, runner, path)
    assert result.status == "completed"
    assert calls == [identity]
    assert json.loads(path.read_text())["identity"] == str(identity)


def test_shared_evaluation_reuses_scenarios_and_requires_explicit_sealed_entry() -> None:
    scenarios = [{"scenario_id": "s1"}, {"scenario_id": "s2"}]
    seen = []

    def method(scenario):
        seen.append(scenario["scenario_id"])
        return {"scenario_id": scenario["scenario_id"], "reduction_rate": 0.5}

    result = evaluate_shared_scenarios({"a": method, "b": method}, scenarios, split="validation")
    assert result["scenario_ids"] == ["s1", "s2"]
    assert seen == ["s1", "s2", "s1", "s2"]


def test_stale_running_job_resumes_only_after_lease_is_confirmed_dead(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    identity = make_job_identity(
        "sr_mappo_mobile", "s1", 0, {"x": 1}, git_commit="abc",
    )
    record = JobRecord(
        identity=identity,
        status="running",
        attempts=1,
        checkpoint_path=checkpoint,
        owner_pid=999999,
        owner_host="test-host",
        lease_started_at="2026-08-14T00:00:00+00:00",
    )
    calls: list[str] = []
    runner = JobRunner(
        lambda job: calls.append(job.status) or {"checkpoint_path": str(checkpoint)},
        max_attempts=2,
        checkpoint_validator=lambda _: None,
        running_job_is_stale=lambda _: True,
    )

    completed = runner.run(record)

    assert completed.status == "completed"
    assert completed.attempts == 2
    assert calls == ["running"]


def test_live_running_job_cannot_be_stolen(tmp_path: Path) -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 0, {"x": 1}, git_commit="abc")
    runner = JobRunner(
        lambda _: (_ for _ in ()).throw(AssertionError("worker must not run")),
        running_job_is_stale=lambda _: False,
    )

    with pytest.raises(ValueError, match="active lease"):
        runner.run(JobRecord(identity=identity, status="running", attempts=1))


def test_remote_running_job_becomes_stale_only_after_lease_timeout() -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 0, {"x": 1}, git_commit="abc")
    runner = JobRunner(lambda _: None, lease_timeout_s=60.0)
    now = datetime.now(timezone.utc)

    recent = JobRecord(
        identity=identity,
        status="running",
        owner_pid=123,
        owner_host="remote-host",
        lease_started_at=(now - timedelta(seconds=30)).isoformat(),
    )
    expired = JobRecord(
        identity=identity,
        status="running",
        owner_pid=123,
        owner_host="remote-host",
        lease_started_at=(now - timedelta(seconds=90)).isoformat(),
    )

    assert runner._running_job_is_stale(recent) is False
    assert runner._running_job_is_stale(expired) is True
