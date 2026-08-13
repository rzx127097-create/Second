"""Shared-scenario evaluation with explicit split guardrails."""

from __future__ import annotations

from typing import Any, Callable, Mapping


def evaluate_shared_scenarios(methods: Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]], scenarios: list[dict[str, Any]], *, split: str) -> dict[str, Any]:
    if split not in {"validation", "sealed_test", "train"}:
        raise ValueError("unknown evaluation split")
    if split == "sealed_test" and not methods:
        raise ValueError("sealed evaluation requires frozen methods")
    scenario_ids = [str(scenario["scenario_id"]) for scenario in scenarios]
    results = {name: [method(dict(scenario)) for scenario in scenarios] for name, method in methods.items()}
    return {"split": split, "scenario_ids": scenario_ids, "results": results}
