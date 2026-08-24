"""Exact interaction-budget and checkpoint-ancestry contract for two-stage SR-MAPPO."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TwoStageSchedule:
    total_interaction_budget: int
    uav_stage_budget: int
    vehicle_stage_budget: int
    schedule_version: str

    def __post_init__(self) -> None:
        for name in (
            "total_interaction_budget",
            "uav_stage_budget",
            "vehicle_stage_budget",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.uav_stage_budget + self.vehicle_stage_budget != self.total_interaction_budget:
            raise ValueError("two-stage budgets must sum exactly to the joint interaction budget")
        if not isinstance(self.schedule_version, str) or not self.schedule_version.strip():
            raise ValueError("schedule_version must be non-empty text")

    def checkpoint_ancestry(
        self,
        *,
        parent_checkpoint_sha256: str,
        uav_stage_checkpoint_sha256: str,
    ) -> dict[str, str | int]:
        for name, value in (
            ("parent_checkpoint_sha256", parent_checkpoint_sha256),
            ("uav_stage_checkpoint_sha256", uav_stage_checkpoint_sha256),
        ):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"{name} must be a lowercase SHA-256")
        return {
            "method_id": "sr_mappo_two_stage",
            "schedule_version": self.schedule_version,
            "total_interaction_budget": self.total_interaction_budget,
            "uav_stage_budget": self.uav_stage_budget,
            "vehicle_stage_budget": self.vehicle_stage_budget,
            "parent_checkpoint_sha256": parent_checkpoint_sha256,
            "uav_stage_checkpoint_sha256": uav_stage_checkpoint_sha256,
        }


__all__ = ["TwoStageSchedule"]
