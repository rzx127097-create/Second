from __future__ import annotations

import json
from pathlib import Path

from problem2.experiments.evaluation import evaluate_shared_scenarios
from problem2.experiments.job_identity import make_job_identity
from problem2.experiments.recovery import atomic_checkpoint, load_checkpoint, retry_failed_job
from problem2.experiments.runner import JobRecord, JobRunner


def test_job_identity_is_immutable_and_contains_config_and_commit() -> None:
    identity = make_job_identity("sr_mappo_mobile", "s1", 3, {"lr": 0.001}, git_commit="abc123")
    assert identity.method == "sr_mappo_mobile"
    assert identity.scale == "s1"
    assert identity.training_seed == 3
    assert identity.config_hash
    assert identity.git_commit == "abc123"
    assert str(identity).startswith("sr_mappo_mobile+s1+3+")


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

