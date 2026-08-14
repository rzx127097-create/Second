from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from problem2.environment.action_masks import ActionMask
from problem2.experiments.methods import (
    apply_vehicle_behavior_override,
    method_profile,
)


FULL_COMPONENTS = {
    "observation_normalization": True,
    "return_normalization": True,
    "orthogonal_initialization": True,
    "layer_normalization": True,
    "value_clipping": True,
    "huber_value_loss": True,
    "learning_rate_decay": True,
}


@dataclass
class Snapshot:
    role_observations: dict[str, dict[str, str]]
    action_masks: dict[str, ActionMask]
    candidate_mapping: dict[str, tuple[tuple[str, str], ...]]


def _snapshot() -> Snapshot:
    return Snapshot(
        role_observations={"uav-1": {"role": "uav"}, "vehicle-1": {"role": "vehicle"}},
        action_masks={
            "uav-1": ActionMask(np.array([1, 1]), ("hold", "spray")),
            "vehicle-1": ActionMask(np.array([1, 1, 1]), ("hold", "slot-0", "slot-1")),
        },
        candidate_mapping={
            "vehicle-1": (("slot-1", "req-2:rv-2"), ("slot-0", "req-1:rv-1")),
        },
    )


def test_method_profiles_keep_physics_equal_and_change_only_declared_learning_contract() -> None:
    """A method must not gain an unregistered environment or optimizer advantage."""
    algorithm_config = {"stability_components": FULL_COMPONENTS}
    mobile = method_profile("sr_mappo_mobile", algorithm_config)
    fixed = method_profile("sr_mappo_fixed", algorithm_config)
    astar = method_profile("sr_mappo_astar", algorithm_config)
    mappo = method_profile("mappo_mobile", algorithm_config)
    staged = method_profile("sr_mappo_two_stage", algorithm_config)

    assert mobile.vehicle_controller == "learned"
    assert fixed.vehicle_controller == "fixed"
    assert astar.vehicle_controller == "rolling_astar"
    assert staged.vehicle_controller == "two_stage"
    assert mobile.stability_components == FULL_COMPONENTS
    assert fixed.stability_components == FULL_COMPONENTS
    assert astar.stability_components == FULL_COMPONENTS
    assert staged.stability_components == FULL_COMPONENTS
    assert mappo.stability_components == {key: False for key in FULL_COMPONENTS}
    assert {profile.environment_mode for profile in (mobile, astar, mappo, staged)} == {"mobile"}
    assert fixed.environment_mode == "fixed"


def test_external_vehicle_controller_rewrites_the_exact_behavior_record() -> None:
    """Executed A* actions must not be replayed as if the vehicle actor sampled them."""
    transition = {
        "actions": {"uav": [1], "vehicle": [0]},
        "log_probs": {"uav": [-0.2], "vehicle": [-1.1]},
        "entropies": {"uav": [0.5], "vehicle": [0.7]},
        "valid_actor_sample": {"uav": [True], "vehicle": [True]},
    }
    profile = method_profile("sr_mappo_astar", {"stability_components": FULL_COMPONENTS})

    apply_vehicle_behavior_override(
        _snapshot(), transition, profile,
        update_index=1, total_updates=4,
    )

    # Candidate mapping order is the frozen priority order; slot-1 is selected.
    assert transition["actions"]["vehicle"] == [2]
    assert transition["log_probs"]["vehicle"] == [0.0]
    assert transition["entropies"]["vehicle"] == [0.0]
    assert transition["valid_actor_sample"]["vehicle"] == [False]


def test_two_stage_profile_freezes_vehicle_before_boundary_and_learns_afterward() -> None:
    """Changing the stage boundary must change only the declared vehicle controller."""
    profile = method_profile("sr_mappo_two_stage", {"stability_components": FULL_COMPONENTS})
    first = {
        "actions": {"uav": [1], "vehicle": [0]},
        "log_probs": {"uav": [0.0], "vehicle": [-0.4]},
        "entropies": {"uav": [0.0], "vehicle": [0.3]},
        "valid_actor_sample": {"uav": [True], "vehicle": [True]},
    }
    second = {
        "actions": {"uav": [1], "vehicle": [1]},
        "log_probs": {"uav": [0.0], "vehicle": [-0.4]},
        "entropies": {"uav": [0.0], "vehicle": [0.3]},
        "valid_actor_sample": {"uav": [True], "vehicle": [True]},
    }

    assert apply_vehicle_behavior_override(_snapshot(), first, profile, update_index=1, total_updates=4) == "stage_1_astar"
    assert first["valid_actor_sample"]["vehicle"] == [False]
    assert apply_vehicle_behavior_override(_snapshot(), second, profile, update_index=3, total_updates=4) == "stage_2_joint"
    assert second["actions"]["vehicle"] == [1]
    assert second["log_probs"]["vehicle"] == [-0.4]
    assert second["valid_actor_sample"]["vehicle"] == [True]


def test_fixed_profile_accepts_candidate_without_learning_vehicle_movement() -> None:
    transition = {
        "actions": {"uav": [1], "vehicle": [2]},
        "log_probs": {"uav": [0.0], "vehicle": [-0.4]},
        "entropies": {"uav": [0.0], "vehicle": [0.3]},
        "valid_actor_sample": {"uav": [True], "vehicle": [True]},
    }
    profile = method_profile("sr_mappo_fixed", {"stability_components": FULL_COMPONENTS})

    phase = apply_vehicle_behavior_override(_snapshot(), transition, profile, update_index=1, total_updates=2)

    assert phase == "fixed_support"
    # The fixed-mode environment exposes candidates only at the support node.
    assert transition["actions"]["vehicle"] == [2]
    assert transition["valid_actor_sample"]["vehicle"] == [False]
