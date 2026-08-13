from __future__ import annotations

import pytest

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState


def test_transfer_preserves_global_pesticide_total() -> None:
    resources = PesticideResources(
        uavs={
            "uav-1": UAVState(
                uav_id="uav-1", onboard_l=0.25, capacity_l=1.0, spray_flow_l_s=0.01
            ),
            "uav-2": UAVState(
                uav_id="uav-2", onboard_l=0.40, capacity_l=1.0, spray_flow_l_s=0.01
            ),
        },
        vehicles={
            "vehicle-1": VehicleState(
                vehicle_id="vehicle-1",
                inventory_l=0.60,
                capacity_l=0.60,
                transfer_rate_l_s=0.02,
                service_cap_l=0.50,
            )
        },
    )
    initial_total = resources.total_pesticide_l

    resources.transfer("uav-1", "vehicle-1", requested_l=0.50)
    resources.transfer("uav-2", "vehicle-1", requested_l=0.30)

    assert resources.total_pesticide_l == pytest.approx(initial_total)
    resources.spray("uav-1", amount_l=0.10)
    resources.spray("uav-2", amount_l=0.20)
    resources.assert_conservation()
    assert resources.total_pesticide_l == pytest.approx(initial_total - 0.30)


def test_conservation_audit_detects_external_mutation() -> None:
    resources = PesticideResources(
        uavs={
            "uav-1": UAVState(
                uav_id="uav-1", onboard_l=0.20, capacity_l=1.0, spray_flow_l_s=0.01
            )
        },
        vehicles={
            "vehicle-1": VehicleState(
                vehicle_id="vehicle-1",
                inventory_l=0.30,
                capacity_l=0.30,
                transfer_rate_l_s=0.02,
                service_cap_l=0.20,
            )
        },
    )
    resources.vehicle("vehicle-1").inventory_l = 0.10

    with pytest.raises(AssertionError, match="conservation"):
        resources.assert_conservation()
