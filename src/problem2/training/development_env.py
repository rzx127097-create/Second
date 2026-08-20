"""Deterministic non-sealed environment adapter for G3 engineering smoke."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from problem2.config import G3Config
from problem2.environment.action_masks import (
    convert_g2_masks_to_roles,
)
from problem2.environment.observations import (
    build_role_observations,
    build_structured_critic_state,
)


RESERVED_RANGES = ((20000, 20049), (30000, 30099))


def _reserved_seed(seed: int) -> bool:
    return any(lower <= seed <= upper for lower, upper in RESERVED_RANGES)


class DevelopmentCooperativeEnv:
    """Small deterministic cooperative adapter with no resource mutation."""

    def __init__(self, seed: int, config: G3Config, *, horizon: int = 4) -> None:
        self.seed = int(seed)
        if _reserved_seed(self.seed):
            raise ValueError(
                "reserved validation or sealed seed is not permitted in G3 development"
            )
        if config.training_partition != "development":
            raise ValueError("G3 smoke requires the development training partition")
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        self.config = config
        self.horizon = int(horizon)
        self.rng = np.random.default_rng(self.seed)
        self.step_count = 0
        self._snapshot: dict[str, Any] | None = None

    def _make_snapshot(self) -> dict[str, Any]:
        positions = self.rng.integers(1, 9, size=(self.config.uav_count, 2))
        positions[0] = (0, 0)
        uavs = []
        for index in range(self.config.uav_count):
            uavs.append(
                {
                    "id": f"uav-{index}",
                    "x": float(positions[index, 0]),
                    "y": float(positions[index, 1]),
                    "pesticide_l": float(0.4 + 0.1 * index),
                    "capacity_l": 1.0,
                    "service_locked": False,
                    "active_request_id": None,
                    "request_remaining_l": 0.0,
                }
            )
        requests = [
            {
                "id": "req-dev-0",
                "uav_id": "uav-1",
                "remaining_l": 0.5,
                "urgency": 0.25,
                "road_distance_m": 2.0,
                "valid": True,
            }
        ]
        candidates = [
            {
                "slot": 0,
                "request_id": "req-dev-0",
                "uav_id": "uav-1",
                "remaining_l": 0.5,
                "urgency": 0.25,
                "road_distance_m": 2.0,
                "valid": True,
            }
        ]
        return {
            "step": 0,
            "max_steps": self.horizon,
            "field_summary": self.rng.random(8).round(6).tolist(),
            "uavs": uavs,
            "vehicle": {
                "id": "vehicle-0",
                "x": 4.0,
                "y": 4.0,
                "inventory_l": 2.0,
                "capacity_l": 4.0,
                "mode": "idle",
                "active_request_id": None,
            },
            "requests": requests,
            "candidate_slots": candidates,
            "critic_only": self.rng.random(3).round(6).tolist(),
        }

    def _state(self) -> dict[str, Any]:
        if self._snapshot is None:
            raise RuntimeError("environment must be reset before use")
        snapshot = self._snapshot
        old_uav_mask = []
        for uav in snapshot["uavs"]:
            x = float(uav["x"])
            y = float(uav["y"])
            old_uav_mask.append(
                [
                    True,
                    y < 9.0,
                    y > 0.0,
                    x > 0.0,
                    x < 9.0,
                    float(uav["pesticide_l"]) > 0.0,
                ]
            )
        old_vehicle_mask = [True, True, True, True, True]
        uav_mask, vehicle_mask = convert_g2_masks_to_roles(
            uav_mask=old_uav_mask[0],
            vehicle_mask=old_vehicle_mask,
            candidate_slot_mask=[True, False, False, False],
        )
        uav_masks = np.asarray(
            [
                convert_g2_masks_to_roles(
                    uav_mask=row,
                    vehicle_mask=old_vehicle_mask,
                    candidate_slot_mask=[True, False, False, False],
                )[0]
                for row in old_uav_mask
            ],
            dtype=bool,
        )
        del uav_mask
        del vehicle_mask
        return {
            "observations": build_role_observations(
                snapshot,
                self.config.uav_count,
                self.config.max_candidate_slots,
            ),
            "critic_state": build_structured_critic_state(
                snapshot,
                self.config.uav_count,
                self.config.max_candidate_slots,
            ),
            "masks": {
                "uav": uav_masks,
                "vehicle": np.asarray(
                    [
                        convert_g2_masks_to_roles(
                            uav_mask=old_uav_mask[0],
                            vehicle_mask=old_vehicle_mask,
                            candidate_slot_mask=[True, False, False, False],
                        )[1]
                    ],
                    dtype=bool,
                ),
            },
            "candidate_mapping": {
                "vehicle": ["req-dev-0", None, None, None]
            },
            "agent_ids": {
                "uav": [row["id"] for row in snapshot["uavs"]],
                "vehicle": ["vehicle-0"],
            },
            "episode_id": f"development-{self.seed}",
            "config_hash": self.config.config_hash,
            "sealed_test_accessed": False,
            "step": self.step_count,
        }

    def reset(self) -> dict[str, Any]:
        self.rng = np.random.default_rng(self.seed)
        self.step_count = 0
        self._snapshot = self._make_snapshot()
        return self._state()

    def step(self, actions: Mapping[str, Any]) -> dict[str, Any]:
        if self._snapshot is None:
            raise RuntimeError("environment must be reset before use")
        if self.step_count >= self.horizon:
            raise RuntimeError("development episode is already finished")
        uav_actions = np.asarray(actions.get("uav", ()), dtype=np.int64).reshape(-1)
        vehicle_actions = np.asarray(actions.get("vehicle", ()), dtype=np.int64).reshape(-1)
        current = self._state()
        if uav_actions.shape != (self.config.uav_count,):
            raise ValueError("illegal UAV action vector shape")
        if vehicle_actions.shape != (1,):
            raise ValueError("illegal vehicle action vector shape")
        if not current["masks"]["uav"][np.arange(self.config.uav_count), uav_actions].all():
            raise ValueError("illegal UAV action")
        if not current["masks"]["vehicle"][0, vehicle_actions[0]]:
            raise ValueError("illegal vehicle action")

        for index, action in enumerate(uav_actions.tolist()):
            uav = self._snapshot["uavs"][index]
            if action == 0:
                uav["y"] = min(9.0, float(uav["y"]) + 1.0)
            elif action == 1:
                uav["y"] = max(0.0, float(uav["y"]) - 1.0)
            elif action == 2:
                uav["x"] = max(0.0, float(uav["x"]) - 1.0)
            elif action == 3:
                uav["x"] = min(9.0, float(uav["x"]) + 1.0)
        self.step_count += 1
        self._snapshot["step"] = self.step_count
        reward = float(
            np.mean([0.05 if action == 5 else 0.0 for action in uav_actions])
            - 0.01 * np.count_nonzero(uav_actions[:4])
        )
        terminated = False
        truncated = self.step_count >= self.horizon
        next_state = self._state()
        next_state.update(
            {
                "reward": reward,
                "reward_components": {
                    "development_control": reward,
                    "resource_transfer": 0.0,
                },
                "terminated": terminated,
                "truncated": truncated,
            }
        )
        return next_state


__all__ = ["DevelopmentCooperativeEnv", "RESERVED_RANGES"]
