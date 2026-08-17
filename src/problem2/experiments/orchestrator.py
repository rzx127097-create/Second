"""Frozen Chapter 4.5 matrix expansion and persisted worker orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from problem2.config import config_identity, load_config_bundle
from problem2.scenarios.interventions import ScenarioIntervention

from .job_identity import JobIdentity, capture_git_provenance, make_job_identity
from .methods import method_profile
from .specification import Chapter45Spec, ExperimentCondition, load_experiment_spec, protocol_identity


@dataclass(frozen=True)
class PlannedJob:
    identity: JobIdentity
    intervention: ScenarioIntervention

    def to_dict(self) -> dict[str, object]:
        return {
            **self.identity.to_dict(),
            "job_id": self.identity.job_id,
            "intervention": self.intervention.to_dict(),
            "intervention_hash": self.intervention.identity_hash,
        }


def resolve_condition_intervention(
    spec: Chapter45Spec,
    algorithm_config: dict[str, Any],
    *,
    family: str,
    condition_id: str,
    method: str,
) -> ScenarioIntervention:
    profile = method_profile(method, algorithm_config)
    if condition_id == "direct":
        return ScenarioIntervention("direct", support_mode=profile.environment_mode)
    matches = [
        condition for condition in spec.expand(family)
        if condition.condition_id == condition_id
    ]
    if len(matches) != 1:
        raise ValueError(f"condition_id {condition_id!r} is not unique in family {family!r}")
    condition = matches[0]
    if family == "main_comparison":
        return ScenarioIntervention(condition_id, support_mode=profile.environment_mode)
    intervention = ScenarioIntervention.from_condition(condition)
    if intervention.support_mode == "mobile" and profile.environment_mode == "fixed":
        intervention = replace(intervention, support_mode="fixed")
    return intervention


class Chapter45Orchestrator:
    def __init__(
        self,
        config_dir: str | Path,
        output_root: str | Path,
        *,
        protocol_path: str | Path | None = None,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.output_root = Path(output_root)
        self.protocol_path = Path(protocol_path or (self.config_dir / "experiments" / "chapter4_5.yaml"))
        self.config = load_config_bundle(self.config_dir)
        self.spec: Chapter45Spec = load_experiment_spec(self.protocol_path, self.config)
        self.protocol_hash = protocol_identity(self.protocol_path)
        self.config_hash = config_identity(self.config)
        self.git_provenance = capture_git_provenance(str(Path(__file__).resolve().parents[3]))
        self.git_commit = self.git_provenance.commit

    def _identity(
        self,
        *,
        method: str,
        scale: str,
        seed: int,
        family: str,
        condition_id: str,
        execution_profile: str,
    ) -> JobIdentity:
        return make_job_identity(
            method,
            scale,
            seed,
            self.config_hash,
            config_hash=self.config_hash,
            git_commit=self.git_commit,
            execution_profile=execution_profile,
            target_updates=1 if execution_profile == "smoke" else int(self.config.algorithm["total_updates"]),
            rollout_horizon=3 if execution_profile == "smoke" else int(self.config.algorithm["rollout_horizon"]),
            family=family,
            condition_id=condition_id,
            scenario_split="train",
            protocol_hash=self.protocol_hash,
            source_tree_hash=self.git_provenance.source_tree_hash,
            git_dirty=self.git_provenance.dirty,
        )

    def _condition_method(self, condition: ExperimentCondition) -> str:
        if condition.family != "ablation":
            return condition.method
        if condition.kind == "same_source_mappo":
            return "mappo_mobile"
        if condition.kind == "two_stage_training":
            return "sr_mappo_two_stage"
        return "sr_mappo_mobile"

    def _intervention(self, condition: ExperimentCondition, method: str) -> ScenarioIntervention:
        return resolve_condition_intervention(
            self.spec,
            self.config.algorithm,
            family=condition.family,
            condition_id=condition.condition_id,
            method=method,
        )

    def plan(self, family: str, *, execution_profile: str = "formal") -> tuple[PlannedJob, ...]:
        if execution_profile not in {"formal", "simulation", "smoke"}:
            raise ValueError("execution_profile must be formal, simulation or smoke")
        family = str(family)
        conditions = self.spec.expand(family)
        jobs: list[PlannedJob] = []
        if family == "main_comparison":
            lookup = {
                (condition.method, condition.scale, condition.training_seed): condition
                for condition in conditions
            }
            for scale in self.spec.scales:
                for seed in self.spec.training_seeds:
                    for method in self.spec.main_methods:
                        condition = lookup[(method, scale, seed)]
                        intervention = self._intervention(condition, method)
                        jobs.append(PlannedJob(
                            self._identity(
                                method=method,
                                scale=scale,
                                seed=seed,
                                family=family,
                                condition_id=condition.condition_id,
                                execution_profile=execution_profile,
                            ),
                            intervention,
                        ))
            return tuple(jobs)
        scope = self.spec.family_scopes[family]
        for scale in scope["scales"]:
            for seed in scope["training_seeds"]:
                for condition in conditions:
                    method = self._condition_method(condition)
                    intervention = self._intervention(condition, method)
                    jobs.append(PlannedJob(
                        self._identity(
                            method=method,
                            scale=str(scale),
                            seed=int(seed),
                            family=family,
                            condition_id=condition.condition_id,
                            execution_profile=execution_profile,
                        ),
                        intervention,
                    ))
        return tuple(jobs)


__all__ = ["Chapter45Orchestrator", "PlannedJob", "resolve_condition_intervention"]
