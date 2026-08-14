"""Build a small immutable metric road cache from an offline GraphML source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.road.graphml import GRAPHML_NS, load_graphml


def _component(graph, nodes: set[str]) -> list[set[str]]:
    remaining = set(nodes)
    result: list[set[str]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        current = {start}
        remaining.remove(start)
        while stack:
            node = stack.pop()
            for neighbour in graph.adjacency[node]:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    current.add(neighbour)
                    stack.append(neighbour)
        result.append(current)
    return result


def _write_graph(path: Path, nodes: dict[str, tuple[float, float]], edges: list[tuple[str, str, float]]) -> None:
    ET.register_namespace("", GRAPHML_NS)
    root = ET.Element(f"{{{GRAPHML_NS}}}graphml")
    ET.SubElement(root, f"{{{GRAPHML_NS}}}key", {"id": "x", "for": "node", "attr.name": "x", "attr.type": "double"})
    ET.SubElement(root, f"{{{GRAPHML_NS}}}key", {"id": "y", "for": "node", "attr.name": "y", "attr.type": "double"})
    ET.SubElement(root, f"{{{GRAPHML_NS}}}key", {"id": "length", "for": "edge", "attr.name": "length", "attr.type": "double"})
    graph = ET.SubElement(root, f"{{{GRAPHML_NS}}}graph", {"id": "frozen-road", "edgedefault": "undirected"})
    for node_id in sorted(nodes):
        node = ET.SubElement(graph, f"{{{GRAPHML_NS}}}node", {"id": node_id})
        for key, value in (("x", nodes[node_id][0]), ("y", nodes[node_id][1])):
            ET.SubElement(node, f"{{{GRAPHML_NS}}}data", {"key": key}).text = f"{value:.9f}"
    for index, (left, right, length) in enumerate(edges):
        edge = ET.SubElement(graph, f"{{{GRAPHML_NS}}}edge", {"id": f"e{index}", "source": left, "target": right})
        ET.SubElement(edge, f"{{{GRAPHML_NS}}}data", {"key": "length"}).text = f"{length:.9f}"
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def build(source: Path, output: Path, metadata_path: Path, *, origin_lon: float, origin_lat: float) -> dict[str, object]:
    graph, source_metadata = load_graphml(source, coordinate_mode="lonlat", origin_lonlat=(origin_lon, origin_lat))
    crop = {
        node for node, (x, y) in graph.nodes.items()
        if 0.0 <= x <= 500.0 and 0.0 <= y <= 300.0
    }
    components = _component(graph, crop)
    selected = max(components, key=lambda component: (len(component), tuple(sorted(component))))
    if len(selected) < 4:
        raise ValueError("the selected road crop has fewer than four connected nodes")
    min_x = min(graph.nodes[node][0] for node in selected)
    min_y = min(graph.nodes[node][1] for node in selected)
    span_x = max(graph.nodes[node][0] for node in selected) - min_x
    span_y = max(graph.nodes[node][1] for node in selected) - min_y
    scale = min(450.0 / max(span_x, 1e-9), 270.0 / max(span_y, 1e-9))
    nodes = {
        node: ((graph.nodes[node][0] - min_x) * scale, (graph.nodes[node][1] - min_y) * scale)
        for node in selected
    }
    edges: list[tuple[str, str, float]] = []
    for left in sorted(selected):
        for right, length in graph.adjacency[left].items():
            if right in selected and left < right:
                edges.append((left, right, float(length) * scale))
    _write_graph(output, nodes, edges)
    derived_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    _, derived_metadata = load_graphml(output, coordinate_mode="metric", origin_lonlat=(0.0, 0.0))
    payload = {
        "name": "frozen_road_source",
        "status": "observed",
        "ready": bool(derived_metadata["component_sizes"] == [len(selected)]),
        "source": {
            "path": str(source.resolve()),
            "sha256": source_metadata["source_sha256"],
            "coordinate_mode": "lonlat",
            "origin_lonlat": [origin_lon, origin_lat],
            "crop_metric_bbox": [0.0, 0.0, 500.0, 300.0],
        },
        "derivation": {
            "selection": "largest connected component within crop",
            "selected_node_count": len(selected),
            "coordinate_transform": {"translate_x_m": min_x, "translate_y_m": min_y, "uniform_scale": scale},
            "physical_extent_m": [300.0, 500.0],
        },
        "derived": {"path": str(output.resolve()), "sha256": derived_hash, "metadata": derived_metadata},
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--origin-lon", type=float, required=True)
    parser.add_argument("--origin-lat", type=float, required=True)
    args = parser.parse_args(argv)
    payload = build(args.source, args.output, args.metadata, origin_lon=args.origin_lon, origin_lat=args.origin_lat)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
