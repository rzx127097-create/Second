from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_g5_validation_tuning.py"


def _validation_script():
    spec = importlib.util.spec_from_file_location("phase1_validation_tuning", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "condition_id",
    [
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "sr_mappo_nearest",
        "sr_mappo_urgency",
        "sr_mappo_two_stage",
    ],
)
def test_selected_refit_forwards_the_executable_condition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, condition_id: str
) -> None:
    module = _validation_script()
    observed: dict[str, object] = {}

    def fake_runner(job: dict[str, object], device: str, interactions: int, output: Path) -> dict[str, object]:
        observed.update(job)
        return {
            "method": str(job["method"]),
            "condition_id": str(job["condition_id"]),
            "candidate_id": str(job["candidate_id"]),
            "candidate_config_hash": "a" * 64,
            "scale": str(job["scale"]),
            "training_seed": int(job["training_seed"]),
            "scenario_id": 10000,
            "scenario_ids": list(range(10000, 10020)),
            "partition": "development",
            "interactions": interactions,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    monkeypatch.setattr(module, "run_physical_development_refit_training", fake_runner)
    result = module._run_selected_refit_job(
        {
            "method": "sr_mappo_mobile",
            "condition_id": condition_id,
            "scale": "g20x20_d2",
            "training_seed": 51001,
            "scenario_id": 10000,
            "scenario_ids": list(range(10000, 10020)),
            "partition": "development",
        },
        "cpu",
        128,
        tmp_path,
        selected={"sr_mappo_mobile": {"candidate_id": "c01", "config_hash": "a" * 64}},
        contract=object(),
    )
    assert observed["condition_id"] == condition_id
    assert result["condition_id"] == condition_id


@pytest.mark.parametrize(
    ("condition_id", "controller", "vehicle_trainable", "training_mode"),
    [
        ("sr_mappo_mobile", "learned", True, "joint"),
        ("sr_mappo_fixed", "fixed_support", False, "uav_only"),
        ("sr_mappo_astar", "rolling_astar", False, "uav_only"),
        ("sr_mappo_nearest", "nearest_feasible", False, "uav_only"),
        ("sr_mappo_urgency", "urgency_priority", False, "uav_only"),
        ("sr_mappo_two_stage", "learned_two_stage", True, "two_stage"),
    ],
)
def test_condition_selects_the_intended_controller_and_training_behavior(
    condition_id: str, controller: str, vehicle_trainable: bool, training_mode: str
) -> None:
    from problem2.training.conditions import resolve_condition_execution

    execution = resolve_condition_execution(condition_id)
    assert execution.condition_id == condition_id
    assert execution.vehicle_controller == controller
    assert execution.vehicle_trainable is vehicle_trainable
    assert execution.training_mode == training_mode
