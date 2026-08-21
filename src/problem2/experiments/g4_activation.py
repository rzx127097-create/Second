from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from problem2.config import G2Config, load_g2_config
from problem2.domain import Action, EpisodeState, RequestStatus, UavState, VehicleState
from problem2.resources.ledger import new_ledger
from problem2.road.cache import RoadCacheExpectation, load_road_cache
from problem2.simulation.engine import build_action_masks, step_episode
from problem2.experiments.g4_contract import G4Contract, G4ContractError, G4ProbeManifest
from problem2.experiments.g4_support import FixedSupportPolicy, MobileSupportPolicy


ROOT = Path(__file__).resolve().parents[3]
G2_CONFIG_PATH = ROOT / "configs/problem2/g2_deterministic.yaml"
CANONICAL_G4_ROOT = (ROOT / "outputs/problem2_sr_mappo_v1/g4").resolve()
SOURCE_PROVENANCE_PATHS = (
    "configs/problem2/g2_deterministic.yaml",
    "docs/evidence/g4/g4_contract.yaml",
    "docs/evidence/g4/g4_probe_manifest.yaml",
    "scripts/audit_g4_mechanism.py",
    "scripts/run_g4_mechanism_probe.py",
    "src/problem2/experiments/g4_activation.py",
    "src/problem2/experiments/g4_audit.py",
    "src/problem2/experiments/g4_contract.py",
    "src/problem2/experiments/g4_counterfactual.py",
    "src/problem2/experiments/g4_support.py",
)
REQUIRED_METRICS = (
    "scarcity_active",
    "activation_window",
    "request_count",
    "reservation_count",
    "service_count",
    "started_service_waiting_time_s",
    "euclidean_service_start_distance_m",
    "pesticide_disabled_time_s",
    "sprayed_volume_l",
    "conservation_error_l",
)


def _scarcity_levels(contract: G4Contract) -> tuple[float, float, float]:
    lower, upper = contract.admissible_band
    return lower, round((lower + upper) / 2.0, 10), upper


def validate_activation_band(
    records: Iterable[Mapping[str, Any]],
    expected_levels: Sequence[float],
) -> dict[tuple[str, int], tuple[float, float]]:
    """Validate contiguous activation for every frozen scale/seed combination."""

    levels = tuple(sorted({float(level) for level in expected_levels}))
    if len(levels) < 2:
        raise G4ContractError("activation band requires at least two sampled levels")
    grouped: dict[tuple[str, int], dict[float, bool]] = {}
    for record in records:
        key = (str(record.get("scale_id")), int(record.get("seed")))
        level = float(record.get("scarcity_level_l"))
        if level not in levels:
            raise G4ContractError(
                f"activation record for {key} contains an unexpected scarcity level"
            )
        levels_for_key = grouped.setdefault(key, {})
        if level in levels_for_key:
            raise G4ContractError(f"duplicate activation level for frozen probe {key}")
        levels_for_key[level] = bool(record.get("scarcity_active"))

    if not grouped:
        raise G4ContractError("no activation records were provided")

    windows: dict[tuple[str, int], tuple[float, float]] = {}
    for key, observed in grouped.items():
        if set(observed) != set(levels):
            raise G4ContractError(f"activation levels are incomplete for frozen probe {key}")
        active = [level for level in levels if observed[level]]
        if not active:
            raise G4ContractError(f"no activation for frozen probe {key}")
        if len(active) == 1:
            raise G4ContractError(
                f"activation requires at least two sampled points for frozen probe {key}"
            )
        active_indices = [levels.index(level) for level in active]
        expected_indices = list(range(active_indices[0], active_indices[-1] + 1))
        if active_indices != expected_indices:
            raise G4ContractError(
                f"activation points are not contiguous for frozen probe {key}"
            )
        windows[key] = (active[0], active[-1])
    return windows


def _require_common_activation_window(
    windows: Mapping[tuple[str, int], tuple[float, float]],
    *,
    context: str,
) -> tuple[float, float]:
    unique = set(windows.values())
    if len(unique) != 1:
        raise G4ContractError(f"{context} activation windows do not match")
    return next(iter(unique))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        value = subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise G4ContractError("G4 generator requires Git provenance") from exc
    if not value or value == "unknown":
        raise G4ContractError("G4 generator produced unknown Git provenance")
    return value


def _source_tree_identity() -> tuple[str, str]:
    commit = _git("log", "-1", "--format=%H", "--", *SOURCE_PROVENANCE_PATHS)
    return commit, _git("rev-parse", f"{commit}^{{tree}}")


