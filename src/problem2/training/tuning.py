"""Fail-closed validation access accounting for frozen G5 candidates."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.config import load_g2_config
from problem2.domain import EpisodeState, UavState, VehicleState
from problem2.resources.ledger import new_ledger
from problem2.road.cache import RoadCacheExpectation, load_road_cache

from .cooperative_env import Problem2CooperativeEnv


INITIAL_ONBOARD_PESTICIDE_L = 0.2875
DEVELOPMENT_SCENARIO_IDS = range(10000, 10020)
VALIDATION_SCENARIO_IDS = range(20000, 20050)
SEALED_SCENARIO_IDS = range(30000, 30100)


class _Task12PhysicalEnv(Problem2CooperativeEnv):
    """Keep active dispatch mapping aligned with its one-hot behavior mask."""

    def _candidate_requests(self) -> tuple[list[Any], list[str | None]]:
        if self._dispatch is None:
            return super()._candidate_requests()
        dispatch = self._dispatch
        request = next(
            item for item in self._state.requests if item.request_id == dispatch.request_id
        )
        mapping: list[str | None] = [None, None, None, None]
        mapping[dispatch.sampled_slot - 1] = dispatch.request_id
        self._dispatch = replace(dispatch, candidate_mapping=tuple(mapping))
        self._candidate_nodes = {
            dispatch.request_id: (
                dispatch.selected_service_node,
                dispatch.route_length_m,
            )
        }
        return [request], mapping


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain an object")
    return payload


def validate_validation_episode(row: Mapping[str, Any]) -> None:
    """Reject proxy outcomes and any validation/sealed boundary ambiguity."""

    if not isinstance(row, Mapping):
        raise ValueError("validation episode must be a mapping")
    if row.get("partition") != "validation" or row.get("validation_accessed") is not True:
        raise ValueError("validation episode must record validation access")
    scenario_id = row.get("scenario_id")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int) or scenario_id not in range(20000, 20050):
        raise ValueError("validation scenario identity is outside 20000-20049")
    if row.get("sealed_accessed") is not False:
        raise ValueError("sealed access is forbidden during G5")
    if row.get("battery_replenishment_enabled") is not False:
        raise ValueError("battery replenishment must remain inactive")
    if row.get("metric_source") != "action_driven_environment":
        raise ValueError("validation metrics must come from an action-driven environment")
    spray_count = row.get("spray_action_count")
    sprayed_l = row.get("sprayed_pesticide_l")
    if isinstance(spray_count, bool) or not isinstance(spray_count, int) or spray_count < 0:
        raise ValueError("spray action count must be a non-negative integer")
    if isinstance(sprayed_l, bool) or not isinstance(sprayed_l, (int, float)) or not math.isfinite(float(sprayed_l)) or float(sprayed_l) < 0:
        raise ValueError("sprayed pesticide must be non-negative")
    initial = row.get("initial_total_pest")
    final = row.get("final_total_pest")
    reduction = row.get("reduction_rate")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in (initial, final, reduction)):
        raise ValueError("pest metrics must be finite numbers")
    if float(initial) <= 0 or float(final) < 0 or float(final) > float(initial):
        raise ValueError("pest totals are physically invalid")
    expected = 1.0 - float(final) / float(initial)
    if expected > 0 and (spray_count == 0 or float(sprayed_l) <= 0):
        raise ValueError("positive pest reduction requires at least one spray action")
    if not math.isclose(float(reduction), expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("reduction rate is not derived from pest totals")
    if row.get("success_at_0_85") is not (expected >= 0.85):
        raise ValueError("success indicator does not match the 0.85 threshold")


class ValidationAccessLedger:
    """Bind the first validation row to immutable candidate and budget bytes."""

    def __init__(self, candidate_manifest: Path | str, budget_manifest: Path | str, ledger_path: Path | str) -> None:
        self.candidate_manifest = Path(candidate_manifest).resolve()
        self.budget_manifest = Path(budget_manifest).resolve()
        self.ledger_path = Path(ledger_path).resolve()
        candidates = _load_json(self.candidate_manifest, "candidate manifest")
        budget = _load_json(self.budget_manifest, "budget manifest")
        declared = candidates.get("equal_environment_interactions")
        if isinstance(declared, bool) or not isinstance(declared, int) or declared <= 0:
            raise ValueError("candidate manifest lacks equal environment interactions")
        methods = candidates.get("candidates")
        if not isinstance(methods, dict) or not methods:
            raise ValueError("candidate manifest is incomplete")
        self._candidates: dict[tuple[str, str], str] = {}
        for method, rows in methods.items():
            if not isinstance(rows, list) or len(rows) != 4:
                raise ValueError("candidate manifest must contain four candidates per method")
            for row in rows:
                if not isinstance(row, dict) or row.get("environment_interactions") != declared:
                    raise ValueError("all candidates must have equal environment interactions")
                candidate_id = row.get("candidate_id")
                config_hash = row.get("config_hash")
                if not isinstance(candidate_id, str) or not isinstance(config_hash, str) or len(config_hash) != 64:
                    raise ValueError("candidate identity is incomplete")
                self._candidates[(str(method), candidate_id)] = config_hash
        if budget.get("decision", {}).get("selected_budget") != declared:
            raise ValueError("candidate and pilot budget manifests disagree")
        self.interactions = declared
        self.candidate_sha256 = _file_sha256(self.candidate_manifest)
        self.budget_sha256 = _file_sha256(self.budget_manifest)

    def append(self, row: Mapping[str, Any]) -> dict[str, Any]:
        if _file_sha256(self.candidate_manifest) != self.candidate_sha256:
            raise ValueError("candidate manifest changed after validation access")
        if _file_sha256(self.budget_manifest) != self.budget_sha256:
            raise ValueError("budget manifest changed after validation access")
        validate_validation_episode(row)
        identity = (row.get("method"), row.get("candidate_id"))
        if identity not in self._candidates or row.get("config_hash") != self._candidates[identity]:
            raise ValueError("validation row is not a frozen candidate")
        if row.get("interaction_count") != self.interactions:
            raise ValueError("validation row violates the equal environment interactions budget")
        previous = _load_json(self.ledger_path, "validation access ledger") if self.ledger_path.exists() else {
            "schema_version": "g5-validation-access-v1",
            "status": "validation_accessed_candidates_locked",
            "candidate_manifest_sha256": self.candidate_sha256,
            "budget_manifest_sha256": self.budget_sha256,
            "row_count": 0,
            "row_chain_sha256": "0" * 64,
            "sealed_accessed": False,
            "actual_unlock_count": 0,
        }
        if previous.get("candidate_manifest_sha256") != self.candidate_sha256 or previous.get("budget_manifest_sha256") != self.budget_sha256:
            raise ValueError("validation access ledger provenance drifted")
        row_raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        chain = hashlib.sha256((str(previous["row_chain_sha256"])).encode("ascii") + row_raw).hexdigest()
        updated = {**previous, "row_count": int(previous["row_count"]) + 1, "row_chain_sha256": chain}
        atomic_write_bytes(self.ledger_path, (json.dumps(updated, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        return updated

    def verify_rows(self, rows: list[Mapping[str, Any]]) -> None:
        """Verify a recovered JSONL prefix against the persisted hash chain."""

        if not self.ledger_path.is_file():
            if rows:
                raise ValueError("validation rows exist without an access ledger")
            return
        ledger = _load_json(self.ledger_path, "validation access ledger")
        if ledger.get("candidate_manifest_sha256") != self.candidate_sha256 or ledger.get("budget_manifest_sha256") != self.budget_sha256:
            raise ValueError("validation access ledger provenance drifted")
        chain = "0" * 64
        for row in rows:
            validate_validation_episode(row)
            raw = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            chain = hashlib.sha256(chain.encode("ascii") + raw).hexdigest()
        if ledger.get("row_count") != len(rows) or ledger.get("row_chain_sha256") != chain:
            raise ValueError("validation recovery row chain mismatch")


class ActionDrivenValidationEnv:
    """Attach deterministic local pest mortality to accepted physical spray events."""

    def __init__(
        self,
        physical_environment: Any,
        *,
        initial_pest: np.ndarray,
        mortality_per_l: float,
        partition: str = "validation",
        source_provenance: Mapping[str, Any] | None = None,
    ) -> None:
        physical_scenario_id = getattr(physical_environment, "scenario_id", None)
        _validate_partition_scenario(partition, physical_scenario_id)
        density = np.asarray(initial_pest, dtype=np.float64)
        if density.ndim != 2 or density.size == 0 or not np.isfinite(density).all() or np.any(density < 0):
            raise ValueError("initial pest field must be a finite non-negative matrix")
        if isinstance(mortality_per_l, bool) or not isinstance(mortality_per_l, (int, float)) or not math.isfinite(float(mortality_per_l)) or mortality_per_l <= 0:
            raise ValueError("mortality_per_l must be positive and finite")
        self.physical = physical_environment
        self.initial_pest = density.copy()
        self.mortality_per_l = float(mortality_per_l)
        self.pest = density.copy()
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self.partition = partition
        self.source_provenance = dict(source_provenance or {})
        self.replenished_resource = "pesticide"
        self.battery_replenishment_enabled = False

    @property
    def state(self) -> Any:
        return self.physical.state

    def _field_summary(self) -> tuple[float, ...]:
        return (
            float(np.mean(self.pest)),
            float(np.max(self.pest)),
            float(np.min(self.pest)),
            float(np.count_nonzero(self.pest < self.initial_pest) / self.pest.size),
        )

    def reset(self, *, scenario_id: int | None = None) -> dict[str, Any]:
        self.pest = self.initial_pest.copy()
        self.spray_action_count = 0
        self.sprayed_pesticide_l = 0.0
        self.physical.initial_total_pest = float(np.sum(self.initial_pest))
        self.physical.final_total_pest = float(np.sum(self.pest))
        self.physical.field_summary = self._field_summary()
        return self.physical.reset(scenario_id=scenario_id)

    def _cell_for_uav(self, uav_id: str) -> tuple[int, int]:
        uav = next(item for item in self.physical.state.uavs if item.uav_id == uav_id)
        x0, y0, x1, y1 = self.physical.graph.aoi_bounds_m
        x_fraction = 0.0 if x1 <= x0 else (uav.x_m - x0) / (x1 - x0)
        y_fraction = 0.0 if y1 <= y0 else (uav.y_m - y0) / (y1 - y0)
        col = min(self.pest.shape[1] - 1, max(0, int(round(x_fraction * (self.pest.shape[1] - 1)))))
        row = min(self.pest.shape[0] - 1, max(0, int(round(y_fraction * (self.pest.shape[0] - 1)))))
        return row, col

    def step(self, action_result: Any, **kwargs: Any) -> dict[str, Any]:
        pest_before = float(np.sum(self.pest))
        physical_view = self.physical.step(action_result, **kwargs)
        for event in physical_view.get("events", ()):
            if getattr(event, "kind", None) != "spray":
                continue
            amount_l = float(dict(event.payload).get("delta_l", 0.0))
            if amount_l <= 0:
                continue
            row, col = self._cell_for_uav(str(event.entity_id))
            self.pest[row, col] = max(0.0, self.pest[row, col] - amount_l * self.mortality_per_l)
            self.spray_action_count += 1
            self.sprayed_pesticide_l += amount_l
        self.physical.final_total_pest = float(np.sum(self.pest))
        self.physical.field_summary = self._field_summary()
        # Problem2CooperativeEnv built its first next view before local pest
        # mortality was applied. Rebuild from the same completed physical state
        # so actors and the critic receive the action-complete ecological view.
        view = self.physical._make_view(events=tuple(physical_view.get("events", ())))
        if "sampled_actions" in physical_view:
            view["sampled_actions"] = physical_view["sampled_actions"]
        immediate_decrease = max(0.0, pest_before - self.physical.final_total_pest)
        initial_total = float(np.sum(self.initial_pest))
        view["pest_total_before"] = pest_before
        view["pest_total"] = self.physical.final_total_pest
        view["team_reward"] = immediate_decrease / initial_total
        view["metric_source"] = "action_driven_environment"
        return view

    def episode_record(self) -> Any:
        return self.physical.episode_record()


def _road_cache_expectation(metadata: Mapping[str, Any]) -> RoadCacheExpectation:
    return RoadCacheExpectation(
        scale_id=str(metadata["scale_id"]),
        source_sha256=str(metadata["source"]["sha256"]),
        source_crs=str(metadata["source"]["crs"]),
        target_crs=str(metadata["projection"]["target_crs"]),
        aoi_bounds_m=tuple(float(value) for value in metadata["projection"]["aoi_bounds_m"]),
        grid_shape=tuple(int(value) for value in metadata["grid"]["shape"]),
        preprocess_version=str(metadata["preprocess_version"]),
        generator_commit=str(metadata["generator"]["git_commit"]),
        generator_sha256=str(metadata["generator"]["sha256"]),
    )


def _validate_partition_scenario(partition: str, scenario_id: int) -> None:
    if partition not in {"development", "validation"}:
        raise ValueError("physical scenario partition must be exactly development or validation")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise ValueError(f"{partition} scenario identity must be an integer")
    if scenario_id in SEALED_SCENARIO_IDS:
        raise ValueError("sealed scenarios are forbidden everywhere in G5")
    allowed = DEVELOPMENT_SCENARIO_IDS if partition == "development" else VALIDATION_SCENARIO_IDS
    if scenario_id not in allowed:
        start, stop = allowed.start, allowed.stop - 1
        raise ValueError(f"only {partition} scenarios {start}-{stop} may be constructed in G5")


def _build_physical_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str,
    partition: str,
) -> ActionDrivenValidationEnv:
    _validate_partition_scenario(partition, scenario_id)
    root = Path(repository_root).resolve()
    contract = load_g5_contract(root)
    scenario_contract = contract.physical_scenario
    config = load_g2_config(root / "configs" / "problem2" / "g2_deterministic.yaml")
    scale_config = next((item for item in config.scales if item.scale_id == scale), None)
    if scale_config is None:
        raise ValueError(f"unknown frozen scale {scale!r}")
    cache_root = root / "outputs" / "problem2_sr_mappo_v1" / "g2" / "roads" / scale
    metadata = _load_json(cache_root / "metadata.json", "frozen G2 road metadata")
    graph = load_road_cache(
        cache_root / "road_graph.npz",
        cache_root / "metadata.json",
        _road_cache_expectation(metadata),
    )
    if INITIAL_ONBOARD_PESTICIDE_L > config.usable_capacity_l + config.tolerance:
        raise ValueError("frozen initial onboard pesticide exceeds usable UAV capacity")
    rng = np.random.default_rng(scenario_id)
    primary_nodes = np.flatnonzero(
        np.asarray([
            int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
            for row, col in zip(graph.node_rows, graph.node_cols)
        ], dtype=bool)
    )
    if not primary_nodes.size:
        raise ValueError("frozen road graph has no primary component nodes")
    try:
        uav_count = int(scale.rsplit("_d", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError("scale does not encode its UAV count") from exc
    selected = rng.choice(primary_nodes, size=uav_count + 1, replace=primary_nodes.size < uav_count + 1)
    uavs = tuple(
        UavState(
            f"uav-{index}",
            float(graph.node_x_m[int(node)]),
            float(graph.node_y_m[int(node)]),
            pesticide_l=INITIAL_ONBOARD_PESTICIDE_L,
        )
        for index, node in enumerate(selected[:-1])
    )
    vehicle_node = int(selected[-1])
    vehicle = VehicleState(
        "vehicle-0",
        vehicle_node,
        float(graph.node_x_m[vehicle_node]),
        float(graph.node_y_m[vehicle_node]),
        inventory_l=config.vehicle_inventory_l,
    )
    state = EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, vehicle.inventory_l))
    raw_pest = rng.gamma(
        shape=scenario_contract.gamma_shape,
        scale=scenario_contract.gamma_scale,
        size=scale_config.grid_shape,
    )
    pest = raw_pest * (
        scenario_contract.normalized_initial_pest_total / float(np.sum(raw_pest))
    )
    physical = _Task12PhysicalEnv(
        state,
        graph,
        config,
        max_steps=scale_config.max_steps,
        scenario_id=scenario_id,
    )
    scenario_contract_path = root / "docs/evidence/g5/physical_scenario_contract.yaml"
    scenario_contract_sha256 = contract.file_hashes[
        "docs/evidence/g5/physical_scenario_contract.yaml"
    ]
    content_metadata = {
        "partition": partition,
        "scenario_id": scenario_id,
        "scale_id": scale,
        "physical_scenario_contract_sha256": scenario_contract_sha256,
        "initial_pest_shape": list(pest.shape),
    }
    content_hasher = hashlib.sha256()
    content_hasher.update(
        json.dumps(content_metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    content_hasher.update(np.asarray(pest, dtype="<f8").tobytes(order="C"))
    source_provenance = {
        "environment_factory": f"problem2.training.tuning.build_{partition}_environment",
        "road_cache_scale": scale,
        "road_cache_metadata_sha256": _file_sha256(cache_root / "metadata.json"),
        "road_cache_graph_sha256": _file_sha256(cache_root / "road_graph.npz"),
        "road_source_sha256": str(metadata["source"]["sha256"]),
        "physical_scenario_contract": str(scenario_contract_path),
        "physical_scenario_contract_sha256": scenario_contract_sha256,
        "physical_scenario_assumption_status": scenario_contract.assumption_status,
        "physical_scenario_empirical_claim": scenario_contract.empirical_claim,
        "physical_scenario_deployment_claim": scenario_contract.deployment_claim,
        "gamma_shape": scenario_contract.gamma_shape,
        "gamma_shape_unit": scenario_contract.gamma_shape_unit,
        "gamma_scale": scenario_contract.gamma_scale,
        "gamma_scale_unit": scenario_contract.gamma_scale_unit,
        "normalized_initial_pest_total": scenario_contract.normalized_initial_pest_total,
        "normalized_initial_pest_total_unit": scenario_contract.normalized_initial_pest_total_unit,
        "spray_mortality_per_l": scenario_contract.spray_mortality_per_l,
        "spray_mortality_unit": scenario_contract.spray_mortality_unit,
        "scenario_content_sha256": content_hasher.hexdigest(),
        "scenario_content_hash_encoding": scenario_contract.content_hash_encoding,
    }
    return ActionDrivenValidationEnv(
        physical,
        initial_pest=pest,
        mortality_per_l=scenario_contract.spray_mortality_per_l,
        partition=partition,
        source_provenance=source_provenance,
    )


def build_development_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str = "g20x20_d2",
) -> ActionDrivenValidationEnv:
    """Create one development scenario from the frozen G2 road cache."""

    return _build_physical_environment(
        repository_root,
        scenario_id=scenario_id,
        scale=scale,
        partition="development",
    )


def build_validation_environment(
    repository_root: Path | str,
    *,
    scenario_id: int,
    scale: str = "g30x50_d4",
) -> ActionDrivenValidationEnv:
    """Create one validation-only scenario from the frozen G2 road cache."""

    return _build_physical_environment(
        repository_root,
        scenario_id=scenario_id,
        scale=scale,
        partition="validation",
    )


__all__ = [
    "ActionDrivenValidationEnv",
    "DEVELOPMENT_SCENARIO_IDS",
    "INITIAL_ONBOARD_PESTICIDE_L",
    "SEALED_SCENARIO_IDS",
    "VALIDATION_SCENARIO_IDS",
    "ValidationAccessLedger",
    "build_development_environment",
    "build_validation_environment",
    "validate_validation_episode",
]
