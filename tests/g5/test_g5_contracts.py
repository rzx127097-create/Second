from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from problem2.experiments.g5_contract import (
    BudgetSelectionError,
    G5ContractError,
    load_g5_contract,
    select_formal_budget,
)


ROOT = Path(__file__).resolve().parents[2]
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
FAIRNESS_FLAGS = {
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
}
STABILITY_FLAGS = {
    "observation_normalization",
    "return_normalization",
    "orthogonal_initialization",
    "layer_normalization",
    "value_clipping",
    "huber_value_loss",
    "learning_rate_decay",
}
LINEAGE_BLOBS = {
    "source/locust_rl_selected/agents/sr_mappo_agent.py": "fe3479f0a86f7957f3329650f24da1f561f40759",
    "source/locust_rl_selected/agents/mappo_agent.py": "e73a1be28469afc410ffadca7a48dbf9992e1a94",
    "source/locust_rl_selected/agents/ippo_agent.py": "e46b1dc8f673310587d2a1888d5cb77a322d906a",
    "source/locust_rl_selected/agents/maddpg_agent.py": "4371654da593b6d69e8e5853113fd6dbdbc2181f",
    "source/locust_rl_selected/agents/iql_agent.py": "0327d210e6d9c2fd21c48324963e4a4d0dd80953",
    "source/locust_rl_selected/training/trainer.py": "935aed90b16a897f4449673f530f0aa31a1536e3",
    "scripts/run_sr_mappo_ablation.py": "bfda945b554f3a299765aeef2a5df23b7b2d88d1",
    "scripts/run_sr_mappo_sensitivity.py": "9281a0dc76647e4ed534d36f165b058cd8a354a8",
}


def _copy_contract_root(tmp_path: Path) -> Path:
    candidate = tmp_path / "repo"
    shutil.copytree(ROOT / "configs", candidate / "configs")
    shutil.copytree(ROOT / "docs/evidence", candidate / "docs/evidence")
    for name in ("requirements-g2.lock", "requirements-g3.lock", "requirements-g5.lock"):
        shutil.copy2(ROOT / name, candidate / name)
    return candidate


def _mutate_yaml(root: Path, relative: str, mutate) -> None:
    path = root / relative
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _runtime_rows(elapsed_seconds: float) -> list[dict[str, object]]:
    return [
        {
            "method_id": method,
            "scale_id": "g30x50_d4",
            "interactions": 1000,
            "elapsed_seconds": elapsed_seconds,
        }
        for method in LEARNING_METHODS
    ]


def test_dependency_locks_preserve_g3_cpu_and_pin_g5_cuda() -> None:
    g3_before = (ROOT / "requirements-g3.lock").read_bytes()
    assert hashlib.sha256(g3_before).hexdigest() == (
        "d4bb20fafcfbc849b09419a764ac2e8aa37669ac9d6c8df0da4df42d4e90acbd"
    )
    assert b"torch==2.13.0+cpu" in g3_before
    assert b"https://download.pytorch.org/whl/cpu" in g3_before

    g5 = (ROOT / "requirements-g5.lock").read_text(encoding="utf-8").splitlines()
    assert g5 == [
        "# Verified environment: Python 3.11, CUDA 12.6 PyTorch.",
        "--index-url https://pypi.org/simple",
        "--extra-index-url https://download.pytorch.org/whl/cu126",
        "-r requirements-g2.lock",
        "torch==2.13.0+cu126",
    ]


def test_contract_registers_exact_learning_methods_and_problem2_conditions() -> None:
    contract = load_g5_contract(ROOT)
    assert contract.methods == LEARNING_METHODS
    assert contract.conditions == PROBLEM2_CONDITIONS
    assert contract.algorithm_name == "SR-MAPPO"
    assert contract.problem_description == "air_ground_heterogeneous_extension"


def test_contract_freezes_exact_on_policy_stability_differences() -> None:
    contract = load_g5_contract(ROOT)

    assert set(contract.stability_components) == {
        "sr_mappo_mobile",
        "mappo_mobile",
        "ippo_mobile",
    }
    assert set(contract.stability_components["sr_mappo_mobile"]) == STABILITY_FLAGS
    assert all(contract.stability_components["sr_mappo_mobile"].values())
    assert not any(contract.stability_components["mappo_mobile"].values())
    assert not any(contract.stability_components["ippo_mobile"].values())
    with pytest.raises(TypeError):
        contract.stability_components["mappo_mobile"]["value_clipping"] = True


@pytest.mark.parametrize(
    ("method_id", "flag", "value"),
    [
        ("sr_mappo_mobile", "value_clipping", False),
        ("mappo_mobile", "layer_normalization", True),
        ("ippo_mobile", "return_normalization", True),
    ],
)
def test_contract_rejects_on_policy_stability_drift(
    tmp_path: Path,
    method_id: str,
    flag: str,
    value: bool,
) -> None:
    root = _copy_contract_root(tmp_path)
    _mutate_yaml(
        root,
        "configs/problem2/g5/methods.yaml",
        lambda payload: payload["on_policy_stability_components"][method_id].__setitem__(
            flag, value
        ),
    )

    with pytest.raises(G5ContractError, match="stability"):
        load_g5_contract(root)


