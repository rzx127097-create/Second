from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import numpy as np

from problem2.config import G2Config
from problem2.domain import Action
from problem2.road.models import ProjectedRoadSource, RasterRoadGraph, RepairRecord


class CacheValidationError(ValueError):
    """Raised when a road cache is stale, corrupt, or structurally invalid."""


@dataclass(frozen=True)
class RoadCacheExpectation:
    scale_id: str
    source_sha256: str
    target_crs: str
    aoi_bounds_m: tuple[float, float, float, float]
    grid_shape: tuple[int, int]
    preprocess_version: str
    generator_sha256: str


_ARRAY_NAMES = (
    "road_mask",
    "action_mask",
    "component_id",
    "node_rows",
    "node_cols",
    "node_x_m",
    "node_y_m",
    "edges",
    "edge_lengths_m",
)


def _arrays_for_graph(graph: RasterRoadGraph) -> dict[str, np.ndarray]:
    return {name: np.asarray(getattr(graph, name)) for name in _ARRAY_NAMES}


def _hash_arrays(arrays: Mapping[str, np.ndarray], names: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for name in sorted(names):
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("ascii"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _json_error(constant: str) -> None:
    raise CacheValidationError(f"metadata contains non-finite JSON value {constant}")


def _validate_hex(value: str, length: int, name: str) -> None:
    if len(value) != length or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise CacheValidationError(f"{name} must be {length}-character hexadecimal text")


def _metadata(
    graph: RasterRoadGraph,
    source: ProjectedRoadSource,
    config: G2Config,
    arrays: Mapping[str, np.ndarray],
    generator_commit: str,
    generator_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "g2-road-cache-v1",
        "scale_id": graph.scale_id,
        "preprocess_version": config.preprocess_version,
        "source": {
            "path": source.source_path,
            "sha256": source.source_sha256,
            "crs": source.source_crs,
            "bbox_lonlat": list(source.source_bbox_lonlat),
        },
        "projection": {
            "target_crs": source.target_crs,
            "aoi_bounds_m": list(source.aoi_bounds_m),
            "aoi_bbox_lonlat": list(source.aoi_bbox_lonlat),
        },
        "grid": {
            "shape": list(graph.grid_shape),
            "cell_width_m": graph.cell_width_m,
            "cell_height_m": graph.cell_height_m,
        },
        "topology": {
            "convention": config.topology,
            "component_sizes": list(graph.component_sizes),
            "primary_component_id": graph.primary_component_id,
            "repair_count": len(graph.repairs),
        },
        "mapping": {
            "source_node_to_cell": {
                key: list(value) for key, value in sorted(graph.source_node_to_cell.items())
            },
            "source_edge_to_cells": {
                key: [list(cell) for cell in value]
                for key, value in sorted(graph.source_edge_to_cells.items())
            },
        },
        "repairs": [asdict(repair) for repair in graph.repairs],
        "generator": {
            "git_commit": generator_commit,
            "sha256": generator_sha256,
        },
        "dependencies": {
            package: version(package)
            for package in ("networkx", "numpy", "pyproj", "PyYAML", "shapely")
        },
        "content_checksum": _hash_arrays(arrays, _ARRAY_NAMES),
        "adjacency_checksum": _hash_arrays(
            arrays,
            ("node_rows", "node_cols", "edges", "edge_lengths_m"),
        ),
    }


def write_road_cache(
    graph: RasterRoadGraph,
    source: ProjectedRoadSource,
    config: G2Config,
    output_root: Path,
    generator_commit: str,
    generator_sha256: str,
) -> tuple[Path, Path]:
    _validate_hex(generator_commit, 40, "generator_commit")
    _validate_hex(generator_sha256, 64, "generator_sha256")
    arrays = _arrays_for_graph(graph)
    metadata = _metadata(
        graph, source, config, arrays, generator_commit, generator_sha256
    )
    scale_dir = Path(output_root) / "roads" / graph.scale_id
    scale_dir.mkdir(parents=True, exist_ok=True)
    npz_path = scale_dir / "road_graph.npz"
    metadata_path = scale_dir / "metadata.json"
    npz_fd, npz_temp_name = tempfile.mkstemp(prefix="road-", suffix=".npz.tmp", dir=scale_dir)
    json_fd, json_temp_name = tempfile.mkstemp(prefix="metadata-", suffix=".json.tmp", dir=scale_dir)
    os.close(npz_fd)
    os.close(json_fd)
    npz_temp = Path(npz_temp_name)
    json_temp = Path(json_temp_name)
    expectation = RoadCacheExpectation(
        scale_id=graph.scale_id,
        source_sha256=source.source_sha256,
        target_crs=source.target_crs,
        aoi_bounds_m=source.aoi_bounds_m,
        grid_shape=graph.grid_shape,
        preprocess_version=config.preprocess_version,
        generator_sha256=generator_sha256,
    )
    try:
        with npz_temp.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        with json_temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(metadata, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        load_road_cache(npz_temp, json_temp, expectation)
        os.replace(npz_temp, npz_path)
        os.replace(json_temp, metadata_path)
    finally:
        npz_temp.unlink(missing_ok=True)
        json_temp.unlink(missing_ok=True)
    return npz_path, metadata_path


def _tuple_cells(payload: Mapping[str, Any]) -> dict[str, tuple[tuple[int, int], ...]]:
    return {
        str(key): tuple((int(cell[0]), int(cell[1])) for cell in value)
        for key, value in payload.items()
    }


def load_road_cache(
    npz_path: Path,
    metadata_path: Path,
    expected: RoadCacheExpectation,
) -> RasterRoadGraph:
    try:
        metadata = json.loads(
            Path(metadata_path).read_text(encoding="utf-8"),
            parse_constant=_json_error,
        )
    except CacheValidationError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheValidationError(f"cannot read road cache metadata: {exc}") from exc
    if not isinstance(metadata, dict):
        raise CacheValidationError("road cache metadata must be an object")

    observed = {
        "scale_id": metadata.get("scale_id"),
        "source_sha256": metadata.get("source", {}).get("sha256"),
        "target_crs": metadata.get("projection", {}).get("target_crs"),
        "aoi_bounds_m": tuple(metadata.get("projection", {}).get("aoi_bounds_m", ())),
        "grid_shape": tuple(metadata.get("grid", {}).get("shape", ())),
        "preprocess_version": metadata.get("preprocess_version"),
        "generator_sha256": metadata.get("generator", {}).get("sha256"),
    }
    for field, wanted in (
        ("scale_id", expected.scale_id),
        ("source_sha256", expected.source_sha256),
        ("target_crs", expected.target_crs),
        ("aoi_bounds_m", expected.aoi_bounds_m),
        ("grid_shape", expected.grid_shape),
        ("preprocess_version", expected.preprocess_version),
        ("generator_sha256", expected.generator_sha256),
    ):
        if observed[field] != wanted:
            raise CacheValidationError(
                f"{field} mismatch: expected {wanted!r}, observed {observed[field]!r}"
            )
    generator_commit = str(metadata.get("generator", {}).get("git_commit", ""))
    _validate_hex(generator_commit, 40, "generator git commit")

    try:
        with np.load(npz_path, allow_pickle=False) as archive:
            missing = sorted(set(_ARRAY_NAMES) - set(archive.files))
            if missing:
                raise CacheValidationError(f"road cache arrays missing: {missing}")
            arrays = {name: archive[name].copy() for name in _ARRAY_NAMES}
    except CacheValidationError:
        raise
    except (OSError, ValueError) as exc:
        raise CacheValidationError(f"cannot read road cache arrays: {exc}") from exc

    content_checksum = _hash_arrays(arrays, _ARRAY_NAMES)
    if content_checksum != metadata.get("content_checksum"):
        raise CacheValidationError("road cache content checksum mismatch")
    adjacency_checksum = _hash_arrays(
        arrays, ("node_rows", "node_cols", "edges", "edge_lengths_m")
    )
    if adjacency_checksum != metadata.get("adjacency_checksum"):
        raise CacheValidationError("road cache adjacency checksum mismatch")

    height, width = expected.grid_shape
    if arrays["road_mask"].shape != (height, width):
        raise CacheValidationError("road_mask shape mismatch")
    if arrays["action_mask"].shape != (height, width, 5):
        raise CacheValidationError("action_mask shape mismatch")
    if arrays["component_id"].shape != (height, width):
        raise CacheValidationError("component_id shape mismatch")
    node_count = len(arrays["node_rows"])
    for name in ("node_cols", "node_x_m", "node_y_m"):
        if len(arrays[name]) != node_count:
            raise CacheValidationError(f"{name} node count mismatch")
    if arrays["edges"].ndim != 2 or arrays["edges"].shape[1:] != (2,):
        raise CacheValidationError("edges must have shape (N, 2)")
    if len(arrays["edge_lengths_m"]) != len(arrays["edges"]):
        raise CacheValidationError("edge length count mismatch")
    for left, right in arrays["edges"]:
        if not (0 <= int(left) < node_count and 0 <= int(right) < node_count):
            raise CacheValidationError("edge endpoint is outside node range")
        dr = abs(int(arrays["node_rows"][left]) - int(arrays["node_rows"][right]))
        dc = abs(int(arrays["node_cols"][left]) - int(arrays["node_cols"][right]))
        if dr + dc != 1:
            raise CacheValidationError("road cache contains a non-four-connected edge")

    road_mask = arrays["road_mask"].astype(np.bool_, copy=False)
    expected_road_mask = np.zeros((height, width), dtype=np.bool_)
    expected_action_mask = np.zeros((height, width, 5), dtype=np.bool_)
    for row, col in zip(arrays["node_rows"], arrays["node_cols"]):
        row_i, col_i = int(row), int(col)
        if not (0 <= row_i < height and 0 <= col_i < width):
            raise CacheValidationError("road node lies outside grid_shape")
        expected_road_mask[row_i, col_i] = True
        expected_action_mask[row_i, col_i, int(Action.STAY)] = True
    if not np.array_equal(road_mask, expected_road_mask):
        raise CacheValidationError("road_mask does not match canonical road nodes")
    if not np.array_equal(arrays["component_id"] >= 0, expected_road_mask):
        raise CacheValidationError("component_id does not match road_mask")

    cell_width_m = float(metadata["grid"]["cell_width_m"])
    cell_height_m = float(metadata["grid"]["cell_height_m"])
    for edge_index, (left, right) in enumerate(arrays["edges"]):
        left_i, right_i = int(left), int(right)
        left_row, left_col = int(arrays["node_rows"][left_i]), int(arrays["node_cols"][left_i])
        right_row, right_col = int(arrays["node_rows"][right_i]), int(arrays["node_cols"][right_i])
        dr, dc = right_row - left_row, right_col - left_col
        left_action = {
            (-1, 0): Action.UP,
            (1, 0): Action.DOWN,
            (0, -1): Action.LEFT,
            (0, 1): Action.RIGHT,
        }[(dr, dc)]
        right_action = {
            Action.UP: Action.DOWN,
            Action.DOWN: Action.UP,
            Action.LEFT: Action.RIGHT,
            Action.RIGHT: Action.LEFT,
        }[left_action]
        expected_action_mask[left_row, left_col, int(left_action)] = True
        expected_action_mask[right_row, right_col, int(right_action)] = True
        expected_length = cell_height_m if dr else cell_width_m
        if not np.isfinite(arrays["edge_lengths_m"][edge_index]) or not np.isclose(
            arrays["edge_lengths_m"][edge_index], expected_length, atol=1e-12, rtol=0.0
        ):
            raise CacheValidationError("edge_lengths_m does not match grid geometry")
    if not np.array_equal(arrays["action_mask"], expected_action_mask):
        raise CacheValidationError("action_mask does not match canonical adjacency")

    mapping = metadata.get("mapping", {})
    source_node_to_cell = {
        str(key): (int(value[0]), int(value[1]))
        for key, value in mapping.get("source_node_to_cell", {}).items()
    }
    source_edge_to_cells = _tuple_cells(mapping.get("source_edge_to_cells", {}))
    repairs = tuple(
        RepairRecord(
            source_edge_id=str(item["source_edge_id"]),
            from_cell=tuple(int(value) for value in item["from_cell"]),
            inserted_cell=tuple(int(value) for value in item["inserted_cell"]),
            to_cell=tuple(int(value) for value in item["to_cell"]),
            metric_length_m=float(item["metric_length_m"]),
            reason=str(item["reason"]),
        )
        for item in metadata.get("repairs", [])
    )
    topology = metadata.get("topology", {})
    for array in arrays.values():
        array.flags.writeable = False
    return RasterRoadGraph(
        scale_id=expected.scale_id,
        grid_shape=expected.grid_shape,
        aoi_bounds_m=expected.aoi_bounds_m,
        cell_width_m=cell_width_m,
        cell_height_m=cell_height_m,
        road_mask=arrays["road_mask"],
        action_mask=arrays["action_mask"],
        component_id=arrays["component_id"],
        node_rows=arrays["node_rows"],
        node_cols=arrays["node_cols"],
        node_x_m=arrays["node_x_m"],
        node_y_m=arrays["node_y_m"],
        edges=arrays["edges"],
        edge_lengths_m=arrays["edge_lengths_m"],
        component_sizes=tuple(int(value) for value in topology["component_sizes"]),
        primary_component_id=int(topology["primary_component_id"]),
        source_node_to_cell=source_node_to_cell,
        source_edge_to_cells=source_edge_to_cells,
        repairs=repairs,
    )
