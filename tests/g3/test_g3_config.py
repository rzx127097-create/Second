from __future__ import annotations

from pathlib import Path
import hashlib
from types import MappingProxyType

import pytest
import yaml

from problem2.config import G3ConfigError, load_g3_config, load_g3_payload


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g3_heterogeneous_marl.yaml"
REGISTRY_PATH = ROOT / "docs" / "evidence" / "g3" / "g3_contract.yaml"
LOCK_PATH = ROOT / "requirements-g3.lock"


def _payload() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        yaml.safe_dump(
            payload,
            sort_keys=True,
            allow_unicode=False,
            default_flow_style=False,
        ).encode("utf-8")
    ).hexdigest()


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

    assert isinstance(config.stability_components, MappingProxyType)
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
    with pytest.raises(TypeError):
        config.stability_components["value_clipping"] = False
    assert config.training_partition == "development"
    assert config.gamma == pytest.approx(0.99)
    assert config.gae_lambda == pytest.approx(0.95)
    assert config.value_clip_eps == pytest.approx(0.2)
    assert config.learning_rate == pytest.approx(0.0003)
    assert config.entropy_coef == pytest.approx(0.01)
    assert config.value_loss_coef == pytest.approx(0.5)
    assert config.max_grad_norm == pytest.approx(0.5)
    assert config.ppo_epochs == 2
    assert config.rollout_horizon == 32
    assert config.total_updates == 1000
    assert config.minibatch_size == 64


def test_g3_config_records_canonical_identity_and_dependency() -> None:
    config = load_g3_config(CONFIG_PATH)
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    assert len(config.config_hash) == 64
    assert config.config_hash == config.canonical_yaml_sha256
    assert config.config_hash == _canonical_hash(_payload())
    assert config.config_hash == registry["configuration"]["canonical_yaml_sha256"]
    assert config.pytorch_dependency == "torch==2.13.0+cpu"
    assert config.pytorch_index_url == "https://download.pytorch.org/whl/cpu"
    assert config.pytorch_version == "2.13.0+cpu"
    assert config.algorithm_name == "SR-MAPPO"
    assert config.replenished_resource == "pesticide"
    assert config.battery_replenishment_enabled is False


def test_g3_lock_file_declares_installable_cpu_torch_index() -> None:
    content = LOCK_PATH.read_text(encoding="utf-8")

    assert "--index-url https://pypi.org/simple" in content
    assert "--extra-index-url https://download.pytorch.org/whl/cpu" in content
    assert "torch==2.13.0+cpu" in content


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
        (("gamma",), 0.98),
        (("total_updates",), 999),
        (("learning_rate",), 0.0002),
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


@pytest.mark.parametrize(
    ("path", "key", "value"),
    [
        ((), "sealed_test_accessed", True),
        ((), "resource_replenishment", "battery"),
        (("resources",), "battery_replenishment", True),
        (("stability_components",), "undocumented_flag", True),
    ],
)
def test_g3_config_rejects_unknown_or_alias_fields(
    path: tuple[str, ...], key: str, value: object
) -> None:
    payload = _payload()
    target = payload
    for item in path:
        target = target[item]
    target[key] = value

    with pytest.raises(G3ConfigError):
        load_g3_payload(payload)


def test_g3_config_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        CONFIG_PATH.read_text(encoding="utf-8") + "\ngamma: 0.98\n",
        encoding="utf-8",
    )

    with pytest.raises(G3ConfigError, match="duplicate"):
        load_g3_config(duplicate)
