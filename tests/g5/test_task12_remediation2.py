from __future__ import annotations

import json
import importlib.util
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms.protocol import ActionResult
from problem2.config import load_g2_config
from problem2.domain import Action, EpisodeState, UavState, VehicleState
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.experiments.identity import canonical_evaluation_identity, canonical_training_identity
from problem2.evaluation.validator import validate_long_table
from problem2.experiments.g5_contract import load_g5_contract
from problem2.resources.ledger import new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from problem2.training.selection import select_candidates
from problem2.training.tuning import (
    CanonicalValidationStore,
    ValidationAccessLedger,
    ValidationAccessError,
    map_validation_episode_to_raw,
)
from problem2.training import selection as selection_module
from scripts import freeze_g5 as freeze_module
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
G5 = ROOT / "outputs" / "problem2_sr_mappo_v1" / "g5"
DYNAMIC_CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")
DYNAMIC_SCENARIO = generate_dynamic_scenario(
    "validation", 20000, "g30x50_d4", (30, 50), DYNAMIC_CONFIG
)


def _validation_script():
    spec = importlib.util.spec_from_file_location(
        "run_g5_validation_tuning_under_test",
        ROOT / "scripts" / "run_g5_validation_tuning.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frozen_manifests(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    candidates = tmp_path / "validation-candidates.json"
    budget = tmp_path / "pilot-budget.json"
    candidates.write_bytes((G5 / "manifests" / candidates.name).read_bytes())
    budget.write_bytes((G5 / "manifests" / budget.name).read_bytes())
    return candidates, budget


def test_g5_freeze_refit_counts_follow_the_executable_pilot_matrix() -> None:
    contract = load_g5_contract(ROOT)

    assert freeze_module._expected_refit_counts(contract) == (120, 2400)


def _row(store: CanonicalValidationStore, *, scenario_id: int = 20000) -> dict[str, object]:
    config_hash = store.candidate_hash("sr_mappo_mobile", "c01")
    source_commit = "d" * 40
    training_identity = canonical_training_identity(
        "sr_mappo_mobile", "g30x50_d4", 51001, config_hash, source_commit
    )
    checkpoint_hash = "e" * 64
    evaluator_hash = "f" * 64
    panel_hash = "1" * 64
    evaluation_identity = canonical_evaluation_identity(
        training_identity, "sr_mappo_mobile", "g30x50_d4", 51001,
        scenario_id, "validation", checkpoint_hash, evaluator_hash, panel_hash,
    )
    return {
        "evaluation_identity": evaluation_identity,
        "canonical_training_identity": training_identity,
        "method": "sr_mappo_mobile",
        "candidate_id": "c01",
        "condition_id": "sr_mappo_mobile",
        "scale": "g30x50_d4",
        "training_seed": 51001,
        "scenario_id": scenario_id,
        "partition": "validation",
        "source_commit": source_commit,
        "config_hash": config_hash,
        "protocol_hash": "2" * 64,
        "checkpoint_hash": checkpoint_hash,
        "evaluator_hash": evaluator_hash,
        "scenario_panel_hash": panel_hash,
        "candidate_manifest_sha256": store.candidate_sha256,
        "budget_manifest_sha256": store.budget_sha256,
        "physical_scenario_contract_sha256": store.physical_scenario_contract_hash,
        "episode_index": 0,
        "interaction_count": 200000,
        "termination_reason": "horizon",
        "terminated": True,
        "initial_total_pest": 100.0,
        "final_total_pest": 20.0,
        "reduction_rate": 0.8,
        "success_at_0_85": False,
        "pesticide_initial_l": 1.0,
        "pesticide_remaining_l": 0.0,
        "pesticide_transferred_l": 1.0,
        "resource_conservation_residual_l": 0.0,
        "battery_replenishment_l": 0.0,
        "action_uav": 0,
        "action_vehicle_slot": 0,
        "rendezvous_distance_m": 2.0,
        "vehicle_service_travel_m": 3.0,
        "waiting_steps": 1,
        "completed_request_waiting_steps": 1,
        "pesticide_disabled_steps": 0,
        "return_steps": 0,
        "effective_spray_steps": 2,
        "decision_runtime_s": 0.01,
        "source_locator": "raw/episodes.jsonl:1",
    }


def _store(tmp_path: Path, *, require_dynamic_ecology: bool = False) -> CanonicalValidationStore:
    candidates, budget = _frozen_manifests(tmp_path)
    return CanonicalValidationStore(
        ROOT,
        output_root=tmp_path / "validation",
        candidate_manifest=candidates,
        budget_manifest=budget,
        source_commit="d" * 40,
        protocol_hash="2" * 64,
        scenario_panel_hash="1" * 64,
        physical_scenario_contract_hash=load_g5_contract(ROOT).file_hashes[
            "docs/evidence/g5/physical_scenario_contract.yaml"
        ],
        allow_noncanonical_test=True,
        require_dynamic_ecology=require_dynamic_ecology,
    )


def test_canonical_plan_is_exactly_20_candidates_by_3_seeds_by_50_scenarios(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert len(store.expected_identity_keys) == 3000
    assert len(set(store.expected_identity_keys)) == 3000
    assert store.expected_identity_keys[0] == ("sr_mappo_mobile", "c01", 51001, 20000)
    assert store.expected_identity_keys[-1] == ("iql_mobile", "c04", 51003, 20049)


def test_process_held_lock_rejects_contender_without_writes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    contender = CanonicalValidationStore(
        ROOT,
        output_root=store.output_root,
        candidate_manifest=store.candidate_manifest,
        budget_manifest=store.budget_manifest,
        source_commit="d" * 40,
        allow_noncanonical_test=True,
    )
    store.output_root.mkdir(parents=True)
    before = sorted(store.output_root.rglob("*"))
    with store.exclusive_lock():
        with pytest.raises(ValidationAccessError, match="writer lock"):
            with contender.exclusive_lock():
                pass
    assert sorted(store.output_root.rglob("*")) == before


def test_row_commit_is_atomic_and_consolidation_is_rebuilt_from_rows(tmp_path: Path) -> None:
    store = _store(tmp_path)
    row = _row(store)
    store.commit_row(row)
    row_files = list((store.rows_root).glob("*.json"))
    assert len(row_files) == 1
    assert store.consolidate() == [row]
    assert json.loads(store.ledger_path.read_text(encoding="utf-8"))["row_count"] == 1
    store.consolidated_path.write_text("tampered\n", encoding="utf-8")
    assert store.consolidate() == [row]
    assert json.loads(store.consolidated_path.read_text(encoding="utf-8").splitlines()[0]) == row


def test_row_written_before_ledger_is_recovered_and_ledger_ahead_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    row = _row(store)
    store.commit_row(row)
    store.ledger_path.unlink()
    assert store.recover() == [row]
    payload = json.loads(store.ledger_path.read_text(encoding="utf-8"))
    payload["row_count"] = 2
    store.ledger_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="ledger is ahead"):
        store.recover()


def test_recovery_rejects_a_tampered_sealed_access_ledger(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit_row(_row(store))
    payload = json.loads(store.ledger_path.read_text(encoding="utf-8"))
    payload["sealed_accessed"] = True
    store.ledger_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sealed|unlock"):
        store.recover()


def test_recovery_rejects_a_tampered_row_chain(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.commit_row(_row(store))
    payload = json.loads(store.ledger_path.read_text(encoding="utf-8"))
    payload["row_chain_sha256"] = "f" * 64
    store.ledger_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="chain|drift|mismatch"):
        store.recover()


def test_full_uav_does_not_create_an_illegal_service_request() -> None:
    config = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
    graph = make_raster_graph([(0, 0)], [])
    uav = UavState("uav-0", 5.0, 35.0, pesticide_l=config.usable_capacity_l)
    vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
    state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
    environment = Problem2CooperativeEnv(state, graph, config, max_steps=2, scenario_id=10000)
    current = environment.reset(scenario_id=10000)
    next_view = environment.step(ActionResult(
        actions={"uav": np.asarray([int(Action.STAY)]), "vehicle": np.asarray([int(Action.STAY)])},
        masks=current["masks"],
    ))
    assert next_view["truncated"] is False
    assert environment.state.requests == ()


def test_technical_failures_are_append_only_and_same_identity_can_retry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    key = ("sr_mappo_mobile", "c01", 51001, 20000)
    failure = store.record_technical_failure(key, RuntimeError("worker stopped"))
    assert failure["attempt"] == 1
    assert failure["exception_type"] == "RuntimeError"
    assert store.record_technical_failure(key, ValueError("retry"))["attempt"] == 2
    assert len(store.failure_records()) == 2
    store.commit_row(_row(store))
    assert len(store.failure_records()) == 2


def test_validation_episode_mapping_is_strict_raw_schema_and_provenance_complete(tmp_path: Path) -> None:
    store = _store(tmp_path)
    row = map_validation_episode_to_raw(
        {**_row(store), "metric_source": "action_driven_environment", "spray_action_count": 2,
         "sprayed_pesticide_l": 1.0, "mechanism_metrics": {"waiting_steps": 1}},
        source_commit="d" * 40,
        protocol_hash="2" * 64,
        checkpoint_hash="e" * 64,
        evaluator_hash="f" * 64,
        scenario_panel_hash="1" * 64,
        raw_trace_locator="raw/episodes.jsonl:1",
        candidate_manifest_sha256=store.candidate_sha256,
        budget_manifest_sha256=store.budget_sha256,
        physical_scenario_contract_sha256=store.physical_scenario_contract_hash,
    )
    assert set(row) == set(__import__("problem2.evaluation.schema", fromlist=["RAW_EPISODE_SCHEMA"]).RAW_EPISODE_SCHEMA["required"]) | {"metric_source"}
    validate_long_table([row], allow_validation_access=True, expected_identities={row["evaluation_identity"]}, expected_provenance={
        "source_commit": "d" * 40, "config_hash": row["config_hash"], "protocol_hash": "2" * 64,
        "checkpoint_hash": "e" * 64, "evaluator_hash": "f" * 64, "scenario_panel_hash": "1" * 64,
        "candidate_manifest_sha256": store.candidate_sha256, "budget_manifest_sha256": store.budget_sha256,
        "physical_scenario_contract_sha256": store.physical_scenario_contract_hash,
    })


def test_dynamic_validation_mapping_persists_complete_ecology_provenance(tmp_path: Path) -> None:
    store = _store(tmp_path, require_dynamic_ecology=True)
    source = {
        **_row(store),
        "metric_source": "dynamic_ecology_environment",
        "initial_total_pest": float(DYNAMIC_SCENARIO.initial_prey.sum()),
        "reduction_rate": 1.0 - 20.0 / float(DYNAMIC_SCENARIO.initial_prey.sum()),
        "ecology_version": "problem2-dynamic-pest-v1",
        "ecology_config_sha256": DYNAMIC_CONFIG.contract_sha256,
        "ecology_scenario_sha256": DYNAMIC_SCENARIO.scenario_sha256,
        "ecology_source_commit": DYNAMIC_SCENARIO.source_commit,
        "ecology_implementation_version": DYNAMIC_SCENARIO.implementation_version,
        "initial_total_predator": float(DYNAMIC_SCENARIO.initial_predator.sum()),
        "final_total_predator": 10.0,
        "cumulative_deposited_effect": 0.75,
        "terminal_mean_concentration": 0.05,
        "terminal_max_concentration": 0.2,
        "terminal_wind_direction": 0.4,
        "terminal_wind_strength": 0.25,
        "dynamic_step_count": 350,
    }
    row = map_validation_episode_to_raw(
        source,
        source_commit="d" * 40,
        protocol_hash="2" * 64,
        checkpoint_hash="e" * 64,
        evaluator_hash="f" * 64,
        scenario_panel_hash="1" * 64,
        raw_trace_locator="raw/episodes.jsonl:1",
        candidate_manifest_sha256=store.candidate_sha256,
        budget_manifest_sha256=store.budget_sha256,
        physical_scenario_contract_sha256=store.physical_scenario_contract_hash,
    )

    assert row["metric_source"] == "dynamic_ecology_environment"
    for field in (
        "ecology_version", "ecology_config_sha256", "ecology_scenario_sha256",
        "ecology_source_commit", "ecology_implementation_version",
        "initial_total_predator", "final_total_predator",
        "cumulative_deposited_effect", "terminal_mean_concentration",
        "terminal_max_concentration", "terminal_wind_direction", "terminal_wind_strength",
        "dynamic_step_count",
    ):
        assert field in row

    store.commit_row(row)
    persisted = json.loads((store.rows_root / "0000.json").read_text(encoding="utf-8"))
    assert persisted == row


def test_dynamic_canonical_store_rejects_rows_without_dynamic_provenance(tmp_path: Path) -> None:
    store = _store(tmp_path, require_dynamic_ecology=True)
    with pytest.raises(ValueError, match="dynamic ecology"):
        store.commit_row(_row(store))


def test_selection_requires_complete_3000_cells_and_writes_provenance(tmp_path: Path) -> None:
    store = _store(tmp_path)
    summaries = []
    for method in store.methods:
        for candidate_id in store.candidate_ids:
            summaries.append({
                "method": method, "candidate_id": candidate_id,
                "config_hash": store.candidate_hash(method, candidate_id),
                "mean_validation_reduction_rate": 0.8,
                "success_probability": 0.0, "interaction_count": 200000,
                "episode_count": 149,
            })
    with pytest.raises(ValueError, match="3000"):
        select_candidates(summaries, require_complete=True, expected_cell_count=3000)
    for row in summaries:
        row["episode_count"] = 150
    selected = select_candidates(
        summaries, require_complete=True, expected_cell_count=3000,
        candidate_manifest_sha256="a" * 64, budget_manifest_sha256="b" * 64,
        physical_scenario_contract_sha256="c" * 64,
    )
    assert set(selected) == set(store.methods)
    assert selected["sr_mappo_mobile"]["candidate_manifest_sha256"] == "a" * 64


def test_candidate_generation_guard_is_one_way_after_first_committed_row(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    candidates, budget = _frozen_manifests(tmp_path)
    store = CanonicalValidationStore(
        repository,
        output_root=repository / "outputs/problem2_sr_mappo_v1/g5/validation",
        candidate_manifest=candidates,
        budget_manifest=budget,
        source_commit="d" * 40,
        physical_scenario_contract_hash=load_g5_contract(ROOT).file_hashes[
            "docs/evidence/g5/physical_scenario_contract.yaml"
        ],
        allow_noncanonical_test=True,
    )
    store.commit_row(_row(store))
    with pytest.raises(ValueError, match="after first validation row"):
        CanonicalValidationStore.assert_candidate_generation_allowed(repository)


def test_duplicate_and_out_of_order_rows_fail_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _row(store)
    store.commit_row(first)
    with pytest.raises(ValueError, match="different row content"):
        store.commit_row({**first, "final_total_pest": 10.0, "reduction_rate": 0.9, "success_at_0_85": True})
    later = _row(store, scenario_id=20002)
    with pytest.raises(ValueError, match="out of order"):
        store.commit_row(later)


def test_legacy_validation_ledger_rejects_tampered_sealed_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    legacy = ValidationAccessLedger(store.candidate_manifest, store.budget_manifest, store.ledger_path)
    row = {
        **_row(store),
        "validation_accessed": True,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
        "metric_source": "action_driven_environment",
        "spray_action_count": 2,
        "sprayed_pesticide_l": 1.0,
    }
    legacy.append(row)
    payload = json.loads(store.ledger_path.read_text(encoding="utf-8"))
    payload["sealed_accessed"] = True
    store.ledger_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sealed|unlock|ledger"):
        legacy.verify_rows([row])


def test_formal_freeze_rejects_non_hex_training_identity() -> None:
    jobs = [{
        "canonical_training_identity": "g" * 64,
        "config_hash": "a" * 64,
        "family": "algorithm_scale",
    }] * 375
    with pytest.raises(ValueError, match="SHA-256"):
        selection_module.build_formal_freeze_payloads(
            jobs,
            validation_scenario_ids=range(20000, 20050),
            validation_panel_hash="b" * 64,
            sealed_scenario_ids=range(30000, 30100),
            sealed_panel_hash="c" * 64,
            source_commit="d" * 40,
            protocol_hash="e" * 64,
        )


def test_selected_refit_runner_uses_physical_development_training(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _validation_script()
    observed: dict[str, object] = {}

    def fake_physical_runner(
        job: dict[str, object], device: str, interactions: int, output: Path
    ) -> dict[str, object]:
        observed.update(job)
        return {
            "method": str(job["method"]),
            "condition_id": str(job["method"]),
            "candidate_id": str(job["candidate_id"]),
            "candidate_config_hash": "a" * 64,
            "scale": str(job["scale"]),
            "training_seed": int(job["training_seed"]),
            "scenario_id": 10000,
            "scenario_ids": list(range(10000, 10020)),
            "partition": "development",
            "interactions": interactions,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    monkeypatch.setattr(module, "run_physical_development_refit_training", fake_physical_runner)
    monkeypatch.setattr(
        module,
        "run_training_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("synthetic runner used")),
    )
    result = module._run_selected_refit_job(
        {
            "method": "sr_mappo_mobile",
            "condition_id": "sr_mappo_fixed",
            "scale": "g20x20_d2",
            "training_seed": 51001,
            "scenario_id": 10000,
            "scenario_ids": list(range(10000, 10020)),
            "partition": "development",
        },
        "cpu",
        128,
        tmp_path,
        selected={"sr_mappo_mobile": {"candidate_id": "c01", "config_hash": "a" * 64}},
        contract=object(),
    )
    assert observed["candidate_id"] == "c01"
    assert observed["condition_id"] == "sr_mappo_mobile"
    assert result["condition_id"] == "sr_mappo_fixed"


def test_freeze_source_clean_guard_rejects_tracked_dirty_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        freeze_module.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": " M src/file.py\n"})(),
    )
    with pytest.raises(ValueError, match="source tree is dirty"):
        freeze_module._assert_source_clean(tmp_path)


def test_freeze_payload_check_rejects_stale_existing_bytes(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"
    target.write_text('{"status":"stale"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="payload drifted"):
        freeze_module._assert_json_payload(target, {"status": "expected"})


def test_canonical_candidate_training_uses_the_frozen_validation_scale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _validation_script()
    observed: dict[str, str] = {}

    monkeypatch.setattr(module, "_load_training_candidate_manifest", lambda path: {
        "equal_environment_interactions": 200000,
        "candidates": {"sr_mappo_mobile": [
            {
                "candidate_id": candidate_id,
                "config_hash": "a" * 64,
                "environment_interactions": 200000,
            }
            for candidate_id in ("c01", "c02", "c03", "c04")
        ]},
    })
    monkeypatch.setattr(module, "load_g5_contract", lambda root: object())
    monkeypatch.setattr(module, "_sha256", lambda path: module.EXPECTED_CANDIDATE_SHA256 if "candidates" in str(path) else module.EXPECTED_BUDGET_SHA256)

    def fake_runner(job: dict[str, object], device: str, interactions: int, output: Path) -> dict[str, object]:
        observed["runner_scale"] = str(job["scale"])
        return {"manifest": str(output / "manifest.json")}

    def fake_loader(path: Path, **kwargs: object) -> dict[str, object]:
        observed["loader_canonical"] = str(kwargs["canonical"])
        return {"summary": str(path.parent / "summary.json")}

    monkeypatch.setattr(module, "run_physical_candidate_training", fake_runner)
    monkeypatch.setattr(module, "_load_training_result", fake_loader)
    result = module._run_candidate_matrix(
        ROOT,
        output_root=tmp_path,
        device="cpu",
        interactions=200000,
        methods=("sr_mappo_mobile",),
        seeds=(51001,),
        canonical=True,
        rerun_invalid_from_scratch=False,
    )

    assert result["job_count"] == 4
    assert observed["runner_scale"] == module.CANONICAL_SCALE
    assert observed["loader_canonical"] == "True"


def test_validation_tuning_holds_writer_lock_before_candidate_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _validation_script()
    state = {"locked": False}

    class FakeStore:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.interactions = 200000

        @contextmanager
        def exclusive_lock(self):
            state["locked"] = True
            try:
                yield
            finally:
                state["locked"] = False

    candidates = {
        method: [
            {"candidate_id": candidate_id, "config_hash": "a" * 64, "scenario_panel_hash": "b" * 64}
            for candidate_id in ("c01", "c02", "c03", "c04")
        ]
        for method in module.METHODS
    }
    fake_contract = type("Contract", (), {
        "file_hashes": {
            "configs/problem2/g5/protocol.yaml": "c" * 64,
            "docs/evidence/g5/physical_scenario_contract.yaml": "d" * 64,
        }
    })()
    monkeypatch.setattr(module, "CanonicalValidationStore", FakeStore)
    monkeypatch.setattr(module, "load_g5_contract", lambda root: fake_contract)
    monkeypatch.setattr(module, "_sha256", lambda path: module.EXPECTED_CANDIDATE_SHA256 if "candidates" in str(path) else module.EXPECTED_BUDGET_SHA256)
    monkeypatch.setattr(module, "_load_training_candidate_manifest", lambda path: {
        "candidates": candidates,
    })
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: "e" * 40)

    def fail_if_unlocked(*args: object, **kwargs: object) -> dict[str, object]:
        assert state["locked"] is True
        raise RuntimeError("stop before validation")

    monkeypatch.setattr(module, "_train_frozen_candidates", fail_if_unlocked)
    with pytest.raises(RuntimeError, match="stop before validation"):
        module.run_validation_tuning(
            ROOT,
            output_root=ROOT / "outputs/problem2_sr_mappo_v1/g5/validation",
            device="cpu",
        )
    assert state["locked"] is False


def test_selection_rejects_noncanonical_candidate_ids_or_uneven_cells(tmp_path: Path) -> None:
    store = _store(tmp_path)
    summaries = [
        {
            "method": method,
            "candidate_id": candidate_id,
            "config_hash": store.candidate_hash(method, candidate_id),
            "mean_validation_reduction_rate": 0.8,
            "success_probability": 0.0,
            "interaction_count": 200000,
            "episode_count": 150,
        }
        for method in store.methods
        for candidate_id in store.candidate_ids
    ]
    summaries[0]["episode_count"] = 149
    summaries[1]["episode_count"] = 151
    with pytest.raises(ValueError, match="150"):
        select_candidates(
            summaries,
            require_complete=True,
            candidate_manifest_sha256="a" * 64,
            budget_manifest_sha256="b" * 64,
            physical_scenario_contract_sha256="c" * 64,
        )
    summaries[0]["episode_count"] = 150
    summaries[1]["episode_count"] = 150
    summaries[0]["candidate_id"] = "c05"
    with pytest.raises(ValueError, match="c01-c04"):
        select_candidates(
            summaries,
            require_complete=True,
            candidate_manifest_sha256="a" * 64,
            budget_manifest_sha256="b" * 64,
            physical_scenario_contract_sha256="c" * 64,
        )
