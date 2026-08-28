from __future__ import annotations

import json
from pathlib import Path

import pytest
import numpy as np

from problem2.algorithms import build_algorithm
from problem2.algorithms.protocol import ActionResult
from problem2.config import load_g2_config
from problem2.domain import EpisodeState, UavState, VehicleState
from problem2.experiments.g5_contract import load_g5_contract
from problem2.resources.ledger import new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from problem2.training.pilot import verify_pilot_artifacts
from problem2.training.runner import run_training_job
from problem2.training.selection import (
    build_formal_freeze_payloads,
    select_candidates,
)
from problem2.training.tuning import (
    ActionDrivenValidationEnv,
    ValidationAccessLedger,
    build_validation_environment,
    validate_validation_episode,
)
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
G5 = ROOT / "outputs" / "problem2_sr_mappo_v1" / "g5"


def _candidate_manifest(tmp_path: Path) -> Path:
    source = G5 / "manifests" / "validation-candidates.json"
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    return target


def _budget_manifest(tmp_path: Path) -> Path:
    source = G5 / "manifests" / "pilot-budget.json"
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    return target


def _validation_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "method": "sr_mappo_mobile",
        "candidate_id": "c01",
        "config_hash": "15209e2c8425a697957421fd843759dbae1edc070973cc41cddb98722e58befe",
        "partition": "validation",
        "scenario_id": 20000,
        "training_seed": 51001,
        "interaction_count": 200000,
        "initial_total_pest": 100.0,
        "final_total_pest": 20.0,
        "reduction_rate": 0.8,
        "success_at_0_85": False,
        "spray_action_count": 12,
        "sprayed_pesticide_l": 1.2,
        "metric_source": "action_driven_environment",
        "validation_accessed": True,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
    }
    row.update(overrides)
    return row


def test_persisted_pilot_lineage_accepts_ancestor_with_unchanged_frozen_scope() -> None:
    contract = load_g5_contract(ROOT)
    verify_pilot_artifacts(
        contract,
        G5 / "validated" / "pilot-episodes.jsonl",
        G5 / "audits" / "pilot-audit.json",
        G5 / "audits" / "pilot-artifact-manifest.json",
    )


def test_validation_access_locks_candidate_bytes_after_first_row(tmp_path: Path) -> None:
    candidates = _candidate_manifest(tmp_path)
    budget = _budget_manifest(tmp_path)
    ledger = ValidationAccessLedger(candidates, budget, tmp_path / "access.json")
    ledger.append(_validation_row())

    payload = json.loads(candidates.read_text(encoding="utf-8"))
    payload["candidates"]["sr_mappo_mobile"][0]["parameters"]["learning_rate"] = 0.5
    candidates.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate manifest changed after validation access"):
        ledger.append(_validation_row(scenario_id=20001))


def test_validation_access_ledger_verifies_recovery_row_chain(tmp_path: Path) -> None:
    ledger = ValidationAccessLedger(
        _candidate_manifest(tmp_path),
        _budget_manifest(tmp_path),
        tmp_path / "access.json",
    )
    row = _validation_row()
    ledger.append(row)
    ledger.verify_rows([row])
    with pytest.raises(ValueError, match="row chain"):
        ledger.verify_rows([{**row, "scenario_id": 20001}])


def test_validation_access_rejects_unequal_declared_candidate_budgets(tmp_path: Path) -> None:
    candidates = _candidate_manifest(tmp_path)
    payload = json.loads(candidates.read_text(encoding="utf-8"))
    payload["candidates"]["iql_mobile"][3]["environment_interactions"] = 199999
    candidates.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="equal environment interactions"):
        ValidationAccessLedger(candidates, _budget_manifest(tmp_path), tmp_path / "access.json")


def test_selection_uses_every_frozen_tie_break_in_order() -> None:
    rows = [
        {"method": "sr_mappo_mobile", "candidate_id": "c01", "config_hash": "d" * 64, "mean_validation_reduction_rate": 0.7, "success_probability": 0.8, "interaction_count": 200000},
        {"method": "sr_mappo_mobile", "candidate_id": "c02", "config_hash": "c" * 64, "mean_validation_reduction_rate": 0.8, "success_probability": 0.7, "interaction_count": 200000},
        {"method": "sr_mappo_mobile", "candidate_id": "c03", "config_hash": "b" * 64, "mean_validation_reduction_rate": 0.8, "success_probability": 0.8, "interaction_count": 200001},
        {"method": "sr_mappo_mobile", "candidate_id": "c04", "config_hash": "a" * 64, "mean_validation_reduction_rate": 0.8, "success_probability": 0.8, "interaction_count": 200000},
    ]
    selected = select_candidates(rows)
    assert selected["sr_mappo_mobile"]["candidate_id"] == "c04"


