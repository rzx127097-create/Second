"""Serializable, method-neutral update and validity diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DIAGNOSTICS_SCHEMA_VERSION = "g5-diagnostics-v1"


class DiagnosticCounters:
    def __init__(self, counters: Mapping[str, int] | None = None) -> None:
        self._counters: dict[str, int] = {}
        if counters is not None:
            self.load_state_dict({"schema_version": DIAGNOSTICS_SCHEMA_VERSION, "counters": counters})

    def increment(self, name: str, amount: int = 1) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("diagnostic name must be non-empty text")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("diagnostic increment must be a positive integer")
        self._counters[name] = self._counters.get(name, 0) + amount

    def snapshot(self) -> dict[str, int]:
        return dict(sorted(self._counters.items()))

    def state_dict(self) -> dict[str, Any]:
        return {"schema_version": DIAGNOSTICS_SCHEMA_VERSION, "counters": self.snapshot()}

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping) or state.get("schema_version") != DIAGNOSTICS_SCHEMA_VERSION:
            raise ValueError("unsupported diagnostics schema")
        counters = state.get("counters")
        if not isinstance(counters, Mapping):
            raise ValueError("diagnostic counters must be a mapping")
        normalized: dict[str, int] = {}
        for name, value in counters.items():
            if not isinstance(name, str) or not name.strip() or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("diagnostic counters must be nonnegative integer values")
            normalized[name] = value
        self._counters = normalized


__all__ = ["DIAGNOSTICS_SCHEMA_VERSION", "DiagnosticCounters"]
