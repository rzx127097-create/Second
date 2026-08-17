"""Shared-scenario evaluation with explicit split guardrails."""

from __future__ import annotations

from collections.abc import Sequence
import inspect
import pickle
from pathlib import Path
from time import perf_counter
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
    measure_decision_time: bool | None = None,
    evidence_mode: str = "formal",
) -> list[EpisodeRecord]:
    """Evaluate a policy on exact, resettable ScenarioBundle scenarios."""
    if split not in {"smoke", "train", "validation", "sealed_test"}:
        raise ValueError("unknown evaluation split")
    if evidence_mode not in {"formal", "simulation"}:
        raise ValueError("evidence_mode must be formal or simulation")
    if measure_decision_time is None:
        measure_decision_time = split != "smoke"
    if split == "sealed_test":
        if not deterministic:
            raise ValueError("sealed_test requires deterministic=True")
        if not getattr(policy, "name", None) or not hasattr(policy, "eval"):
            raise ValueError("sealed_test requires a named frozen policy with eval mode")
        if getattr(policy, "frozen", False) is not True or getattr(policy, "training", False) is True:
            raise ValueError("sealed_test requires a frozen policy")
    if split != "smoke" and getattr(policy, "smoke_only", False):
        raise ValueError("smoke_only policy cannot be used for formal evaluation")
    records: list[EpisodeRecord] = []
    for scenario_id in scenarios:
        scenario_key = str(scenario_id)
        bundle = scenario_factory(scenario_key) if not isinstance(scenario_factory, Mapping) else scenario_factory[scenario_key]
        if str(getattr(bundle, "scenario_id", getattr(bundle, "scale_id", scenario_key))) != scenario_key:
            raise ValueError(f"scenario factory returned mismatched scenario: {scenario_key}")
        if evidence_mode == "simulation":
            bundle.assert_simulation_ready()
        elif split != "smoke":
            bundle.assert_formal_ready()
        was_training = getattr(policy, "training", None)
        if hasattr(policy, "eval"):
            policy.eval()
        snapshot = bundle.reset()
        initial_pest_total = float(np.asarray(bundle.pest_density, dtype=float).sum())
        pesticide_initial_l = float(bundle.resources.total_pesticide_l)
        total_reward = 0.0
        components: dict[str, float] = {}
        events: list[dict[str, object]] = []
        decision_times_s: list[float] = []
        agent_ids = {"uav": [], "vehicle": []}
        try:
            while True:
                parameters = inspect.signature(policy.act).parameters
                accepts_deterministic = "deterministic" in parameters or any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in parameters.values()
                )
                decision_started = perf_counter() if measure_decision_time else 0.0
                proposed = policy.act(snapshot, deterministic=deterministic) if accepts_deterministic else policy.act(snapshot)
                environment_actions = actions_to_environment(snapshot, proposed)
                if measure_decision_time:
                    decision_times_s.append(perf_counter() - decision_started)
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
            if was_training is not None and hasattr(policy, "train"):
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
            decision_times_s=decision_times_s,
            evidence_mode=evidence_mode,
            simulation_profile_sha256=str(
                getattr(bundle, "simulation_profile_sha256", "")
            ) if evidence_mode == "simulation" else "",
            preflight_warnings=(
                getattr(bundle, "simulation_preflight_warnings", ())
                if evidence_mode == "simulation" else ()
            ),
        ))
    return records


__all__ = ["evaluate_shared_scenarios", "evaluate_policy"]


def load_evaluation_checkpoint(path: str | Path, algorithm_factory: Callable[[], Any]) -> tuple[Any, dict[str, int]]:
    """Load an evaluation checkpoint through atomic persistence with integrity checks."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"checkpoint does not exist: {source}")
    try:
        try:
            import torch
        except ImportError:
            with source.open("rb") as handle:
                raw_payload = pickle.load(handle)
        else:
            raw_payload = torch.load(source, map_location="cpu", weights_only=False)
        if not isinstance(raw_payload, Mapping):
            raise ValueError("checkpoint payload must be a mapping")
        raw_format = raw_payload["format"]
        raw_step = raw_payload["step"]
        if type(raw_format) is not int or raw_format != 2:
            raise ValueError("checkpoint format must be exactly integer 2")
        if type(raw_step) is not int or raw_step < 0:
            raise ValueError("checkpoint step must be a non-negative integer")
    except Exception as exc:  # noqa: BLE001 - normalize all malformed payloads
        raise ValueError(f"invalid evaluation checkpoint: {source}") from exc
    try:
        from problem2.algorithms.common.checkpoint import load_checkpoint
        algorithm, metadata = load_checkpoint(source, algorithm_factory)
    except Exception as exc:  # noqa: BLE001 - normalize persistence errors at evaluation boundary
        raise ValueError(f"invalid evaluation checkpoint: {source}") from exc
    if not isinstance(metadata, Mapping) or type(metadata.get("format")) is not int or type(metadata.get("step")) is not int:
        raise ValueError("unsupported checkpoint format")
    if metadata["format"] != raw_format or metadata["step"] != raw_step:
        raise ValueError("checkpoint metadata changed during load")
    step = metadata["step"]
    if step < 0:
        raise ValueError("checkpoint step metadata is invalid")
    algorithm.eval() if hasattr(algorithm, "eval") else None
    return algorithm, {
        "step": step,
        "format": 2,
        "provenance": dict(raw_payload.get("provenance") or {}),
    }


__all__.append("load_evaluation_checkpoint")
