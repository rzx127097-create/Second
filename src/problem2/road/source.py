from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Iterable

import networkx as nx
from pyproj import CRS, Transformer
from shapely import wkt
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Point, box
from shapely.ops import transform

from problem2.config import G2Config
from problem2.road.models import (
    ProjectedRoadEdge,
    ProjectedRoadNode,
    ProjectedRoadSource,
)


class SourceIntegrityError(ValueError):
    """Raised when offline road-source provenance or geometry is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise SourceIntegrityError(f"cannot read road source {path}: {exc}") from exc
    return digest.hexdigest().upper()


def _finite_coordinate(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceIntegrityError(f"{label} must be a finite coordinate") from exc
    if not math.isfinite(number):
        raise SourceIntegrityError(f"{label} must be finite")
    return number


def _line_parts(geometry) -> Iterable[LineString]:
    if isinstance(geometry, LineString):
        yield geometry
    elif isinstance(geometry, MultiLineString):
        yield from geometry.geoms
    elif isinstance(geometry, GeometryCollection):
        for part in geometry.geoms:
            yield from _line_parts(part)


def _validate_line(line: LineString, edge_id: str) -> None:
    if line.is_empty or len(line.coords) < 2:
        raise SourceIntegrityError(f"edge {edge_id} geometry has fewer than two points")
    for index, coordinate in enumerate(line.coords):
        if len(coordinate) < 2:
            raise SourceIntegrityError(f"edge {edge_id} geometry coordinate is invalid")
        _finite_coordinate(coordinate[0], f"edge {edge_id} x[{index}]")
        _finite_coordinate(coordinate[1], f"edge {edge_id} y[{index}]")


def _edge_geometry(data: dict, endpoints: LineString, edge_id: str) -> LineString:
    raw = data.get("geometry")
    if raw in (None, ""):
        return endpoints
    if not isinstance(raw, str):
        raise SourceIntegrityError(f"edge {edge_id} geometry must be WKT text")
    try:
        geometry = wkt.loads(raw)
    except Exception as exc:
        raise SourceIntegrityError(f"edge {edge_id} geometry is invalid") from exc
    if not isinstance(geometry, LineString):
        raise SourceIntegrityError(f"edge {edge_id} geometry must be a LINESTRING")
    _validate_line(geometry, edge_id)
    return geometry


def load_projected_road_source(config: G2Config) -> ProjectedRoadSource:
    actual_hash = sha256_file(config.source_path)
    if actual_hash != config.source_sha256.upper():
        raise SourceIntegrityError(
            "road source SHA-256 mismatch: "
            f"expected {config.source_sha256.upper()}, observed {actual_hash}"
        )
    try:
        graph = nx.read_graphml(
            config.source_path,
            node_type=str,
            edge_key_type=str,
            force_multigraph=True,
        )
    except Exception as exc:
        raise SourceIntegrityError(f"cannot parse GraphML road source: {exc}") from exc

    declared_crs = graph.graph.get("crs")
    if declared_crs is None:
        raise SourceIntegrityError("GraphML road source has no CRS declaration")
    try:
        observed_crs = CRS.from_user_input(declared_crs)
        expected_crs = CRS.from_user_input(config.source_crs)
        target_crs = CRS.from_user_input(config.target_crs)
    except Exception as exc:
        raise SourceIntegrityError(f"road CRS is invalid: {exc}") from exc
    if observed_crs != expected_crs:
        raise SourceIntegrityError(
            f"road CRS mismatch: expected {expected_crs.to_string()}, "
            f"observed {observed_crs.to_string()}"
        )

    transformer = Transformer.from_crs(expected_crs, target_crs, always_xy=True)
    inverse = Transformer.from_crs(target_crs, expected_crs, always_xy=True)
    center_x, center_y = transformer.transform(*config.center_lonlat)
    width_m, height_m = config.extent_m
    aoi_bounds = (
        center_x - width_m / 2.0,
        center_y - height_m / 2.0,
        center_x + width_m / 2.0,
        center_y + height_m / 2.0,
    )
    aoi = box(*aoi_bounds)
    aoi_corners = [
        inverse.transform(aoi_bounds[0], aoi_bounds[1]),
        inverse.transform(aoi_bounds[2], aoi_bounds[3]),
    ]
    aoi_lonlat = (
        min(point[0] for point in aoi_corners),
        min(point[1] for point in aoi_corners),
        max(point[0] for point in aoi_corners),
        max(point[1] for point in aoi_corners),
    )

    lonlat_by_node: dict[str, tuple[float, float]] = {}
    projected_nodes: dict[str, ProjectedRoadNode] = {}
    for node_id, data in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
        lon = _finite_coordinate(data.get("x"), f"node {node_id} longitude")
        lat = _finite_coordinate(data.get("y"), f"node {node_id} latitude")
        lonlat_by_node[str(node_id)] = (lon, lat)
        x_m, y_m = transformer.transform(lon, lat)
        _finite_coordinate(x_m, f"node {node_id} projected x")
        _finite_coordinate(y_m, f"node {node_id} projected y")
        if aoi.covers(Point(x_m, y_m)):
            projected_nodes[str(node_id)] = ProjectedRoadNode(
                source_id=str(node_id), lon=lon, lat=lat, x_m=x_m, y_m=y_m
            )

    if not lonlat_by_node:
        raise SourceIntegrityError("GraphML road source contains no nodes")
    source_bbox = (
        min(point[0] for point in lonlat_by_node.values()),
        min(point[1] for point in lonlat_by_node.values()),
        max(point[0] for point in lonlat_by_node.values()),
        max(point[1] for point in lonlat_by_node.values()),
    )

    projected_edges: list[ProjectedRoadEdge] = []
    edges = sorted(
        graph.edges(keys=True, data=True),
        key=lambda item: (str(item[0]), str(item[1]), str(item[2])),
    )
    for source_u, source_v, key, data in edges:
        u_id, v_id = str(source_u), str(source_v)
        edge_id = f"{u_id}|{v_id}|{key}"
        endpoints = LineString([lonlat_by_node[u_id], lonlat_by_node[v_id]])
        source_line = _edge_geometry(data, endpoints, edge_id)
        try:
            metric_line = transform(transformer.transform, source_line)
            clipped = metric_line.intersection(aoi)
        except Exception as exc:
            raise SourceIntegrityError(
                f"edge {edge_id} geometry projection or clipping failed"
            ) from exc
        parts = list(_line_parts(clipped))
        for part_index, part in enumerate(parts):
            if part.is_empty or part.length == 0.0:
                continue
            _validate_line(part, edge_id)
            source_osm_id = str(data.get("osmid", key))
            projected_edges.append(
                ProjectedRoadEdge(
                    source_id=f"{edge_id}#{part_index}",
                    source_osm_id=source_osm_id,
                    source_u=u_id,
                    source_v=v_id,
                    coords_m=tuple((float(x), float(y)) for x, y, *_ in part.coords),
                )
            )

    if not projected_edges:
        raise SourceIntegrityError("road source has no edges intersecting the metric AOI")
    projected_edges.sort(key=lambda edge: edge.source_id)
    return ProjectedRoadSource(
        source_path=str(config.source_path.resolve()),
        source_sha256=actual_hash,
        source_crs=expected_crs.to_string(),
        target_crs=target_crs.to_string(),
        source_bbox_lonlat=source_bbox,
        aoi_bounds_m=tuple(float(value) for value in aoi_bounds),
        aoi_bbox_lonlat=tuple(float(value) for value in aoi_lonlat),
        nodes=projected_nodes,
        edges=tuple(projected_edges),
    )
