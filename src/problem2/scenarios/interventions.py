"""Immutable Chapter 4.5 scenario interventions with auditable identities."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


PARAMETER_KEYS = {
    "uav_initial_pesticide_ratio",
    "vehicle_speed",
    "service_setup_time",
    "rendezvous_radius",
}
ADAPTATION_KEYS = {
    "hotspot_road_separation",
    "demand_dispersion",
    "simultaneous_requests",
    "road_blockage",
}


@dataclass(frozen=True)
class ScenarioIntervention:
    condition_id: str
    support_mode: str = "mobile"
    pesticide_mode: str = "finite"
    parameter_overrides: tuple[tuple[str, object], ...] = ()
    adaptation_overrides: tuple[tuple[str, object], ...] = ()
    ablation_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.condition_id).strip():
            raise ValueError("condition_id must be non-empty")
        if self.support_mode not in {"mobile", "fixed", "disabled", "teleport"}:
            raise ValueError("support_mode must be mobile, fixed, disabled or teleport")
        if self.pesticide_mode not in {"finite", "unlimited"}:
            raise ValueError("pesticide_mode must be finite or unlimited")
        parameters = dict(self.parameter_overrides)
        adaptations = dict(self.adaptation_overrides)
        if len(parameters) != len(self.parameter_overrides):
            raise ValueError("duplicate parameter override")
        if len(adaptations) != len(self.adaptation_overrides):
            raise ValueError("duplicate adaptation override")
        unknown_parameters = set(parameters) - PARAMETER_KEYS
        unknown_adaptations = set(adaptations) - ADAPTATION_KEYS
        if unknown_parameters:
            raise ValueError(f"unknown parameter overrides: {sorted(unknown_parameters)}")
        if unknown_adaptations:
            raise ValueError(f"unknown adaptation overrides: {sorted(unknown_adaptations)}")
        ratio = parameters.get("uav_initial_pesticide_ratio", 1.0)
        if not 0.0 < float(ratio) <= 1.0:
            raise ValueError("uav_initial_pesticide_ratio must lie in (0, 1]")
        blockage = adaptations.get("road_blockage", 0.0)
        if not 0.0 <= float(blockage) <= 0.5:
            raise ValueError("road_blockage must lie in [0, 0.5]")

    @property
    def parameters(self) -> dict[str, object]:
        return dict(self.parameter_overrides)

    @property
    def adaptations(self) -> dict[str, object]:
        return dict(self.adaptation_overrides)

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "support_mode": self.support_mode,
            "pesticide_mode": self.pesticide_mode,
            "parameter_overrides": dict(sorted(self.parameter_overrides)),
            "adaptation_overrides": dict(sorted(self.adaptation_overrides)),
            "ablation_flags": sorted(set(self.ablation_flags)),
        }

    @property
    def identity_hash(self) -> str:
        payload = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_condition(cls, condition: Any) -> "ScenarioIntervention":
        overrides = dict(getattr(condition, "overrides", ()))
        family = str(getattr(condition, "family", ""))
        support_mode = str(overrides.pop("support_mode", "mobile"))
        pesticide_mode = str(overrides.pop("pesticide_mode", "finite"))
        if family == "sensitivity":
            return cls(
                str(condition.condition_id),
                parameter_overrides=tuple(sorted(overrides.items())),
            )
        if family == "adaptation":
            return cls(
                str(condition.condition_id),
                adaptation_overrides=tuple(sorted(overrides.items())),
            )
        return cls(
            str(condition.condition_id),
            support_mode=support_mode,
            pesticide_mode=pesticide_mode,
            ablation_flags=(str(getattr(condition, "kind", "")),) if family == "ablation" else (),
        )


def baseline_intervention() -> ScenarioIntervention:
    return ScenarioIntervention("baseline")


__all__ = ["ScenarioIntervention", "baseline_intervention"]