def _safe_output_root(output_root: Path | str) -> Path:
    candidate = Path(output_root).resolve()
    try:
        candidate.relative_to(CANONICAL_G4_ROOT)
    except ValueError as exc:
        raise G4ContractError("G4 output must remain beneath the canonical G4 root") from exc
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _validate_inputs(contract: G4Contract, manifest: G4ProbeManifest) -> None:
    if manifest.validation_access_allowed:
        raise G4ContractError("validation access must remain disabled")
    if manifest.sealed_test_access_allowed:
        raise G4ContractError("sealed-test access must remain disabled")
    if tuple(contract.probe_scales) != tuple(manifest.probe_scales):
        raise G4ContractError("contract and probe manifest scales must match")
    if tuple(contract.probe_seeds) != tuple(manifest.probe_seeds):
        raise G4ContractError("contract and probe manifest seeds must match")
    if any(20000 <= seed <= 20049 or 30000 <= seed <= 30099 for seed in manifest.probe_seeds):
        raise G4ContractError("validation and sealed probe seeds are forbidden")


def _validate_g2_resource_contract(contract: G4Contract, config: G2Config) -> None:
    if not math.isclose(
        contract.fixed_vehicle_inventory_l,
        config.vehicle_inventory_l,
        rel_tol=0.0,
        abs_tol=config.tolerance,
    ):
        raise G4ContractError("G4 fixed vehicle inventory must match frozen G2 config")
    if contract.admissible_band[0] < 0.0 or contract.admissible_band[1] > config.usable_capacity_l:
        raise G4ContractError("G4 scarcity band must remain within usable UAV capacity")


def _load_graph(config: G2Config, scale_id: str):
    scale = next((item for item in config.scales if item.scale_id == scale_id), None)
    if scale is None:
        raise G4ContractError(f"scale is not in frozen G2 configuration: {scale_id}")
    cache_root = ROOT / "outputs/problem2_sr_mappo_v1/g2/roads" / scale_id
    metadata = json.loads((cache_root / "metadata.json").read_text(encoding="utf-8"))
    generator = metadata["generator"]
    expectation = RoadCacheExpectation(
        scale_id=scale_id,
        source_sha256=config.source_sha256,
        source_crs=config.source_crs,
        target_crs=config.target_crs,
        aoi_bounds_m=tuple(metadata["projection"]["aoi_bounds_m"]),
        grid_shape=scale.grid_shape,
        preprocess_version=config.preprocess_version,
        generator_commit=generator["git_commit"],
        generator_sha256=generator["sha256"],
    )
    return load_road_cache(cache_root / "road_graph.npz", cache_root / "metadata.json", expectation)


def _uav_count(scale_id: str) -> int:
    match = re.search(r"_d(\d+)$", scale_id)
    if match is None:
        raise G4ContractError(f"scale lacks frozen UAV count suffix: {scale_id}")
    return int(match.group(1))


