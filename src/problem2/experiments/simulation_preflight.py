"""Technical preflight for controlled-simulation execution.

The preflight validates reproducibility and model invariants.  Missing field
calibration is deliberately reported as a warning because this project now
uses explicit controlled-simulation assumptions rather than claiming field
validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.job_identity import capture_git_provenance
from problem2.road.graphml import load_graphml


ENGINEERING_PARAMETERS = (
    "uav_onboard_pesticide",
    "uav_spray_flow",
    "uav_usable_fraction",
    "uav_speed",
    "vehicle_inventory",
    "vehicle_transfer_rate",
    "vehicle_service_capacity",
    "service_setup_time",
    "request_safety_margin",
    "rendezvous_radius",
    "vehicle_speed",
    "decision_dt",
)
FIELD_PARAMETERS = (
    "pest_growth_rate_s",
    "pest_carrying_capacity",
    "pest_diffusion_rate_m2_s",
    "wind_vx_m_s",
    "wind_vy_m_s",
    "pesticide_decay_rate_s",
    "pesticide_diffusion_rate_m2_s",
    "pesticide_efficacy_per_l",
    "pest_mortality_per_exposure",
)
CLAIM_BOUNDARY = (
    "Results are produced in a controlled simulation and do not constitute "
    "field validation or measured deployment effectiveness."
)


@dataclass(frozen=True)
class SimulationIssue:
    level: str
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True)
class SimulationProfile:
    document: dict[str, Any]
    path: Path
    sha256: str


@dataclass(frozen=True)
class SimulationPreflightReport:
    ready: bool
    evidence_mode: str
    errors: tuple[SimulationIssue, ...]
    warnings: tuple[SimulationIssue, ...]
    derived_regimes: dict[str, Any]
    profile_sha256: str
    claim_boundary: str = CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "evidence_mode": self.evidence_mode,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "derived_regimes": self.derived_regimes,
            "profile_sha256": self.profile_sha256,
            "claim_boundary": self.claim_boundary,
        }


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_simulation_profile(config_dir: str | Path) -> SimulationProfile:
    path = Path(config_dir).resolve() / "simulation_profile.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"simulation profile does not exist: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("simulation profile root must be a mapping")
    return SimulationProfile(document, path, _sha256(path))


def _runtime_documents(config: Any) -> dict[str, Mapping[str, Any]]:
    return {
        "parameter_registry": config.parameters,
        "field_dynamics": config.field_dynamics,
        "scales": config.scales,
        "environment": config.environment,
        "algorithm": config.algorithm,
        "experiments": config.experiments,
    }


def _runtime_value(documents: Mapping[str, Mapping[str, Any]], path: str) -> Any:
    current: Any = documents
    for part in str(path).split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def _issue(level: str, code: str, path: str, message: str) -> SimulationIssue:
    return SimulationIssue(level, code, path, message)


def _check_profile_record(
    record: object,
    *,
    path: str,
    runtime_record: object,
    errors: list[SimulationIssue],
    warnings: list[SimulationIssue],
) -> None:
    if not isinstance(record, Mapping):
        errors.append(_issue("error", "invalid_profile_record", path, "profile parameter record must be a mapping"))
        return
    if not isinstance(runtime_record, Mapping):
        errors.append(_issue("error", "invalid_runtime_record", path, "runtime parameter record must be a mapping"))
        return
    for key in ("runtime_path", "unit", "conversion", "assumption_rationale", "selection_rule"):
        if not str(record.get(key, "")).strip():
            errors.append(_issue("error", f"missing_{key}", f"{path}.{key}", f"{key} is required"))
    for key in ("value", "min", "max"):
        if not _finite(record.get(key)):
            errors.append(_issue("error", "invalid_profile_number", f"{path}.{key}", "value must be finite numeric"))
    if _finite(record.get("min")) and _finite(record.get("max")):
        if float(record["min"]) > float(record["max"]):
            errors.append(_issue("error", "invalid_profile_range", path, "min must not exceed max"))
        if _finite(record.get("value")) and not float(record["min"]) <= float(record["value"]) <= float(record["max"]):
            errors.append(_issue("error", "profile_value_out_of_range", path, "profile value lies outside its range"))
    if str(record.get("unit")) != str(runtime_record.get("unit")):
        errors.append(_issue("error", "profile_runtime_unit_mismatch", path, "profile and runtime units differ"))
    profile_source_type = str(record.get("source_type", "")).strip()
    runtime_source_type = str(runtime_record.get("source_type", "")).strip()
    runtime_source_id = str(
        runtime_record.get("simulation_source_id")
        if runtime_source_type == "assumption"
        and runtime_record.get("simulation_source_id")
        else runtime_record.get("source_id", "")
    ).strip()
    if (
        profile_source_type != runtime_source_type
        or str(record.get("source_id", "")).strip() != runtime_source_id
    ):
        errors.append(_issue(
            "error",
            "profile_runtime_source_mismatch",
            path,
            "profile and runtime source metadata differ",
        ))
    if _finite(record.get("value")) and _finite(runtime_record.get("value")):
        if not math.isclose(float(record["value"]), float(runtime_record["value"]), rel_tol=1e-12, abs_tol=1e-12):
            errors.append(_issue("error", "profile_runtime_mismatch", path, "profile and runtime values differ"))
    sensitivity_required = record.get("sensitivity_required")
    if not isinstance(sensitivity_required, bool):
        errors.append(_issue("error", "missing_sensitivity_policy", f"{path}.sensitivity_required", "sensitivity_required must be boolean"))
    elif sensitivity_required:
        levels = record.get("sensitivity_levels")
        if not isinstance(levels, list) or len(levels) < 2 or not all(_finite(value) for value in levels):
            errors.append(_issue("error", "invalid_sensitivity_levels", f"{path}.sensitivity_levels", "at least two finite sensitivity levels are required"))
    elif not str(record.get("sensitivity_exclusion_rationale", "")).strip():
        errors.append(_issue("error", "missing_sensitivity_exclusion", path, "an exclusion rationale is required when sensitivity is false"))
    if profile_source_type == "assumption":
        warnings.append(_issue("warning", "assumption_source", path, "parameter is an explicit controlled-simulation assumption"))


def _validate_resource_report(
    path: Path,
    *,
    expected_identity: Mapping[str, str],
    errors: list[SimulationIssue],
    warnings: list[SimulationIssue],
) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(_issue("error", "invalid_resource_report", str(path), f"resource report is unreadable: {exc}"))
        return
    if not isinstance(payload, Mapping) or not isinstance(payload.get("activated"), bool):
        errors.append(_issue("error", "invalid_resource_report", str(path), "resource report requires boolean activated"))
        return
    if payload["activated"] is False:
        warnings.append(_issue("warning", "resource_mechanism_inactive", str(path), "resource pilot did not activate the replenishment mechanism"))
        return
    means = payload.get("condition_means")
    required = {"finite_no_support", "matched_fixed", "sr_mappo_mobile", "teleport_diagnostic"}
    if not isinstance(means, Mapping) or not required.issubset({str(key) for key in means}):
        errors.append(_issue("error", "invalid_resource_report", str(path), "activated resource report lacks required conditions"))
        return
    for condition in required:
        metrics = means[condition]
        if not isinstance(metrics, Mapping) or not all(_finite(metrics.get(key)) for key in ("request_count", "requested_l", "transferred_l", "pesticide_disabled_s")):
            errors.append(_issue("error", "invalid_resource_report", f"{path}:{condition}", "resource condition lacks finite event metrics"))
            return
    identity_keys = tuple(expected_identity)
    missing = [key for key in identity_keys if not isinstance(payload.get(key), str) or not str(payload[key]).strip()]
    if missing:
        warnings.append(
            _issue(
                "warning",
                "resource_report_identity_missing",
                str(path),
                "activated resource evidence lacks current config/profile/source identity and is not current mechanism evidence",
            )
        )
        return
    mismatches = [key for key in identity_keys if str(payload[key]) != str(expected_identity[key])]
    if mismatches:
        errors.append(
            _issue(
                "error",
                "resource_report_identity_mismatch",
                str(path),
                f"resource evidence identity differs for: {', '.join(mismatches)}",
            )
        )


def _audit_road(config_dir: Path, config: Any, errors: list[SimulationIssue]) -> None:
    road = config.environment.get("road", {})
    if not isinstance(road, Mapping) or road.get("source") != "frozen_gis" or road.get("vehicle_must_stay_on_graph") is not True:
        errors.append(_issue("error", "invalid_road_contract", "environment.road", "simulation requires frozen GIS and graph-constrained vehicle motion"))
        return
    graph_path = Path(str(road.get("graphml_path", "")))
    if not graph_path.is_absolute():
        graph_path = config_dir.resolve().parent / graph_path
    if not graph_path.is_file() or _sha256(graph_path) != str(road.get("source_sha256", "")):
        errors.append(_issue("error", "road_hash_mismatch", "environment.road.graphml_path", "road source is missing or its SHA-256 differs from the frozen value"))
    metadata_path = Path(str(road.get("cache_metadata_path", "")))
    if not metadata_path.is_absolute():
        metadata_path = config_dir.resolve().parent / metadata_path
    if not metadata_path.is_file() or _sha256(metadata_path) != str(road.get("source_metadata_sha256", "")):
        errors.append(_issue("error", "road_metadata_hash_mismatch", "environment.road.cache_metadata_path", "road metadata is missing or differs from the frozen value"))


def _audit_splits(config: Any, errors: list[SimulationIssue]) -> None:
    scale_ids = {str(item.get("id")) for item in config.scales.get("scales", []) if isinstance(item, Mapping)}
    if scale_ids != {f"s{index}" for index in range(1, 7)}:
        errors.append(_issue("error", "scale_registry_incomplete", "scales.scales", "six scales s1 through s6 are required"))
    split_sets: dict[str, set[str]] = {}
    for split, key in (("train", "train_scenarios"), ("validation", "validation_scenarios"), ("sealed_test", "sealed_test_scenarios")):
        values = {str(value) for value in config.experiments.get(key, ())}
        split_sets[split] = values
        if not values:
            errors.append(_issue("error", "missing_scenario_split", key, "scenario split cannot be empty"))
        for scenario_id in values:
            record = config.scenarios.get(scenario_id)
            if not isinstance(record, Mapping) or str(record.get("scale")) not in scale_ids or record.get("split") != split:
                errors.append(_issue("error", "scenario_registry_mismatch", f"scenarios.{scenario_id}", "scenario is absent or has the wrong split/scale"))
    names = list(split_sets.values())
    if len(set.union(*names)) != sum(len(values) for values in names):
        errors.append(_issue("error", "scenario_split_overlap", "experiments", "train, validation and sealed-test scenarios overlap"))


def _derived_regimes(config: Any, profile: SimulationProfile, errors: list[SimulationIssue], warnings: list[SimulationIssue]) -> dict[str, Any]:
    runtime_parameters = config.parameters.get("parameters", {})
    runtime_field = config.field_dynamics.get("parameters", {})
    dt = float(runtime_parameters["decision_dt"]["value"])
    vx = float(runtime_field["wind_vx_m_s"]["value"])
    vy = float(runtime_field["wind_vy_m_s"]["value"])
    pest_diffusion = float(runtime_field["pest_diffusion_rate_m2_s"]["value"])
    pesticide_diffusion = float(runtime_field["pesticide_diffusion_rate_m2_s"]["value"])
    rows: dict[str, Any] = {}
    rendezvous_candidate_count: dict[str, int] = {}
    uav_steps_per_cell: dict[str, float] = {}
    max_courant = 0.0
    max_pest_diffusion_number = 0.0
    max_pesticide_diffusion_number = 0.0
    minimum_horizon_s = math.inf
    road_config = config.environment.get("road", {})
    graphml_path = Path(str(road_config.get("graphml_path", "")))
    if not graphml_path.is_absolute():
        graphml_path = profile.path.parent.parent / graphml_path
    origin = road_config.get("origin_lonlat", [0.0, 0.0])
    road_graph, _road_metadata = load_graphml(
        graphml_path,
        coordinate_mode=str(road_config.get("coordinate_mode", "metric")),
        origin_lonlat=(float(origin[0]), float(origin[1])),
        directed_policy=str(road_config.get("directed_policy", "undirected")),
        bbox_lonlat=tuple(road_config["bbox_lonlat"]) if road_config.get("bbox_lonlat") else None,
    )
    rendezvous_radius = float(runtime_parameters["rendezvous_radius"]["value"])
    uav_step_distance = float(runtime_parameters["uav_speed"]["value"]) * dt
    for scale in config.scales.get("scales", []):
        scale_id = str(scale["id"])
        grid_rows, grid_cols = (int(scale["grid"][0]), int(scale["grid"][1]))
        extent = tuple(float(value) for value in config.scales.get("physical_extent_m", profile.document["physical_extent_m"]))
        dy, dx = extent[0] / grid_rows, extent[1] / grid_cols
        courant = {"x": abs(vx) * dt / dx, "y": abs(vy) * dt / dy}
        pest_number = pest_diffusion * dt * (1.0 / dx**2 + 1.0 / dy**2)
        pesticide_number = pesticide_diffusion * dt * (1.0 / dx**2 + 1.0 / dy**2)
        horizon_s = float(scale["max_steps"]) * dt
        minimum_horizon_s = min(minimum_horizon_s, horizon_s)
        max_courant = max(max_courant, *courant.values())
        max_pest_diffusion_number = max(max_pest_diffusion_number, pest_number)
        max_pesticide_diffusion_number = max(max_pesticide_diffusion_number, pesticide_number)
        rows[scale_id] = {
            "cell_size_m": [dy, dx],
            "horizon_s": horizon_s,
            "wind_courant": courant,
            "pest_diffusion_number": pest_number,
            "pesticide_diffusion_number": pesticide_number,
        }
        candidate_count = 0
        for x_m, y_m in road_graph.nodes.values():
            mapped_x = round(float(x_m) / dx) * dx
            mapped_y = round(float(y_m) / dy) * dy
            if math.hypot(float(x_m) - mapped_x, float(y_m) - mapped_y) <= rendezvous_radius + 1e-12:
                candidate_count += 1
        rendezvous_candidate_count[scale_id] = candidate_count
        uav_steps_per_cell[scale_id] = min(dx, dy) / max(uav_step_distance, 1e-12)
        if candidate_count == 0:
            errors.append(_issue(
                "error",
                "no_rendezvous_geometry",
                f"scales.{scale_id}",
                "no road node maps to a UAV cell within the configured rendezvous radius",
            ))
    if max_courant > 1.0 + 1e-12:
        errors.append(_issue("error", "wind_cfl_violation", "field_dynamics", f"maximum wind Courant number is {max_courant:.6g}"))
    if max_pest_diffusion_number > 0.5 + 1e-12 or max_pesticide_diffusion_number > 0.5 + 1e-12:
        errors.append(_issue("error", "diffusion_stability_violation", "field_dynamics", "explicit diffusion number exceeds 0.5"))
    usable_l = float(runtime_parameters["uav_onboard_pesticide"]["value"]) * float(runtime_parameters["uav_usable_fraction"]["value"])
    transfer_rate = float(runtime_parameters["vehicle_transfer_rate"]["value"])
    service_time = float(runtime_parameters["service_setup_time"]["value"]) + float(runtime_parameters["vehicle_service_capacity"]["value"]) / max(transfer_rate, 1e-12)
    if service_time > minimum_horizon_s:
        errors.append(_issue("error", "service_exceeds_horizon", "engineering_parameters", "nominal service cannot complete within the shortest episode horizon"))
    decay = float(runtime_field["pesticide_decay_rate_s"]["value"])
    efficacy = float(runtime_field["pesticide_efficacy_per_l"]["value"])
    mortality = float(runtime_field["pest_mortality_per_exposure"]["value"])
    ratios: dict[str, float] = {}
    for scale in config.scales.get("scales", []):
        horizon = float(scale["max_steps"]) * dt
        exposure_integral = horizon if decay <= 0 else -math.expm1(-decay * horizon) / decay
        total_liquid = int(scale["uav_count"]) * usable_l + float(runtime_parameters["vehicle_inventory"]["value"])
        initial_total = float(profile.document["derived_regimes"].get("initial_density_reference_mean", 0.8)) * int(scale["grid"][0]) * int(scale["grid"][1])
        ratios[str(scale["id"])] = total_liquid * efficacy * mortality * exposure_integral / max(initial_total, 1e-12)
    warning_ratio = float(profile.document["derived_regimes"].get("treatment_reachability_warning_ratio", 0.85))
    if ratios and min(ratios.values()) < warning_ratio:
        warnings.append(_issue("warning", "treatment_capacity_unreachable", "field_dynamics", "idealized pesticide exposure cannot reach the declared reduction threshold at every scale"))
    return {
        "usable_uav_liquid_l": usable_l,
        "spray_endurance_s": usable_l / max(float(runtime_parameters["uav_spray_flow"]["value"]), 1e-12),
        "nominal_refill_time_s": service_time,
        "vehicle_to_uav_inventory_ratio": float(runtime_parameters["vehicle_inventory"]["value"]) / max(usable_l, 1e-12),
        "uav_distance_per_decision_m": float(runtime_parameters["uav_speed"]["value"]) * dt,
        "vehicle_distance_per_decision_m": float(runtime_parameters["vehicle_speed"]["value"]) * dt,
        "request_safety_margin_s": float(runtime_parameters["request_safety_margin"]["value"]),
        "rendezvous_candidate_count": rendezvous_candidate_count,
        "uav_steps_per_cell": uav_steps_per_cell,
        "max_wind_courant": max_courant,
        "max_pest_diffusion_number": max_pest_diffusion_number,
        "max_pesticide_diffusion_number": max_pesticide_diffusion_number,
        "treatment_reachability_ratio": ratios,
        "scales": rows,
    }


def audit_simulation_preflight(
    config_dir: str | Path,
    *,
    resource_report: str | Path | None = None,
) -> SimulationPreflightReport:
    config_path = Path(config_dir).resolve()
    errors: list[SimulationIssue] = []
    warnings: list[SimulationIssue] = []
    try:
        profile = load_simulation_profile(config_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        issue = _issue("error", "invalid_simulation_profile", "simulation_profile.yaml", str(exc))
        return SimulationPreflightReport(False, "controlled_simulation", (issue,), (), {}, "")
    document = profile.document
    if document.get("status") != "frozen_for_controlled_simulation" or document.get("evidence_mode") != "controlled_simulation":
        errors.append(_issue("error", "invalid_simulation_status", "simulation_profile.yaml", "profile is not frozen for controlled simulation"))
    claim_boundary = str(document.get("claim_boundary", "")).strip()
    if not claim_boundary:
        errors.append(_issue("error", "missing_claim_boundary", "simulation_profile.claim_boundary", "claim boundary is required"))
    try:
        config = load_config_bundle(config_path)
    except Exception as exc:  # noqa: BLE001 - preflight converts config faults to diagnostics
        errors.append(_issue("error", "invalid_runtime_configuration", "configs", str(exc)))
        return SimulationPreflightReport(False, "controlled_simulation", tuple(errors), tuple(warnings), {}, profile.sha256, claim_boundary or CLAIM_BOUNDARY)
    documents = _runtime_documents(config)
    for group_name, names in (("engineering_parameters", ENGINEERING_PARAMETERS), ("field_parameters", FIELD_PARAMETERS)):
        group = document.get(group_name)
        if not isinstance(group, Mapping):
            errors.append(_issue("error", "missing_profile_group", group_name, "parameter group is required"))
            continue
        for name in names:
            path = f"{group_name}.{name}"
            record = group.get(name)
            if not isinstance(record, Mapping):
                errors.append(_issue("error", "missing_profile_parameter", path, "parameter is required"))
                continue
            try:
                runtime_record = _runtime_value(documents, str(record.get("runtime_path", "")))
            except KeyError:
                errors.append(_issue("error", "invalid_runtime_path", f"{path}.runtime_path", "runtime path does not resolve"))
                continue
            _check_profile_record(record, path=path, runtime_record=runtime_record, errors=errors, warnings=warnings)
    if config.scenario_dynamics_kind != "reaction_diffusion_advection_exposure":
        errors.append(_issue("error", "invalid_field_model", "scenarios.dynamics_kind", "mechanistic reaction-diffusion-advection-exposure model is required"))
    if config.algorithm.get("name") != "SR-MAPPO":
        errors.append(_issue("error", "invalid_algorithm_name", "algorithms.sr_mappo.name", "flagship algorithm must remain SR-MAPPO"))
    stability = config.algorithm.get("stability_components", {})
    required_stability = {"observation_normalization", "return_normalization", "orthogonal_initialization", "layer_normalization", "value_clipping", "huber_value_loss", "learning_rate_decay"}
    if not required_stability.issubset({str(key) for key in stability}):
        errors.append(_issue("error", "incomplete_sr_mappo_stability", "algorithms.sr_mappo.stability_components", "all declared SR-MAPPO stability components are required"))
    elif any(stability.get(key) is not True for key in required_stability):
        errors.append(_issue("error", "disabled_sr_mappo_stability", "algorithms.sr_mappo.stability_components", "all SR-MAPPO stability components must be enabled for the flagship simulation profile"))
    _audit_road(config_path, config, errors)
    _audit_splits(config, errors)
    try:
        derived = _derived_regimes(config, profile, errors, warnings)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        errors.append(_issue("error", "invalid_derived_regimes", "derived_regimes", str(exc)))
        derived = {}
    if resource_report is None:
        warnings.append(_issue("warning", "resource_mechanism_unconfirmed", "resource_report", "no resource pilot report was supplied"))
    else:
        try:
            provenance = capture_git_provenance(str(Path(__file__).resolve().parents[3]))
            expected_identity = {
                "config_hash": config_identity(config),
                "simulation_profile_sha256": profile.sha256,
                "git_commit": provenance.commit,
                "source_tree_hash": provenance.source_tree_hash,
            }
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(_issue("error", "resource_report_identity_unavailable", "resource_report", str(exc)))
            expected_identity = {}
        _validate_resource_report(
            Path(resource_report).resolve(),
            expected_identity=expected_identity,
            errors=errors,
            warnings=warnings,
        )
    return SimulationPreflightReport(
        not errors,
        "controlled_simulation",
        tuple(errors),
        tuple(warnings),
        derived,
        profile.sha256,
        claim_boundary or CLAIM_BOUNDARY,
    )


__all__ = [
    "SimulationIssue",
    "SimulationPreflightReport",
    "SimulationProfile",
    "audit_simulation_preflight",
    "load_simulation_profile",
]
