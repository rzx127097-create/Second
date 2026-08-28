from pathlib import Path

import pytest

from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.evaluation.validator import ValidationError, validate_dynamic_episode


ROOT = Path(__file__).resolve().parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")
SCENARIO = generate_dynamic_scenario(
    "validation", 20000, "g30x50_d4", (30, 50), CONFIG
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "metric_source": "dynamic_ecology_environment",
        "partition": "validation",
        "scenario_id": 20000,
        "scale": "g30x50_d4",
        "initial_total_pest": 10.0,
        "final_total_pest": 9.0,
        "reduction_rate": 0.1,
        "success_at_0_85": False,
        "initial_total_predator": 3.0,
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
