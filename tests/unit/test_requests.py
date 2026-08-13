from __future__ import annotations

import pytest

from problem2.domain.requests import RequestManager, RequestStatus


def test_duplicate_open_request_returns_existing_request() -> None:
    manager = RequestManager()

    first = manager.create_request("uav-1", requested_l=0.60, step=3)
    duplicate = manager.create_request("uav-1", requested_l=0.20, step=4)

    assert duplicate.request_id == first.request_id
    assert len(manager) == 1
    assert duplicate.requested_l == pytest.approx(0.60)


def test_request_lifecycle_and_partial_service() -> None:
    manager = RequestManager()
    request = manager.create_request("uav-1", requested_l=0.60, step=3)

    reserved = manager.reserve_next("vehicle-1", current_step=4)
    assert reserved.request_id == request.request_id
    assert reserved.status is RequestStatus.RESERVED
    manager.start_service(request.request_id, step=5)
    manager.apply_transfer(request.request_id, amount_l=0.25, step=6)
    assert manager.get(request.request_id).status is RequestStatus.PARTIALLY_SATISFIED
    assert manager.get(request.request_id).remaining_l == pytest.approx(0.35)
    manager.reopen(request.request_id, step=6)
    manager.reserve_next("vehicle-1", current_step=7)
    manager.start_service(request.request_id, step=7)
    manager.apply_transfer(request.request_id, amount_l=0.35, step=8)

    completed = manager.get(request.request_id)
    assert completed.status is RequestStatus.COMPLETED
    assert completed.remaining_l == pytest.approx(0.0)
    assert completed.completed_step == 8


def test_fifo_reservation_skips_reserved_request_and_ties_break_by_request_id() -> None:
    manager = RequestManager()
    first = manager.create_request("uav-2", requested_l=0.10, step=1)
    second = manager.create_request("uav-1", requested_l=0.10, step=1)
    first_reserved = manager.reserve_next("vehicle-1", current_step=2)
    next_request = manager.reserve_next("vehicle-2", current_step=2)

    assert first_reserved.request_id == second.request_id
    assert next_request.request_id == first.request_id


def test_invalid_lifecycle_transition_is_rejected() -> None:
    manager = RequestManager()
    request = manager.create_request("uav-1", requested_l=0.30, step=1)

    with pytest.raises(ValueError, match="serving"):
        manager.apply_transfer(request.request_id, amount_l=0.10, step=2)

    manager.reserve_next("vehicle-1", current_step=2)
    with pytest.raises(ValueError, match="already"):
        manager.reserve_next("vehicle-1", current_step=3)
