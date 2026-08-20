from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from problem2.config import G3ConfigError, load_g3_config, load_g3_payload


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g3_heterogeneous_marl.yaml"


def _payload() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_g3_config_freezes_dimensions_and_roles() -> None:
    config = load_g3_config(CONFIG_PATH)

    assert config.uav_count == 2
    assert config.uav_obs_dim == 179
    assert config.vehicle_obs_dim == 28
    assert config.critic_state_dim == 185
    assert config.uav_action_dim == 6
    assert config.vehicle_action_dim == 5
    assert config.max_candidate_slots == 4
    assert config.uav_actions == (
        "up",
        "down",
        "left",
        "right",
        "stay",
        "spray",
    )
    assert config.vehicle_actions == (
        "hold",
        "slot-0",
        "slot-1",
        "slot-2",
        "slot-3",
    )


def test_g3_config_freezes_stability_and_training_contract() -> None:
    config = load_g3_config(CONFIG_PATH)

    assert set(config.stability_components) == {
        "observation_normalization",
        "return_normalization",
        "orthogonal_initialization",
        "layer_normalization",
        "value_clipping",
        "huber_value_loss",
        "learning_rate_decay",
    }
    assert all(config.stability_components.values())
    assert config.training_partition == "development"
    for value in (
        config.gamma,
        config.gae_lambda,
        config.value_clip_eps,
        config.learning_rate,
        config.entropy_coef,
        config.value_loss_coef,
    ):
        assert value == pytest.approx(value)
        assert value != float("inf")
        assert value != float("-inf")
    assert config.ppo_epochs > 0
    assert config.rollout_horizon > 0
    assert config.total_updates > 0


def test_g3_config_records_canonical_identity_and_dependency() -> None:
    config = load_g3_config(CONFIG_PATH)

    assert len(config.config_hash) == 64
    assert config.config_hash == config.canonical_yaml_sha256
    assert config.pytorch_dependency == "torch>=2.13,<2.14"
    assert config.pytorch_version == "2.13.0+cpu"
    assert config.algorithm_name == "SR-MAPPO"
    assert config.replenished_resource == "pesticide"
    assert config.battery_replenishment_enabled is False


@pytest.mark.parametrize("partition", ["validation", "sealed_test"])
def test_g3_config_rejects_non_development_training_partition(
    partition: str,
) -> None:
    payload = _payload()
    payload["training_partition"] = partition

    with pytest.raises(G3ConfigError, match="development"):
        load_g3_payload(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("gamma",), float("nan")),
        (("uav_obs_dim",), 178),
        (("stability_components", "value_clipping"), False),
        (("resources", "battery_replenishment_enabled"), True),
        (("resources", "replenished_resource"), "battery"),
    ],
)
def test_g3_config_rejects_contract_drift(
    path: tuple[str, ...], value: object
) -> None:
    payload = _payload()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(G3ConfigError):
        load_g3_payload(payload)
