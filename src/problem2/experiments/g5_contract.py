from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

import yaml


LEARNING_METHODS = (
    "sr_mappo_mobile",
    "mappo_mobile",
    "ippo_mobile",
    "maddpg_mobile",
    "iql_mobile",
)
PROBLEM2_CONDITIONS = (
    "sr_mappo_mobile",
    "sr_mappo_fixed",
    "sr_mappo_astar",
    "mappo_mobile",
    "sr_mappo_two_stage",
    "sr_mappo_nearest",
    "sr_mappo_urgency",
)
FROZEN_CANDIDATE_BUDGETS = (50000, 100000, 200000)
FROZEN_CHECKPOINT_COUNT = 20
FROZEN_MAX_PROJECTED_HOURS = 12.0
REPRESENTATIVE_SCALE = "g30x50_d4"
FAIRNESS_FLAGS = (
    "same_environment",
    "same_environment_interactions",
    "same_episode_horizon",
    "same_training_scenes",
    "same_training_seeds",
    "same_evaluation_scenarios",
    "same_role_observations",
    "same_action_masks",
    "same_team_reward",
    "same_information_conditions",
    "same_total_pesticide",
    "same_initial_vehicle_inventory",
    "same_transfer_rate",
    "same_service_cap",
    "same_setup_time",
    "same_evaluation_budget",
    "no_future_information",
)
STABILITY_FLAGS = (
    "observation_normalization",
    "return_normalization",
    "orthogonal_initialization",
    "layer_normalization",
    "value_clipping",
    "huber_value_loss",
    "learning_rate_decay",
)
ON_POLICY_METHODS = (
    "sr_mappo_mobile",
    "mappo_mobile",
    "ippo_mobile",
)
METRIC_NAMES = (
    "reduction_rate",
    "success_at_0_85",
    "rendezvous_distance_m",
    "vehicle_service_travel_m",
    "waiting_steps",
    "completed_request_waiting_steps",
    "pesticide_disabled_steps",
    "return_steps",
    "effective_spray_steps",
    "decision_runtime_s",
)
CONTRACT_FILES = (
    "configs/problem2/g5/protocol.yaml",
    "configs/problem2/g5/methods.yaml",
    "configs/problem2/g5/pilot.yaml",
    "configs/problem2/g5/tuning_candidates.yaml",
    "configs/problem2/g5/budget_rule.yaml",
    "configs/problem2/g5/metrics.yaml",
    "configs/problem2/g5/statistics.yaml",
    "configs/problem2/g5/families.yaml",
    "configs/problem2/g5/ablations.yaml",
    "configs/problem2/g5/sensitivity.yaml",
    "docs/evidence/g5/problem1_lineage.yaml",
    "docs/evidence/g5/heterogeneous_interface.yaml",
    "docs/evidence/g5/fairness_matrix.yaml",
    "docs/evidence/g5/exclusion_contract.yaml",
    "docs/evidence/g5/checkpoint_selection.yaml",
    "docs/evidence/g1/scenario_seed_manifest.yaml",
    "docs/evidence/g1/sealed_test_lock.yaml",
    "requirements-g3.lock",
    "requirements-g5.lock",
)
FORBIDDEN_NAME_RE = re.compile(r"(?i)(?:\bHAPPO\b|AG-SR-MAPPO)")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
REDUCTION_RATE_DEFINITION = (
    "one_minus_final_total_pest_divided_by_initial_total_pest_plus_epsilon"
)
REDUCTION_RATE_EPSILON = 1.0e-12


class G5ContractError(ValueError):
    """Raised when a frozen G5 contract is incomplete or inconsistent."""


class BudgetSelectionError(G5ContractError):
    """Raised when runtime evidence cannot select a frozen formal budget."""


@dataclass(frozen=True)
class TuningCandidate:
    candidate_id: str
    parameters: Mapping[str, int | float]
    config_hash: str


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    value_type: str
    unit: str
    category: str
    definition: str
    epsilon: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class BudgetDecision:
    selected_budget: int
    checkpoint_interval: int
    checkpoint_count: int
    projected_slowest_hours: float


