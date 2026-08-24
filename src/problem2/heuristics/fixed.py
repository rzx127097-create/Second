"""Resource-matched stationary-support comparison contract."""

from __future__ import annotations

from dataclasses import dataclass
import math
from time import perf_counter

from problem2.heuristics import ControllerDecision, DispatchObservation, hold_decision


@dataclass(frozen=True)
class FixedSupportController:
    support_node: int
    initial_inventory_l: float
    service_cap_l: float
    transfer_rate_lpm: float
    setup_time_s: float
    tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if isinstance(self.support_node, bool) or not isinstance(self.support_node, int) or self.support_node < 0:
            raise ValueError("support_node must be a nonnegative integer")
        for name in (
            "initial_inventory_l",
            "service_cap_l",
            "transfer_rate_lpm",
            "setup_time_s",
            "tolerance",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")

    def assert_resource_matched(
        self,
        *,
        mobile_initial_inventory_l: float,
        mobile_service_cap_l: float,
        mobile_transfer_rate_lpm: float,
        mobile_setup_time_s: float,
    ) -> None:
        pairs = (
            (self.initial_inventory_l, mobile_initial_inventory_l),
            (self.service_cap_l, mobile_service_cap_l),
            (self.transfer_rate_lpm, mobile_transfer_rate_lpm),
            (self.setup_time_s, mobile_setup_time_s),
        )
        if any(
            not math.isfinite(float(observed))
            or abs(float(expected) - float(observed)) > self.tolerance
            for expected, observed in pairs
        ):
            raise ValueError("fixed support must remain resource-matched to mobile support")

    def decide(self, observation: DispatchObservation) -> ControllerDecision:
        started = perf_counter()
        if observation.active_request_id is not None:
            if observation.selected_service_node != self.support_node:
                raise ValueError("fixed support cannot continue a dispatch at another node")
            return ControllerDecision(
                int(observation.active_sampled_slot),
                observation.active_request_id,
                self.support_node,
                0.0,
                perf_counter() - started,
            )
        eligible = []
        for request in observation.requests:
            transferable = min(
                request.requested_l,
                max(0.0, request.usable_capacity_l - request.pesticide_l),
                self.service_cap_l,
                observation.vehicle.inventory_l,
            )
            if (
                self.support_node in request.service_nodes
                and transferable > observation.tolerance
            ):
                eligible.append(request)
        if not eligible:
            return hold_decision(perf_counter() - started)
        selected = min(
            eligible,
            key=lambda item: (item.created_step, item.uav_id, item.request_id),
        )
        return ControllerDecision(
            selected.slot + 1,
            selected.request_id,
            self.support_node,
            0.0,
            perf_counter() - started,
        )


__all__ = ["FixedSupportController"]
