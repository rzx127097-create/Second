"""Shared-scenario evaluation with explicit split guardrails."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from .metrics import EpisodeRecord, episode_record_from_bundle
from .policy_protocol import actions_to_environment


def evaluate_shared_scenarios(methods: Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]], scenarios: list[dict[str, Any]], *, split: str) -> dict[str, Any]:
    if split not in {"validation", "sealed_test", "train"}:
        raise ValueError("unknown evaluation split")
    if split == "sealed_test" and not methods:
        raise ValueError("sealed evaluation requires frozen methods")
    scenario_ids = [str(scenario["scenario_id"]) for scenario in scenarios]
    results = {name: [method(dict(scenario)) for scenario in scenarios] for name, method in methods.items()}
    return {"split": split, "scenario_ids": scenario_ids, "results": results}


def evaluate_policy(
    policy: Any,
    scenario_factory: Callable[[str], Any],
    *,
    scenarios: Sequence[str],
    split: str,
    deterministic: bool,
) -> list[EpisodeRecord]:
    """Evaluate a policy on exact, resettable ScenarioBundle scenarios."""
    if split not in {"smoke", "train", "validation", "sealed_test"}:
        raise ValueError("unknown evaluation split")
    if split == "sealed_test" and not getattr(policy, "name", None):
        raise ValueError("sealed evaluation requires a named frozen policy")
    records: list[EpisodeRecord] = []
    for scenario_id in scenarios:
        scenario_key = str(scenario_id)
        bundle = scenario_factory(scenario_key) if not isinstance(scenario_factory, Mapping) else scenario_factory[scenario_key]
        if str(getattr(bundle, "scale_id", scenario_key)) != scenario_key:
            raise ValueError(f"scenario factory returned mismatched scenario: {scenario_key}")
        if split != "smoke":
            bundle.assert_formal_ready()
        was_training = getattr(policy, "training", None)
        if deterministic and hasattr(policy, "eval"):
            policy.eval()
        snapshot = bundle.reset()
        initial_pest_total = float(np.asarray(bundle.pest_density, dtype=float).sum())
        pesticide_initial_l = float(bundle.resources.total_pesticide_l)
        total_reward = 0.0
        components: dict[str, float] = {}
        events: list[dict[str, object]] = []
        agent_ids = {"uav": [], "vehicle": []}
        try:
            while True:
                try:
                    proposed = policy.act(snapshot, deterministic=deterministic)
                except TypeError:
                    proposed = policy.act(snapshot)
                environment_actions = actions_to_environment(snapshot, proposed)
                for agent_id, observation in snapshot.role_observations.items():
                    role = str(observation.get("role"))
                    if role in agent_ids and agent_id not in agent_ids[role]:
                        agent_ids[role].append(agent_id)
                stepped = bundle.step(environment_actions)
                total_reward += float(stepped.reward)
                for key, value in stepped.reward_components.items():
                    components[key] = components.get(key, 0.0) + float(value)
                events.extend(dict(event) for event in stepped.events)
                snapshot = stepped
                if stepped.terminated or stepped.truncated:
                    break
        finally:
            if deterministic and was_training is not None and hasattr(policy, "train"):
                policy.train(bool(was_training))
        records.append(episode_record_from_bundle(
            bundle,
            episode_id=str(bundle.episode_id),
            steps=int(bundle.step_count),
            total_reward=total_reward,
            reward_components=components,
            initial_pest_total=initial_pest_total,
            pesticide_initial_l=pesticide_initial_l,
            events=events,
            agent_ids=agent_ids,
            policy_name=str(getattr(policy, "name", policy.__class__.__name__)),
            split=split,
            scenario_id=scenario_key,
        ))
    return records


__all__ = ["evaluate_shared_scenarios", "evaluate_policy"]


def load_evaluation_checkpoint(path: str | Path, algorithm_factory: Callable[[], Any]) -> tuple[Any, dict[str, int]]:
    """Load an evaluation checkpoint through atomic persistence with integrity checks."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"checkpoint does not exist: {source}")
    from problem2.algorithms.common.checkpoint import load_checkpoint

    try:
        algorithm, metadata = load_checkpoint(source, algorithm_factory)
    except Exception as exc:  # noqa: BLE001 - normalize persistence errors at evaluation boundary
        raise ValueError(f"invalid evaluation checkpoint: {source}") from exc
    if not isinstance(metadata, Mapping) or metadata.get("format") != 2:
        raise ValueError("unsupported checkpoint format")
    step = metadata.get("step")
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("checkpoint step metadata is invalid")
    algorithm.eval() if hasattr(algorithm, "eval") else None
    return algorithm, {"step": step, "format": 2}


__all__.append("load_evaluation_checkpoint")
