"""Offline GraphML ingestion with deterministic metric-road metadata."""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from .graph import RoadGraph
from .projection import LocalMetricProjection


GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"


def _tag(name: str) -> str:
    return f"{{{GRAPHML_NS}}}{name}"


def _data_map(element: ET.Element, keys: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for data in element.findall(_tag("data")):
        key = str(data.attrib.get("key", ""))
        name = keys.get(key, key)
        result[name] = (data.text or "").strip()
    return result


def _number(value: str, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"GraphML {field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"GraphML {field} must be finite")
    return result


def _adjacency_checksum(graph: RoadGraph) -> str:
    lines = [
        f"{source}|{target}|{weight:.12g}"
        for source in sorted(graph.adjacency)
        for target, weight in sorted(graph.adjacency[source].items())
    ]
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _component_sizes(graph: RoadGraph) -> list[int]:
    """Return connected-component sizes with one traversal per component."""

    remaining = set(graph.nodes)
    sizes: list[int] = []
    while remaining:
        start = min(remaining)
        component = graph.component(start)
        sizes.append(len(component))
        remaining.difference_update(component)
    return sorted(sizes, reverse=True)


def load_graphml(
    path: str | Path,
    *,
    coordinate_mode: str = "lonlat",
    origin_lonlat: tuple[float, float] | None = None,
    directed_policy: str = "undirected",
    bbox_lonlat: tuple[float, float, float, float] | None = None,
) -> tuple[RoadGraph, dict[str, Any]]:
    """Load a local GraphML road file without network access.

    ``RoadGraph`` stores an undirected graph.  A directed GraphML source is
    therefore accepted only with the explicit ``undirected`` policy, which
    adds both directions and is recorded in the returned metadata.
    """

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"GraphML road source does not exist: {source}")
    if coordinate_mode not in {"lonlat", "metric"}:
        raise ValueError("coordinate_mode must be 'lonlat' or 'metric'")
    if directed_policy != "undirected":
        raise ValueError("RoadGraph currently supports only directed_policy='undirected'")
    if coordinate_mode == "lonlat" and origin_lonlat is None:
        raise ValueError("origin_lonlat is required for lonlat GraphML input")
    if bbox_lonlat is not None:
        if len(bbox_lonlat) != 4 or bbox_lonlat[0] > bbox_lonlat[2] or bbox_lonlat[1] > bbox_lonlat[3]:
            raise ValueError("bbox_lonlat must be (min_lon, min_lat, max_lon, max_lat)")

    root = ET.parse(source).getroot()
    keys = {
        str(item.attrib.get("id")): str(item.attrib.get("attr.name", item.attrib.get("id", "")))
        for item in root.findall(_tag("key"))
    }
    graph_element = root.find(_tag("graph"))
    if graph_element is None:
        raise ValueError("GraphML source has no graph element")

    projection = LocalMetricProjection(origin_lonlat) if coordinate_mode == "lonlat" else None
    raw_points: dict[str, tuple[float, float]] = {}
    for node in graph_element.findall(_tag("node")):
        node_id = str(node.attrib.get("id", ""))
        if not node_id:
            raise ValueError("GraphML node id cannot be empty")
        fields = _data_map(node, keys)
        if "x" not in fields or "y" not in fields:
            raise ValueError(f"GraphML node {node_id!r} is missing x/y coordinates")
        x, y = _number(fields["x"], "node x"), _number(fields["y"], "node y")
        if bbox_lonlat is not None and not (
            bbox_lonlat[0] <= x <= bbox_lonlat[2] and bbox_lonlat[1] <= y <= bbox_lonlat[3]
        ):
            continue
        raw_points[node_id] = (x, y)
    if not raw_points:
        raise ValueError("GraphML source contains no nodes after bbox filtering")

    nodes = {
        node_id: projection.project(point) if projection is not None else point
        for node_id, point in raw_points.items()
    }
    edges: list[tuple[str, str, float]] = []
    for edge in graph_element.findall(_tag("edge")):
        left, right = str(edge.attrib.get("source", "")), str(edge.attrib.get("target", ""))
        if left not in nodes or right not in nodes or left == right:
            continue
        fields = _data_map(edge, keys)
        weight = _number(fields["length"], "edge length") if fields.get("length") else math.hypot(
            nodes[right][0] - nodes[left][0], nodes[right][1] - nodes[left][1]
        )
        if weight <= 0:
            raise ValueError(f"GraphML edge {left!r}->{right!r} has non-positive length")
        edges.append((left, right, weight))
    if not edges:
        raise ValueError("GraphML source contains no usable edges after filtering")
    graph = RoadGraph.from_edges(nodes, edges)
    component_sizes = _component_sizes(graph)
    all_lonlat = list(raw_points.values())
    metadata: dict[str, Any] = {
        "source_path": str(source),
        "source_sha256": sha256(source.read_bytes()).hexdigest(),
        "coordinate_mode": coordinate_mode,
        "source_crs": "EPSG:4326" if coordinate_mode == "lonlat" else "metric",
        "origin_lonlat": list(origin_lonlat) if origin_lonlat is not None else None,
        "directed_policy": directed_policy,
        "bbox_lonlat": [
            min(point[0] for point in all_lonlat),
            min(point[1] for point in all_lonlat),
            max(point[0] for point in all_lonlat),
            max(point[1] for point in all_lonlat),
        ] if coordinate_mode == "lonlat" else None,
        "node_count": len(graph.nodes),
        "edge_count": len(edges),
        "component_sizes": component_sizes,
        "adjacency_checksum": _adjacency_checksum(graph),
    }
    return graph, metadata


__all__ = ["load_graphml"]
