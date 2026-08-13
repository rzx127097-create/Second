"""Small dependency-free longitude/latitude to local metre projection.

The simulator only needs a local metric CRS.  The equirectangular projection
used here is deterministic and accurate for the small agricultural areas this
package models; callers can replace it with a GIS CRS at the data-ingestion
boundary without changing graph code.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, radians
from typing import Iterable

EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class LocalMetricProjection:
    """Local equirectangular projection centred on ``origin_lonlat``."""

    origin_lonlat: tuple[float, float]

    def __post_init__(self) -> None:
        lon, lat = self.origin_lonlat
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("origin longitude/latitude is out of range")

    @property
    def _latitude_scale(self) -> float:
        return cos(radians(self.origin_lonlat[1]))

    def project(self, lonlat: tuple[float, float]) -> tuple[float, float]:
        lon, lat = lonlat
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("longitude/latitude is out of range")
        lon0, lat0 = self.origin_lonlat
        x = radians(lon - lon0) * EARTH_RADIUS_M * self._latitude_scale
        y = radians(lat - lat0) * EARTH_RADIUS_M
        return (x, y)

    def unproject(self, xy: tuple[float, float]) -> tuple[float, float]:
        x, y = xy
        lon0, lat0 = self.origin_lonlat
        if abs(self._latitude_scale) < 1e-15:
            raise ValueError("projection is undefined at a pole")
        lon = lon0 + x / (EARTH_RADIUS_M * self._latitude_scale) * 180.0 / pi
        lat = lat0 + y / EARTH_RADIUS_M * 180.0 / pi
        return (lon, lat)

    def distance_m(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        ax, ay = self.project(a)
        bx, by = self.project(b)
        return ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5

    def project_many(self, points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
        return [self.project(point) for point in points]


def project_lonlat(
    lonlat: tuple[float, float], origin_lonlat: tuple[float, float]
) -> tuple[float, float]:
    """Project one ``(longitude, latitude)`` pair into metres."""

    return LocalMetricProjection(origin_lonlat).project(lonlat)


# A concise alias useful to callers that prefer the generic name.
Projection = LocalMetricProjection