def test_freeze_payloads_have_exact_g6_and_g7_counts_without_sealed_content() -> None:
    jobs = [
        {
            "canonical_training_identity": f"{index:064x}",
            "family": "algorithm_scale" if index < 150 else "other",
            "method": "sr_mappo_mobile",
            "config_hash": "a" * 64,
        }
        for index in range(375)
    ]
    payloads = build_formal_freeze_payloads(
        jobs,
        validation_scenario_ids=range(20000, 20050),
        validation_panel_hash="b" * 64,
        sealed_scenario_ids=range(30000, 30100),
        sealed_panel_hash="c" * 64,
        source_commit="d" * 40,
        protocol_hash="e" * 64,
    )
    assert payloads["g6_training"]["base_job_count"] == 150
    assert payloads["g6_training"]["job_count"] == 375
    assert payloads["g7_sealed"]["expected_evaluation_count"] == 42500
    assert payloads["g7_sealed"]["scenario_content"] is None
    assert payloads["g7_sealed"]["evaluation_results"] == []
    assert payloads["g7_sealed"]["sealed_accessed"] is False


@pytest.mark.parametrize("field", ["validation_panel_hash", "sealed_panel_hash", "source_commit", "protocol_hash"])
def test_freeze_payloads_reject_missing_provenance_hash(field: str) -> None:
    kwargs = {
        "validation_scenario_ids": range(20000, 20050),
        "validation_panel_hash": "b" * 64,
        "sealed_scenario_ids": range(30000, 30100),
        "sealed_panel_hash": "c" * 64,
        "source_commit": "d" * 40,
        "protocol_hash": "e" * 64,
    }
    kwargs[field] = ""
    with pytest.raises(ValueError, match="hash|commit"):
        build_formal_freeze_payloads([], **kwargs)


def test_validation_episode_requires_action_dependent_pest_metrics_and_zero_sealed_access() -> None:
    validate_validation_episode(_validation_row())
    with pytest.raises(ValueError, match="action-driven"):
        validate_validation_episode(_validation_row(metric_source="training_loss"))
    with pytest.raises(ValueError, match="spray action"):
        validate_validation_episode(_validation_row(spray_action_count=0, sprayed_pesticide_l=0.0))
    with pytest.raises(ValueError, match="sealed"):
        validate_validation_episode(_validation_row(sealed_accessed=True))


def test_validation_environment_pest_change_is_caused_by_real_spray_actions() -> None:
    config = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
    graph = make_raster_graph([(0, 0)], [])

    def run(action: int) -> tuple[float, int]:
        uav = UavState("uav-0", 5.0, 35.0, pesticide_l=config.usable_capacity_l / 2.0)
        vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
        state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
        base = Problem2CooperativeEnv(state, graph, config, max_steps=1, scenario_id=20000)
        environment = ActionDrivenValidationEnv(base, initial_pest=np.ones((2, 2)), mortality_per_l=1.0)
        view = environment.reset(scenario_id=20000)
        environment.step(ActionResult(
            actions={"uav": np.asarray([action]), "vehicle": np.asarray([0])},
            masks=view["masks"],
        ))
        record = environment.episode_record()
        assert record.reduction_rate == pytest.approx(1.0 - float(environment.pest.sum()) / 4.0)
        return float(environment.pest.sum()), environment.spray_action_count

    sprayed = run(5)
    held = run(4)
    replay = run(5)
    assert sprayed[0] < held[0]
    assert sprayed[1] == 1
    assert held[1] == 0
    assert replay == sprayed


def test_spray_is_reflected_in_the_returned_next_observation() -> None:
    config = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
    graph = make_raster_graph([(0, 0)], [])

    def run(action: int) -> tuple[float, float, float]:
        uav = UavState("uav-0", 5.0, 35.0, pesticide_l=0.2875)
        vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
        state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
        environment = ActionDrivenValidationEnv(
            Problem2CooperativeEnv(state, graph, config, max_steps=1, scenario_id=10000),
            initial_pest=np.ones((2, 2)),
            mortality_per_l=1.0,
            partition="development",
        )
        current = environment.reset(scenario_id=10000)
        next_view = environment.step(ActionResult(
            actions={"uav": np.asarray([action]), "vehicle": np.asarray([0])},
            masks=current["masks"],
        ))
        return (
            float(current["observations"]["uav"][0, 12]),
            float(next_view["observations"]["uav"][0, 12]),
            float(environment.pest.mean()),
        )

    sprayed = run(5)
    held = run(4)
    assert sprayed[1] == pytest.approx(sprayed[2])
    assert sprayed[1] < sprayed[0]
    assert held[1] == pytest.approx(held[0])
    assert held[2] == pytest.approx(held[0])


