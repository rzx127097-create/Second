from __future__ import annotations

from problem2.demand.candidate_slots import candidate_slots
from problem2.demand.feasibility import is_serviceable
from problem2.demand.rendezvous import RendezvousPoint


def test_candidate_slots_are_sorted_and_include_only_reachable_road_nodes() -> None:
    points = [
        RendezvousPoint("p2", "road-2", (2.0, 0.0), 4.0),
        RendezvousPoint("p1", "road-1", (1.0, 0.0), 2.0),
    ]
    result = candidate_slots(points, uav_position=(0.0, 0.0), max_radius_m=3.0)
    assert [point.point_id for point in result] == ["p1"]


def test_service_feasibility_requires_radius_and_positive_inventory() -> None:
    assert is_serviceable(distance_m=3.0, rendezvous_radius_m=5.0, vehicle_inventory_l=0.1)
    assert not is_serviceable(distance_m=6.0, rendezvous_radius_m=5.0, vehicle_inventory_l=0.1)
    assert not is_serviceable(distance_m=3.0, rendezvous_radius_m=5.0, vehicle_inventory_l=0.0)
