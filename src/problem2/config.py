from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import yaml


class G2ConfigError(ValueError):
    """Raised when the frozen G2 configuration is invalid."""


@dataclass(frozen=True)
class ScaleConfig:
    scale_id: str
    grid_shape: tuple[int, int]
    max_steps: int


@dataclass(frozen=True)
class G2Config:
    source_path: Path
    source_sha256: str
    source_crs: str
    target_crs: str
    center_lonlat: tuple[float, float]
    extent_m: tuple[float, float]
    topology: str
    max_segment_m: float
    preprocess_version: str
    scales: tuple[ScaleConfig, ...]
    dt_s: float
    uav_speed_mps: float
    vehicle_speed_mps: float
    usable_capacity_l: float
    spray_flow_lpm: float
    vehicle_inventory_l: float
    transfer_rate_lpm: float
    setup_time_s: float
    service_cap_l: float
    request_margin_s: float
    rendezvous_radius_m: float
    audit_seed: int
    tolerance: float
    output_root: Path

    @property
    def spray_per_step_l(self) -> float:
        return self.spray_flow_lpm * self.dt_s / 60.0


_FROZEN_SCALES = (
    ("g20x20_d2", (20, 20), 150),
    ("g20x30_d3", (20, 30), 180),
    ("g20x40_d3", (20, 40), 220),
    ("g30x30_d3", (30, 30), 220),
    ("g30x40_d4", (30, 40), 280),
    ("g30x50_d4", (30, 50), 350),
)


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise G2ConfigError(f"{name} must be a mapping")
    return value


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise G2ConfigError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise G2ConfigError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise G2ConfigError(f"{name} must be positive")
    return result


def _integer(value: Any, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise G2ConfigError(f"{name} must be an integer")
    if positive and value <= 0:
        raise G2ConfigError(f"{name} must be positive")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise G2ConfigError(f"{name} must be non-empty text")
    return value.strip()


def load_g2_config(path: Path | str) -> G2Config:
    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise G2ConfigError(f"cannot load G2 configuration: {exc}") from exc
    root = _mapping(payload, "configuration")
    if root.get("schema_version") != "g2.v1":
        raise G2ConfigError("schema_version must be g2.v1")

    source = _mapping(root.get("source"), "source")
    projection = _mapping(root.get("projection"), "projection")
    road = _mapping(root.get("road"), "road")
    physics = _mapping(root.get("physics"), "physics")
    resources = _mapping(root.get("resources"), "resources")
    service = _mapping(root.get("service"), "service")
    audit = _mapping(root.get("audit"), "audit")

    if resources.get("replenished_resource") != "pesticide":
        raise G2ConfigError("the replenished resource must be pesticide")
    if resources.get("battery_replenishment_enabled") is not False:
        raise G2ConfigError("battery replenishment must remain disabled")

    center_raw = projection.get("center_lonlat")
    extent_raw = projection.get("extent_m")
    if not isinstance(center_raw, list) or len(center_raw) != 2:
        raise G2ConfigError("center_lonlat must contain longitude and latitude")
    if not isinstance(extent_raw, list) or len(extent_raw) != 2:
        raise G2ConfigError("extent_m must contain width and height")
    center = (
        _number(center_raw[0], "center longitude"),
        _number(center_raw[1], "center latitude"),
    )
    extent = (
        _number(extent_raw[0], "extent width", positive=True),
        _number(extent_raw[1], "extent height", positive=True),
    )

    scales_raw = root.get("scales")
    if not isinstance(scales_raw, list):
        raise G2ConfigError("scales must be a list")
    scales: list[ScaleConfig] = []
    for index, item in enumerate(scales_raw):
        scale = _mapping(item, f"scales[{index}]")
        scales.append(
            ScaleConfig(
                scale_id=_text(scale.get("id"), f"scales[{index}].id"),
                grid_shape=(
                    _integer(scale.get("height"), "scale height", positive=True),
                    _integer(scale.get("width"), "scale width", positive=True),
                ),
                max_steps=_integer(
                    scale.get("max_steps"), "scale max_steps", positive=True
                ),
            )
        )
    observed_scales = tuple(
        (scale.scale_id, scale.grid_shape, scale.max_steps) for scale in scales
    )
    if observed_scales != _FROZEN_SCALES:
        raise G2ConfigError("configuration must define the six frozen scales")

    dt_s = _number(physics.get("dt_s"), "dt_s", positive=True)
    nominal_capacity = _number(
        resources.get("uav_nominal_capacity_l"),
        "uav_nominal_capacity_l",
        positive=True,
    )
    usable_fraction = _number(
        resources.get("uav_usable_fraction"), "uav_usable_fraction", positive=True
    )
    if usable_fraction > 1.0:
        raise G2ConfigError("uav_usable_fraction must not exceed 1")

    output_root = Path(_text(audit.get("output_root"), "audit.output_root"))
    if output_root.as_posix() != "outputs/problem2_sr_mappo_v1/g2":
        raise G2ConfigError("audit.output_root must be the frozen G2 output root")

    source_hash = _text(source.get("sha256"), "source.sha256").upper()
    if len(source_hash) != 64 or any(c not in "0123456789ABCDEF" for c in source_hash):
        raise G2ConfigError("source.sha256 must be a 64-character hexadecimal hash")

    return G2Config(
        source_path=Path(_text(source.get("path"), "source.path")),
        source_sha256=source_hash,
        source_crs=_text(source.get("crs"), "source.crs"),
        target_crs=_text(projection.get("target_crs"), "projection.target_crs"),
        center_lonlat=center,
        extent_m=extent,
        topology=_text(road.get("topology"), "road.topology"),
        max_segment_m=_number(
            road.get("max_segment_m"), "road.max_segment_m", positive=True
        ),
        preprocess_version=_text(
            road.get("preprocess_version"), "road.preprocess_version"
        ),
        scales=tuple(scales),
        dt_s=dt_s,
        uav_speed_mps=_number(
            physics.get("uav_speed_mps"), "uav_speed_mps", positive=True
        ),
        vehicle_speed_mps=_number(
            physics.get("vehicle_speed_mps"), "vehicle_speed_mps", positive=True
        ),
        usable_capacity_l=nominal_capacity * usable_fraction,
        spray_flow_lpm=_number(
            resources.get("spray_flow_lpm"), "spray_flow_lpm", positive=True
        ),
        vehicle_inventory_l=_number(
            resources.get("vehicle_inventory_l"),
            "vehicle_inventory_l",
            positive=True,
        ),
        transfer_rate_lpm=_number(
            service.get("transfer_rate_lpm"), "transfer_rate_lpm", positive=True
        ),
        setup_time_s=_number(
            service.get("setup_time_s"), "setup_time_s", positive=True
        ),
        service_cap_l=_number(
            service.get("service_cap_l"), "service_cap_l", positive=True
        ),
        request_margin_s=_number(
            service.get("request_margin_s"), "request_margin_s"
        ),
        rendezvous_radius_m=_number(
            service.get("rendezvous_radius_m"),
            "rendezvous_radius_m",
            positive=True,
        ),
        audit_seed=_integer(audit.get("seed"), "audit.seed"),
        tolerance=_number(audit.get("tolerance"), "audit.tolerance", positive=True),
        output_root=output_root,
    )
