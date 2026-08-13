from __future__ import annotations

import pytest

from problem2.demand.eta import eta_seconds
from problem2.demand.urgency import urgency_score
from problem2.road.projection import LocalMetricProjection


def test_local_projection_returns_metre_scale_for_one_degree_latitude() -> None:
    projection = LocalMetricProjection((120.0, 30.0))
    x, y = projection.project((120.0, 31.0))
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(111_195.08, rel=1e-5)
    assert projection.distance_m((120.0, 30.0), (120.0, 31.0)) == pytest.approx(y)


def test_eta_and_urgency_are_physical_and_monotonic() -> None:
    assert eta_seconds(100.0, 10.0) == pytest.approx(10.0)
    assert urgency_score(0.0) == float("inf")
    assert urgency_score(1.0, eta_s=20.0) > urgency_score(1.0, eta_s=5.0)
    with pytest.raises(ValueError):
        eta_seconds(1.0, 0.0)

