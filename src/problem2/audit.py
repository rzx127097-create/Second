from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np

from problem2.config import G2Config
from problem2.domain import Action, UavState, VehicleState
from problem2.dynamics.motion import masked_probabilities, move_uav, move_vehicle
from problem2.road.cache import (
    RoadCacheExpectation,
    load_road_cache,
    write_road_cache,
)
from problem2.road.raster import rasterize_road_source
from problem2.road.search import astar_distance, dijkstra_distance
from problem2.road.source import load_projected_road_source, sha256_file


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR_PATHS = (
    "pyproject.toml",
    "requirements-g2.lock",
    "configs/problem2/g2_deterministic.yaml",
    "src/problem2",
    "scripts/preprocess_g2_roads.py",
    "scripts/audit_g2_deterministic.py",
)


class G2AuditError(ValueError):
    """Raised when the deterministic gate cannot publish passing evidence."""


@dataclass(frozen=True)
class GeneratorProvenance:
    git_commit: str
    tree_sha256: str


@dataclass(frozen=True)
class RoadCacheRecord:
    scale_id: str
    npz_path: Path
    metadata_path: Path
    node_count: int
    edge_count: int
    component_sizes: tuple[int, ...]
    repair_count: int


def _generator_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in _GENERATOR_PATHS:
        path = root / relative
        if path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*.py")
                if "__pycache__" not in candidate.parts
            )
        elif path.is_file():
            files.append(path)
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def resolve_generator_provenance(
    root: Path = REPOSITORY_ROOT,
) -> GeneratorProvenance:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *_GENERATOR_PATHS],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if dirty.returncode != 0:
        raise G2AuditError(f"cannot inspect generator worktree: {dirty.stderr.strip()}")
    if dirty.stdout.strip():
        raise G2AuditError("G2 generator code or configuration is dirty")
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *_GENERATOR_PATHS],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if commit.returncode != 0 or len(commit.stdout.strip()) != 40:
        raise G2AuditError(f"cannot resolve generator Git commit: {commit.stderr.strip()}")
    digest = hashlib.sha256()
    files = _generator_files(root)
    if not files:
        raise G2AuditError("generator file set is empty")
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return GeneratorProvenance(commit.stdout.strip(), digest.hexdigest())


def resolve_output_root(
    config: G2Config,
    override: Path | None,
) -> Path:
    frozen = (REPOSITORY_ROOT / config.output_root).resolve()
    if override is None:
        return frozen
    resolved = Path(override).resolve()
    if resolved == frozen:
        return frozen
    raise G2AuditError(
        f"output must remain inside the frozen G2 output root {frozen}"
    )


