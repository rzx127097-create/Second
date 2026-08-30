from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_formal_cli_modules_expose_real_entry_points_without_blocked_guard() -> None:
    from scripts import run_g6_jobs, resume_g6_jobs

    assert callable(run_g6_jobs.main)
    assert callable(resume_g6_jobs.main)
    assert "formal G6 execution is not authorized" not in run_g6_jobs.main.__code__.co_consts
    assert "formal G6 recovery is not authorized" not in resume_g6_jobs.main.__code__.co_consts


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
