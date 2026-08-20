from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from problem2.config import G2ConfigError, load_g2_config
from problem2.domain import Action, UavState, VehicleMode, VehicleState


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g2_deterministic.yaml"


def _write_config(tmp_path: Path, mutate) -> Path:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "g2.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_loads_frozen_six_scale_metric_contract() -> None:
    config = load_g2_config(CONFIG_PATH)

    assert config.source_crs == "EPSG:4326"
    assert config.target_crs == "EPSG:32643"
    assert config.center_lonlat == (73.0351433, 26.2967719)
    assert config.extent_m == (500.0, 300.0)
    assert [
        (scale.scale_id, scale.grid_shape, scale.max_steps)
        for scale in config.scales
    ] == [
        ("g20x20_d2", (20, 20), 150),
        ("g20x30_d3", (20, 30), 180),
        ("g20x40_d3", (20, 40), 220),
        ("g30x30_d3", (30, 30), 220),
        ("g30x40_d4", (30, 40), 280),
        ("g30x50_d4", (30, 50), 350),
    ]
    assert config.usable_capacity_l == pytest.approx(1.08)
    assert config.spray_per_step_l == pytest.approx(0.02)
    assert config.output_root.as_posix() == "outputs/problem2_sr_mappo_v1/g2"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["physics"].__setitem__(
                "vehicle_speed_mps", float("nan")
            ),
            "finite",
        ),
        (
            lambda payload: payload["resources"].__setitem__(
                "battery_replenishment_enabled", True
            ),
            "battery replenishment",
        ),
        (
            lambda payload: payload["service"].__setitem__(
                "transfer_rate_lpm", 0.0
            ),
            "positive",
        ),
    ],
)
def test_rejects_invalid_physical_contract(
    tmp_path: Path, mutation, message: str
) -> None:
    path = _write_config(tmp_path, mutation)

    with pytest.raises(G2ConfigError, match=message):
        load_g2_config(path)


def test_rejects_scale_set_drift(tmp_path: Path) -> None:
    path = _write_config(tmp_path, lambda payload: payload["scales"].pop())

    with pytest.raises(G2ConfigError, match="six frozen scales"):
        load_g2_config(path)


def test_domain_states_reject_negative_or_nonfinite_resources() -> None:
    with pytest.raises(ValueError, match="pesticide_l"):
        UavState("u0", x_m=1.0, y_m=2.0, pesticide_l=-0.1)

    with pytest.raises(ValueError, match="inventory_l"):
        VehicleState(
            vehicle_id="v0",
            current_node=0,
            x_m=1.0,
            y_m=2.0,
            inventory_l=float("inf"),
        )


def test_domain_enums_and_frozen_states_define_action_contract() -> None:
    assert [int(action) for action in Action] == [0, 1, 2, 3, 4, 5]
    assert [action.name for action in Action] == [
        "STAY",
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
        "SPRAY",
    ]
    state = VehicleState(
        vehicle_id="v0",
        current_node=0,
        x_m=1.0,
        y_m=2.0,
        inventory_l=20.0,
    )
    assert state.mode is VehicleMode.IDLE
    assert replace(state, mode=VehicleMode.TRANSIT).mode is VehicleMode.TRANSIT
