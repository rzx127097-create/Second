from __future__ import annotations

import pytest

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.domain.types import ResourceInvariantError


def make_resources() -> PesticideResources:
    return PesticideResources(
        uavs={
            "uav-1": UAVState(
                uav_id="uav-1", onboard_l=0.20, capacity_l=1.0, spray_flow_l_s=0.01
            )
        },
        vehicles={
            "vehicle-1": VehicleState(
                vehicle_id="vehicle-1",
                inventory_l=0.50,
                capacity_l=0.50,
                transfer_rate_l_s=0.02,
                service_cap_l=0.30,
            )
        },
    )


def test_transfer_is_limited_by_uav_gap_vehicle_inventory_and_service_cap() -> None:
    resources = make_resources()

    result = resources.transfer("uav-1", "vehicle-1", requested_l=0.80)

    assert result.amount_l == pytest.approx(0.30)
    assert result.uav_free_capacity_before_l == pytest.approx(0.80)
    assert resources.uav("uav-1").onboard_l == pytest.approx(0.50)
    assert resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.20)


def test_partial_transfer_can_finish_at_inventory_depletion_without_negative_values() -> None:
    resources = make_resources()
    resources.transfer("uav-1", "vehicle-1", requested_l=0.30)

    result = resources.transfer("uav-1", "vehicle-1", requested_l=0.30)

    assert result.amount_l == pytest.approx(0.20)
    assert resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.0)
    assert resources.uav("uav-1").onboard_l == pytest.approx(0.70)
    resources.assert_conservation()


def test_spray_consumption_uses_flow_rate_and_never_goes_below_zero() -> None:
    resources = make_resources()

    sprayed = resources.spray_step("uav-1", dt_s=10.0)

    assert sprayed.amount_l == pytest.approx(0.10)
    assert resources.uav("uav-1").onboard_l == pytest.approx(0.10)
    drained = resources.spray("uav-1", amount_l=0.20)
    assert drained.amount_l == pytest.approx(0.10)
    assert resources.uav("uav-1").onboard_l == pytest.approx(0.0)
    assert drained.pesticide_limited is True


def test_negative_resource_state_is_rejected() -> None:
    with pytest.raises(ResourceInvariantError):
        UAVState(uav_id="uav-1", onboard_l=-0.1, capacity_l=1.0, spray_flow_l_s=0.01)

    with pytest.raises(ResourceInvariantError):
        VehicleState(
            vehicle_id="vehicle-1",
            inventory_l=0.1,
            capacity_l=0.05,
            transfer_rate_l_s=0.02,
            service_cap_l=0.3,
        )