def _expectation(
    scale_id: str,
    grid_shape: tuple[int, int],
    source,
    config: G2Config,
    provenance: GeneratorProvenance,
) -> RoadCacheExpectation:
    return RoadCacheExpectation(
        scale_id=scale_id,
        source_sha256=source.source_sha256,
        source_crs=source.source_crs,
        target_crs=source.target_crs,
        aoi_bounds_m=source.aoi_bounds_m,
        grid_shape=grid_shape,
        preprocess_version=config.preprocess_version,
        generator_commit=provenance.git_commit,
        generator_sha256=provenance.tree_sha256,
    )


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _recover_roads_transaction(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    final_roads = output_root / "roads"
    backup_roads = output_root / ".roads-backup"
    for staging_root in output_root.glob(".roads-staging-*"):
        _remove_tree(staging_root)
    if backup_roads.exists():
        if final_roads.exists():
            _remove_tree(backup_roads)
        else:
            os.replace(backup_roads, final_roads)


def _publish_roads_directory(staged_roads: Path, output_root: Path) -> None:
    final_roads = output_root / "roads"
    backup_roads = output_root / ".roads-backup"
    had_prior = final_roads.exists()
    if backup_roads.exists():
        raise G2AuditError("roads transaction backup was not recovered")
    if had_prior:
        os.replace(final_roads, backup_roads)
    try:
        os.replace(staged_roads, final_roads)
    except BaseException:
        if final_roads.exists():
            _remove_tree(final_roads)
        if had_prior and backup_roads.exists():
            os.replace(backup_roads, final_roads)
        raise
    if backup_roads.exists():
        try:
            _remove_tree(backup_roads)
        except BaseException:
            _remove_tree(final_roads)
            os.replace(backup_roads, final_roads)
            raise


def preprocess_all(
    config: G2Config,
    output_root: Path,
    provenance: GeneratorProvenance,
) -> tuple[RoadCacheRecord, ...]:
    output_root = Path(output_root)
    _recover_roads_transaction(output_root)
    source = load_projected_road_source(config)
    staging_root = Path(
        tempfile.mkdtemp(prefix=".roads-staging-", dir=output_root)
    )
    record_values: list[tuple[str, int, int, tuple[int, ...], int]] = []
    try:
        for scale in config.scales:
            graph = rasterize_road_source(source, scale, config.max_segment_m)
            npz_path, metadata_path = write_road_cache(
                graph,
                source,
                config,
                staging_root,
                provenance.git_commit,
                provenance.tree_sha256,
            )
            validated = load_road_cache(
                npz_path,
                metadata_path,
                _expectation(
                    scale.scale_id, scale.grid_shape, source, config, provenance
                ),
            )
            record_values.append(
                (
                    scale.scale_id,
                    len(validated.node_rows),
                    len(validated.edges),
                    validated.component_sizes,
                    len(validated.repairs),
                )
            )
        if len(record_values) != len(config.scales):
            raise G2AuditError("preprocessing did not stage all six road caches")
        _publish_roads_directory(staging_root / "roads", output_root)
        return tuple(
            RoadCacheRecord(
                scale_id,
                output_root / "roads" / scale_id / "road_graph.npz",
                output_root / "roads" / scale_id / "metadata.json",
                node_count,
                edge_count,
                component_sizes,
                repair_count,
            )
            for (
                scale_id,
                node_count,
                edge_count,
                component_sizes,
                repair_count,
            ) in record_values
        )
    finally:
        _remove_tree(staging_root)


def _primary_nodes(graph) -> np.ndarray:
    return np.asarray(
        [
            node
            for node, (row, col) in enumerate(zip(graph.node_rows, graph.node_cols))
            if int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
        ],
        dtype=np.int32,
    )


def _audit_scale(graph, config: G2Config, generator: np.random.Generator) -> dict[str, Any]:
    primary = _primary_nodes(graph)
    if len(primary) == 0:
        raise G2AuditError(f"scale {graph.scale_id} has an empty primary component")
    pairs = generator.choice(primary, size=(20, 2), replace=True)
    differences: list[float] = []
    for start, goal in pairs:
        differences.append(
            abs(
                astar_distance(graph, int(start), int(goal))
                - dijkstra_distance(graph, int(start), int(goal))
            )
        )
    max_difference = max(differences, default=0.0)
    if max_difference > config.tolerance:
        raise G2AuditError(
            f"scale {graph.scale_id} A*/Dijkstra difference {max_difference} exceeds tolerance"
        )
    illegal_probability_count = 0
    for node in range(len(graph.node_rows)):
        row, col = int(graph.node_rows[node]), int(graph.node_cols[node])
        mask = graph.action_mask[row, col]
        probabilities = masked_probabilities(np.zeros(5), mask)
        illegal_probability_count += int(np.count_nonzero(probabilities[~mask]))
    if illegal_probability_count:
        raise G2AuditError(
            f"scale {graph.scale_id} assigns probability to illegal actions"
        )

    center_x = (graph.aoi_bounds_m[0] + graph.aoi_bounds_m[2]) / 2.0
    center_y = (graph.aoi_bounds_m[1] + graph.aoi_bounds_m[3]) / 2.0
    uav = UavState("audit-uav", center_x, center_y, config.usable_capacity_l)
    moved_uav, uav_event = move_uav(
        uav, Action.RIGHT, config, graph.aoi_bounds_m
    )
    uav_distance = float(dict(uav_event.payload)["actual_distance_m"])
    if abs(uav_distance - config.uav_speed_mps * config.dt_s) > config.tolerance:
        raise G2AuditError(f"scale {graph.scale_id} violates the UAV metric speed")

    start = next((node for node in primary if graph.neighbors(int(node))), None)
    if start is None:
        raise G2AuditError(f"scale {graph.scale_id} primary component has no edge")
    first_neighbor, first_action, _ = graph.neighbors(int(start))[0]
    vehicle = VehicleState(
        "audit-vehicle",
        int(start),
        float(graph.node_x_m[start]),
        float(graph.node_y_m[start]),
        config.vehicle_inventory_l,
    )
    moved_vehicle, vehicle_event = move_vehicle(
        vehicle,
        first_action,
        graph,
        config.vehicle_speed_mps * config.dt_s,
    )
    vehicle_distance = float(dict(vehicle_event.payload)["actual_distance_m"])
    if vehicle_distance <= 0.0 or vehicle_distance > config.vehicle_speed_mps * config.dt_s + config.tolerance:
        raise G2AuditError(f"scale {graph.scale_id} violates the vehicle metric speed")
    if moved_vehicle.route_distance_m != vehicle_distance:
        raise G2AuditError(f"scale {graph.scale_id} route-distance accounting mismatch")
    return {
        "scale_id": graph.scale_id,
        "grid_shape": list(graph.grid_shape),
        "node_count": len(graph.node_rows),
        "edge_count": len(graph.edges),
        "component_sizes": list(graph.component_sizes),
        "primary_component_id": graph.primary_component_id,
        "repair_count": len(graph.repairs),
        "path_pairs_checked": len(pairs),
        "astar_dijkstra_max_abs_difference_m": max_difference,
        "illegal_action_nonzero_probability_count": illegal_probability_count,
        "uav_test_distance_m": uav_distance,
        "vehicle_test_distance_m": vehicle_distance,
        "vehicle_test_target_node": int(first_neighbor),
    }


def _run_replay_process(config_path: Path, output: Path, hash_seed: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = hash_seed
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "problem2.simulation.replay",
            "--config",
            str(config_path),
            "--output",
            str(output),
            "--seed",
            "42",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


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


def _artifact_record(path: Path, output_root: Path, role: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(output_root).as_posix(),
        "role": role,
        "sha256": sha256_file(path).lower(),
        "bytes": path.stat().st_size,
    }


def run_g2_audit(
    config: G2Config,
    config_path: Path,
    output_root: Path,
    report_path: Path,
    provenance: GeneratorProvenance,
) -> dict[str, Any]:
    if config.audit_seed != 42:
        raise G2AuditError("G2 deterministic audit seed must remain 42")
    report_path = report_path.resolve()
    expected_report = output_root / "g2-deterministic-audit.json"
    if report_path.resolve() != expected_report.resolve():
        raise G2AuditError(f"audit report must be written to {expected_report}")
    source = load_projected_road_source(config)
    generator = np.random.Generator(np.random.PCG64(config.audit_seed))
    scale_reports: list[dict[str, Any]] = []
    cache_paths: list[Path] = []
    for scale in config.scales:
        npz_path = output_root / "roads" / scale.scale_id / "road_graph.npz"
        metadata_path = output_root / "roads" / scale.scale_id / "metadata.json"
        graph = load_road_cache(
            npz_path,
            metadata_path,
            _expectation(
                scale.scale_id, scale.grid_shape, source, config, provenance
            ),
        )
        scale_reports.append(_audit_scale(graph, config, generator))
        cache_paths.extend((npz_path, metadata_path))

    with tempfile.TemporaryDirectory(prefix="g2-replay-") as temporary:
        temp_root = Path(temporary)
        first_path = temp_root / "hashseed-1.jsonl"
        second_path = temp_root / "hashseed-98765.jsonl"
        first = _run_replay_process(config_path, first_path, "1")
        second = _run_replay_process(config_path, second_path, "98765")
        if first.returncode != 0 or second.returncode != 0:
            raise G2AuditError(
                "cross-process replay failed: "
                f"first={first.stderr.strip()!r}, second={second.stderr.strip()!r}"
            )
        first_content = first_path.read_bytes()
        second_content = second_path.read_bytes()
    if first_content != second_content:
        raise G2AuditError("cross-process replay event sequences differ")
    replay_hash = hashlib.sha256(first_content).hexdigest()
    replay_records = [json.loads(line) for line in first_content.splitlines()]
    conservation_errors = [
        float(record["payload"]["error_l"])
        for record in replay_records
        if record["kind"] == "conservation_checked"
    ]
    max_conservation_error = max(conservation_errors, default=math.inf)
    if max_conservation_error > config.tolerance:
        raise G2AuditError(
            f"replay conservation error {max_conservation_error} exceeds tolerance"
        )

    trace_path = output_root / "deterministic-event-trace.jsonl"
    report = {
        "schema_version": "g2-deterministic-audit-v1",
        "status": "pass",
        "gate": "G2",
        "maturity": "M2",
        "generator": {
            "git_commit": provenance.git_commit,
            "tree_sha256": provenance.tree_sha256,
        },
        "source": {
            "path": source.source_path,
            "sha256": source.source_sha256,
            "source_crs": source.source_crs,
            "target_crs": source.target_crs,
            "aoi_bounds_m": list(source.aoi_bounds_m),
        },
        "scales": scale_reports,
        "cross_process_replay": {
            "match": True,
            "python_hash_seeds": [1, 98765],
            "event_count": len(replay_records),
            "sha256": replay_hash,
        },
        "resource_conservation": {
            "tolerance_l": config.tolerance,
            "max_abs_error_l": max_conservation_error,
        },
        "sealed_test": {"accessed": False, "unlock_count": 0},
        "training": {"performed": False},
        "formal_experiments": {"performed": False},
        "permitted_claim": "G2 deterministic implementation verified",
    }
    report_content = _canonical_json(report)
    _atomic_write(trace_path, first_content)
    _atomic_write(report_path, report_content)
    artifacts = [
        _artifact_record(path, output_root, "road-cache")
        for path in sorted(cache_paths)
    ]
    artifacts.extend(
        [
            _artifact_record(trace_path, output_root, "deterministic-event-trace"),
            _artifact_record(report_path, output_root, "g2-audit-report"),
        ]
    )
    manifest = {
        "schema_version": "g2-artifact-manifest-v1",
        "status": "pass",
        "gate": "G2",
        "generator": report["generator"],
        "artifacts": artifacts,
    }
    _atomic_write(output_root / "artifact-manifest.json", _canonical_json(manifest))
    return report