@dataclass(frozen=True)
class G5Contract:
    source_root: Path
    algorithm_name: str
    problem_description: str
    methods: tuple[str, ...]
    conditions: tuple[str, ...]
    stability_components: Mapping[str, Mapping[str, bool]]
    partitions: Mapping[str, tuple[int, ...]]
    fairness: Mapping[str, bool]
    primary_budget: str
    reported_budgets: tuple[str, ...]
    tuning_candidates: Mapping[str, tuple[TuningCandidate, ...]]
    metrics: Mapping[str, MetricDefinition]
    problem1_commit: str
    problem1_blobs: Mapping[str, str]
    problem1_runtime_import_allowed: bool
    file_hashes: Mapping[str, str]
    validation_accessed: bool
    sealed_accessed: bool


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.Node
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise G5ContractError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise G5ContractError(f"{name} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise G5ContractError(f"{name} keys must be text")
    return value


def _sequence(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise G5ContractError(f"{name} must be a list")
    return value


def _require_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    observed = set(value)
    unknown = sorted(observed - expected)
    missing = sorted(expected - observed)
    if unknown:
        raise G5ContractError(f"{name} contains unknown keys: {', '.join(unknown)}")
    if missing:
        raise G5ContractError(f"{name} is missing keys: {', '.join(missing)}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise G5ContractError(f"{name} must be non-empty text")
    return value.strip()


def _integer(value: Any, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise G5ContractError(f"{name} must be an integer")
    if positive and value <= 0:
        raise G5ContractError(f"{name} must be positive")
    return value


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise G5ContractError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise G5ContractError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise G5ContractError(f"{name} must be positive")
    return result


def _strict_bool(value: Any, name: str, expected: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise G5ContractError(f"{name} must be boolean")
    if expected is not None and value is not expected:
        raise G5ContractError(f"{name} must be {str(expected).lower()}")
    return value


def _integer_tuple(value: Any, name: str) -> tuple[int, ...]:
    items = _sequence(value, name)
    result = tuple(_integer(item, f"{name} item") for item in items)
    if len(result) != len(set(result)):
        raise G5ContractError(f"{name} contains duplicate IDs")
    return result


def _text_tuple(value: Any, name: str) -> tuple[str, ...]:
    items = _sequence(value, name)
    result = tuple(_text(item, f"{name} item") for item in items)
    if len(result) != len(set(result)):
        raise G5ContractError(f"{name} contains duplicate values")
    return result


def _range_tuple(value: Any, name: str) -> tuple[int, ...]:
    record = _mapping(value, name)
    _require_keys(record, {"start", "end"}, name)
    start = _integer(record["start"], f"{name}.start")
    end = _integer(record["end"], f"{name}.end")
    if start > end:
        raise G5ContractError(f"{name} range is reversed")
    return tuple(range(start, end + 1))


def _validate_finite(value: Any, location: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _validate_finite(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_finite(nested, f"{location}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise G5ContractError(f"{location} must be finite")


def _validate_names(value: Any, location: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _validate_names(key, f"{location}.key")
            _validate_names(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_names(nested, f"{location}[{index}]")
    elif isinstance(value, str) and FORBIDDEN_NAME_RE.search(value):
        raise G5ContractError(f"forbidden algorithm name at {location}: {value}")


def _load_yaml(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        payload = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except G5ContractError:
        raise
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise G5ContractError(f"cannot load {relative}: {exc}") from exc
    result = _mapping(payload, relative)
    _validate_finite(result, relative)
    _validate_names(result, relative)
    return result


def _header(
    payload: dict[str, Any],
    contract_id: str,
    name: str,
    extra_keys: set[str],
) -> None:
    _require_keys(
        payload,
        {"schema_version", "contract_id", "status", *extra_keys},
        name,
    )
    if payload["schema_version"] != "g5.v1":
        raise G5ContractError(f"{name}.schema_version must be g5.v1")
    if payload["contract_id"] != contract_id:
        raise G5ContractError(f"{name}.contract_id must be {contract_id}")
    if payload["status"] != "design_frozen":
        raise G5ContractError(f"{name}.status must be design_frozen")


def _registry_header(
    payload: dict[str, Any],
    registry_id: str,
    name: str,
    extra_keys: set[str],
) -> None:
    _require_keys(
        payload,
        {"schema_version", "registry_id", "status", *extra_keys},
        name,
    )
    if payload["schema_version"] != "g5.v1":
        raise G5ContractError(f"{name}.schema_version must be g5.v1")
    if payload["registry_id"] != registry_id:
        raise G5ContractError(f"{name}.registry_id must be {registry_id}")
    if payload["status"] != "design_frozen":
        raise G5ContractError(f"{name}.status must be design_frozen")


def _load_protocol(root: Path) -> tuple[str, str, dict[str, tuple[int, ...]], bool, bool]:
    name = "protocol"
    payload = _load_yaml(root, "configs/problem2/g5/protocol.yaml")
    _header(
        payload,
        "G5-PROTOCOL",
        name,
        {"algorithm_name", "problem_description", "output_root", "resources", "partitions", "access"},
    )
    algorithm_name = _text(payload["algorithm_name"], "protocol.algorithm_name")
    if algorithm_name != "SR-MAPPO":
        raise G5ContractError("protocol algorithm name must be SR-MAPPO")
    problem_description = _text(payload["problem_description"], "protocol.problem_description")
    if problem_description != "air_ground_heterogeneous_extension":
        raise G5ContractError("protocol problem description is invalid")
    if payload["output_root"] != "outputs/problem2_sr_mappo_v1/g5":
        raise G5ContractError("protocol output root is not canonical")
    resources = _mapping(payload["resources"], "protocol.resources")
    _require_keys(resources, {"replenished_resource", "battery_replenishment_enabled"}, "protocol.resources")
    if resources["replenished_resource"] != "pesticide":
        raise G5ContractError("the replenished resource must be pesticide")
    if resources["battery_replenishment_enabled"] is not False:
        raise G5ContractError("battery replenishment must remain disabled")

    raw = _mapping(payload["partitions"], "protocol.partitions")
    _require_keys(
        raw,
        {"development_training", "development_scenarios", "formal_training", "validation", "sealed_test"},
        "protocol.partitions",
    )
    development_training = _mapping(raw["development_training"], "development_training")
    formal_training = _mapping(raw["formal_training"], "formal_training")
    _require_keys(development_training, {"seeds"}, "development_training")
    _require_keys(formal_training, {"seeds"}, "formal_training")
    partitions = {
        "development_training": _integer_tuple(development_training["seeds"], "development training seeds"),
        "development_scenarios": _range_tuple(raw["development_scenarios"], "development scenarios"),
        "formal_training": _integer_tuple(formal_training["seeds"], "formal training seeds"),
        "validation": _range_tuple(raw["validation"], "validation scenarios"),
        "sealed_test": _range_tuple(raw["sealed_test"], "sealed test scenarios"),
    }
    expected = {
        "development_training": (51001, 51002, 51003),
        "development_scenarios": tuple(range(10000, 10020)),
        "formal_training": (42, 123, 2024, 3407, 7919),
        "validation": tuple(range(20000, 20050)),
        "sealed_test": tuple(range(30000, 30100)),
    }
    if partitions != expected:
        raise G5ContractError("G5 partition identities drifted from the frozen protocol")
    values = list(partitions.items())
    for index, (left_name, left) in enumerate(values):
        for right_name, right in values[index + 1 :]:
            if set(left) & set(right):
                raise G5ContractError(f"partition overlap: {left_name} and {right_name}")

    access = _mapping(payload["access"], "protocol.access")
    _require_keys(
        access,
        {"validation_accessed", "validation_tuning_authorized", "sealed_accessed", "actual_unlock_count"},
        "protocol.access",
    )
    validation_accessed = _strict_bool(access["validation_accessed"], "validation access", False)
    _strict_bool(access["validation_tuning_authorized"], "validation tuning authorization", False)
    sealed_accessed = _strict_bool(access["sealed_accessed"], "sealed access", False)
    if _integer(access["actual_unlock_count"], "actual unlock count") != 0:
        raise G5ContractError("sealed access actual unlock count must be zero")
    return algorithm_name, problem_description, partitions, validation_accessed, sealed_accessed


def _load_methods(
    root: Path,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    Mapping[str, Mapping[str, bool]],
]:
    payload = _load_yaml(root, "configs/problem2/g5/methods.yaml")
    _header(
        payload,
        "G5-METHODS",
        "methods",
        {
            "learning_algorithms",
            "on_policy_stability_components",
            "problem2_conditions",
        },
    )
    methods: list[str] = []
    for index, raw in enumerate(_sequence(payload["learning_algorithms"], "learning_algorithms")):
        item = _mapping(raw, f"learning_algorithms[{index}]")
        _require_keys(item, {"id", "display_name", "algorithm_family", "role_handling"}, f"learning_algorithms[{index}]")
        methods.append(_text(item["id"], f"learning_algorithms[{index}].id"))
        _text(item["display_name"], f"learning_algorithms[{index}].display_name")
        _text(item["algorithm_family"], f"learning_algorithms[{index}].algorithm_family")
        _text(item["role_handling"], f"learning_algorithms[{index}].role_handling")
    conditions: list[str] = []
    for index, raw in enumerate(_sequence(payload["problem2_conditions"], "problem2_conditions")):
        item = _mapping(raw, f"problem2_conditions[{index}]")
        _require_keys(item, {"id", "condition_type", "vehicle_policy", "vehicle_trainable"}, f"problem2_conditions[{index}]")
        conditions.append(_text(item["id"], f"problem2_conditions[{index}].id"))
        _text(item["condition_type"], f"problem2_conditions[{index}].condition_type")
        _text(item["vehicle_policy"], f"problem2_conditions[{index}].vehicle_policy")
        _strict_bool(item["vehicle_trainable"], f"problem2_conditions[{index}].vehicle_trainable")
    if tuple(methods) != LEARNING_METHODS:
        raise G5ContractError("learning algorithms do not match the exact G5 method family")
    if tuple(conditions) != PROBLEM2_CONDITIONS:
        raise G5ContractError("Problem-2 conditions do not match the frozen family")
    raw_stability = _mapping(
        payload["on_policy_stability_components"],
        "methods.on_policy_stability_components",
    )
    _require_keys(
        raw_stability,
        set(ON_POLICY_METHODS),
        "methods.on_policy_stability_components",
    )
    stability: dict[str, Mapping[str, bool]] = {}
    for method_id in ON_POLICY_METHODS:
        raw_flags = _mapping(
            raw_stability[method_id],
            f"methods.on_policy_stability_components.{method_id}",
        )
        _require_keys(
            raw_flags,
            set(STABILITY_FLAGS),
            f"methods.on_policy_stability_components.{method_id}",
        )
        expected = method_id == "sr_mappo_mobile"
        flags = {
            flag: _strict_bool(
                raw_flags[flag],
                f"methods.on_policy_stability_components.{method_id}.{flag}",
                expected,
            )
            for flag in STABILITY_FLAGS
        }
        stability[method_id] = MappingProxyType(flags)
    return tuple(methods), tuple(conditions), MappingProxyType(stability)


def _canonical_hash(method: str, candidate_id: str, parameters: Mapping[str, Any]) -> str:
    content = json.dumps(
        {"candidate_id": candidate_id, "method": method, "parameters": parameters},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _load_tuning(root: Path) -> Mapping[str, tuple[TuningCandidate, ...]]:
    payload = _load_yaml(root, "configs/problem2/g5/tuning_candidates.yaml")
    _header(payload, "G5-TUNING-CANDIDATES", "tuning candidates", {"immutable", "selection_rule", "candidate_sets"})
    _strict_bool(payload["immutable"], "tuning candidates immutable", True)
    rule = _mapping(payload["selection_rule"], "selection_rule")
    _require_keys(rule, {"primary", "tie_breakers"}, "selection_rule")
    if rule["primary"] != "mean_validation_reduction_rate" or _text_tuple(rule["tie_breakers"], "tie breakers") != (
        "higher_success_probability",
        "lower_interaction_count",
        "lexicographically_smaller_config_hash",
    ):
        raise G5ContractError("tuning selection rule drifted")
    raw_sets = _mapping(payload["candidate_sets"], "candidate_sets")
    _require_keys(raw_sets, set(LEARNING_METHODS), "candidate_sets")
    result: dict[str, tuple[TuningCandidate, ...]] = {}
    for method in LEARNING_METHODS:
        candidates: list[TuningCandidate] = []
        for index, raw in enumerate(_sequence(raw_sets[method], f"candidate_sets.{method}"), start=1):
            item = _mapping(raw, f"candidate_sets.{method}[{index - 1}]")
            _require_keys(item, {"candidate_id", "parameters"}, f"candidate_sets.{method}[{index - 1}]")
            candidate_id = _text(item["candidate_id"], "candidate_id")
            if candidate_id != f"c{index:02d}":
                raise G5ContractError(f"{method} candidate IDs are not canonical")
            parameters = _mapping(item["parameters"], f"{method}.{candidate_id}.parameters")
            expected_keys = (
                {"learning_rate", "clip_radius", "entropy_coefficient", "discount", "gae_lambda", "hidden_width", "hidden_depth", "rollout_horizon", "ppo_epochs", "minibatch_size"}
                if method in LEARNING_METHODS[:3]
                else {"hidden_width", "hidden_depth", "replay_capacity", "discount", "exploration_initial", "exploration_final", "actor_lr", "critic_lr", "tau", "batch_size"}
                if method == "maddpg_mobile"
                else {"hidden_width", "hidden_depth", "replay_capacity", "discount", "epsilon_initial", "epsilon_final", "learning_rate", "target_update_interval", "epsilon_decay", "batch_size"}
            )
            _require_keys(parameters, expected_keys, f"{method}.{candidate_id}.parameters")
            frozen_parameters = MappingProxyType(dict(parameters))
            candidates.append(
                TuningCandidate(
                    candidate_id=candidate_id,
                    parameters=frozen_parameters,
                    config_hash=_canonical_hash(method, candidate_id, parameters),
                )
            )
        if len(candidates) != 4:
            raise G5ContractError(f"{method} must define exactly four tuning candidates")
        result[method] = tuple(candidates)

    on_policy_expected = ((32, 2, 64), (64, 2, 64), (64, 4, 128), (128, 4, 128))
    for method in LEARNING_METHODS[:3]:
        observed = tuple(
            (int(item.parameters["rollout_horizon"]), int(item.parameters["ppo_epochs"]), int(item.parameters["minibatch_size"]))
            for item in result[method]
        )
        if observed != on_policy_expected:
            raise G5ContractError(f"{method} on-policy candidate grid drifted")
        for item in result[method]:
            fixed = item.parameters
            if (
                fixed["learning_rate"], fixed["clip_radius"], fixed["entropy_coefficient"], fixed["discount"], fixed["gae_lambda"], fixed["hidden_width"], fixed["hidden_depth"]
            ) != (0.0003, 0.20, 0.010, 0.99, 0.95, 128, 2):
                raise G5ContractError(f"{method} fixed tuning center drifted")
    maddpg_expected = (
        (0.0001, 0.0003, 0.005, 64),
        (0.0003, 0.0003, 0.005, 64),
        (0.0001, 0.001, 0.010, 128),
        (0.0003, 0.001, 0.010, 128),
    )
    if tuple(
        (item.parameters["actor_lr"], item.parameters["critic_lr"], item.parameters["tau"], item.parameters["batch_size"])
        for item in result["maddpg_mobile"]
    ) != maddpg_expected:
        raise G5ContractError("MADDPG tuning candidate grid drifted")
    iql_expected = (
        (0.0001, 100, 0.999, 64),
        (0.0003, 100, 0.999, 64),
        (0.0003, 250, 0.995, 128),
        (0.0005, 250, 0.995, 128),
    )
    if tuple(
        (item.parameters["learning_rate"], item.parameters["target_update_interval"], item.parameters["epsilon_decay"], item.parameters["batch_size"])
        for item in result["iql_mobile"]
    ) != iql_expected:
        raise G5ContractError("IQL tuning candidate grid drifted")
    return MappingProxyType(result)


def _load_budget(root: Path) -> None:
    payload = _load_yaml(root, "configs/problem2/g5/budget_rule.yaml")
    _header(payload, "G5-BUDGET-RULE", "budget rule", {"representative_scale", "candidate_budgets", "max_projected_hours", "minimum_checkpoint_count", "checkpoint_target_count", "selection", "failure_policy"})
    if payload["representative_scale"] != REPRESENTATIVE_SCALE:
        raise G5ContractError("budget representative scale drifted")
    if _integer_tuple(payload["candidate_budgets"], "candidate budgets") != FROZEN_CANDIDATE_BUDGETS:
        raise G5ContractError("budget frozen candidate grid drifted")
    if _number(payload["max_projected_hours"], "max projected hours", positive=True) != FROZEN_MAX_PROJECTED_HOURS:
        raise G5ContractError("budget maximum projected hours drifted")
    if _integer(payload["minimum_checkpoint_count"], "minimum checkpoint count", positive=True) != 20:
        raise G5ContractError("minimum checkpoint count drifted")
    if _integer(payload["checkpoint_target_count"], "checkpoint target count", positive=True) != 20:
        raise G5ContractError("checkpoint target count drifted")
    if payload["selection"] != "largest_feasible_candidate" or payload["failure_policy"] != "fail_closed_no_invented_budget":
        raise G5ContractError("budget decision policy drifted")


def _load_pilot(root: Path, partitions: Mapping[str, tuple[int, ...]]) -> None:
    payload = _load_yaml(root, "configs/problem2/g5/pilot.yaml")
    _header(payload, "G5-PILOT", "pilot", {"training_seed_ids", "scenario_ids", "scales", "coverage", "formal_training_performed", "validation_accessed", "sealed_accessed"})
    if _integer_tuple(payload["training_seed_ids"], "pilot training seeds") != partitions["development_training"]:
        raise G5ContractError("pilot training partition does not match development IDs")
    if _range_tuple(payload["scenario_ids"], "pilot scenarios") != partitions["development_scenarios"]:
        raise G5ContractError("pilot scenario partition does not match development IDs")
    if _text_tuple(payload["scales"], "pilot scales") != ("g20x20_d2", "g30x50_d4"):
        raise G5ContractError("pilot scales must cover the frozen smallest and largest scales")
    if payload["coverage"] != "all_learning_methods_and_condition_types":
        raise G5ContractError("pilot coverage contract drifted")
    _strict_bool(payload["formal_training_performed"], "formal training performed", False)
    _strict_bool(payload["validation_accessed"], "pilot validation access", False)
    _strict_bool(payload["sealed_accessed"], "pilot sealed access", False)


def _load_metrics(root: Path) -> Mapping[str, MetricDefinition]:
    payload = _load_yaml(root, "configs/problem2/g5/metrics.yaml")
    _header(payload, "G5-METRICS", "metrics", {"metrics"})
    result: dict[str, MetricDefinition] = {}
    for index, raw in enumerate(_sequence(payload["metrics"], "metrics.metrics")):
        item = _mapping(raw, f"metrics[{index}]")
        required = {"name", "type", "unit", "category", "definition"}
        if item.get("name") == "reduction_rate":
            required.add("epsilon")
        elif item.get("name") == "success_at_0_85":
            required.add("threshold")
        _require_keys(item, required, f"metrics[{index}]")
        name = _text(item["name"], f"metrics[{index}].name")
        if name in result:
            raise G5ContractError(f"duplicate metric: {name}")
        threshold = _number(item["threshold"], f"metrics[{index}].threshold") if "threshold" in item else None
        epsilon = (
            _number(item["epsilon"], f"metrics[{index}].epsilon", positive=True)
            if "epsilon" in item
            else None
        )
        result[name] = MetricDefinition(
            name=name,
            value_type=_text(item["type"], f"metrics[{index}].type"),
            unit=_text(item["unit"], f"metrics[{index}].unit"),
            category=_text(item["category"], f"metrics[{index}].category"),
            definition=_text(item["definition"], f"metrics[{index}].definition"),
            epsilon=epsilon,
            threshold=threshold,
        )
    if tuple(result) != METRIC_NAMES:
        raise G5ContractError("formal G5 metric registry order or membership drifted")
    if result["success_at_0_85"].threshold != 0.85:
        raise G5ContractError("primary success threshold drifted")
    reduction = result["reduction_rate"]
    if reduction.definition != REDUCTION_RATE_DEFINITION:
        raise G5ContractError("reduction_rate definition drifted")
    if reduction.epsilon != REDUCTION_RATE_EPSILON:
        raise G5ContractError("reduction_rate epsilon drifted")
    return MappingProxyType(result)


def _load_statistics(root: Path) -> None:
    payload = _load_yaml(root, "configs/problem2/g5/statistics.yaml")
    _header(payload, "G5-STATISTICS", "statistics", {"independent_replication_unit", "paired_within_unit", "primary_outcomes", "success_threshold", "bootstrap", "practical_equivalence_margins", "multiplicity", "training_reward_is_diagnostic_only"})
    if payload["independent_replication_unit"] != "training_seed" or payload["paired_within_unit"] != "scenario_id":
        raise G5ContractError("statistical replication or pairing unit drifted")
    if _text_tuple(payload["primary_outcomes"], "statistics primary outcomes") != ("reduction_rate", "success_at_0_85"):
        raise G5ContractError("statistics primary outcomes drifted")
    if _number(payload["success_threshold"], "statistics success threshold") != 0.85:
        raise G5ContractError("statistics success threshold drifted")
    bootstrap = _mapping(payload["bootstrap"], "statistics.bootstrap")
    _require_keys(bootstrap, {"kind", "replicates", "rng_seed", "interval"}, "statistics.bootstrap")
    if bootstrap != {"kind": "hierarchical_paired", "replicates": 10000, "rng_seed": 20260822, "interval": "percentile_95"}:
        raise G5ContractError("hierarchical paired bootstrap contract drifted")
    margins = _mapping(payload["practical_equivalence_margins"], "statistics margins")
    _require_keys(margins, {"reduction_rate", "success_at_0_85"}, "statistics margins")
    if (_number(margins["reduction_rate"], "reduction margin"), _number(margins["success_at_0_85"], "success margin")) != (0.02, 0.05):
        raise G5ContractError("practical-equivalence margins drifted")
    multiplicity = _mapping(payload["multiplicity"], "statistics multiplicity")
    _require_keys(multiplicity, {"method", "applied_separately_by_confirmatory_family"}, "statistics multiplicity")
    if multiplicity["method"] != "holm":
        raise G5ContractError("multiplicity method must be Holm")
    _strict_bool(multiplicity["applied_separately_by_confirmatory_family"], "Holm family separation", True)
    _strict_bool(payload["training_reward_is_diagnostic_only"], "training reward diagnostic flag", True)


def _load_fairness(root: Path) -> tuple[Mapping[str, bool], str, tuple[str, ...]]:
    payload = _load_yaml(root, "docs/evidence/g5/fairness_matrix.yaml")
    _registry_header(payload, "G5-FAIRNESS-MATRIX", "fairness", {"primary_budget", "reported_budgets", "invariants", "algorithm_specific_tuning"})
    if payload["primary_budget"] != "environment_interactions":
        raise G5ContractError("primary fairness budget must be environment interactions")
    reported = _text_tuple(payload["reported_budgets"], "reported fairness budgets")
    if reported != ("optimizer_updates", "trainable_parameter_count", "wall_clock_runtime_s", "decision_runtime_s"):
        raise G5ContractError("reported fairness budgets drifted")
    invariants = _mapping(payload["invariants"], "fairness.invariants")
    _require_keys(invariants, set(FAIRNESS_FLAGS), "fairness.invariants")
    frozen: dict[str, bool] = {}
    for flag in FAIRNESS_FLAGS:
        frozen[flag] = _strict_bool(invariants[flag], f"fairness invariant {flag}", True)
    tuning = _mapping(payload["algorithm_specific_tuning"], "fairness.algorithm_specific_tuning")
    _require_keys(tuning, {"equal_candidate_count", "equal_environment_interactions", "candidates_hashed_before_validation"}, "fairness.algorithm_specific_tuning")
    for key, value in tuning.items():
        _strict_bool(value, f"fairness tuning {key}", True)
    return MappingProxyType(frozen), payload["primary_budget"], reported


def _git_text(repository: Path, *args: str) -> str:
    try:
        completed = subprocess.run(["git", *args], cwd=repository, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise G5ContractError("Git is unavailable for Problem-1 lineage resolution") from exc
    if completed.returncode != 0:
        raise G5ContractError(f"Problem-1 blob resolution failed: {' '.join(args)}")
    return completed.stdout.strip()


def _load_problem1_lineage(root: Path) -> tuple[str, Mapping[str, str], bool]:
    payload = _load_yaml(root, "docs/evidence/g5/problem1_lineage.yaml")
    _registry_header(payload, "G5-PROBLEM1-LINEAGE", "Problem-1 lineage", {"repository_path", "source_commit", "read_only", "runtime_import_allowed", "checkpoint_import_allowed", "output_or_result_import_allowed", "sources"})
    repository = Path(_text(payload["repository_path"], "Problem-1 repository path"))
    if not repository.is_dir():
        raise G5ContractError("Problem-1 repository path is unavailable")
    commit = _text(payload["source_commit"], "Problem-1 source commit")
    if commit != "1ca9e5ccc5f77ed775cd2b607dd70d635720accf":
        raise G5ContractError("Problem-1 source commit drifted")
    resolved = _git_text(repository, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if resolved != commit:
        raise G5ContractError("Problem-1 source commit is unresolved")
    _strict_bool(payload["read_only"], "Problem-1 read-only flag", True)
    runtime_allowed = _strict_bool(payload["runtime_import_allowed"], "Problem-1 runtime import", False)
    _strict_bool(payload["checkpoint_import_allowed"], "Problem-1 checkpoint import", False)
    _strict_bool(payload["output_or_result_import_allowed"], "Problem-1 output import", False)
    blobs: dict[str, str] = {}
    for index, raw in enumerate(_sequence(payload["sources"], "Problem-1 sources")):
        item = _mapping(raw, f"Problem-1 sources[{index}]")
        _require_keys(item, {"path", "blob_id", "adopted_concept", "destination"}, f"Problem-1 sources[{index}]")
        path = _text(item["path"], f"Problem-1 sources[{index}].path")
        blob = _text(item["blob_id"], f"Problem-1 sources[{index}].blob_id")
        if not SHA1_RE.fullmatch(blob):
            raise G5ContractError(f"Problem-1 blob ID is invalid: {path}")
        listing = _git_text(repository, "ls-tree", commit, "--", path)
        parts = listing.split(maxsplit=3)
        if len(parts) != 4 or parts[1] != "blob" or parts[2] != blob:
            raise G5ContractError(f"Problem-1 blob does not resolve: {path}")
        if path in blobs:
            raise G5ContractError(f"duplicate Problem-1 lineage path: {path}")
        blobs[path] = blob
        _text(item["adopted_concept"], f"Problem-1 sources[{index}].adopted_concept")
        _text(item["destination"], f"Problem-1 sources[{index}].destination")
    if len(blobs) != 8:
        raise G5ContractError("Problem-1 lineage must contain exactly eight source blobs")
    return commit, MappingProxyType(blobs), runtime_allowed


def _load_interface(root: Path, algorithm_name: str, problem_description: str) -> None:
    payload = _load_yaml(root, "docs/evidence/g5/heterogeneous_interface.yaml")
    _registry_header(payload, "G5-HETEROGENEOUS-INTERFACE", "heterogeneous interface", {"algorithm_name", "problem_description", "roles", "critic", "transition", "resources"})
    if payload["algorithm_name"] != algorithm_name or payload["problem_description"] != problem_description:
        raise G5ContractError("heterogeneous interface identity drifted")
    roles = _mapping(payload["roles"], "heterogeneous roles")
    _require_keys(roles, {"uav", "vehicle"}, "heterogeneous roles")
    for role, expected in {
        "uav": (2, True, 179, ("up", "down", "left", "right", "stay", "spray")),
        "vehicle": (1, False, 28, ("hold", "slot-0", "slot-1", "slot-2", "slot-3")),
    }.items():
        record = _mapping(roles[role], f"heterogeneous role {role}")
        _require_keys(record, {"count", "shared_parameters", "observation_dim", "action_names"}, f"heterogeneous role {role}")
        observed = (_integer(record["count"], f"{role} count"), _strict_bool(record["shared_parameters"], f"{role} sharing"), _integer(record["observation_dim"], f"{role} observation dim"), _text_tuple(record["action_names"], f"{role} actions"))
        if observed != expected:
            raise G5ContractError(f"heterogeneous {role} interface drifted")
    critic = _mapping(payload["critic"], "heterogeneous critic")
    _require_keys(critic, {"structured_state_dim", "actors_receive_critic_only_state"}, "heterogeneous critic")
    if _integer(critic["structured_state_dim"], "critic state dim") != 185:
        raise G5ContractError("critic state dimension drifted")
    _strict_bool(critic["actors_receive_critic_only_state"], "critic leakage", False)
    transition = _mapping(payload["transition"], "heterogeneous transition")
    _require_keys(transition, {"stores_exact_behavior_mask", "shared_team_reward", "deterministic_evaluation_freezes_state"}, "heterogeneous transition")
    for key, value in transition.items():
        _strict_bool(value, f"heterogeneous transition {key}", True)
    resources = _mapping(payload["resources"], "heterogeneous resources")
    _require_keys(resources, {"replenished_resource", "battery_replenishment_enabled"}, "heterogeneous resources")
    if resources["replenished_resource"] != "pesticide" or resources["battery_replenishment_enabled"] is not False:
        raise G5ContractError("heterogeneous interface must remain pesticide-only with battery replenishment disabled")


def _load_exclusions(root: Path) -> None:
    payload = _load_yaml(root, "docs/evidence/g5/exclusion_contract.yaml")
    _registry_header(payload, "G5-EXCLUSION-CONTRACT", "exclusion contract", {"allowed_reasons", "forbidden_reasons", "retry_uses_identical_identity"})
    if _text_tuple(payload["allowed_reasons"], "allowed exclusion reasons") != (
        "identity_or_hash_mismatch", "non_finite_output", "corrupt_or_truncated_artifact", "impossible_resource_conservation", "wrong_scenario_partition", "incomplete_horizon_without_valid_termination", "failed_deterministic_replay"
    ):
        raise G5ContractError("technical exclusion reasons drifted")
    if _text_tuple(payload["forbidden_reasons"], "forbidden exclusion reasons") != (
        "poor_performance", "long_waiting", "failure_to_reach_0_85", "unfavorable_method_ranking"
    ):
        raise G5ContractError("performance exclusion prohibitions drifted")
    _strict_bool(payload["retry_uses_identical_identity"], "identical retry identity", True)


def _load_checkpoint_selection(root: Path, partitions: Mapping[str, tuple[int, ...]]) -> None:
    payload = _load_yaml(root, "docs/evidence/g5/checkpoint_selection.yaml")
    _registry_header(payload, "G5-CHECKPOINT-SELECTION", "checkpoint selection", {"candidate_manifest_hashed_before_validation", "candidates_per_learning_algorithm", "validation_scenarios", "equal_environment_interactions", "selection_order", "candidate_edits_after_validation_access", "validation_accessed", "sealed_accessed", "actual_unlock_count"})
    _strict_bool(payload["candidate_manifest_hashed_before_validation"], "candidate manifest hash freeze", True)
    if _integer(payload["candidates_per_learning_algorithm"], "candidate count") != 4:
        raise G5ContractError("checkpoint selection must retain four candidates per learning algorithm")
    if _range_tuple(payload["validation_scenarios"], "checkpoint validation scenarios") != partitions["validation"]:
        raise G5ContractError("checkpoint selection validation partition drifted")
    _strict_bool(payload["equal_environment_interactions"], "checkpoint equal interactions", True)
    if _text_tuple(payload["selection_order"], "checkpoint selection order") != (
        "mean_validation_reduction_rate", "higher_success_probability", "lower_interaction_count", "lexicographically_smaller_config_hash"
    ):
        raise G5ContractError("checkpoint selection tie-break chain drifted")
    _strict_bool(payload["candidate_edits_after_validation_access"], "candidate edits after validation", False)
    _strict_bool(payload["validation_accessed"], "checkpoint validation access", False)
    _strict_bool(payload["sealed_accessed"], "checkpoint sealed access", False)
    if _integer(payload["actual_unlock_count"], "checkpoint actual unlock count") != 0:
        raise G5ContractError("checkpoint selection sealed access count must be zero")


def _load_g1_partitions(root: Path, partitions: Mapping[str, tuple[int, ...]]) -> None:
    payload = _load_yaml(root, "docs/evidence/g1/scenario_seed_manifest.yaml")
    _require_keys(payload, {"schema_version", "registry_id", "status", "development", "partitions", "overlap_policy"}, "G1 scenario seed registry")
    if (payload["schema_version"], payload["registry_id"], payload["status"], payload["overlap_policy"]) != ("g1.v1", "G1-SCENARIO-SEEDS", "design_frozen", "disjoint"):
        raise G5ContractError("G1 scenario seed registry header drifted")
    development = _mapping(payload["development"], "G1 development IDs")
    _require_keys(development, {"training_seeds", "scenario_range", "purpose", "tuning_allowed"}, "G1 development IDs")
    if _integer_tuple(development["training_seeds"], "G1 development training seeds") != partitions["development_training"] or _range_tuple(development["scenario_range"], "G1 development scenarios") != partitions["development_scenarios"]:
        raise G5ContractError("G1 development partition differs from G5")
    if development["purpose"] != "g5_development_smoke_and_pilot":
        raise G5ContractError("G1 development partition purpose drifted")
    _strict_bool(development["tuning_allowed"], "G1 development tuning", True)
    existing = _mapping(payload["partitions"], "G1 partitions")
    if tuple(existing["training"]["seeds"]) != partitions["formal_training"]:
        raise G5ContractError("G1 formal training identities changed")
    if tuple(range(existing["validation"]["start"], existing["validation"]["end"] + 1)) != partitions["validation"]:
        raise G5ContractError("G1 validation identities changed")
    if tuple(range(existing["sealed_test"]["start"], existing["sealed_test"]["end"] + 1)) != partitions["sealed_test"]:
        raise G5ContractError("G1 sealed identities changed")


def _load_sealed_lock(root: Path) -> None:
    payload = _load_yaml(root, "docs/evidence/g1/sealed_test_lock.yaml")
    if payload.get("maximum_unlock_count") != 1 or payload.get("actual_unlock_count") != 0:
        raise G5ContractError("sealed access lock counts drifted")
    if payload.get("status") != "locked" or payload.get("unlock_gate") != "G7":
        raise G5ContractError("sealed access remains locked until G7")
    if payload.get("battery_replenishment") != "inactive" or payload.get("resource_replenishment") != "pesticide_only":
        raise G5ContractError("sealed lock resource contract drifted")


def _load_task7_registries(root: Path) -> None:
    families = _load_yaml(root, "configs/problem2/g5/families.yaml")
    _header(families, "G5-FAMILIES", "families", {"families"})
    expected_families = {
        "algorithm_convergence": ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"),
        "algorithm_scale": ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"),
        "problem2_required": ("sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage"),
        "vehicle_heuristics": ("sr_mappo_nearest", "sr_mappo_urgency"),
        "sr_mappo_ablation": ("no_observation_normalization", "no_return_normalization", "no_network_stabilization", "no_robust_value_update", "no_learning_rate_decay"),
        "sr_mappo_sensitivity": ("learning_rate", "clip_range", "entropy_coef", "gamma", "gae_lambda"),
    }
    observed = _mapping(families["families"], "Task 7 families")
    if set(observed) != set(expected_families):
        raise G5ContractError("Task 7 family IDs drifted")
    expected_scales = ("g20x20_d2", "g20x30_d3", "g20x40_d3", "g30x30_d3", "g30x40_d4", "g30x50_d4")
    for family, conditions in expected_families.items():
        item = _mapping(observed[family], f"Task 7 family {family}")
        _require_keys(item, {"conditions", "scales", "seeds"}, f"Task 7 family {family}")
        if tuple(item["conditions"]) != conditions or tuple(item["seeds"]) != (42, 123, 2024, 3407, 7919):
            raise G5ContractError(f"Task 7 family {family} values drifted")
        expected = ("g30x30_d3",) if family in ("sr_mappo_ablation", "sr_mappo_sensitivity") else expected_scales
        if tuple(item["scales"]) != expected:
            raise G5ContractError(f"Task 7 family {family} scales drifted")

    ablations = _load_yaml(root, "configs/problem2/g5/ablations.yaml")
    _header(ablations, "G5-ABLATIONS", "ablations", {"full_condition", "remove_one"})
    if ablations["full_condition"] != "sr_mappo_mobile":
        raise G5ContractError("Task 7 ablation full condition drifted")
    expected_groups = {
        "no_observation_normalization": ["observation_normalization"],
        "no_return_normalization": ["return_normalization"],
        "no_network_stabilization": ["orthogonal_initialization", "layer_normalization"],
        "no_robust_value_update": ["value_clipping", "huber_value_loss"],
        "no_learning_rate_decay": ["learning_rate_decay"],
    }
    if ablations["remove_one"] != expected_groups:
        raise G5ContractError("Task 7 ablation groups drifted")

    sensitivity = _load_yaml(root, "configs/problem2/g5/sensitivity.yaml")
    _header(sensitivity, "G5-SENSITIVITY", "sensitivity", {"center", "algorithmic_axes", "mechanism_axes"})
    expected_center = {"learning_rate": 0.0003, "clip_range": 0.20, "entropy_coef": 0.010, "gamma": 0.99, "gae_lambda": 0.95}
    expected_algorithmic = {
        "learning_rate": [0.0001, 0.0003, 0.0005], "clip_range": [0.10, 0.20, 0.30],
        "entropy_coef": [0.005, 0.010, 0.020], "gamma": [0.95, 0.99, 0.995], "gae_lambda": [0.90, 0.95, 0.98],
    }
    expected_mechanism = {
        "initial_uav_pesticide_l": [0.05, 0.2875, 0.525], "vehicle_speed_m_s": [4, 8, 12],
        "transfer_rate_l_min": [2, 4, 8], "setup_time_s": [5, 10, 30], "rendezvous_radius_m": [5, 15, 30],
    }
    if sensitivity["center"] != expected_center or sensitivity["algorithmic_axes"] != expected_algorithmic or sensitivity["mechanism_axes"] != expected_mechanism:
        raise G5ContractError("Task 7 sensitivity registry drifted")


def _validate_dependency_locks(root: Path) -> None:
    g3 = (root / "requirements-g3.lock").read_text(encoding="utf-8").splitlines()
    if "torch==2.13.0+cpu" not in g3 or "--extra-index-url https://download.pytorch.org/whl/cpu" not in g3:
        raise G5ContractError("G3 CPU dependency lock changed")
    g5 = (root / "requirements-g5.lock").read_text(encoding="utf-8").splitlines()
    if g5 != [
        "# Verified environment: Python 3.11, CUDA 12.6 PyTorch.",
        "--index-url https://pypi.org/simple",
        "--extra-index-url https://download.pytorch.org/whl/cu126",
        "-r requirements-g2.lock",
        "torch==2.13.0+cu126",
    ]:
        raise G5ContractError("G5 CUDA dependency lock is not exact")


def load_g5_contract(root: Path) -> G5Contract:
    repository_root = Path(root).resolve()
    algorithm_name, problem_description, partitions, validation_accessed, sealed_accessed = _load_protocol(repository_root)
    methods, conditions, stability_components = _load_methods(repository_root)
    tuning_candidates = _load_tuning(repository_root)
    _load_budget(repository_root)
    _load_pilot(repository_root, partitions)
    metrics = _load_metrics(repository_root)
    _load_statistics(repository_root)
    fairness, primary_budget, reported_budgets = _load_fairness(repository_root)
    problem1_commit, problem1_blobs, runtime_allowed = _load_problem1_lineage(repository_root)
    _load_interface(repository_root, algorithm_name, problem_description)
    _load_exclusions(repository_root)
    _load_checkpoint_selection(repository_root, partitions)
    _load_g1_partitions(repository_root, partitions)
    _load_sealed_lock(repository_root)
    _load_task7_registries(repository_root)
    _validate_dependency_locks(repository_root)
    file_hashes = {
        relative: _sha256(repository_root / relative)
        for relative in CONTRACT_FILES
    }
    return G5Contract(
        source_root=repository_root,
        algorithm_name=algorithm_name,
        problem_description=problem_description,
        methods=methods,
        conditions=conditions,
        stability_components=stability_components,
        partitions=MappingProxyType(dict(partitions)),
        fairness=fairness,
        primary_budget=primary_budget,
        reported_budgets=reported_budgets,
        tuning_candidates=tuning_candidates,
        metrics=metrics,
        problem1_commit=problem1_commit,
        problem1_blobs=problem1_blobs,
        problem1_runtime_import_allowed=runtime_allowed,
        file_hashes=MappingProxyType(file_hashes),
        validation_accessed=validation_accessed,
        sealed_accessed=sealed_accessed,
    )


def select_formal_budget(
    runtime_rows: Iterable[Mapping[str, Any]],
    candidate_budgets: Sequence[int],
) -> BudgetDecision:
    candidates = tuple(candidate_budgets)
    if candidates != FROZEN_CANDIDATE_BUDGETS:
        raise BudgetSelectionError("candidate budgets must match the frozen candidate grid")
    rates: dict[str, list[float]] = {method: [] for method in LEARNING_METHODS}
    for index, row in enumerate(runtime_rows):
        if not isinstance(row, Mapping):
            raise BudgetSelectionError(f"runtime row {index} must be a mapping")
        method = row.get("method_id")
        scale = row.get("scale_id")
        if method not in rates or scale != REPRESENTATIVE_SCALE:
            raise BudgetSelectionError("runtime rows must cover only frozen methods at g30x50_d4")
        interactions = _integer(row.get("interactions"), f"runtime row {index} interactions", positive=True)
        elapsed = _number(row.get("elapsed_seconds"), f"runtime row {index} elapsed_seconds", positive=True)
        rates[str(method)].append(elapsed / interactions)
    if any(not values for values in rates.values()):
        raise BudgetSelectionError("runtime rows must cover every frozen learning method")
    conservative_seconds_per_interaction = max(max(values) for values in rates.values())
    decisions: list[BudgetDecision] = []
    for budget in candidates:
        if budget % FROZEN_CHECKPOINT_COUNT:
            continue
        checkpoint_interval = budget // FROZEN_CHECKPOINT_COUNT
        checkpoint_count = budget // checkpoint_interval
        projected_hours = conservative_seconds_per_interaction * budget / 3600.0
        if projected_hours <= FROZEN_MAX_PROJECTED_HOURS and checkpoint_count >= 20:
            decisions.append(
                BudgetDecision(
                    selected_budget=budget,
                    checkpoint_interval=checkpoint_interval,
                    checkpoint_count=checkpoint_count,
                    projected_slowest_hours=projected_hours,
                )
            )
    if not decisions:
        raise BudgetSelectionError("no frozen candidate budget satisfies the runtime rule")
    return decisions[-1]


__all__ = [
    "BudgetDecision",
    "BudgetSelectionError",
    "G5Contract",
    "G5ContractError",
    "MetricDefinition",
    "TuningCandidate",
    "load_g5_contract",
    "select_formal_budget",
]
