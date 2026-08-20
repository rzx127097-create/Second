from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any

import yaml


class G2ConfigError(ValueError):
    """Raised when the frozen G2 configuration is invalid."""


class G3ConfigError(ValueError):
    """Raised when the frozen G3 configuration is invalid."""


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


@dataclass(frozen=True)
class G3Config:
    """Validated, development-only contract for heterogeneous SR-MAPPO."""

    source_path: Path | None
    algorithm_name: str
    problem_description: str
    uav_count: int
    uav_obs_dim: int
    vehicle_obs_dim: int
    critic_state_dim: int
    uav_action_dim: int
    vehicle_action_dim: int
    uav_actions: tuple[str, ...]
    vehicle_actions: tuple[str, ...]
    max_candidate_slots: int
    gamma: float
    gae_lambda: float
    ppo_epochs: int
    rollout_horizon: int
    total_updates: int
    learning_rate: float
    value_clip_eps: float
    value_loss_coef: float
    entropy_coef: float
    max_grad_norm: float
    minibatch_size: int
    stability_components: dict[str, bool]
    training_partition: str
    replenished_resource: str
    battery_replenishment_enabled: bool
    pytorch_dependency: str
    pytorch_dependency_floor: str
    pytorch_version: str
    python_version: str
    config_hash: str
    canonical_yaml_sha256: str

    @property
    def k_max(self) -> int:
        return self.max_candidate_slots

    @property
    def K_max(self) -> int:  # noqa: N802 - mirrors the frozen contract name
        return self.max_candidate_slots

    @property
    def torch_dependency(self) -> str:
        return self.pytorch_dependency

    @property
    def torch_version(self) -> str:
        return self.pytorch_version


_FROZEN_SCALES = (
    ("g20x20_d2", (20, 20), 150),
    ("g20x30_d3", (20, 30), 180),
    ("g20x40_d3", (20, 40), 220),
    ("g30x30_d3", (30, 30), 220),
    ("g30x40_d4", (30, 40), 280),
    ("g30x50_d4", (30, 50), 350),
)

_FROZEN_GIS_AUDIT = {
    "source_crs": "EPSG:4326",
    "target_crs": "EPSG:32643",
    "center_lonlat": (73.0351433, 26.2967719),
    "extent_m": (500.0, 300.0),
    "topology": "four_connected_undirected",
    "preprocess_version": "g2-road-v1",
    "audit_seed": 42,
}


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

    source_crs = _text(source.get("crs"), "source.crs")
    target_crs = _text(projection.get("target_crs"), "projection.target_crs")
    topology = _text(road.get("topology"), "road.topology")
    preprocess_version = _text(
        road.get("preprocess_version"), "road.preprocess_version"
    )
    audit_seed = _integer(audit.get("seed"), "audit.seed")
    observed_contract = {
        "source_crs": source_crs,
        "target_crs": target_crs,
        "center_lonlat": center,
        "extent_m": extent,
        "topology": topology,
        "preprocess_version": preprocess_version,
        "audit_seed": audit_seed,
    }
    if observed_contract != _FROZEN_GIS_AUDIT:
        raise G2ConfigError(
            "configuration must preserve the frozen G2 GIS and audit contract"
        )

    request_margin_s = _number(
        service.get("request_margin_s"), "request_margin_s"
    )
    if request_margin_s < 0.0:
        raise G2ConfigError("request_margin_s must be nonnegative")

    return G2Config(
        source_path=Path(_text(source.get("path"), "source.path")),
        source_sha256=source_hash,
        source_crs=source_crs,
        target_crs=target_crs,
        center_lonlat=center,
        extent_m=extent,
        topology=topology,
        max_segment_m=_number(
            road.get("max_segment_m"), "road.max_segment_m", positive=True
        ),
        preprocess_version=preprocess_version,
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
        request_margin_s=request_margin_s,
        rendezvous_radius_m=_number(
            service.get("rendezvous_radius_m"),
            "rendezvous_radius_m",
            positive=True,
        ),
        audit_seed=audit_seed,
        tolerance=_number(audit.get("tolerance"), "audit.tolerance", positive=True),
        output_root=output_root,
    )


