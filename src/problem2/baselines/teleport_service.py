"""Diagnostic zero-travel service condition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class TeleportServiceBaseline:
    name = "teleport_service"

    def act(self, observations: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
        return {
            agent_id: "spray" if data.get("role") == "uav" else "teleport_service"
            for agent_id, data in observations.items()
        }

    __call__ = act

