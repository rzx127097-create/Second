from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

import yaml

from problem2.scenarios.factory import build_synthetic_scenario


ROOT = Path(__file__).resolve().parents[2]
GRAPHML = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="x" for="node" attr.name="x" attr.type="double"/>
  <key id="y" for="node" attr.name="y" attr.type="double"/>
  <graph id="G" edgedefault="undirected">
    <node id="a"><data key="x">0.0</data><data key="y">0.0</data></node>
    <node id="b"><data key="x">0.0001</data><data key="y">0.0</data></node>
    <edge id="e" source="a" target="b"/>
  </graph>
</graphml>
"""


def test_factory_uses_declared_frozen_gis_source_when_configured(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    shutil.copytree(ROOT / "configs", config_dir)
    graphml = tmp_path / "roads.graphml"
    graphml.write_text(GRAPHML, encoding="utf-8")

    environment_path = config_dir / "environment.yaml"
    environment = yaml.safe_load(environment_path.read_text(encoding="utf-8"))
    environment["road"].update({
        "source": "frozen_gis",
        "source_status": "verified",
        "graphml_path": str(graphml),
        "origin_lonlat": [0.0, 0.0],
        "source_sha256": hashlib.sha256(graphml.read_bytes()).hexdigest(),
    })
    environment_path.write_text(yaml.safe_dump(environment, sort_keys=False), encoding="utf-8")
    scenario_path = config_dir / "scenarios.yaml"
    scenarios = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    scenarios.update({
        "source_kind": "frozen_gis",
        "dynamics_kind": "calibrated_reaction_diffusion_advection",
        "source_metadata_hash": "a" * 64,
    })
    scenario_path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding="utf-8")

    bundle = build_synthetic_scenario("s1", 0, config_dir=config_dir, scenario_id="train_001")

    assert set(bundle.road_graph.nodes) == {"a", "b"}
    assert bundle.cell_size_m == (30.0, 25.0)
    assert bundle.scenario_source_kind == "frozen_gis"
    assert bundle.source_metadata_hash == "a" * 64
