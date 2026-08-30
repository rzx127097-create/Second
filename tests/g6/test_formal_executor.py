from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from problem2.experiments.identity import canonical_training_identity


ROOT = Path(__file__).resolve().parents[2]
TRAINING_MANIFEST = ROOT / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/g6-training-jobs.json"


def test_load_frozen_job_follows_frozen_scheduler_order() -> None:
    from problem2.training.formal_g6 import load_frozen_job

    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = load_frozen_job(ROOT, index=0)

    scheduler_identity = payload["scheduler_order"][0]
    expected = next(
        entry for entry in payload["jobs"]
        if entry["canonical_training_identity"] == scheduler_identity
    )
    assert job == expected
    assert job["canonical_training_identity"] == scheduler_identity
    assert job["canonical_training_identity"] == canonical_training_identity(
        job["method"], job["scale"], job["training_seed"], job["config_hash"], job["git_commit"]
    )


def test_load_frozen_job_rejects_out_of_range_and_identity_drift() -> None:
    from problem2.training.formal_g6 import load_frozen_job

    with pytest.raises(ValueError, match="index"):
        load_frozen_job(ROOT, index=375)

    with pytest.raises(ValueError, match="identity"):
        load_frozen_job(ROOT, index=0, expected_identity="0" * 64)


def test_formal_job_paths_are_confined_to_dynamic_g6_root(tmp_path: Path) -> None:
    from problem2.training.formal_g6 import formal_job_paths

    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = payload["jobs"][0]
    paths = formal_job_paths(ROOT, job, output_root=tmp_path)

    assert paths.root.is_relative_to(tmp_path.resolve())
    assert paths.checkpoints.is_relative_to(paths.root)
    assert paths.ledger.is_relative_to(tmp_path.resolve())


def test_validation_manifest_must_match_job_panel_and_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from problem2.training import formal_g6

    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = next(
        entry for entry in payload["jobs"]
        if entry["canonical_training_identity"] == payload["scheduler_order"][0]
    )
    validation = json.loads(
        (ROOT / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/g6-validation-evaluations.json").read_text(
            encoding="utf-8"
        )
    )
    validation["scenario_panel_hash"] = "0" * 64
    original_load_json = formal_g6._load_json

    def load_json(path: Path, label: str):
        if path.name == "g6-validation-evaluations.json":
            return validation
        return original_load_json(path, label)

    monkeypatch.setattr(formal_g6, "_load_json", load_json)

    with pytest.raises(ValueError, match="scenario panel"):
        formal_g6._validate_validation_manifest(ROOT, job)


def test_validate_job_rejects_candidate_configuration_drift() -> None:
    from problem2.training import formal_g6

    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = dict(
        next(
            entry for entry in payload["jobs"]
            if entry["canonical_training_identity"] == payload["scheduler_order"][0]
        )
    )
    source_commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    job["git_commit"] = source_commit
    job["canonical_training_identity"] = canonical_training_identity(
        job["method"], job["scale"], job["training_seed"], job["config_hash"], source_commit
    )
    job["dependency_graph"] = dict(job["dependency_graph"], source_commit=source_commit)
    job["selected_candidate_config_hash"] = "0" * 64

    with pytest.raises(ValueError, match="candidate"):
        formal_g6._validate_job(ROOT, job)


def test_frozen_source_commit_accepts_ancestor_with_matching_source_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from problem2.training import formal_g6
    from scripts.freeze_g5 import _source_scope_hash

    frozen_commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True
    ).strip()
    source_scope = _source_scope_hash(ROOT)
    monkeypatch.setattr(formal_g6, "_source_scope_hash", lambda root: source_scope)

    assert formal_g6._source_commit_compatible(ROOT, frozen_commit, source_scope)


def test_formal_cli_modules_expose_real_entry_points_without_blocked_guard() -> None:
    from scripts import run_g6_jobs, resume_g6_jobs

    assert callable(run_g6_jobs.main)
    assert callable(resume_g6_jobs.main)
    assert "formal G6 execution is not authorized" not in run_g6_jobs.main.__code__.co_consts
    assert "formal G6 recovery is not authorized" not in resume_g6_jobs.main.__code__.co_consts


