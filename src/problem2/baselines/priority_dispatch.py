"""Urgency-first request dispatch shared by learned and planning policies."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class PriorityDispatchPolicy:
    name = "priority_dispatch"

    def select(
        self,
        requests: Iterable[Mapping[str, Any]],
        *,
        vehicle_inventory_l: float,
        service_cap_l: float,
    ) -> Mapping[str, Any] | None:
        if vehicle_inventory_l < 0 or service_cap_l < 0:
            raise ValueError("resource limits must be non-negative")
        feasible = [
            request
            for request in requests
            if float(request.get("requested_l", request.get("remaining_l", 0.0)))
            <= min(vehicle_inventory_l, service_cap_l) + 1e-12
        ]
        if not feasible:
            return None
        # Larger urgency wins; creation time and identifier make ties stable.
        return min(
            feasible,
            key=lambda request: (
                -float(request.get("urgency", 0.0)),
                int(request.get("created_step", 0)),
                str(request.get("request_id", "")),
            ),
        )

    dispatch = select

