from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

import numpy as np

from problem2.config import G2Config, ScaleConfig, load_g2_config
from problem2.domain import Action, EpisodeState, Event, UavState, VehicleState
from problem2.resources.ledger import new_ledger
from problem2.road.models import ProjectedRoadEdge, ProjectedRoadSource, RasterRoadGraph
from problem2.road.raster import rasterize_road_source
from problem2.simulation.engine import build_action_masks, step_episode


def _json_value(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def canonical_event_jsonl(events: Iterable[Event]) -> bytes:
    lines: list[str] = []
    for event in events:
        payload = {str(key): _json_value(value) for key, value in event.payload}
        record = {
            "entity_id": event.entity_id,
            "kind": event.kind,
            "payload": payload,
            "phase": event.phase,
            "step": event.step,
        }
        lines.append(
            json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def replay_digest(events: Iterable[Event]) -> str:
    return hashlib.sha256(canonical_event_jsonl(events)).hexdigest()


def deterministic_fixture_graph() -> RasterRoadGraph:
    source = ProjectedRoadSource(
        source_path="embedded:g2-replay-fixture",
        source_sha256="0" * 64,
        source_crs="EPSG:32643",
        target_crs="EPSG:32643",
        source_bbox_lonlat=(0.0, 0.0, 0.0, 0.0),
        aoi_bounds_m=(0.0, 0.0, 20.0, 20.0),
        aoi_bbox_lonlat=(0.0, 0.0, 0.0, 0.0),
        nodes={},
        edges=(
            ProjectedRoadEdge(
                "fixture-edge", "fixture-edge", "left", "right", ((5.0, 15.0), (15.0, 15.0))
            ),
        ),
    )
    return rasterize_road_source(source, ScaleConfig("g2-replay", (2, 2), 35), 5.0)


def run_deterministic_fixture(
    graph: RasterRoadGraph,
    config: G2Config,
    *,
    seed: int = 42,
    max_steps: int = 35,
) -> tuple[EpisodeState, tuple[Event, ...]]:
    generator = np.random.Generator(np.random.PCG64(seed))
    primary_nodes = [
        node
        for node, (row, col) in enumerate(zip(graph.node_rows, graph.node_cols))
        if int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
    ]
    start_node = primary_nodes[int(generator.integers(0, len(primary_nodes)))]
    initial_pesticide = (0.02, 0.04)[int(generator.integers(0, 2))]
    uav = UavState(
        "u0",
        float(graph.node_x_m[start_node]),
        float(graph.node_y_m[start_node]),
        initial_pesticide,
    )
    inventory = config.usable_capacity_l - initial_pesticide + config.spray_per_step_l
    vehicle = VehicleState(
        "v0",
        start_node,
        float(graph.node_x_m[start_node]),
        float(graph.node_y_m[start_node]),
        inventory,
    )
    state = EpisodeState(
        0,
        (uav,),
        vehicle,
        ledger=new_ledger([uav], inventory),
    )
    events: list[Event] = []
    while not state.terminated:
        masks = build_action_masks(state, graph, config)
        current_uav = state.uavs[0]
        action = (
            Action.SPRAY
            if masks.for_uav(current_uav.uav_id)[int(Action.SPRAY)]
            else Action.STAY
        )
        state = step_episode(
            state,
            {current_uav.uav_id: action},
            Action.STAY,
            masks,
            graph,
            config,
            max_steps=max_steps,
        )
        events.extend(state.last_step_events)
    return state, tuple(events)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the canonical G2 replay fixture.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    config = load_g2_config(args.config)
    _, events = run_deterministic_fixture(
        deterministic_fixture_graph(), config, seed=args.seed
    )
    content = canonical_event_jsonl(events)
    _atomic_write(args.output, content)
    print(json.dumps({"events": len(events), "sha256": hashlib.sha256(content).hexdigest()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
