"""Diagnostic unlimited-supply condition.

This policy only emits actions.  It deliberately does not edit resource state;
the environment remains the single owner of pesticide accounting.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class UnlimitedSupplyBaseline:
    name = "unlimited_supply"

    def act(self, observations: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
        return {
            agent_id: "spray" if data.get("role") == "uav" else "hold"
            for agent_id, data in observations.items()
        }

    __call__ = act

