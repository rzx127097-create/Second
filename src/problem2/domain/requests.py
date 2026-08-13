"""Deterministic replenishment-request lifecycle and assignment rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RequestStatus(str, Enum):
    OPEN = "open"
    RESERVED = "reserved"
    SERVING = "serving"
    PARTIALLY_SATISFIED = "partially_satisfied"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNSATISFIED = "unsatisfied"


@dataclass
class ReplenishmentRequest:
    request_id: str
    uav_id: str
    requested_l: float
    created_step: int
    remaining_l: float
    status: RequestStatus = RequestStatus.OPEN
    reserved_vehicle_id: str | None = None
    completed_step: int | None = None
    close_reason: str | None = None


class RequestManager:
    def __init__(self) -> None:
        self._requests: dict[str, ReplenishmentRequest] = {}
        self._active_by_uav: dict[str, str] = {}
        self._next_id = 1

    def __len__(self) -> int:
        return len(self._requests)

    def get(self, request_id: str) -> ReplenishmentRequest:
        return self._requests[request_id]

    def create_request(self, uav_id: str, requested_l: float, step: int) -> ReplenishmentRequest:
        if requested_l <= 0:
            raise ValueError("requested_l must be positive")
        existing_id = self._active_by_uav.get(uav_id)
        if existing_id is not None:
            existing = self._requests[existing_id]
            if existing.status not in {RequestStatus.COMPLETED, RequestStatus.CANCELLED, RequestStatus.UNSATISFIED}:
                return existing
        request_id = f"req-{self._next_id:06d}"
        self._next_id += 1
        request = ReplenishmentRequest(request_id, uav_id, requested_l, step, requested_l)
        self._requests[request_id] = request
        self._active_by_uav[uav_id] = request_id
        return request

    def reserve_next(self, vehicle_id: str, current_step: int) -> ReplenishmentRequest | None:
        busy = [r for r in self._requests.values() if r.reserved_vehicle_id == vehicle_id and r.status in {RequestStatus.RESERVED, RequestStatus.SERVING}]
        if busy:
            raise ValueError("vehicle already has an active request")
        eligible = [r for r in self._requests.values() if r.status is RequestStatus.OPEN]
        if not eligible:
            return None
        request = min(eligible, key=lambda r: (r.created_step, r.uav_id, r.request_id))
        request.status = RequestStatus.RESERVED
        request.reserved_vehicle_id = vehicle_id
        return request

    def start_service(self, request_id: str, step: int) -> None:
        request = self.get(request_id)
        if request.status is not RequestStatus.RESERVED:
            raise ValueError("request must be reserved before serving")
        request.status = RequestStatus.SERVING

    def apply_transfer(self, request_id: str, amount_l: float, step: int) -> ReplenishmentRequest:
        if amount_l < 0:
            raise ValueError("amount_l must be non-negative")
        request = self.get(request_id)
        if request.status is not RequestStatus.SERVING:
            raise ValueError("request must be serving before transfer")
        if amount_l > request.remaining_l + 1e-12:
            raise ValueError("transfer exceeds request remaining amount")
        request.remaining_l = max(0.0, request.remaining_l - amount_l)
        if request.remaining_l <= 1e-12:
            request.status = RequestStatus.COMPLETED
            request.completed_step = step
            request.close_reason = "fulfilled"
            self._active_by_uav.pop(request.uav_id, None)
        else:
            request.status = RequestStatus.PARTIALLY_SATISFIED
        return request

    def reopen(self, request_id: str, step: int) -> ReplenishmentRequest:
        request = self.get(request_id)
        if request.status is not RequestStatus.PARTIALLY_SATISFIED:
            raise ValueError("only a partially satisfied request can be reopened")
        request.status = RequestStatus.OPEN
        request.reserved_vehicle_id = None
        return request

    def cancel(self, request_id: str, reason: str, step: int) -> None:
        request = self.get(request_id)
        if request.status in {RequestStatus.COMPLETED, RequestStatus.CANCELLED, RequestStatus.UNSATISFIED}:
            raise ValueError("request is already closed")
        request.status = RequestStatus.CANCELLED
        request.close_reason = reason
        self._active_by_uav.pop(request.uav_id, None)

    def mark_unsatisfied(self, request_id: str, reason: str, step: int) -> None:
        request = self.get(request_id)
        if request.status in {RequestStatus.COMPLETED, RequestStatus.CANCELLED, RequestStatus.UNSATISFIED}:
            raise ValueError("request is already closed")
        request.status = RequestStatus.UNSATISFIED
        request.close_reason = reason
        self._active_by_uav.pop(request.uav_id, None)