def test_problem1_lineage_resolves_exact_commit_and_blobs() -> None:
    contract = load_g5_contract(ROOT)
    assert contract.problem1_commit == "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"
    assert dict(contract.problem1_blobs) == LINEAGE_BLOBS
    assert contract.problem1_runtime_import_allowed is False


def test_partitions_are_exact_and_pairwise_disjoint() -> None:
    contract = load_g5_contract(ROOT)
    assert contract.partitions["development_training"] == (51001, 51002, 51003)
    assert contract.partitions["development_scenarios"] == tuple(range(10000, 10020))
    assert contract.partitions["formal_training"] == (42, 123, 2024, 3407, 7919)
    assert contract.partitions["validation"] == tuple(range(20000, 20050))
    assert contract.partitions["sealed_test"] == tuple(range(30000, 30100))
    values = list(contract.partitions.values())
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            assert set(left).isdisjoint(right)
    assert contract.validation_accessed is False
    assert contract.validation_tuning_authorized is True
    assert contract.sealed_accessed is False


def test_fairness_matrix_requires_every_frozen_invariant() -> None:
    contract = load_g5_contract(ROOT)
    assert set(contract.fairness) == FAIRNESS_FLAGS
    assert all(contract.fairness.values())
    assert contract.primary_budget == "environment_interactions"
    assert contract.reported_budgets == (
        "optimizer_updates",
        "trainable_parameter_count",
        "wall_clock_runtime_s",
        "decision_runtime_s",
    )


def test_on_policy_candidates_are_exact_and_immutable() -> None:
    contract = load_g5_contract(ROOT)
    expected = ((32, 2, 64), (64, 2, 64), (64, 4, 128), (128, 4, 128))
    for method in ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile"):
        candidates = contract.tuning_candidates[method]
        assert tuple(
            (
                candidate.parameters["rollout_horizon"],
                candidate.parameters["ppo_epochs"],
                candidate.parameters["minibatch_size"],
            )
            for candidate in candidates
        ) == expected
        assert all(candidate.parameters["learning_rate"] == 0.0003 for candidate in candidates)
        assert all(candidate.parameters["clip_radius"] == 0.20 for candidate in candidates)
        assert all(candidate.parameters["entropy_coefficient"] == 0.010 for candidate in candidates)
        assert all(candidate.parameters["discount"] == 0.99 for candidate in candidates)
        assert all(candidate.parameters["gae_lambda"] == 0.95 for candidate in candidates)
        with pytest.raises(TypeError):
            candidates[0].parameters["rollout_horizon"] = 999


def test_off_policy_candidates_are_exact() -> None:
    contract = load_g5_contract(ROOT)
    maddpg = contract.tuning_candidates["maddpg_mobile"]
    assert tuple(
        (
            item.parameters["actor_lr"],
            item.parameters["critic_lr"],
            item.parameters["tau"],
            item.parameters["batch_size"],
        )
        for item in maddpg
    ) == (
        (0.0001, 0.0003, 0.005, 64),
        (0.0003, 0.0003, 0.005, 64),
        (0.0001, 0.001, 0.010, 128),
        (0.0003, 0.001, 0.010, 128),
    )
    iql = contract.tuning_candidates["iql_mobile"]
    assert tuple(
        (
            item.parameters["learning_rate"],
            item.parameters["target_update_interval"],
            item.parameters["epsilon_decay"],
            item.parameters["batch_size"],
        )
        for item in iql
    ) == (
        (0.0001, 100, 0.999, 64),
        (0.0003, 100, 0.999, 64),
        (0.0003, 250, 0.995, 128),
        (0.0005, 250, 0.995, 128),
    )
    assert all(len(items) == 4 for items in contract.tuning_candidates.values())
    assert len({item.config_hash for items in contract.tuning_candidates.values() for item in items}) == 20


def test_budget_rule_selects_largest_feasible_frozen_candidate() -> None:
    decision = select_formal_budget(_runtime_rows(300.0), [50000, 100000, 200000])
    assert decision.selected_budget == 100000
    assert decision.checkpoint_interval == 5000
    assert decision.checkpoint_count == 20
    assert decision.projected_slowest_hours == pytest.approx(8.333333333333334)


def test_budget_rule_accepts_200000_when_conservative_projection_fits() -> None:
    decision = select_formal_budget(_runtime_rows(180.0), [50000, 100000, 200000])
    assert decision.selected_budget == 200000
    assert decision.checkpoint_interval == 10000


def test_budget_rule_fails_when_no_frozen_candidate_passes() -> None:
    with pytest.raises(BudgetSelectionError, match="no frozen candidate"):
        select_formal_budget(_runtime_rows(1000.0), [50000, 100000, 200000])