def test_training_runner_honors_the_frozen_candidate_id(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    result = run_training_job(
        {
            "source_root": ROOT,
            "_contract": contract,
            "method": "sr_mappo_mobile",
            "condition_id": "sr_mappo_mobile",
            "candidate_id": "c04",
            "partition": "development",
            "scenario_id": 10000,
            "scenario_ids": list(range(10000, 10020)),
            "training_seed": 51001,
            "scale": "g20x20_d2",
        },
        "cpu",
        1,
        tmp_path,
    )
    assert result["candidate_id"] == "c04"
    assert result["candidate_config_hash"] == "6b5a69c48982fdd6ef4205d68cb0e0ed237be9517451ca8f787235ff566c4883"


def test_validation_scenario_factory_is_deterministic_and_rejects_sealed_ids() -> None:
    first = build_validation_environment(ROOT, scenario_id=20000, scale="g20x20_d2")
    second = build_validation_environment(ROOT, scenario_id=20000, scale="g20x20_d2")
    first_view = first.reset(scenario_id=20000)
    second_view = second.reset(scenario_id=20000)
    assert np.array_equal(first.pest, second.pest)
    assert np.array_equal(first_view["observations"]["uav"], second_view["observations"]["uav"])
    assert first.physical.graph.scale_id == "g20x20_d2"
    with pytest.raises(ValueError, match="sealed|validation"):
        build_validation_environment(ROOT, scenario_id=30000, scale="g20x20_d2")


def test_g5_physical_factories_enforce_partition_and_pesticide_contract() -> None:
    from problem2.training import tuning

    development = tuning.build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    validation = tuning.build_validation_environment(ROOT, scenario_id=20000, scale="g20x20_d2")

    assert [uav.pesticide_l for uav in development.state.uavs] == [
        tuning.INITIAL_ONBOARD_PESTICIDE_L,
        tuning.INITIAL_ONBOARD_PESTICIDE_L,
    ]
    assert [uav.pesticide_l for uav in validation.state.uavs] == [
        tuning.INITIAL_ONBOARD_PESTICIDE_L,
        tuning.INITIAL_ONBOARD_PESTICIDE_L,
    ]
    assert development.replenished_resource == "pesticide"
    assert validation.replenished_resource == "pesticide"
    assert development.battery_replenishment_enabled is False
    assert validation.battery_replenishment_enabled is False
    with pytest.raises(ValueError, match="development"):
        tuning.build_development_environment(ROOT, scenario_id=20000, scale="g20x20_d2")
    with pytest.raises(ValueError, match="validation"):
        build_validation_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    for scenario_id in (30000, 30099):
        with pytest.raises(ValueError, match="sealed"):
            tuning.build_development_environment(ROOT, scenario_id=scenario_id, scale="g20x20_d2")
        with pytest.raises(ValueError, match="sealed"):
            build_validation_environment(ROOT, scenario_id=scenario_id, scale="g20x20_d2")


def test_algorithm_dimensions_follow_the_frozen_scale_uav_count() -> None:
    contract = load_g5_contract(ROOT)
    environment = build_validation_environment(ROOT, scenario_id=20000, scale="g30x50_d4")
    view = environment.reset(scenario_id=20000)
    assert view["observations"]["uav"].shape == (4, 315)
    algorithm = build_algorithm(
        "sr_mappo_mobile",
        contract,
        "cpu",
        candidate_id="c01",
        scale="g30x50_d4",
    )
    result = algorithm.act(view["observations"], view["masks"], deterministic=True)
    assert result.actions["uav"].shape == (4,)


def test_maddpg_critic_dimensions_follow_the_frozen_scale_uav_count() -> None:
    contract = load_g5_contract(ROOT)
    algorithm = build_algorithm(
        "maddpg_mobile",
        contract,
        "cpu",
        candidate_id="c01",
        scale="g30x50_d4",
    )

    assert algorithm.uav_critic.uav_count == 4
    assert algorithm.vehicle_critic.uav_count == 4


def test_road_neighbor_queries_index_the_immutable_edge_table_once() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (1, 1)],
        [(0, 1), (1, 2)],
    )

    class CountingEdges:
        def __init__(self, edges: np.ndarray) -> None:
            self.edges = edges
            self.iterations = 0

        def __iter__(self):
            self.iterations += 1
            return iter(self.edges)

    counting_edges = CountingEdges(graph.edges)
    object.__setattr__(graph, "edges", counting_edges)

    assert graph.neighbors(0)
    assert graph.neighbors(1)
    assert graph.neighbors(2)
    assert counting_edges.iterations == 1


def test_environment_factory_reuses_frozen_static_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    import problem2.training.tuning as tuning

    calls = 0
    original = tuning.load_g5_contract

    def counted_load(root: Path):
        nonlocal calls
        calls += 1
        return original(root)

    monkeypatch.setattr(tuning, "load_g5_contract", counted_load)
    tuning.build_development_environment(ROOT, scenario_id=10000, scale="g30x50_d4")
    tuning.build_development_environment(ROOT, scenario_id=10001, scale="g30x50_d4")

    assert calls <= 1
