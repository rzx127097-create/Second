from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from problem2.config import load_config_bundle
from problem2.scenarios.factory import build_synthetic_scenario


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def _low_supply_actions(snapshot):
    actions = {}
    for agent_id, mask in snapshot.action_masks.items():
        if agent_id.startswith("uav-"):
            actions[agent_id] = "spray" if "spray" in mask.valid_actions else "hold"
        else:
            actions[agent_id] = "hold"
    return actions


def test_resource_demand_reaches_service_state_machine_and_transfers_pesticide():
    bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
    initial = bundle.reset()
    initial_total = bundle.resources.total_pesticide_l

    # Exhaust UAV onboard pesticide until a request is generated.
    for _ in range(120):
        step = bundle.step(_low_supply_actions(initial))
        initial = step
        if any(event["event_type"] == "request_created" for event in step.events):
            break
    else:
        pytest.fail("resource scarcity did not create a replenishment request")

    assert bundle.request_manager is not None
    assert len(bundle.request_manager) > 0
    request = next(iter(bundle.request_manager._requests.values()))
    assert request.status.value in {"open", "reserved", "serving", "partially_satisfied", "completed"}

    transferred = 0.0
    for _ in range(80):
        snapshot = bundle.reset() if False else initial
        vehicle_id = next(iter(bundle.adapter.vehicle_slots))
        vehicle_mask = snapshot.action_masks[vehicle_id]
        legal_slots = [a for a in vehicle_mask.valid_actions if a.startswith("slot-")]
        actions = _low_supply_actions(snapshot)
        actions[vehicle_id] = legal_slots[0] if legal_slots else "hold"
        initial = bundle.step(actions)
        transferred += sum(
            float(event.get("amount_l", 0.0))
            for event in initial.events
            if event.get("event_type") == "pesticide_transfer"
        )
        if transferred > 0:
            break

    assert transferred > 0.0
    assert bundle.resources.total_pesticide_l + bundle.resources._cumulative_sprayed_l == pytest.approx(initial_total)
    event_types = [event["event_type"] for event in initial.events]
    assert "request_created" in event_types or "pesticide_transfer" in event_types


def test_scenario_registry_produces_distinct_reproducible_splits():
    config = load_config_bundle(CONFIG_DIR)
    assert set(config.scenarios) >= {"train_001", "val_001", "test_001"}
    train = build_synthetic_scenario("train_001", seed=0, config_dir=CONFIG_DIR)
    val = build_synthetic_scenario("val_001", seed=0, config_dir=CONFIG_DIR)
    sealed = build_synthetic_scenario("test_001", seed=0, config_dir=CONFIG_DIR)
    assert train.scenario_id != val.scenario_id != sealed.scenario_id
    assert not np.array_equal(train.initial_density, val.initial_density)
    assert not np.array_equal(val.initial_density, sealed.initial_density)
    assert train.reset().episode_id != val.reset().episode_id


def test_algorithm_configuration_controls_gae_and_ppo_epochs(monkeypatch):
    from problem2.experiments import rollout_runner

    config = load_config_bundle(CONFIG_DIR)
    assert config.algorithm["discount_gamma"] != 0.98
    assert "ppo_epochs" in config.algorithm
    assert rollout_runner._training_hyperparameters(config.algorithm)["ppo_epochs"] == int(config.algorithm["ppo_epochs"])


def test_episode_rows_include_event_ledger():
    bundle = build_synthetic_scenario("s1", seed=2, config_dir=CONFIG_DIR)
    snapshot = bundle.reset()
    actions = {agent_id: mask.valid_actions[0] for agent_id, mask in snapshot.action_masks.items()}
    step = bundle.step(actions)
    assert step.events
    from problem2.experiments.metrics import episode_record_from_bundle

    record = episode_record_from_bundle(
        bundle,
        episode_id=bundle.episode_id,
        steps=1,
        total_reward=step.reward,
        reward_components=step.reward_components,
        initial_pest_total=float(bundle.initial_density.sum()),
        pesticide_initial_l=float(bundle.resources.total_pesticide_l + bundle.resources._cumulative_sprayed_l),
        events=list(step.events),
        agent_ids={"uav": ["uav-1"], "vehicle": ["vehicle-1"]},
    )
    row = record.to_row()
    assert isinstance(row["events"], list)
    assert row["event_schema_version"] == 2


def test_resume_jsonl_merge_preserves_existing_rows_and_rejects_duplicate_run_id(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.train import _merge_jsonl_rows

    path = tmp_path / "episodes.jsonl"
    old = [{"run_id": "job:0", "update": 1}]
    new = [{"run_id": "job:1", "update": 2}]
    _merge_jsonl_rows(path, new, expected_job_id="job")
    # Seed the existing file through the same boundary, then append.
    path.write_text(json.dumps(old[0]) + "\n", encoding="utf-8")
    _merge_jsonl_rows(path, new, expected_job_id="job")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["run_id"] for row in rows] == ["job:0", "job:1"]
    with pytest.raises(ValueError, match="duplicate run_id"):
        _merge_jsonl_rows(path, new, expected_job_id="job")


def test_raw_evidence_is_trimmed_to_checkpoint_step_after_interrupted_commit(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.train import _synchronize_raw_with_checkpoint

    path = tmp_path / "episodes.jsonl"
    path.write_text(
        "".join(json.dumps({"run_id": f"job:{i}", "update": i + 1}) + "\n" for i in range(2)),
        encoding="utf-8",
    )
    rows = _synchronize_raw_with_checkpoint(path, checkpoint_step=1, expected_job_id="job")
    assert len(rows) == 1
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["update"] == 1


def test_checkpoint_ahead_of_raw_evidence_is_rejected(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.train import _synchronize_raw_with_checkpoint

    path = tmp_path / "episodes.jsonl"
    path.write_text(json.dumps({"run_id": "job:0", "update": 1}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint step exceeds raw evidence"):
        _synchronize_raw_with_checkpoint(path, checkpoint_step=2, expected_job_id="job")


def test_service_completion_event_receives_completion_bonus() -> None:
    from problem2.environment.rewards import RewardWeights, compute_reward

    result = compute_reward(
        previous_density=1.0,
        current_density=1.0,
        transferred_l=0.4,
        weights=RewardWeights(service_per_l=1.0, completion_bonus=2.0),
        events=[{"event_type": "request_completed", "request_id": "req-1"}],
    )
    assert result.service == pytest.approx(2.4)
    partial = compute_reward(
        previous_density=1.0,
        current_density=1.0,
        transferred_l=0.4,
        weights=RewardWeights(service_per_l=1.0, completion_bonus=2.0),
        events=[{"event_type": "service_released", "request_id": "req-1"}],
    )
    assert partial.service == pytest.approx(0.4)


def test_artifact_outputs_are_atomic_and_leave_no_temporary_files(tmp_path):
    from problem2.artifacts import build_artifacts

    raw = tmp_path / "raw.jsonl"
    row = {
        "run_id": "job:0", "method": "sr_mappo_mobile", "scale": "s1", "training_seed": 0,
        "scenario_id": "val_001", "config_hash": "c", "git_commit": "g", "split": "validation",
        "reduction_rate": 0.5, "success": False, "transferred_l": 0.0, "provisional": True,
    }
    raw.write_text(json.dumps(row) + "\n", encoding="utf-8")
    output = tmp_path / "artifacts"
    build_artifacts(raw, output, manifest=output / "manifest.json")
    assert not list(output.glob("*.tmp*"))
