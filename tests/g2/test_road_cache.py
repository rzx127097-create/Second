from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from problem2.config import ScaleConfig, load_g2_config
from problem2.road.cache import (
    CacheValidationError,
    RoadCacheExpectation,
    load_road_cache,
    write_road_cache,
)
from problem2.road.models import ProjectedRoadEdge, ProjectedRoadSource
from problem2.road.raster import rasterize_road_source


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
GENERATOR_SHA = "B" * 64
GENERATOR_COMMIT = "c" * 40


def _source() -> ProjectedRoadSource:
    return ProjectedRoadSource(
        source_path="fixture.graphml",
        source_sha256="A" * 64,
        source_crs="EPSG:4326",
        target_crs="EPSG:32643",
        source_bbox_lonlat=(0.0, 0.0, 1.0, 1.0),
        aoi_bounds_m=(0.0, 0.0, 100.0, 100.0),
        aoi_bbox_lonlat=(0.0, 0.0, 1.0, 1.0),
        nodes={},
        edges=(
            ProjectedRoadEdge(
                "edge-0",
                "100",
                "n0",
                "n1",
                ((5.0, 95.0), (25.0, 75.0)),
            ),
        ),
    )


@pytest.fixture
def cache_pair(tmp_path: Path):
    source = _source()
    graph = rasterize_road_source(source, ScaleConfig("fixture", (10, 10), 10))
    paths = write_road_cache(
        graph,
        source,
        CONFIG,
        tmp_path,
        generator_commit=GENERATOR_COMMIT,
        generator_sha256=GENERATOR_SHA,
    )
    expectation = RoadCacheExpectation(
        scale_id="fixture",
        source_sha256=source.source_sha256,
        source_crs=source.source_crs,
        target_crs=source.target_crs,
        aoi_bounds_m=source.aoi_bounds_m,
        grid_shape=graph.grid_shape,
        preprocess_version=CONFIG.preprocess_version,
        generator_commit=GENERATOR_COMMIT,
        generator_sha256=GENERATOR_SHA,
    )
    return paths, expectation, graph


def test_round_trip_preserves_arrays_mappings_repairs_and_provenance(cache_pair) -> None:
    (npz_path, metadata_path), expectation, original = cache_pair

    loaded = load_road_cache(npz_path, metadata_path, expectation)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    np.testing.assert_array_equal(loaded.edges, original.edges)
    np.testing.assert_array_equal(loaded.action_mask, original.action_mask)
    assert loaded.source_edge_to_cells == original.source_edge_to_cells
    assert loaded.repairs == original.repairs
    assert metadata["generator"]["git_commit"] == GENERATOR_COMMIT
    assert metadata["generator"]["sha256"] == GENERATOR_SHA
    assert set(metadata["dependencies"]) == {
        "networkx",
        "numpy",
        "pyproj",
        "PyYAML",
        "shapely",
    }


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source_sha256", "D" * 64, "source_sha256"),
        ("source_crs", "EPSG:3857", "source_crs"),
        ("target_crs", "EPSG:3857", "target_crs"),
        ("aoi_bounds_m", (0.0, 0.0, 90.0, 100.0), "aoi_bounds_m"),
        ("grid_shape", (9, 10), "grid_shape"),
        ("preprocess_version", "g2-road-v2", "preprocess_version"),
        ("generator_commit", "d" * 40, "generator_commit"),
        ("generator_sha256", "E" * 64, "generator_sha256"),
    ],
)
def test_cache_rejects_changed_expectation(
    cache_pair, field: str, replacement, message: str
) -> None:
    (npz_path, metadata_path), expectation, _ = cache_pair
    changed = replace(expectation, **{field: replacement})

    with pytest.raises(CacheValidationError, match=message):
        load_road_cache(npz_path, metadata_path, changed)


def test_cache_rejects_array_tampering(cache_pair) -> None:
    (npz_path, metadata_path), expectation, _ = cache_pair
    with np.load(npz_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["edge_lengths_m"][0] = 999.0
    with npz_path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    with pytest.raises(CacheValidationError, match="content checksum"):
        load_road_cache(npz_path, metadata_path, expectation)


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "crs", "EPSG:3857", "source_crs"),
        ("generator", "git_commit", "d" * 40, "generator_commit"),
    ],
)
def test_cache_rejects_provenance_metadata_tampering(
    cache_pair,
    section: str,
    field: str,
    replacement: str,
    message: str,
) -> None:
    (npz_path, metadata_path), expectation, _ = cache_pair
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata[section][field] = replacement
    metadata_path.write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(CacheValidationError, match=message):
        load_road_cache(npz_path, metadata_path, expectation)


def test_semantic_content_checksum_is_reproducible(tmp_path: Path) -> None:
    source = _source()
    graph = rasterize_road_source(source, ScaleConfig("fixture", (10, 10), 10))
    first = write_road_cache(
        graph, source, CONFIG, tmp_path / "first", GENERATOR_COMMIT, GENERATOR_SHA
    )
    second = write_road_cache(
        graph, source, CONFIG, tmp_path / "second", GENERATOR_COMMIT, GENERATOR_SHA
    )

    first_metadata = json.loads(first[1].read_text(encoding="utf-8"))
    second_metadata = json.loads(second[1].read_text(encoding="utf-8"))

    assert first_metadata["content_checksum"] == second_metadata["content_checksum"]
    assert first_metadata["adjacency_checksum"] == second_metadata["adjacency_checksum"]


def test_writer_rejects_checksum_consistent_but_semantically_wrong_action_mask(
    tmp_path: Path,
) -> None:
    source = _source()
    graph = rasterize_road_source(source, ScaleConfig("fixture", (10, 10), 10))
    wrong_mask = graph.action_mask.copy()
    wrong_mask[:] = False
    invalid_graph = replace(graph, action_mask=wrong_mask)

    with pytest.raises(CacheValidationError, match="action_mask"):
        write_road_cache(
            invalid_graph,
            source,
            CONFIG,
            tmp_path,
            GENERATOR_COMMIT,
            GENERATOR_SHA,
        )
