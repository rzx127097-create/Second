from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from problem2.road.graphml import load_graphml


GRAPHML = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="x" for="node" attr.name="x" attr.type="double"/>
  <key id="y" for="node" attr.name="y" attr.type="double"/>
  <key id="length" for="edge" attr.name="length" attr.type="double"/>
  <graph id="G" edgedefault="directed">
    <node id="a"><data key="x">0.0</data><data key="y">0.0</data></node>
    <node id="b"><data key="x">0.001</data><data key="y">0.0</data></node>
    <node id="c"><data key="x">0.001</data><data key="y">0.001</data></node>
    <edge id="e1" source="a" target="b"><data key="length">10.0</data></edge>
    <edge id="e2" source="b" target="c"/>
  </graph>
</graphml>
"""


def test_graphml_loader_projects_coordinates_and_records_source_metadata(tmp_path: Path) -> None:
    source = tmp_path / "roads.graphml"
    source.write_text(GRAPHML, encoding="utf-8")

    graph, metadata = load_graphml(source, origin_lonlat=(0.0, 0.0))

    assert set(graph.nodes) == {"a", "b", "c"}
    assert graph.edge_weight("a", "b") == pytest.approx(10.0)
    assert graph.edge_weight("b", "a") == pytest.approx(10.0)
    assert graph.edge_weight("b", "c") == pytest.approx(111.2, rel=0.02)
    assert metadata["coordinate_mode"] == "lonlat"
    assert metadata["directed_policy"] == "undirected"
    assert metadata["node_count"] == 3
    assert metadata["edge_count"] == 2
    assert metadata["component_sizes"] == [3]
    assert metadata["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(metadata["adjacency_checksum"]) == 64


def test_graphml_loader_requires_explicit_origin_for_lonlat(tmp_path: Path) -> None:
    source = tmp_path / "roads.graphml"
    source.write_text(GRAPHML, encoding="utf-8")

    with pytest.raises(ValueError, match="origin_lonlat"):
        load_graphml(source)


def test_graphml_loader_rejects_missing_source_and_unknown_coordinate_mode(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_graphml(tmp_path / "missing.graphml", origin_lonlat=(0.0, 0.0))

    source = tmp_path / "roads.graphml"
    source.write_text(GRAPHML, encoding="utf-8")
    with pytest.raises(ValueError, match="coordinate_mode"):
        load_graphml(source, coordinate_mode="pixel", origin_lonlat=(0.0, 0.0))


def test_road_source_audit_cli_emits_metadata(tmp_path: Path) -> None:
    source = tmp_path / "roads.graphml"
    source.write_text(GRAPHML, encoding="utf-8")
    report_path = tmp_path / "road-audit.json"

    from scripts.audit_road_source import main

    assert main([
        str(source),
        "--origin-lon",
        "0",
        "--origin-lat",
        "0",
        "--report",
        str(report_path),
    ]) == 0
    import json

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ready"] is True
    assert payload["metadata"]["node_count"] == 3
