"""Explicit preparation, transfer and completion phases for replenishment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from problem2.domain.requests import ReplenishmentRequest, RequestManager, RequestStatus
from problem2.domain.resources import PesticideResources


class ServicePhase(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    TRANSFERRING = "transferring"


@dataclass
class ServiceStateMachine:
    phase: ServicePhase = ServicePhase.IDLE
    request_id: str | None = None
    setup_remaining_s: float = 0.0

    @property
    def locked_uav_id(self) -> str | None:
        return self.request_id

    def reserve(
        self,
        manager: RequestManager,
        vehicle_id: str,
        step: int,
        setup_s: float,
    ) -> ReplenishmentRequest | None:
        if self.phase is not ServicePhase.IDLE:
            return None
        request = manager.reserve_next(vehicle_id, step)
        if request is None:
            return None
        self.request_id = request.request_id
        self.setup_remaining_s = max(0.0, setup_s)
        self.phase = ServicePhase.PREPARING
        return request

    def tick(
        self,
        manager: RequestManager,
        resources: PesticideResources,
        vehicle_id: str,
        dt_s: float,
        step: int,
    ) -> float:
        """Advance one service phase and return actual transferred volume."""
        if self.phase is ServicePhase.IDLE:
            return 0.0
        if self.phase is ServicePhase.PREPARING:
            self.setup_remaining_s = max(0.0, self.setup_remaining_s - dt_s)
            if self.setup_remaining_s <= 1e-12:
                assert self.request_id is not None
                manager.start_service(self.request_id, step)
                self.phase = ServicePhase.TRANSFERRING
            return 0.0
        assert self.request_id is not None
        request = manager.get(self.request_id)
        amount = min(
            request.remaining_l,
            resources.uav(request.uav_id).capacity_l - resources.uav(request.uav_id).onboard_l,
        )
        result = resources.transfer(request.uav_id, vehicle_id, amount)
        manager.apply_transfer(self.request_id, result.amount_l, step)
        if manager.get(self.request_id).status is RequestStatus.COMPLETED or result.amount_l <= 1e-12:
            self.phase = ServicePhase.IDLE
            self.request_id = None
            self.setup_remaining_s = 0.0
        return result.amount_l
