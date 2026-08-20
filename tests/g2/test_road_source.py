from __future__ import annotations

from dataclasses import replace
import hashlib
import math
from pathlib import Path

import pytest

from problem2.config import load_g2_config
from problem2.road.source import SourceIntegrityError, load_projected_road_source


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g2_deterministic.yaml"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiny_road.graphml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


@pytest.fixture
def tiny_config():
    return replace(
        load_g2_config(CONFIG_PATH),
        source_path=FIXTURE_PATH,
        source_sha256=_sha256(FIXTURE_PATH),
    )


def test_projects_known_lonlat_offset_to_metric_distance(tiny_config) -> None:
    source = load_projected_road_source(tiny_config)

    center = source.nodes["center"]
    east = source.nodes["east"]
    distance = math.hypot(east.x_m - center.x_m, east.y_m - center.y_m)

    assert distance == pytest.approx(99.8648, abs=0.15)
    assert source.source_crs == "EPSG:4326"
    assert source.target_crs == "EPSG:32643"


def test_uses_wkt_and_endpoint_fallback_geometries(tiny_config) -> None:
    source = load_projected_road_source(tiny_config)
    by_osmid = {edge.source_osm_id: edge for edge in source.edges}

    assert len(by_osmid["101"].coords_m) == 3
    assert len(by_osmid["102"].coords_m) == 2


def test_keeps_edge_that_crosses_aoi_with_endpoints_outside(tiny_config) -> None:
    source = load_projected_road_source(tiny_config)
    crossing = next(edge for edge in source.edges if edge.source_osm_id == "103")
    min_x, _, max_x, _ = source.aoi_bounds_m

    assert crossing.coords_m[0][0] == pytest.approx(min_x, abs=1e-6)
    assert crossing.coords_m[-1][0] == pytest.approx(max_x, abs=1e-6)
    assert "far_west" not in source.nodes
    assert "far_east" not in source.nodes


def test_rejects_source_hash_mismatch(tiny_config) -> None:
    with pytest.raises(SourceIntegrityError, match="SHA-256"):
        load_projected_road_source(
            replace(tiny_config, source_sha256="0" * 64)
        )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("EPSG:4326", "EPSG:3857", "CRS"),
        ("73.0351433", "nan", "finite"),
        (
            "LINESTRING (73.0351433 26.2967719, 73.0356433 26.2970719, 73.0361433 26.2967719)",
            "LINESTRING (invalid)",
            "geometry",
        ),
    ],
)
def test_rejects_invalid_source_data(
    tmp_path: Path, tiny_config, old: str, new: str, message: str
) -> None:
    mutated = tmp_path / "invalid.graphml"
    mutated.write_text(
        FIXTURE_PATH.read_text(encoding="utf-8").replace(old, new, 1),
        encoding="utf-8",
    )
    config = replace(
        tiny_config,
        source_path=mutated,
        source_sha256=_sha256(mutated),
    )

    with pytest.raises(SourceIntegrityError, match=message):
        load_projected_road_source(config)