def test_budget_rule_rejects_invented_candidate_grid() -> None:
    with pytest.raises(BudgetSelectionError, match="frozen candidate grid"):
        select_formal_budget(_runtime_rows(100.0), [25000, 50000, 100000])


def test_metric_registry_freezes_primary_and_mechanism_semantics() -> None:
    contract = load_g5_contract(ROOT)
    assert tuple(contract.metrics) == (
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
    reduction = contract.metrics["reduction_rate"]
    assert reduction.category == "primary_outcome"
    assert reduction.epsilon == 1.0e-12
    assert contract.metrics["success_at_0_85"].threshold == 0.85
    assert contract.metrics["success_at_0_85"].epsilon is None
    assert contract.metrics["rendezvous_distance_m"].unit == "m"
    assert "shortest_feasible_road_network_route" in contract.metrics["rendezvous_distance_m"].definition
    assert "unresolved_terminal_requests" in contract.metrics["waiting_steps"].definition
    assert "excluding_environment_and_file_io" in contract.metrics["decision_runtime_s"].definition


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["metrics"][0].pop("epsilon", None), "missing keys"),
        (
            lambda payload: payload["metrics"][1].__setitem__("epsilon", 1.0e-12),
            "unknown keys",
        ),
        (
            lambda payload: payload["metrics"][0].__setitem__("epsilon", float("nan")),
            "finite",
        ),
        (lambda payload: payload["metrics"][0].__setitem__("epsilon", 0.0), "epsilon"),
        (lambda payload: payload["metrics"][0].__setitem__("epsilon", -1.0e-12), "epsilon"),
        (lambda payload: payload["metrics"][0].__setitem__("epsilon", 1.0e-9), "epsilon"),
    ],
)
def test_metric_registry_rejects_missing_extra_or_drifted_epsilon(
    tmp_path: Path, mutate, message: str
) -> None:
    candidate = _copy_contract_root(tmp_path)
    _mutate_yaml(candidate, "configs/problem2/g5/metrics.yaml", mutate)

    with pytest.raises(G5ContractError, match=message):
        load_g5_contract(candidate)


@pytest.mark.parametrize(
    ("relative", "mutate", "message"),
    [
        (
            "configs/problem2/g5/protocol.yaml",
            lambda payload: payload.__setitem__("unexpected", True),
            "unknown keys",
        ),
        (
            "configs/problem2/g5/budget_rule.yaml",
            lambda payload: payload.__setitem__("max_projected_hours", float("nan")),
            "finite",
        ),
        (
            "configs/problem2/g5/protocol.yaml",
            lambda payload: payload["resources"].__setitem__("battery_replenishment_enabled", True),
            "battery replenishment",
        ),
        (
            "configs/problem2/g5/methods.yaml",
            lambda payload: payload["learning_algorithms"][0].__setitem__("display_name", "HAPPO"),
            "forbidden algorithm name",
        ),
        (
            "configs/problem2/g5/protocol.yaml",
            lambda payload: payload["access"].__setitem__("sealed_accessed", True),
            "sealed access",
        ),
        (
            "configs/problem2/g5/pilot.yaml",
            lambda payload: payload["scenario_ids"].update({"start": 30000, "end": 30019}),
            "partition",
        ),
    ],
)
def test_loader_fails_closed_on_contract_drift(
    tmp_path: Path, relative: str, mutate, message: str
) -> None:
    candidate = _copy_contract_root(tmp_path)
    _mutate_yaml(candidate, relative, mutate)
    with pytest.raises(G5ContractError, match=message):
        load_g5_contract(candidate)


def test_loader_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    candidate = _copy_contract_root(tmp_path)
    path = candidate / "configs/problem2/g5/protocol.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "schema_version: g5.v1\n",
        encoding="utf-8",
    )
    with pytest.raises(G5ContractError, match="duplicate YAML key"):
        load_g5_contract(candidate)


def test_loader_rejects_unresolved_problem1_blob(tmp_path: Path) -> None:
    candidate = _copy_contract_root(tmp_path)
    _mutate_yaml(
        candidate,
        "docs/evidence/g5/problem1_lineage.yaml",
        lambda payload: payload["sources"][0].__setitem__("blob_id", "0" * 40),
    )
    with pytest.raises(G5ContractError, match="Problem-1 blob"):
        load_g5_contract(candidate)


def test_g5_contract_audit_cli_reports_fail_closed_summary() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/audit_g5_contracts.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "pass"
    assert report["methods"] == list(LEARNING_METHODS)
    assert report["conditions"] == list(PROBLEM2_CONDITIONS)
    assert report["partitions"]["development_scenarios"] == [10000, 10019, 20]
    assert report["partitions"]["validation"] == [20000, 20049, 50]
    assert report["partitions"]["sealed_test"] == [30000, 30099, 100]
    assert set(report["fairness"]) == FAIRNESS_FLAGS
    assert all(report["fairness"].values())
    assert report["validation_accessed"] is False
    assert report["sealed_accessed"] is False
    assert report["actual_unlock_count"] == 0
    assert len(report["contract_hashes"]) == 19
