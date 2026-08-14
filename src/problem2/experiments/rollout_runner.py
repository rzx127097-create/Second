"""Real ScenarioBundle rollout collection and CPU SR-MAPPO update runner."""

from __future__ import annotations

from collections import defaultdict
from math import isfinite
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np

from problem2.algorithms.common.checkpoint import save_checkpoint
from problem2.algorithms.sr_mappo.rollout import RolloutBatch

from .metrics import EpisodeRecord, episode_record_from_bundle


def _training_hyperparameters(config: dict[str, Any] | None = None) -> dict[str, float | int]:
    """Normalize the YAML training contract at one boundary."""
    source = dict(config or {})
    return {
        "discount_gamma": float(source.get("discount_gamma", 0.99)),
        "gae_lambda": float(source.get("gae_lambda", 0.95)),
        "clip_epsilon": float(source.get("clip_epsilon", 0.2)),
        "ppo_epochs": int(source.get("ppo_epochs", 1)),
    }


def _role_inputs(snapshot: Any) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, list[str]], dict[str, list[object]]]:
    """Extract stable role arrays from the bundle's per-agent decision snapshot."""

    role_ids: dict[str, list[str]] = {"uav": [], "vehicle": []}
    for agent_id, observation in snapshot.role_observations.items():
        role = str(observation["role"])
        if role not in role_ids:
            raise ValueError(f"unsupported policy role: {role}")
        role_ids[role].append(str(agent_id))
    for ids in role_ids.values():
        ids.sort()
    observations = {
        role: np.asarray([snapshot.role_observations[agent_id]["vector"] for agent_id in ids], dtype=np.float32)
        for role, ids in role_ids.items()
    }
    masks = {
        role: np.asarray([snapshot.action_masks[agent_id].mask for agent_id in ids], dtype=bool)
        for role, ids in role_ids.items()
    }
    action_masks = {
        role: [snapshot.action_masks[agent_id] for agent_id in ids]
        for role, ids in role_ids.items()
    }
    return observations, masks, role_ids, action_masks


def _environment_actions(sampled_actions: dict[str, Any], role_ids: dict[str, list[str]], action_masks: dict[str, list[object]]) -> dict[str, str]:
    """Convert actor indices back into the exact legal environment slot names."""

    converted: dict[str, str] = {}
    for role in ("uav", "vehicle"):
        values = np.asarray(sampled_actions[role]).reshape(-1)
        if len(values) != len(role_ids[role]):
            raise ValueError(f"sampled {role} action count does not match ScenarioBundle slots")
        for agent_id, index, mask in zip(role_ids[role], values, action_masks[role]):
            action_index = int(index)
            if action_index < 0 or action_index >= len(mask.actions) or not mask.mask[action_index]:
                raise ValueError(f"sampled an invalid {role} action for {agent_id}")
            converted[agent_id] = str(mask.actions[action_index])
    return converted


def _scalar_value(algorithm: Any, state: dict[str, Any]) -> float:
    import torch

    with torch.no_grad():
        return float(algorithm.value_physical(state).reshape(-1)[0].item())


