from __future__ import annotations

import pytest

from problem2.domain import UavState
from problem2.resources.ledger import (
    ResourceInvariantError,
    apply_spray,
    apply_transfer,
    assert_conserved,
    new_ledger,
)


def _uav(pesticide_l: float) -> UavState:
    return UavState("u0", x_m=0.0, y_m=0.0, pesticide_l=pesticide_l)


def test_partial_spray_and_transfer_preserve_total() -> None:
    initial = _uav(0.01)
    ledger = new_ledger([initial], vehicle_inventory_l=0.5)

    sprayed_uav, ledger, spray = apply_spray(initial, ledger, requested_l=0.02)
    filled_uav, inventory, ledger, transfer = apply_transfer(
        sprayed_uav,
        vehicle_inventory_l=0.5,
        ledger=ledger,
        service_cap_l=1.08,
        usable_capacity_l=1.08,
    )

    assert dict(spray.payload)["delta_l"] == pytest.approx(0.01)
    assert dict(transfer.payload)["delta_l"] == pytest.approx(0.5)
    assert filled_uav.pesticide_l == pytest.approx(0.5)
    assert inventory == 0.0
    assert ledger.cumulative_sprayed_l == pytest.approx(0.01)
    assert ledger.cumulative_transferred_l == pytest.approx(0.5)
    assert_conserved([filled_uav], inventory, ledger, tolerance=1e-9)


def test_full_spray_debits_exact_requested_amount() -> None:
    initial = _uav(1.08)
    ledger = new_ledger([initial], 20.0)

    sprayed, ledger, _ = apply_spray(initial, ledger, requested_l=0.02)

    assert sprayed.pesticide_l == pytest.approx(1.06)
    assert_conserved([sprayed], 20.0, ledger, 1e-9)


@pytest.mark.parametrize(
    ("vehicle_inventory_l", "service_cap_l", "usable_capacity_l", "message"),
    [
        (-0.1, 1.08, 1.08, "vehicle_inventory_l"),
        (1.0, float("nan"), 1.08, "service_cap_l"),
        (1.0, 1.08, 0.5, "capacity"),
    ],
)
def test_invalid_transfer_rejects_without_mutating_inputs(
    vehicle_inventory_l: float,
    service_cap_l: float,
    usable_capacity_l: float,
    message: str,
) -> None:
    before = _uav(0.75)
    ledger = new_ledger([before], 1.0)

    with pytest.raises(ResourceInvariantError, match=message):
        apply_transfer(
            before,
            vehicle_inventory_l,
            ledger,
            service_cap_l,
            usable_capacity_l,
        )

    assert before.pesticide_l == 0.75
    assert ledger.cumulative_transferred_l == 0.0


def test_conservation_detects_unlogged_resource_change() -> None:
    initial = _uav(1.0)
    ledger = new_ledger([initial], 2.0)

    with pytest.raises(ResourceInvariantError, match="conservation"):
        assert_conserved([_uav(0.9)], 2.0, ledger, tolerance=1e-9)
