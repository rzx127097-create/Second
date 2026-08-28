from pathlib import Path

import pytest

from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.evaluation.schema import DYNAMIC_RAW_EPISODE_SCHEMA
from problem2.evaluation.validator import ValidationError, validate_dynamic_episode


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")
SCENARIO = generate_dynamic_scenario(
    "validation", 20000, "g30x50_d4", (30, 50), CONFIG
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "evaluation_identity": "a" * 64,
        "canonical_training_identity": "b" * 64,
        "method": "sr_mappo_mobile",
        "candidate_id": "c01",
        "condition_id": "sr_mappo_mobile",
        "metric_source": "dynamic_ecology_environment",
        "partition": "validation",
        "scenario_id": 20000,
        "scale": "g30x50_d4",
        "training_seed": 51001,
        "source_commit": "c" * 40,
        "config_hash": "d" * 64,
        "protocol_hash": "e" * 64,
        "checkpoint_hash": "f" * 64,
        "evaluator_hash": "1" * 64,
        "scenario_panel_hash": "2" * 64,
        "candidate_manifest_sha256": "3" * 64,
        "budget_manifest_sha256": "4" * 64,
        "physical_scenario_contract_sha256": "5" * 64,
        "episode_index": 0,
        "interaction_count": 200000,
        "termination_reason": "horizon",
        "terminated": True,
        "initial_total_pest": float(SCENARIO.initial_prey.sum()),
        "final_total_pest": 9.0,
        "reduction_rate": 1.0 - 9.0 / float(SCENARIO.initial_prey.sum()),
        "success_at_0_85": False,
        "pesticide_initial_l": 1.0,
        "pesticide_remaining_l": 0.0,
        "pesticide_transferred_l": 1.0,
        "resource_conservation_residual_l": 0.0,
        "battery_replenishment_l": 0.0,
        "action_uav": 0,
        "action_vehicle_slot": 0,
        "rendezvous_distance_m": 0.0,
        "vehicle_service_travel_m": 0.0,
        "waiting_steps": 0.0,
        "completed_request_waiting_steps": 0.0,
        "pesticide_disabled_steps": 0.0,
        "return_steps": 0.0,
        "effective_spray_steps": 0.0,
        "decision_runtime_s": 0.0,
        "source_locator": "raw/episodes.jsonl:1",
        "initial_total_predator": float(SCENARIO.initial_predator.sum()),
        "final_total_predator": 2.5,
        "ecology_version": CONFIG.version,
        "ecology_config_sha256": CONFIG.contract_sha256,
        "ecology_scenario_sha256": SCENARIO.scenario_sha256,
        "ecology_source_commit": SCENARIO.source_commit,
        "ecology_implementation_version": SCENARIO.implementation_version,
        "cumulative_deposited_effect": 0.0,
        "terminal_mean_concentration": 0.0,
        "terminal_max_concentration": 0.0,
        "terminal_wind_direction": 0.4,
        "terminal_wind_strength": 0.25,
        "dynamic_step_count": 350,
    }
    row.update(overrides)
    assert set(row) == set(DYNAMIC_RAW_EPISODE_SCHEMA["required"])
    return row


def test_dynamic_validator_accepts_zero_prey_terminal_state() -> None:
    row = _row(final_total_pest=0.0, reduction_rate=1.0, success_at_0_85=True)
    validate_dynamic_episode(row)


def test_dynamic_validator_rejects_missing_metric_source() -> None:
    row = _row()
    row.pop("metric_source")
    with pytest.raises(ValidationError, match="metric_source"):
        validate_dynamic_episode(row)


@pytest.mark.parametrize("field", ["ecology_config_sha256", "ecology_scenario_sha256"])
def test_dynamic_validator_rejects_ecology_identity_drift(field: str) -> None:
    row = _row(**{field: "f" * 64})
    with pytest.raises(ValidationError, match="ecology|scenario"):
        validate_dynamic_episode(row)


def test_dynamic_validator_rejects_horizon_drift() -> None:
    with pytest.raises(ValidationError, match="dynamic_step_count"):
        validate_dynamic_episode(_row(dynamic_step_count=0))


def test_dynamic_validator_rejects_initial_ecology_total_drift() -> None:
    with pytest.raises(ValidationError, match="initial_total_pest"):
        validate_dynamic_episode(_row(initial_total_pest=10.0, reduction_rate=0.1))
    with pytest.raises(ValidationError, match="initial_total_predator"):
        validate_dynamic_episode(
            _row(initial_total_predator=float(SCENARIO.initial_predator.sum()) + 1.0)
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("terminal_mean_concentration", 1.1, "concentration"),
        ("terminal_max_concentration", 1.1, "concentration"),
        ("terminal_wind_strength", 0.6, "wind"),
    ],
)
def test_dynamic_validator_rejects_endpoint_values_outside_config(
    field: str, value: float, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_dynamic_episode(_row(**{field: value}))


def test_dynamic_validator_rejects_incomplete_full_row() -> None:
    row = _row()
    row.pop("method")
    with pytest.raises(ValidationError, match="required"):
        validate_dynamic_episode(row)