def run_training_episode(
    bundle: Any,
    algorithm: Any,
    trainer: Any,
    *,
    horizon: int,
    episode_id: str,
    algorithm_config: dict[str, Any] | None = None,
    method_profile: Any | None = None,
    update_index: int = 1,
    total_updates: int = 1,
) -> EpisodeRecord:
    """Collect exactly one real joint trajectory from ``ScenarioBundle``.

    The returned record carries its finished ``RolloutBatch`` privately for
    ``train_policy``.  No action, reward, state, or event is synthesized here.
    """

    del trainer  # Optimizer ownership stays with train_policy after collection.
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if method_profile is None:
        from .methods import method_profile as build_method_profile

        method_profile = build_method_profile("sr_mappo_mobile", algorithm_config or {
            "stability_components": getattr(algorithm, "stability_components", {}),
        })
    snapshot = bundle.reset()
    batch = RolloutBatch()
    initial_pest_total = float(np.asarray(bundle.pest_density, dtype=float).sum())
    pesticide_initial_l = float(bundle.resources.total_pesticide_l)
    all_events: list[dict[str, object]] = []
    components: defaultdict[str, float] = defaultdict(float)
    total_reward = 0.0
    decision_times_s: list[float] = []

    training_phase = method_profile.vehicle_phase(
        update_index=int(update_index), total_updates=int(total_updates),
    )
    for step_index in range(int(horizon)):
        observations, masks, role_ids, action_masks = _role_inputs(snapshot)
        state = snapshot.critic_state
        decision_started = perf_counter()
        transition = algorithm.collect_transition(
            observations,
            masks,
            state,
            agent_ids=role_ids,
            candidate_mapping=snapshot.candidate_mapping,
            valid_actor_sample={
                role: [int(mask.mask.sum()) > 1 for mask in role_masks]
                for role, role_masks in action_masks.items()
            },
        )
        from .methods import apply_vehicle_behavior_override

        training_phase = apply_vehicle_behavior_override(
            snapshot,
            transition,
            method_profile,
            update_index=int(update_index),
            total_updates=int(total_updates),
        )
        environment_actions = _environment_actions(transition["actions"], role_ids, action_masks)
        decision_times_s.append(perf_counter() - decision_started)
        stepped = bundle.step(environment_actions)
        total_reward += float(stepped.reward)
        for name, value in stepped.reward_components.items():
            components[name] += float(value)
        all_events.extend(dict(event) for event in stepped.events)
        horizon_cut = step_index + 1 >= horizon
        done = bool(stepped.terminated or stepped.truncated or horizon_cut)
        next_value = 0.0 if stepped.terminated else _scalar_value(algorithm, stepped.critic_state)
        batch.add(
            observations=observations,
            policy_observations=transition["policy_observations"],
            state=state,
            actions=transition["actions"],
            masks=masks,
            log_probs=transition["log_probs"],
            entropies=transition["entropies"],
            agent_ids=role_ids,
            candidate_mapping=snapshot.candidate_mapping,
            valid_actor_sample=transition["valid_actor_sample"],
            reward=float(stepped.reward),
            reward_components=stepped.reward_components,
            normalization_version=transition["normalization_versions"],
            episode_id=episode_id,
            value=_scalar_value(algorithm, state),
            done=done,
            terminated=bool(stepped.terminated),
            truncated=bool(stepped.truncated or (horizon_cut and not stepped.terminated)),
            next_value=next_value,
        )
        snapshot = stepped
        if done:
            break

    hyper = _training_hyperparameters(algorithm_config)
    batch.finish(gamma=float(hyper["discount_gamma"]), gae_lambda=float(hyper["gae_lambda"]), last_value=0.0)
    record = episode_record_from_bundle(
        bundle,
        episode_id=episode_id,
        steps=len(batch),
        total_reward=total_reward,
        reward_components=components,
        initial_pest_total=initial_pest_total,
        pesticide_initial_l=pesticide_initial_l,
        events=all_events,
        agent_ids=role_ids,
        decision_times_s=decision_times_s,
    )
    record.rollout = batch
    record.policy_name = str(method_profile.name)
    record.training_phase = str(training_phase)
    return record


def train_policy(
    bundle_factory: Callable[[], Any],
    algorithm: Any,
    trainer: Any,
    *,
    updates: int,
    rollout_horizon: int,
    checkpoint_path: Path | None,
    start_update: int = 0,
    total_updates: int | None = None,
    algorithm_config: dict[str, Any] | None = None,
    method_profile: Any | None = None,
) -> list[EpisodeRecord]:
    """Collect, optimize, and atomically checkpoint true ScenarioBundle rollouts."""

    if updates < 1:
        raise ValueError("updates must be positive")
    if total_updates is not None and int(total_updates) < int(start_update) + int(updates):
        raise ValueError("total_updates must cover start_update plus updates")
    records: list[EpisodeRecord] = []
    hyper = _training_hyperparameters(algorithm_config)
    algorithm.train(True)
    for offset in range(int(updates)):
        bundle = bundle_factory()
        update = int(start_update) + offset + 1
        record = run_training_episode(
            bundle,
            algorithm,
            trainer,
            horizon=rollout_horizon,
            episode_id=str(bundle.episode_id),
            algorithm_config=algorithm_config,
            method_profile=method_profile,
            update_index=update,
            total_updates=int(total_updates or (int(start_update) + int(updates))),
        )
        losses = trainer.update_with_epochs(
            record.rollout,
            epochs=int(hyper["ppo_epochs"]),
            clip_epsilon=float(hyper["clip_epsilon"]),
            progress=None if total_updates is None else update / int(total_updates),
        )
        if any(not isfinite(float(value)) for value in losses.values()):
            raise ValueError(f"non-finite PPO loss at update {update}")
        if any(not isfinite(float(value)) for value in record.rollout.rewards):
            raise ValueError(f"non-finite rollout reward at update {update}")
        record.losses = {name: float(value) for name, value in losses.items()}
        record.rollout = None
        records.append(record)
        if checkpoint_path is not None:
            save_checkpoint(checkpoint_path, algorithm, step=update)
    return records


__all__ = ["run_training_episode", "train_policy", "_training_hyperparameters"]
