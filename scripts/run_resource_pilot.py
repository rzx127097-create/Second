"""Run the deterministic resource-counterfactual activation pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.metrics import episode_record_from_bundle
from problem2.experiments.resource_activation import audit_resource_activation
from problem2.experiments.simulation_preflight import load_simulation_profile
from problem2.config import config_identity, load_config_bundle
from problem2.experiments.job_identity import capture_git_provenance
from problem2.scenarios.factory import build_synthetic_scenario
from problem2.scenarios.interventions import ScenarioIntervention


def _conditions() -> tuple[tuple[str, ScenarioIntervention], ...]:
    return (
        ("unlimited_supply", ScenarioIntervention("unlimited_supply", pesticide_mode="unlimited")),
        ("finite_no_support", ScenarioIntervention("finite_no_support", support_mode="disabled")),
        ("matched_fixed", ScenarioIntervention("matched_fixed", support_mode="fixed")),
        ("teleport_diagnostic", ScenarioIntervention("teleport_diagnostic", support_mode="teleport")),
        ("sr_mappo_mobile", ScenarioIntervention("sr_mappo_mobile", support_mode="mobile")),
    )


def _scenario_id(config_dir: Path, scale: str) -> str:
    import yaml

    document = yaml.safe_load((config_dir / "scenarios.yaml").read_text(encoding="utf-8"))
    for scenario_id, record in document.get("scenarios", {}).items():
        if record.get("split") == "train" and str(record.get("scale")) == scale:
            return str(scenario_id)
    raise ValueError(f"no train scenario registered for scale {scale}")


def _action_for_snapshot(snapshot: Any) -> dict[str, str]:
    actions: dict[str, str] = {}
    for agent_id, observation in snapshot.role_observations.items():
        valid = snapshot.action_masks[agent_id].valid_actions
        if observation.get("role") == "uav":
            actions[agent_id] = (
                "spray"
                if "spray" in valid
                else next((name for name in valid if name != "hold"), "hold")
            )
        else:
            actions[agent_id] = next((name for name in valid if name != "hold"), "hold")
    return actions


def _preposition_uavs_for_spatial_probe(bundle: Any) -> None:
    """Place UAVs at shared remote, road-serviceable diagnostic work sites."""

    adapter = bundle.adapter
    probe_uav = adapter.uav_slots[0]
    points = sorted(
        adapter._rendezvous_points(probe_uav, include_all_nodes=True),
        key=lambda point: (point.distance_m, point.road_node_id),
        reverse=True,
    )
    if len(points) < len(adapter.uav_slots):
        raise ValueError("resource pilot needs one serviceable work site per UAV")
    for uav_id, point in zip(adapter.uav_slots, points):
        target_cell = adapter.road_node_to_uav_cell(point.road_node_id)
        row_size_m, col_size_m = adapter.uav_cell_size_m
        adapter.uav_positions[uav_id] = target_cell
        adapter._uav_metric_positions[uav_id] = (
            float(target_cell[1]) * col_size_m,
            float(target_cell[0]) * row_size_m,
        )
    adapter._refresh_request_candidates()
    adapter._refresh_state(events=[])


def _run_episode(config_dir: Path, scale: str, seed: int, scenario_id: str, intervention: ScenarioIntervention, max_steps: int | None) -> dict[str, object]:
    bundle = build_synthetic_scenario(
        scale,
        seed,
        config_dir=config_dir,
        scenario_id=scenario_id,
        intervention=intervention,
    )
    bundle.reset()
    _preposition_uavs_for_spatial_probe(bundle)
    snapshot = bundle._snapshot(events=())
    initial_pest = float(bundle.initial_density.sum())
    initial_pesticide = float(bundle.resources.total_pesticide_l)
    events: list[dict[str, object]] = []
    reward_total = 0.0
    reward_components: dict[str, float] = {}
    steps = 0
    step_limit = bundle.max_steps if max_steps is None else min(int(max_steps), bundle.max_steps)
    while steps < step_limit:
        step = bundle.step(_action_for_snapshot(snapshot))
        steps += 1
        snapshot = step
        events.extend(dict(event) for event in step.events)
        reward_total += float(step.reward)
        for key, value in step.reward_components.items():
            reward_components[key] = reward_components.get(key, 0.0) + float(value)
        if step.terminated or step.truncated:
            break
    record = episode_record_from_bundle(
        bundle,
        episode_id=f"pilot-{intervention.condition_id}-{scale}-{seed}",
        steps=steps,
        total_reward=reward_total,
        reward_components=reward_components,
        initial_pest_total=initial_pest,
        pesticide_initial_l=initial_pesticide,
        events=events,
        agent_ids={"uav": sorted(bundle.resources.uavs), "vehicle": sorted(bundle.resources.vehicles)},
        policy_name="resource_pilot_script",
        split="train",
        scenario_id=scenario_id,
        evidence_mode="simulation",
        simulation_profile_sha256=bundle.simulation_profile_sha256,
        preflight_warnings=bundle.simulation_preflight_warnings,
    )
    row = record.to_row()
    row.update({
        "condition_id": intervention.condition_id,
        "scale": scale,
        "training_seed": seed,
        "scenario_id": scenario_id,
        "provisional": True,
    })
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--scale", action="append", default=[])
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="optional smoke-test truncation; defaults to each scale's frozen horizon",
    )
    args = parser.parse_args(argv)
    if args.episodes < 1 or (args.max_steps is not None and args.max_steps < 1):
        raise ValueError("episodes and max-steps must be positive")
    rows: list[dict[str, object]] = []
    scales = args.scale or ["s1"]
    for scale in tuple(dict.fromkeys(str(value) for value in scales)):
        scenario_id = _scenario_id(args.config_dir, scale)
        for episode in range(args.episodes):
            for _condition_id, intervention in _conditions():
                rows.append(_run_episode(args.config_dir, scale, episode, scenario_id, intervention, args.max_steps))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    activation = audit_resource_activation(rows)
    config = load_config_bundle(args.config_dir)
    profile = load_simulation_profile(args.config_dir)
    provenance = capture_git_provenance(str(ROOT))
    report = {
        **activation.to_dict(),
        "total_shortage": None,
        "spatial_temporal_mismatch": None,
        "mobile_gap_closure": None,
        "diagnosis": (
            "resource_service_chain_activated"
            if activation.activated
            else "resource_service_chain_not_activated"
        ),
        "interpretation_scope": "resource_service_activation_only",
        "endpoint_comparison_valid": False,
        "spatial_probe_initialization": "prepositioned_serviceable_work_sites",
        "policy_note": (
            "The deterministic stress policy maximizes spraying and follows "
            "service masks; treatment endpoints are not a fair algorithm comparison."
        ),
        "raw_path": str(args.output.resolve()),
        "provisional": True,
        "config_hash": config_identity(config),
        "simulation_profile_sha256": profile.sha256,
        "git_commit": provenance.commit,
        "source_tree_hash": provenance.source_tree_hash,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