_G3_STABILITY_FLAGS = (
    "observation_normalization",
    "return_normalization",
    "orthogonal_initialization",
    "layer_normalization",
    "value_clipping",
    "huber_value_loss",
    "learning_rate_decay",
)
_G3_UAV_ACTIONS = ("up", "down", "left", "right", "stay", "spray")
_G3_VEHICLE_ACTIONS = ("hold", "slot-0", "slot-1", "slot-2", "slot-3")


def _g3_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise G3ConfigError(f"{name} must be a mapping")
    return value


def _g3_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise G3ConfigError(f"{name} must be non-empty text")
    return value.strip()


def _g3_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise G3ConfigError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise G3ConfigError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise G3ConfigError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise G3ConfigError(f"{name} must be positive")
    return result


def _g3_integer(value: Any, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise G3ConfigError(f"{name} must be an integer")
    if positive and value <= 0:
        raise G3ConfigError(f"{name} must be positive")
    return value


def _reject_nonfinite_g3_values(value: Any, path: str = "configuration") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        try:
            finite = math.isfinite(float(value))
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            raise G3ConfigError(f"{path} must contain only finite numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nonfinite_g3_values(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite_g3_values(item, f"{path}.{key}")


def _g3_actions(value: Any, name: str, expected: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise G3ConfigError(f"{name} must be a list")
    actions = tuple(_g3_text(item, f"{name}[{index}]") for index, item in enumerate(value))
    if actions != expected:
        raise G3ConfigError(f"{name} must preserve the frozen action order")
    return actions


def _canonical_g3_yaml_bytes(payload: dict[str, Any]) -> bytes:
    try:
        canonical = yaml.safe_dump(
            payload,
            sort_keys=True,
            allow_unicode=False,
            default_flow_style=False,
        )
    except yaml.YAMLError as exc:
        raise G3ConfigError(f"configuration cannot be canonicalized: {exc}") from exc
    return canonical.encode("utf-8")


def load_g3_config(path: Path | str) -> G3Config:
    """Load and validate a development-only G3 YAML configuration."""

    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise G3ConfigError(f"cannot load G3 configuration: {exc}") from exc
    return load_g3_payload(payload, source_path=config_path)


def load_g3_payload(
    payload: Any, *, source_path: Path | str | None = None
) -> G3Config:
    """Validate an already parsed G3 payload and calculate its identity."""

    root = _g3_mapping(payload, "configuration")
    _reject_nonfinite_g3_values(root)

    if root.get("schema_version") != "g3.v1":
        raise G3ConfigError("schema_version must be g3.v1")
    if root.get("algorithm_name") != "SR-MAPPO":
        raise G3ConfigError("the public algorithm name must remain SR-MAPPO")
    if root.get("problem_description") != "air_ground_heterogeneous_extension":
        raise G3ConfigError(
            "problem_description must be the air-ground heterogeneous extension"
        )

    dimensions = {
        "uav_count": (2, True),
        "uav_obs_dim": (179, True),
        "vehicle_obs_dim": (28, True),
        "critic_state_dim": (185, True),
        "uav_action_dim": (6, True),
        "vehicle_action_dim": (5, True),
        "max_candidate_slots": (4, True),
    }
    observed_dimensions: dict[str, int] = {}
    for name, (expected, positive) in dimensions.items():
        observed = _g3_integer(root.get(name), name, positive=positive)
        if observed != expected:
            raise G3ConfigError(f"{name} must remain frozen at {expected}")
        observed_dimensions[name] = observed

    uav_actions = _g3_actions(root.get("uav_actions"), "uav_actions", _G3_UAV_ACTIONS)
    vehicle_actions = _g3_actions(
        root.get("vehicle_actions"), "vehicle_actions", _G3_VEHICLE_ACTIONS
    )
    if observed_dimensions["uav_action_dim"] != len(uav_actions):
        raise G3ConfigError("uav_action_dim must match uav_actions")
    if observed_dimensions["vehicle_action_dim"] != len(vehicle_actions):
        raise G3ConfigError("vehicle_action_dim must match vehicle_actions")

    stability = _g3_mapping(
        root.get("stability_components"), "stability_components"
    )
    if set(stability) != set(_G3_STABILITY_FLAGS):
        raise G3ConfigError("stability_components must define all seven G3 flags")
    stability_components: dict[str, bool] = {}
    for flag in _G3_STABILITY_FLAGS:
        value = stability[flag]
        if value is not True:
            raise G3ConfigError(f"{flag} must be enabled for the G3 contract")
        stability_components[flag] = value

    training_partition = _g3_text(
        root.get("training_partition"), "training_partition"
    )
    if training_partition != "development":
        raise G3ConfigError(
            "training_partition must remain development; validation and sealed_test "
            "are not training partitions"
        )

    resources = _g3_mapping(root.get("resources"), "resources")
    replenished_resource = _g3_text(
        resources.get("replenished_resource"), "resources.replenished_resource"
    )
    if replenished_resource != "pesticide":
        raise G3ConfigError("the replenished resource must be pesticide")
    battery_replenishment_enabled = resources.get("battery_replenishment_enabled")
    if battery_replenishment_enabled is not False:
        raise G3ConfigError("battery replenishment must remain disabled")

    scalar_hyperparameters = {
        "gamma": _g3_number(root.get("gamma"), "gamma"),
        "gae_lambda": _g3_number(root.get("gae_lambda"), "gae_lambda"),
        "learning_rate": _g3_number(
            root.get("learning_rate"), "learning_rate", positive=True
        ),
        "value_clip_eps": _g3_number(
            root.get("value_clip_eps"), "value_clip_eps", positive=True
        ),
        "value_loss_coef": _g3_number(
            root.get("value_loss_coef"), "value_loss_coef", positive=True
        ),
        "entropy_coef": _g3_number(
            root.get("entropy_coef"), "entropy_coef", positive=True
        ),
        "max_grad_norm": _g3_number(
            root.get("max_grad_norm"), "max_grad_norm", positive=True
        ),
    }
    if not 0.0 < scalar_hyperparameters["gamma"] <= 1.0:
        raise G3ConfigError("gamma must be in (0, 1]")
    if not 0.0 < scalar_hyperparameters["gae_lambda"] <= 1.0:
        raise G3ConfigError("gae_lambda must be in (0, 1]")
    integer_hyperparameters = {
        "ppo_epochs": _g3_integer(root.get("ppo_epochs"), "ppo_epochs", positive=True),
        "rollout_horizon": _g3_integer(
            root.get("rollout_horizon"), "rollout_horizon", positive=True
        ),
        "total_updates": _g3_integer(
            root.get("total_updates"), "total_updates", positive=True
        ),
        "minibatch_size": _g3_integer(
            root.get("minibatch_size"), "minibatch_size", positive=True
        ),
    }

    pytorch_dependency = _g3_text(
        root.get("pytorch_dependency"), "pytorch_dependency"
    )
    pytorch_dependency_floor = _g3_text(
        root.get("pytorch_dependency_floor"), "pytorch_dependency_floor"
    )
    pytorch_version = _g3_text(root.get("pytorch_version"), "pytorch_version")
    python_version = _g3_text(root.get("python_version"), "python_version")
    if pytorch_dependency != "torch>=2.13,<2.14":
        raise G3ConfigError("pytorch_dependency must preserve the G3 dependency floor")
    if pytorch_dependency_floor != "2.13":
        raise G3ConfigError("pytorch_dependency_floor must be 2.13")
    if pytorch_version != "2.13.0+cpu":
        raise G3ConfigError("pytorch_version must be 2.13.0+cpu")
    if python_version != "3.11.15":
        raise G3ConfigError("python_version must be 3.11.15")

    canonical_hash = hashlib.sha256(_canonical_g3_yaml_bytes(root)).hexdigest()
    return G3Config(
        source_path=Path(source_path) if source_path is not None else None,
        algorithm_name="SR-MAPPO",
        problem_description="air_ground_heterogeneous_extension",
        **observed_dimensions,
        uav_actions=uav_actions,
        vehicle_actions=vehicle_actions,
        **scalar_hyperparameters,
        **integer_hyperparameters,
        stability_components=stability_components,
        training_partition=training_partition,
        replenished_resource=replenished_resource,
        battery_replenishment_enabled=False,
        pytorch_dependency=pytorch_dependency,
        pytorch_dependency_floor=pytorch_dependency_floor,
        pytorch_version=pytorch_version,
        python_version=python_version,
        config_hash=canonical_hash,
        canonical_yaml_sha256=canonical_hash,
    )