def _initial_state(
    graph,
    config: G2Config,
    scale_id: str,
    seed: int,
    vehicle_inventory_l: float,
    initial_uav_pesticide_l: float,
) -> EpisodeState:
    nodes = [
        node
        for node, (row, col) in enumerate(zip(graph.node_rows, graph.node_cols))
        if int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
    ]
    if not nodes:
        raise G4ContractError(f"G2 graph has no primary road nodes: {scale_id}")
    count = _uav_count(scale_id)
    indices = [
        nodes[0],
        *[
            nodes[(seed + index * max(1, len(nodes) // count)) % len(nodes)]
            for index in range(1, count)
        ],
    ]
    uavs = tuple(
        UavState(
            f"uav-{index}",
            float(graph.node_x_m[node]),
            float(graph.node_y_m[node]),
            initial_uav_pesticide_l,
        )
        for index, node in enumerate(indices)
    )
    support_node = nodes[0]
    vehicle = VehicleState(
        "vehicle-0",
        support_node,
        float(graph.node_x_m[support_node]),
        float(graph.node_y_m[support_node]),
        float(vehicle_inventory_l),
    )
    return EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, vehicle_inventory_l))


def _json_state(state: EpisodeState) -> dict[str, Any]:
    return {
        "step": state.step,
        "uavs": [asdict(uav) for uav in state.uavs],
        "vehicle": asdict(state.vehicle),
        "requests": [asdict(request) for request in state.requests],
        "ledger": asdict(state.ledger),
    }


def _fingerprint(payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, default=lambda value: getattr(value, "value", str(value)), separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _service_start_euclidean_distance(state: EpisodeState, request_id: str) -> float:
    """Measure UAV-vehicle separation from the state where service actually starts."""

    request = next(request for request in state.requests if request.request_id == request_id)
    uav = next(uav for uav in state.uavs if uav.uav_id == request.uav_id)
    return math.hypot(uav.x_m - state.vehicle.x_m, uav.y_m - state.vehicle.y_m)


def _support_probe_name(policy: Any) -> str:
    if isinstance(policy, FixedSupportPolicy):
        return "fixed_support_probe"
    if isinstance(policy, MobileSupportPolicy):
        return "mobile_support_probe"
    raise G4ContractError("support policy must be a frozen fixed or mobile policy")


def _run_one(
    contract: G4Contract,
    config: G2Config,
    manifest: G4ProbeManifest,
    scale_id: str,
    seed: int,
    scarcity_l: float,
    policy: Any,
) -> dict[str, Any]:
    graph = _load_graph(config, scale_id)
    horizon = manifest.horizon_by_scale[scale_id]
    state = _initial_state(
        graph,
        config,
        scale_id,
        seed,
        config.vehicle_inventory_l,
        scarcity_l,
    )
    input_fingerprint = _fingerprint({"scale_id": scale_id, "seed": seed, "horizon": horizon, "state": _json_state(state)})
    events = []
    request_steps: dict[str, int] = {}
    started_service_waiting_time = 0.0
    euclidean_service_start_distances: list[float] = []
    disabled_steps = 0
    max_conservation_error = 0.0
    total_requested_l = 0.0
    while not state.terminated:
        disabled_steps += sum(
            uav.pesticide_l <= config.tolerance for uav in state.uavs
        )
        vehicle_action = policy.choose_vehicle_action(
            state.vehicle, graph, requests=state.requests, uavs=state.uavs
        )
        uav_actions = {
            uav.uav_id: (
                Action.SPRAY
                if uav.pesticide_l > config.tolerance and not uav.service_locked
                else Action.STAY
            )
            for uav in state.uavs
        }
        masks = build_action_masks(state, graph, config)
        next_state = step_episode(
            state, uav_actions, vehicle_action, masks, graph, config, max_steps=horizon
        )
        for event in next_state.last_step_events:
            events.append(event)
            payload = dict(event.payload)
            if event.kind == "request_created":
                request_steps[payload["request_id"]] = event.step
                total_requested_l += float(payload["requested_l"])
            elif event.kind == "service_started":
                request_id = event.entity_id
                if request_id in request_steps:
                    started_service_waiting_time += (event.step - request_steps[request_id]) * config.dt_s
                euclidean_service_start_distances.append(
                    _service_start_euclidean_distance(next_state, request_id)
                )
            if event.kind == "conservation_checked":
                max_conservation_error = max(max_conservation_error, float(payload["error_l"]))
        state = next_state
    counts = {kind: sum(event.kind == kind for event in events) for kind in ("request_created", "request_reserved", "service_completed")}
    sprayed = float(state.ledger.cumulative_sprayed_l)
    total_transferred_l = float(state.ledger.cumulative_transferred_l)
    final_vehicle_inventory_l = float(state.vehicle.inventory_l)
    vehicle_inventory_used_l = config.vehicle_inventory_l - final_vehicle_inventory_l
    active = (
        all(counts[key] > 0 for key in ("request_created", "request_reserved", "service_completed"))
        and total_requested_l > config.tolerance
        and total_transferred_l > config.tolerance
    )
    return {
        "scale_id": scale_id,
        "seed": seed,
        "scarcity_level_l": scarcity_l,
        "initial_uav_pesticide_l": scarcity_l,
        "initial_vehicle_inventory_l": config.vehicle_inventory_l,
        "total_requested_l": total_requested_l,
        "total_transferred_l": total_transferred_l,
        "final_vehicle_inventory_l": final_vehicle_inventory_l,
        "vehicle_inventory_used_l": vehicle_inventory_used_l,
        "support_policy": _support_probe_name(policy),
        "input_fingerprint": input_fingerprint,
        "scarcity_active": active,
        "activation_window": [scarcity_l, scarcity_l] if active else None,
        "request_count": counts["request_created"],
        "reservation_count": counts["request_reserved"],
        "service_count": counts["service_completed"],
        "started_service_waiting_time_s": started_service_waiting_time,
        "euclidean_service_start_distance_m": (
            sum(euclidean_service_start_distances) / len(euclidean_service_start_distances)
            if euclidean_service_start_distances
            else 0.0
        ),
        "pesticide_disabled_time_s": disabled_steps * config.dt_s,
        "sprayed_volume_l": sprayed,
        "conservation_error_l": max_conservation_error,
        "events": events,
    }


def _lineage(contract: G4Contract, manifest: G4ProbeManifest, config: G2Config) -> dict[str, Any]:
    source_commit, source_tree = _source_tree_identity()
    return {
        "g4_contract": str(contract.source_path),
        "probe_manifest": str(manifest.source_path),
        "g4_contract_sha256": _sha256(contract.source_path) if contract.source_path else "unknown",
        "probe_manifest_sha256": _sha256(manifest.source_path) if manifest.source_path else "unknown",
        "g2_config": str(G2_CONFIG_PATH),
        "g2_config_sha256": _sha256(G2_CONFIG_PATH),
        "source_tree_commit": source_commit,
        "source_tree_hash": source_tree,
        "validation_accessed": False,
        "sealed_test_accessed": False,
        "battery_replenishment_enabled": False,
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, default=lambda value: getattr(value, "value", str(value))) + "\n", encoding="utf-8")


def run_activation_probe(contract: G4Contract, manifest: G4ProbeManifest, *, support_policy: Any, output_root: Path | str) -> dict[str, Any]:
    _validate_inputs(contract, manifest)
    if not isinstance(support_policy, (FixedSupportPolicy, MobileSupportPolicy)):
        raise G4ContractError("support policy must be a frozen fixed or mobile policy")
    root = _safe_output_root(output_root)
    config = load_g2_config(G2_CONFIG_PATH)
    _validate_g2_resource_contract(contract, config)
    levels = _scarcity_levels(contract)
    records = []
    raw_lines: list[str] = []
    for scale_id in manifest.probe_scales:
        for seed in manifest.probe_seeds:
            for scarcity_l in levels:
                record = _run_one(
                    contract, config, manifest, scale_id, seed, scarcity_l, support_policy
                )
                record["lineage"] = _lineage(contract, manifest, config)
                records.append(record)
                raw_lines.append(json.dumps({key: value for key, value in record.items() if key != "events"}, sort_keys=True, default=lambda value: getattr(value, "value", str(value))))
    activation_windows = validate_activation_band(records, levels)
    activation_window = _require_common_activation_window(
        activation_windows, context=records[0]["support_policy"]
    )
    summary: dict[str, Any] = {
        "scarcity_active": True,
        "activation_window": list(activation_window),
        "request_count": sum(record["request_count"] for record in records),
        "reservation_count": sum(record["reservation_count"] for record in records),
        "service_count": sum(record["service_count"] for record in records),
        "total_requested_l": sum(record["total_requested_l"] for record in records),
        "total_transferred_l": sum(record["total_transferred_l"] for record in records),
        "final_vehicle_inventory_l": sum(
            record["final_vehicle_inventory_l"] for record in records
        ),
        "vehicle_inventory_used_l": sum(
            record["vehicle_inventory_used_l"] for record in records
        ),
        "started_service_waiting_time_s": sum(
            record["started_service_waiting_time_s"] for record in records
        ),
        "euclidean_service_start_distance_m": sum(
            record["euclidean_service_start_distance_m"] for record in records
        ),
        "pesticide_disabled_time_s": sum(record["pesticide_disabled_time_s"] for record in records),
        "sprayed_volume_l": sum(record["sprayed_volume_l"] for record in records),
        "conservation_error_l": max(record["conservation_error_l"] for record in records),
        "support_policy": records[0]["support_policy"],
        "records": [{key: value for key, value in record.items() if key != "events"} for record in records],
        "lineage": _lineage(contract, manifest, config),
    }
    (root / "raw-probe.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    _write_json(root / "provenance.json", summary["lineage"])
    _write_json(root / "activation-summary.json", summary)
    return summary


def run_probe_matrix(contract: G4Contract, manifest: G4ProbeManifest, *, output_root: Path | str) -> dict[str, Any]:
    _validate_inputs(contract, manifest)
    root = _safe_output_root(output_root)
    _validate_g2_resource_contract(contract, load_g2_config(G2_CONFIG_PATH))
    fixed = run_activation_probe(contract, manifest, support_policy=FixedSupportPolicy(), output_root=root / "fixed")
    mobile = run_activation_probe(contract, manifest, support_policy=MobileSupportPolicy(), output_root=root / "mobile")
    if fixed["activation_window"] != mobile["activation_window"]:
        raise G4ContractError("fixed and mobile arm activation windows do not match")
    fixed_records = {(row["scale_id"], row["seed"], row["scarcity_level_l"]): row for row in fixed["records"]}
    mobile_records = {(row["scale_id"], row["seed"], row["scarcity_level_l"]): row for row in mobile["records"]}
    paired_inputs = []
    for key in sorted(fixed_records):
        paired_inputs.append({"fixed": fixed_records[key], "mobile": mobile_records[key]})
    result = {
        "arms": [fixed, mobile],
        "paired_inputs": paired_inputs,
        "activation_window": fixed["activation_window"],
        "lineage": fixed["lineage"],
    }
    _write_json(root / "probe-matrix-summary.json", result)
    return result


__all__ = ["run_activation_probe", "run_probe_matrix"]
