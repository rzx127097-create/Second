from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
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
REQUIRED_METRICS = (
    "scarcity_active",
    "activation_window",
    "request_count",
    "reservation_count",
    "service_count",
    "waiting_time_s",
    "rendezvous_distance_m",
    "pesticide_disabled_time_s",
    "sprayed_volume_l",
    "conservation_error_l",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


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


def _initial_state(graph, config: G2Config, scale_id: str, seed: int, scarcity_l: float) -> EpisodeState:
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
            0.05,
        )
        for index, node in enumerate(indices)
    )
    support_node = nodes[0]
    vehicle = VehicleState(
        "vehicle-0",
        support_node,
        float(graph.node_x_m[support_node]),
        float(graph.node_y_m[support_node]),
        float(scarcity_l),
    )
    return EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, scarcity_l))


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


def _run_one(config: G2Config, manifest: G4ProbeManifest, scale_id: str, seed: int, scarcity_l: float, policy: Any) -> dict[str, Any]:
    graph = _load_graph(config, scale_id)
    horizon = manifest.horizon_by_scale[scale_id]
    state = _initial_state(graph, config, scale_id, seed, scarcity_l)
    input_fingerprint = _fingerprint({"scale_id": scale_id, "seed": seed, "horizon": horizon, "state": _json_state(state)})
    events = []
    request_steps: dict[str, int] = {}
    waiting_time = 0.0
    rendezvous_distances: list[float] = []
    disabled_steps = 0
    max_conservation_error = 0.0
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
            elif event.kind == "service_started":
                request_id = event.entity_id
                if request_id in request_steps:
                    waiting_time += (event.step - request_steps[request_id]) * config.dt_s
                started_request = next(
                    request
                    for request in next_state.requests
                    if request.request_id == request_id
                )
                uav = next(
                    uav for uav in state.uavs if uav.uav_id == started_request.uav_id
                )
                rendezvous_distances.append(math.hypot(uav.x_m - state.vehicle.x_m, uav.y_m - state.vehicle.y_m))
            if event.kind == "conservation_checked":
                max_conservation_error = max(max_conservation_error, float(payload["error_l"]))
        state = next_state
    counts = {kind: sum(event.kind == kind for event in events) for kind in ("request_created", "request_reserved", "service_completed")}
    sprayed = float(state.ledger.cumulative_sprayed_l)
    active = all(counts[key] > 0 for key in ("request_created", "request_reserved", "service_completed"))
    return {
        "scale_id": scale_id,
        "seed": seed,
        "scarcity_level_l": scarcity_l,
        "support_policy": "mobile" if isinstance(policy, MobileSupportPolicy) else "fixed",
        "input_fingerprint": input_fingerprint,
        "scarcity_active": active,
        "activation_window": [scarcity_l, scarcity_l] if active else None,
        "request_count": counts["request_created"],
        "reservation_count": counts["request_reserved"],
        "service_count": counts["service_completed"],
        "waiting_time_s": waiting_time,
        "rendezvous_distance_m": sum(rendezvous_distances) / len(rendezvous_distances) if rendezvous_distances else 0.0,
        "pesticide_disabled_time_s": disabled_steps * config.dt_s,
        "sprayed_volume_l": sprayed,
        "conservation_error_l": max_conservation_error,
        "events": events,
    }


def _lineage(contract: G4Contract, manifest: G4ProbeManifest, config: G2Config) -> dict[str, Any]:
    return {
        "g4_contract": str(contract.source_path),
        "probe_manifest": str(manifest.source_path),
        "g4_contract_sha256": _sha256(contract.source_path) if contract.source_path else "unknown",
        "probe_manifest_sha256": _sha256(manifest.source_path) if manifest.source_path else "unknown",
        "g2_config": str(G2_CONFIG_PATH),
        "g2_config_sha256": _sha256(G2_CONFIG_PATH),
        "source_tree_commit": _git("rev-parse", "HEAD"),
        "source_tree_hash": _git("rev-parse", "HEAD^{tree}"),
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
    levels = (contract.admissible_band[0], (contract.admissible_band[0] + contract.admissible_band[1]) / 2.0, contract.admissible_band[1])
    records = []
    raw_lines: list[str] = []
    for scale_id in manifest.probe_scales:
        for seed in manifest.probe_seeds:
            for scarcity_l in levels:
                record = _run_one(config, manifest, scale_id, seed, scarcity_l, support_policy)
                record["lineage"] = _lineage(contract, manifest, config)
                records.append(record)
                raw_lines.append(json.dumps({key: value for key, value in record.items() if key != "events"}, sort_keys=True, default=lambda value: getattr(value, "value", str(value))))
    active_levels = sorted({record["scarcity_level_l"] for record in records if record["scarcity_active"]})
    if not active_levels:
        raise G4ContractError("frozen probe set did not activate the scarcity mechanism")
    summary: dict[str, Any] = {
        "scarcity_active": True,
        "activation_window": [min(active_levels), max(active_levels)],
        "request_count": sum(record["request_count"] for record in records),
        "reservation_count": sum(record["reservation_count"] for record in records),
        "service_count": sum(record["service_count"] for record in records),
        "waiting_time_s": sum(record["waiting_time_s"] for record in records),
        "rendezvous_distance_m": sum(record["rendezvous_distance_m"] for record in records),
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
    fixed = run_activation_probe(contract, manifest, support_policy=FixedSupportPolicy(), output_root=root / "fixed")
    mobile = run_activation_probe(contract, manifest, support_policy=MobileSupportPolicy(), output_root=root / "mobile")
    fixed_records = {(row["scale_id"], row["seed"], row["scarcity_level_l"]): row for row in fixed["records"]}
    mobile_records = {(row["scale_id"], row["seed"], row["scarcity_level_l"]): row for row in mobile["records"]}
    paired_inputs = []
    for key in sorted(fixed_records):
        paired_inputs.append({"fixed": fixed_records[key], "mobile": mobile_records[key]})
    result = {
        "arms": [fixed, mobile],
        "paired_inputs": paired_inputs,
        "activation_window": [min(fixed["activation_window"][0], mobile["activation_window"][0]), max(fixed["activation_window"][1], mobile["activation_window"][1])],
        "lineage": fixed["lineage"],
    }
    _write_json(root / "probe-matrix-summary.json", result)
    return result


__all__ = ["run_activation_probe", "run_probe_matrix"]