def test_preflight_cli_resolves_dynamic_freeze_from_script_context() -> None:
    result = __import__("subprocess").run(
        [sys.executable, "scripts/preflight_g6.py", "--root", str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["all_pass"] is True


def test_short_interruption_and_resume_reproduce_uninterrupted_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from problem2.training import formal_g6

    manifest = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = dict(manifest["jobs"][0])
    source_commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    job["git_commit"] = source_commit
    job["canonical_training_identity"] = canonical_training_identity(
        job["method"], job["scale"], job["training_seed"], job["config_hash"], source_commit
    )
    job["environment_interactions"] = 4
    job["checkpoint_interval"] = 2
    job["checkpoint_count"] = 2
    job["dependency_graph"] = dict(job["dependency_graph"], source_commit=source_commit)

    class FakeAlgorithm:
        method_id = "sr_mappo_mobile"

        def __init__(self) -> None:
            self.value = 0

        def act(self, observations, masks, *, deterministic=False, return_details=False):
            return {"actions": {}, "masks": {}} if return_details else SimpleNamespace(actions={}, masks={})

        def state_dict(self):
            return {"value": self.value, "training": True}

        def load_state_dict(self, state):
            self.value = int(state["value"])

        def set_evaluation(self, enabled: bool) -> None:
            del enabled

    class FakeEnvironment:
        scenario_id = 10000
        max_steps = 100

        def __init__(self) -> None:
            self.count = 0
            self._current_view = None
            self.state = SimpleNamespace(terminated=False)

        def _view(self, truncated: bool = False):
            return {"scenario_id": 10000, "observations": {}, "masks": {}, "truncated": truncated, "team_reward": 0.1}

        def reset(self, *, scenario_id=None):
            del scenario_id
            self.count = 0
            self.state.terminated = False
            self._current_view = self._view()
            return self._current_view

        def step(self, action_result, **kwargs):
            del action_result, kwargs
            self.count += 1
            self.state.terminated = self.count >= 100
            self._current_view = self._view(False)
            return self._current_view

        def state_dict(self):
            return {"scenario_id": self.scenario_id, "count": self.count}

        def load_state_dict(self, state):
            self.count = int(state["count"])
            self.state.terminated = False
            self._current_view = self._view()

    monkeypatch.setattr(formal_g6, "build_algorithm", lambda *args, **kwargs: FakeAlgorithm())
    monkeypatch.setattr(formal_g6, "build_development_environment", lambda *args, **kwargs: FakeEnvironment())
    monkeypatch.setattr(formal_g6, "_as_action_result", lambda details: details)
    monkeypatch.setattr(formal_g6, "build_physical_envelope", lambda *args, **kwargs: None)
    monkeypatch.setattr(formal_g6, "_observe_physical_algorithm", lambda *args, **kwargs: None)
    monkeypatch.setattr(formal_g6, "_update_interval", lambda algorithm: ("fake", 1))
    monkeypatch.setattr(formal_g6, "_update_physical_algorithm", lambda algorithm, **kwargs: {"loss": float(algorithm.value + 1)})

    interrupted = formal_g6.run_formal_job(ROOT, job, device="cpu", output_root=tmp_path / "resumed", stop_after_interactions=2, evaluate_validation=False)
    assert interrupted["status"] == "interrupted"
    resumed = formal_g6.resume_formal_job(ROOT, job, device="cpu", output_root=tmp_path / "resumed", evaluate_validation=False)
    direct = formal_g6.run_formal_job(ROOT, job, device="cpu", output_root=tmp_path / "direct", evaluate_validation=False)

    assert resumed["status"] == direct["status"] == "completed"
    assert resumed["interactions"] == direct["interactions"] == 4
    assert [item["interaction_count"] for item in resumed["checkpoints"]] == [2, 4]
    assert resumed["checkpoint_count"] == 2
    resumed_checkpoint = sorted((tmp_path / "resumed" / "jobs" / job["canonical_training_identity"] / "checkpoints").glob("checkpoint-*.pt"))[-1]
    direct_checkpoint = sorted((tmp_path / "direct" / "jobs" / job["canonical_training_identity"] / "checkpoints").glob("checkpoint-*.pt"))[-1]
    resumed_payload = __import__("torch").load(resumed_checkpoint, map_location="cpu", weights_only=False)
    direct_payload = __import__("torch").load(direct_checkpoint, map_location="cpu", weights_only=False)
    assert resumed_payload["state"]["algorithm"] == direct_payload["state"]["algorithm"]
    assert resumed_payload["state"]["formal_state"] == direct_payload["state"]["formal_state"]


def test_resume_backfills_validation_for_existing_checkpoint_without_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from problem2.training import formal_g6

    manifest = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = dict(manifest["jobs"][0])
    source_commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    job["git_commit"] = source_commit
    job["canonical_training_identity"] = canonical_training_identity(
        job["method"], job["scale"], job["training_seed"], job["config_hash"], source_commit
    )
    job["environment_interactions"] = 4
    job["checkpoint_interval"] = 2
    job["checkpoint_count"] = 2
    job["dependency_graph"] = dict(job["dependency_graph"], source_commit=source_commit)

    class FakeAlgorithm:
        method_id = "sr_mappo_mobile"

        def __init__(self) -> None:
            self.value = 0

        def act(self, observations, masks, *, deterministic=False, return_details=False):
            return {"actions": {}, "masks": {}} if return_details else SimpleNamespace(actions={}, masks={})

        def state_dict(self):
            return {"value": self.value, "training": True}

        def load_state_dict(self, state):
            self.value = int(state["value"])

        def set_evaluation(self, enabled: bool) -> None:
            del enabled

    class FakeEnvironment:
        scenario_id = 10000
        max_steps = 100

        def __init__(self) -> None:
            self.count = 0
            self._current_view = None
            self.state = SimpleNamespace(terminated=False)

        def _view(self, truncated: bool = False):
            return {"scenario_id": 10000, "observations": {}, "masks": {}, "truncated": truncated, "team_reward": 0.1}

        def reset(self, *, scenario_id=None):
            del scenario_id
            self.count = 0
            self.state.terminated = False
            self._current_view = self._view()
            return self._current_view

        def step(self, action_result, **kwargs):
            del action_result, kwargs
            self.count += 1
            self.state.terminated = self.count >= 100
            self._current_view = self._view(False)
            return self._current_view

        def state_dict(self):
            return {"scenario_id": self.scenario_id, "count": self.count}

        def load_state_dict(self, state):
            self.count = int(state["count"])
            self.state.terminated = False
            self._current_view = self._view()

    monkeypatch.setattr(formal_g6, "build_algorithm", lambda *args, **kwargs: FakeAlgorithm())
    monkeypatch.setattr(formal_g6, "build_development_environment", lambda *args, **kwargs: FakeEnvironment())
    monkeypatch.setattr(formal_g6, "_as_action_result", lambda details: details)
    monkeypatch.setattr(formal_g6, "build_physical_envelope", lambda *args, **kwargs: None)
    monkeypatch.setattr(formal_g6, "_observe_physical_algorithm", lambda *args, **kwargs: None)
    monkeypatch.setattr(formal_g6, "_update_interval", lambda algorithm: ("fake", 1))
    monkeypatch.setattr(formal_g6, "_update_physical_algorithm", lambda algorithm, **kwargs: {"loss": 1.0})
    monkeypatch.setattr(
        formal_g6,
        "_validate_validation_manifest",
        lambda *args, **kwargs: {
            "evaluator_hash": "a" * 64,
            "scenario_panel_hash": "b" * 64,
        },
    )
    monkeypatch.setattr(formal_g6, "validate_long_table", lambda *args, **kwargs: None)

    output_root = tmp_path / "resumed"
    interrupted = formal_g6.run_formal_job(
        ROOT, job, device="cpu", output_root=output_root,
        stop_after_interactions=2, evaluate_validation=False,
    )
    assert interrupted["status"] == "interrupted"

    evaluated_checkpoints: list[int] = []

    def fake_evaluate(
        root,
        frozen_job,
        checkpoint,
        *,
        device="cpu",
        output_path=None,
        output_root=None,
    ):
        del root, frozen_job, device, output_root
        interaction_count = int(Path(checkpoint).stem.split("-")[-1])
        evaluated_checkpoints.append(interaction_count)
        checkpoint_hash = formal_g6.artifact_sha256(Path(checkpoint))
        rows = [
            {
                "checkpoint_hash": checkpoint_hash,
                "scenario_id": scenario_id,
                "reduction_rate": 0.0,
                "success_at_0_85": False,
                "interaction_count": interaction_count,
            }
            for scenario_id in range(20000, 20050)
        ]
        if output_path is not None:
            for row in rows:
                formal_g6.append_jsonl(Path(output_path), row)
        return rows

    monkeypatch.setattr(formal_g6, "evaluate_formal_checkpoint", fake_evaluate)
    resumed = formal_g6.resume_formal_job(ROOT, job, device="cpu", output_root=output_root, evaluate_validation=True)

    assert resumed["status"] == "completed"
    assert evaluated_checkpoints == [2, 4]
    assert [item["validation_rows"] for item in resumed["checkpoints"]] == [50, 50]
    validation_rows = [
        json.loads(line)
        for line in (output_root / "jobs" / job["canonical_training_identity"] / "validation-episodes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(validation_rows) == 100


def test_checkpoint_schedule_rejects_missing_frozen_checkpoint(tmp_path: Path) -> None:
    from problem2.training.formal_g6 import _validate_checkpoint_schedule

    del tmp_path
    records = [
        {"interaction_count": interaction_count}
        for interaction_count in range(10000, 200001, 10000)
        if interaction_count != 10000
    ]
    job = {"environment_interactions": 200000, "checkpoint_interval": 10000, "checkpoint_count": 20}

    with pytest.raises(ValueError, match="checkpoint schedule"):
        _validate_checkpoint_schedule(records, job, require_complete=True)


def test_resume_revalidates_complete_existing_validation_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from problem2.training import formal_g6

    manifest = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    job = dict(manifest["jobs"][0])
    paths = formal_g6.formal_job_paths(ROOT, job, output_root=tmp_path)
    paths.root.mkdir(parents=True)
    checkpoint_hash = "a" * 64
    records = [{
        "path": "checkpoints/checkpoint-000010000.pt",
        "sha256": checkpoint_hash,
        "bytes": 1,
        "interaction_count": 10000,
        "validation_rows": 0,
    }]
    rows = [
        {"checkpoint_hash": checkpoint_hash, "scenario_id": scenario_id}
        for scenario_id in range(20000, 20050)
    ]
    paths.validation_events.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    calls: list[dict[str, object]] = []

    def reject_tampered_rows(rows, **kwargs):
        calls.append({"rows": rows, "kwargs": kwargs})
        raise ValueError("tampered validation provenance")

    monkeypatch.setattr(
        formal_g6,
        "_validate_validation_manifest",
        lambda *args, **kwargs: {"evaluator_hash": "b" * 64, "scenario_panel_hash": "c" * 64},
    )
    monkeypatch.setattr(formal_g6, "validate_long_table", reject_tampered_rows)
    with pytest.raises(ValueError, match="tampered validation provenance"):
        formal_g6._backfill_missing_validation(ROOT, job, paths, records, device="cpu")
    assert len(calls) == 1
    assert calls[0]["kwargs"]["allow_validation_access"] is True


def test_validation_panel_append_is_atomic_and_preserves_existing_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from problem2.training import formal_g6

    path = tmp_path / "validation-episodes.jsonl"
    path.write_text('{"existing":true}\n', encoding="utf-8")
    writes: list[bytes] = []

    def fake_atomic_write(target: Path, payload: bytes) -> str:
        writes.append(payload)
        target.write_bytes(payload)
        return "0" * 64

    monkeypatch.setattr(formal_g6, "atomic_write_bytes", fake_atomic_write)
    formal_g6._append_validation_rows(path, [{"checkpoint_hash": "a" * 64, "scenario_id": 20000}])

    assert len(writes) == 1
    assert path.read_text(encoding="utf-8").splitlines() == [
        '{"existing":true}',
        '{"checkpoint_hash":"' + "a" * 64 + '","scenario_id":20000}',
    ]
