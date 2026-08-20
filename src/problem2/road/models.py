from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ProjectedRoadNode:
    source_id: str
    lon: float
    lat: float
    x_m: float
    y_m: float


@dataclass(frozen=True)
class ProjectedRoadEdge:
    source_id: str
    source_osm_id: str
    source_u: str
    source_v: str
    coords_m: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ProjectedRoadSource:
    source_path: str
    source_sha256: str
    source_crs: str
    target_crs: str
    source_bbox_lonlat: tuple[float, float, float, float]
    aoi_bounds_m: tuple[float, float, float, float]
    aoi_bbox_lonlat: tuple[float, float, float, float]
    nodes: Mapping[str, ProjectedRoadNode]
    edges: tuple[ProjectedRoadEdge, ...]
