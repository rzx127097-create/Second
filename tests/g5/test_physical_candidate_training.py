from __future__ import annotations

import json
import hashlib
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_training_checkpoint
from problem2.algorithms.protocol import ActionResult, OffPolicyEnvelope, OnPolicyEnvelope
from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments import g5_contract
from problem2.training.physical_training import (
    PHYSICAL_TRAINING_SCHEMA_VERSION,
    build_physical_envelope,
    evaluation_state_digest,
)
from problem2.training import physical_training
from problem2.training.tuning import ActionDrivenValidationEnv, build_development_environment
from problem2.training import tuning
from scripts.run_g5_validation_tuning import (
    _load_training_result,
    train_frozen_candidates,
)
from scripts import run_g5_validation_tuning as task12


ROOT = Path(__file__).resolve().parents[2]
METHODS = (
    "sr_mappo_mobile",
    "mappo_mobile",
    "ippo_mobile",
    "maddpg_mobile",
    "iql_mobile",
)


def _job(method: str, *, candidate_id: str = "c01") -> dict[str, object]:
    return {
        "source_root": ROOT,
        "method": method,
        "condition_id": method,
        "candidate_id": candidate_id,
        "partition": "development",
        "scenario_id": 10000,
        "scenario_ids": list(range(10000, 10020)),
        "training_seed": 51001,
        "scale": "g20x20_d2",
    }


@pytest.mark.parametrize("method", METHODS)
def test_physical_envelope_uses_exact_views_and_one_shared_team_reward(method: str) -> None:
    contract = load_g5_contract(ROOT)
    environment = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    algorithm = build_algorithm(method, contract, "cpu", candidate_id="c01", scale="g20x20_d2")
    current = environment.reset(scenario_id=10000)
    details = algorithm.act(
        current["observations"],
        current["masks"],
        deterministic=False,
        return_details=True,
    )
    action_result = ActionResult(actions=details["actions"], masks=details["masks"])
    next_view = environment.step(action_result)
    envelope = build_physical_envelope(
        algorithm,
        current,
        next_view,
        details,
        team_reward=next_view["team_reward"],
        transition_index=0,
    )

    expected_type = OnPolicyEnvelope if method in METHODS[:3] else OffPolicyEnvelope
    assert isinstance(envelope, expected_type)
    assert np.array_equal(envelope.role_batch.observations["uav"], current["observations"]["uav"])
    assert np.array_equal(envelope.role_batch.next_observations["uav"], next_view["observations"]["uav"])
    assert np.array_equal(envelope.role_batch.masks["vehicle"], current["masks"]["vehicle"])
    assert np.array_equal(envelope.role_batch.next_masks["vehicle"], next_view["masks"]["vehicle"])
    for rewards in envelope.role_batch.rewards.values():
        assert np.all(rewards == pytest.approx(next_view["team_reward"]))
    assert envelope.team_reward == pytest.approx(next_view["team_reward"])


@pytest.mark.parametrize(
    ("method", "expected_updates"),
    (
        ("sr_mappo_mobile", 3),
        ("mappo_mobile", 3),
        ("ippo_mobile", 3),
        ("maddpg_mobile", 1),
        ("iql_mobile", 1),
    ),
)
def test_all_methods_follow_their_frozen_physical_update_cadence(
    tmp_path: Path,
    method: str,
    expected_updates: int,
) -> None:
    result = physical_training.run_noncanonical_physical_candidate_training_for_test(
        _job(method), "cpu", 65, tmp_path / method
    )

    assert result["training_mode"] == "physical_development"
    assert result["scenario_execution"] is True
    assert result["interaction_count"] == 65
    assert result["optimizer_update_count"] == expected_updates
    assert result["source_provenance"]["environment_factory"] == (
        "problem2.training.tuning.build_development_environment"
    )
    assert result["candidate_id"] == "c01"
    assert len(result["candidate_config_hash"]) == 64
    assert result["replenished_resource"] == "pesticide"
    assert result["battery_replenishment_enabled"] is False


def test_terminal_checkpoint_is_compact_strict_and_post_update(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    result = physical_training.run_noncanonical_physical_candidate_training_for_test(
        _job("iql_mobile"),
        "cpu",
        257,
        tmp_path / "training",
    )
    checkpoint = Path(result["checkpoint"])
    restored, _ = load_training_checkpoint(
        checkpoint,
        lambda: build_algorithm(
            "iql_mobile",
            contract,
            "cpu",
            candidate_id="c01",
            scale="g20x20_d2",
        ),
        result["checkpoint_provenance"],
    )
    state = restored.state_dict()

    assert checkpoint.stat().st_size < 100 * 1024 * 1024
    assert result["schema_version"] == PHYSICAL_TRAINING_SCHEMA_VERSION
    assert result["interaction_count"] == 257
    assert result["executed_scenario_ids"] == [10000, 10001]
    assert result["optimizer_update_count"] == 4
    assert result["checkpoint_after_update_count"] == 4
    assert result["trained_evaluation_state_digest"] == result["checkpoint_evaluation_state_digest"]
    assert evaluation_state_digest(restored) == result["trained_evaluation_state_digest"]
    assert result["pending_on_policy_envelopes"] == 0
    assert result["off_policy_replay_rows"] == 0
    assert result["resumable_mid_training"] is False
    assert state["uav_replay"]["size"] == 0
    assert state["vehicle_replay"]["size"] == 0


def test_evaluation_digest_changes_when_only_normalizer_state_changes() -> None:
    contract = load_g5_contract(ROOT)
    algorithm = build_algorithm(
        "sr_mappo_mobile", contract, "cpu", candidate_id="c01", scale="g20x20_d2"
    )
    before = evaluation_state_digest(algorithm)
    algorithm.uav_normalizer.update(np.ones((2, 179), dtype=np.float64))
    after = evaluation_state_digest(algorithm)
    assert after != before


def test_evaluation_digest_includes_ippo_mapped_return_normalizers() -> None:
    contract = load_g5_contract(ROOT)
    algorithm = build_algorithm(
        "ippo_mobile", contract, "cpu", candidate_id="c01", scale="g20x20_d2"
    )
    before = evaluation_state_digest(algorithm)
    algorithm.return_normalizers["uav"].update(np.ones((2, 1), dtype=np.float64))
    assert evaluation_state_digest(algorithm) != before


@pytest.mark.parametrize("method", METHODS)
def test_evaluation_digest_round_trips_all_five_methods(tmp_path: Path, method: str) -> None:
    contract = load_g5_contract(ROOT)
    algorithm = build_algorithm(method, contract, "cpu", candidate_id="c01", scale="g20x20_d2")
    algorithm.set_evaluation(True)
    expected = evaluation_state_digest(algorithm)
    checkpoint = tmp_path / f"{method}.pt"
    provenance = {
        "source_commit": "a" * 40,
        "source_bundle_sha256": "b" * 64,
        "config_hash": "c" * 64,
        "protocol_hash": "d" * 64,
        "ancestry_hash": "e" * 64,
    }
    from problem2.algorithms.common.checkpoint import save_training_checkpoint

    save_training_checkpoint(checkpoint, {"algorithm": algorithm.state_dict()}, provenance)
    restored, _ = load_training_checkpoint(
        checkpoint,
        lambda: build_algorithm(method, contract, "cpu", candidate_id="c01", scale="g20x20_d2"),
        provenance,
    )
    assert evaluation_state_digest(restored) == expected


@pytest.mark.parametrize("method", METHODS)
def test_forced_behavior_rows_are_not_actor_valid_for_any_method(method: str) -> None:
    contract = load_g5_contract(ROOT)
    environment = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    algorithm = build_algorithm(method, contract, "cpu", candidate_id="c01", scale="g20x20_d2")
    current = environment.reset(scenario_id=10000)
    details = algorithm.act(current["observations"], current["masks"], deterministic=False, return_details=True)
    details["masks"] = {
        "uav": np.asarray([[True, False, False, False, False, False], [True] * 6], dtype=bool),
        "vehicle": np.asarray([[False, True, False, False, False]], dtype=bool),
    }
    details["actions"] = {
        "uav": np.asarray([0, int(details["actions"]["uav"][1])]),
        "vehicle": np.asarray([1]),
    }
    current["candidate_mapping"] = {"vehicle": ["request-0", None, None, None]}
    next_view = dict(current)
    next_view["terminated"] = False
    next_view["truncated"] = False
    envelope = build_physical_envelope(
        algorithm, current, next_view, details, team_reward=0.0, transition_index=0
    )
    assert envelope.valid_actor_sample["uav"].tolist() == [False, True]
    assert envelope.valid_actor_sample["vehicle"].tolist() == [False]


def test_physical_scenario_contract_is_strict_and_provenance_bound() -> None:
    contract = load_g5_contract(ROOT)
    scenario = contract.physical_scenario
    assert scenario.assumption_status == "provisional_simulation_assumption"
    assert scenario.empirical_claim is False
    assert scenario.deployment_claim is False
    assert scenario.gamma_shape == pytest.approx(2.0)
    assert scenario.gamma_scale == pytest.approx(1.0)
    assert scenario.normalized_initial_pest_total == pytest.approx(100.0)
    assert scenario.spray_mortality_per_l == pytest.approx(5.0)
    assert contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"] == hashlib.sha256(
        (ROOT / "docs/evidence/g5/physical_scenario_contract.yaml").read_bytes()
    ).hexdigest()

    first = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    second = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    assert first.source_provenance["physical_scenario_contract_sha256"] == contract.file_hashes[
        "docs/evidence/g5/physical_scenario_contract.yaml"
    ]
    assert first.source_provenance["scenario_content_sha256"] == second.source_provenance[
        "scenario_content_sha256"
    ]
    assert first.ecology_mode == "dynamic"
    assert first.primary_eligible is True
    assert float(first.initial_prey.sum()) > 0.0
    assert first.source_provenance["ecology_scenario_sha256"] == (
        second.source_provenance["ecology_scenario_sha256"]
    )


def test_physical_scenario_contract_rejects_unknown_keys(tmp_path: Path) -> None:
    target = tmp_path / "docs/evidence/g5/physical_scenario_contract.yaml"
    target.parent.mkdir(parents=True)
    target.write_bytes(
        (ROOT / "docs/evidence/g5/physical_scenario_contract.yaml").read_bytes()
        + b"unknown_field: forbidden\n"
    )
    with pytest.raises(g5_contract.G5ContractError, match="unknown keys"):
        g5_contract._load_physical_scenario(tmp_path)


def test_canonical_physical_provenance_rejects_dirty_tracked_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = load_g5_contract(ROOT)

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1 if "diff" in command else 0)

    monkeypatch.setattr(physical_training.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="dirty tracked source"):
        physical_training.physical_checkpoint_provenance(
            contract, "iql_mobile", "c01", canonical=True
        )


@pytest.mark.parametrize(
    ("scenario_id", "partition", "message"),
    ((10000, "validation", "validation"), (20000, "development", "development"), (30000, "validation", "sealed"), (10000, "unknown", "partition")),
)
def test_direct_physical_wrapper_rejects_partition_bypasses(
    scenario_id: int, partition: str, message: str
) -> None:
    base = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2").physical
    base.scenario_id = scenario_id
    with pytest.raises(ValueError, match=message):
        ActionDrivenValidationEnv(
            base,
            initial_pest=np.ones((2, 2)),
            mortality_per_l=1.0,
            partition=partition,
        )


def test_physical_wrapper_revalidates_immutable_scenario_identity_on_reset_and_step() -> None:
    base = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2").physical
    environment = ActionDrivenValidationEnv(
        base,
        initial_pest=np.ones((2, 2)),
        mortality_per_l=1.0,
        partition="development",
        purpose="static_ecology_diagnostic",
        output_root=ROOT / "outputs/problem2_sr_mappo_v1/diagnostics/static_ecology/g5",
        repository_root=ROOT,
    )
    environment.reset(scenario_id=10000)
    base.scenario_id = 30000
    with pytest.raises(ValueError, match="sealed|scenario"):
        environment.reset(scenario_id=10000)
    with pytest.raises(ValueError, match="sealed|scenario"):
        environment.step(None)


def test_static_adapter_requires_explicit_diagnostic_scope(tmp_path: Path) -> None:
    base = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2").physical
    with pytest.raises(ValueError, match="static_ecology_diagnostic"):
        ActionDrivenValidationEnv(
            base,
            initial_pest=np.ones((2, 2)),
            mortality_per_l=1.0,
            partition="development",
        )
    diagnostic = ActionDrivenValidationEnv(
        base,
        initial_pest=np.ones((2, 2)),
        mortality_per_l=1.0,
        partition="development",
        purpose="static_ecology_diagnostic",
        output_root=tmp_path,
        repository_root=ROOT,
        allow_noncanonical_output_root=True,
    )
    assert diagnostic.primary_eligible is False


def _update_manifest_artifact(manifest_path: Path, artifact_name: str) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = manifest_path.parent / artifact_name
    for row in payload["artifacts"]:
        if row["path"] == artifact_name:
            row["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            row["bytes"] = artifact.stat().st_size
    manifest_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


@pytest.fixture()
def completed_noncanonical_identity(tmp_path: Path) -> tuple[dict[str, object], Path]:
    result = physical_training.run_noncanonical_physical_candidate_training_for_test(
        _job("iql_mobile"), "cpu", 1, tmp_path / "training"
    )
    return result, Path(result["manifest"])


@pytest.mark.parametrize("damage", ("missing_manifest", "checkpoint_hash", "forged_summary", "extra_artifact", "nonfinite"))
def test_completion_validator_rejects_torn_tampered_or_nonfinite_identity(
    completed_noncanonical_identity: tuple[dict[str, object], Path], damage: str
) -> None:
    result, original_manifest = completed_noncanonical_identity
    damaged = original_manifest.parent.parent / damage
    shutil.copytree(original_manifest.parent, damaged)
    manifest = damaged / "manifest.json"
    summary = damaged / "summary.json"
    relocated = json.loads(summary.read_text(encoding="utf-8"))
    relocated.update({
        "checkpoint": str(damaged / "checkpoint.pt"),
        "training_log": str(damaged / "physical-episodes.jsonl"),
        "summary": str(summary),
        "manifest": str(manifest),
    })
    summary.write_text(json.dumps(relocated, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _update_manifest_artifact(manifest, "summary.json")
    if damage == "missing_manifest":
        manifest.unlink()
    elif damage == "checkpoint_hash":
        (damaged / "checkpoint.pt").write_bytes((damaged / "checkpoint.pt").read_bytes() + b"tamper")
    elif damage == "forged_summary":
        payload = json.loads(summary.read_text(encoding="utf-8"))
        payload["checkpoint_provenance"] = {**payload["checkpoint_provenance"], "source_commit": "0" * 40}
        summary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        _update_manifest_artifact(manifest, "summary.json")
    elif damage == "extra_artifact":
        (damaged / "unexpected.bin").write_bytes(b"extra")
    else:
        payload = json.loads(summary.read_text(encoding="utf-8"))
        payload["finite_metrics"] = False
        summary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        _update_manifest_artifact(manifest, "summary.json")

    with pytest.raises(RuntimeError, match="manifest|artifact|provenance|finite|path"):
        _load_training_result(
            manifest,
            root=ROOT,
            method="iql_mobile",
            candidate_id="c01",
            config_hash=str(result["candidate_config_hash"]),
            seed=51001,
            interactions=1,
            device="cpu",
            canonical=False,
        )


def test_fresh_nonfinite_training_fails_its_completion_validator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_build = physical_training.build_algorithm

    def nonfinite_build(*args: object, **kwargs: object) -> object:
        algorithm = real_build(*args, **kwargs)
        original_update = algorithm.update

        def update() -> dict[str, float]:
            original_update()
            return {"loss": float("nan")}

        algorithm.update = update
        return algorithm

    monkeypatch.setattr(physical_training, "build_algorithm", nonfinite_build)
    with pytest.raises(RuntimeError, match="finite"):
        physical_training.run_noncanonical_physical_candidate_training_for_test(
            _job("iql_mobile"), "cpu", 64, tmp_path / "training"
        )


def test_full_development_scenario_cycle_wraps_10019_to_10000(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_factory = physical_training.build_development_environment

    def one_step_factory(*args: object, **kwargs: object) -> object:
        environment = real_factory(*args, **kwargs)
        environment.physical.max_steps = 1
        return environment

    monkeypatch.setattr(physical_training, "build_development_environment", one_step_factory)
    result = physical_training.run_noncanonical_physical_candidate_training_for_test(
        _job("iql_mobile"), "cpu", 21, tmp_path / "training"
    )
    assert result["executed_scenario_ids"] == [*range(10000, 10020), 10000]


def test_task12_loader_rejects_stopped_synthetic_summary(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "method": "sr_mappo_mobile",
        "candidate_id": "c01",
        "candidate_config_hash": "a" * 64,
        "training_seed": 51001,
        "interactions": 200000,
        "interrupted": False,
        "finite_metrics": True,
        "evaluation_frozen": True,
        "checkpoint": str(tmp_path / "checkpoint.pt"),
    }), encoding="utf-8")

    with pytest.raises(RuntimeError, match="manifest"):
        _load_training_result(
            tmp_path / "manifest.json",
            root=ROOT,
            method="sr_mappo_mobile",
            candidate_id="c01",
            config_hash="a" * 64,
            seed=51001,
            interactions=200000,
            device="cpu",
            canonical=False,
        )


def test_train_only_partitions_exact_identities_below_supplied_root(tmp_path: Path) -> None:
    output_root = tmp_path / "task12"
    result = task12.train_frozen_candidates_for_test(
        ROOT,
        output_root=output_root,
        device="cpu",
        interactions=128,
        methods=("iql_mobile",),
        seeds=(51001,),
    )

    assert result["job_count"] == 4
    assert result["requested_identities"] == [
        {"method": "iql_mobile", "candidate_id": f"c{index:02d}", "training_seed": 51001}
        for index in range(1, 5)
    ]
    for summary_path in result["summary_paths"]:
        assert Path(summary_path).resolve().is_relative_to(output_root.resolve())
    assert result["validation_accessed"] is False
    assert result["sealed_accessed"] is False


@pytest.mark.parametrize("seeds", ((30000,), (51001, 51001)))
def test_train_only_rejects_nonexact_seed_partitions_before_writing(
    tmp_path: Path,
    seeds: tuple[int, ...],
) -> None:
    output_root = tmp_path / "task12"
    with pytest.raises(ValueError, match="training seed|duplicate"):
        task12.train_frozen_candidates_for_test(
            ROOT,
            output_root=output_root,
            device="cpu",
            interactions=128,
            methods=("iql_mobile",),
            seeds=seeds,
        )


@pytest.mark.parametrize(
    "output_root",
    (
        Path("C:/outside-g5-validation"),
        ROOT / "outputs/problem2_sr_mappo_v1/g5/validation/../escape",
    ),
)
def test_canonical_train_only_rejects_output_escape_before_writing(
    output_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(task12, "run_physical_candidate_training", lambda *args, **kwargs: pytest.fail("training started"))
    with pytest.raises(ValueError, match="canonical.*output|confined"):
        train_frozen_candidates(
            ROOT, output_root=output_root, device="cpu", interactions=200000,
            methods=("iql_mobile",), seeds=(51001,)
        )


def test_direct_canonical_physical_runner_rejects_output_escape_before_training(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(physical_training, "_require_clean_tracked_physical_sources", lambda root: None)
    monkeypatch.setattr(
        physical_training,
        "build_algorithm",
        lambda *args, **kwargs: pytest.fail("training started"),
    )
    with pytest.raises(ValueError, match="canonical.*root|output.*confined"):
        physical_training.run_physical_candidate_training(
            _job("iql_mobile"), "cpu", 200000, tmp_path / "outside"
        )
    assert not (tmp_path / "outside").exists()


def test_canonical_train_only_rejects_wrong_budget_and_candidate_declaration_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = ROOT / "outputs/problem2_sr_mappo_v1/g5/validation" / "pytest-must-not-write"
    monkeypatch.setattr(task12, "run_physical_candidate_training", lambda *args, **kwargs: pytest.fail("training started"))
    with pytest.raises(ValueError, match="200000"):
        train_frozen_candidates(
            ROOT, output_root=output_root, device="cpu", interactions=128,
            methods=("iql_mobile",), seeds=(51001,)
        )
    assert not output_root.exists()


def test_canonical_train_only_rejects_candidate_budget_drift_before_training(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = task12._load_training_candidate_manifest(
        ROOT / "outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json"
    )
    payload["candidates"]["iql_mobile"][0]["environment_interactions"] = 199999
    monkeypatch.setattr(task12, "_load_training_candidate_manifest", lambda path: payload)
    monkeypatch.setattr(task12, "run_physical_candidate_training", lambda *args, **kwargs: pytest.fail("training started"))
    with pytest.raises(ValueError, match="candidate.*200000|environment interactions"):
        train_frozen_candidates(
            ROOT,
            output_root=ROOT / "outputs/problem2_sr_mappo_v1/g5/validation",
            device="cpu",
            interactions=200000,
            methods=("iql_mobile",),
            seeds=(51001,),
        )


def test_cli_default_output_is_root_relative_from_an_alternate_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Path] = {}

    def fake_train(root: Path, **kwargs: object) -> dict[str, object]:
        captured["root"] = Path(root).resolve()
        captured["output_root"] = Path(kwargs["output_root"]).resolve()
        return {"status": "not_run"}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(task12, "train_frozen_candidates", fake_train)
    monkeypatch.setattr(
        task12.sys,
        "argv",
        ["run_g5_validation_tuning.py", "--root", str(ROOT), "--train-only"],
    )
    assert task12.main() == 0
    assert captured["root"] == ROOT.resolve()
    assert captured["output_root"] == (
        ROOT / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5"
    ).resolve()


def test_torn_identity_is_append_only_quarantined_and_explicitly_rerunnable(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "task12"
    attempt = (
        output_root
        / "training/iql_mobile/c01/51001/attempt-000001/iql_mobile__iql_mobile__51001"
    )
    attempt.mkdir(parents=True)
    torn = b'{"schema_version":"g5-physical-candidate-training-v1"}\n'
    (attempt / "summary.json").write_bytes(torn)

    with pytest.raises(RuntimeError, match="manifest"):
        task12.train_frozen_candidates_for_test(
            ROOT,
            output_root=output_root,
            device="cpu",
            interactions=1,
            methods=("iql_mobile",),
            seeds=(51001,),
        )
    quarantine = output_root / "training/iql_mobile/c01/51001/quarantine.jsonl"
    assert len(quarantine.read_text(encoding="utf-8").splitlines()) == 1
    assert (attempt / "summary.json").read_bytes() == torn

    result = task12.train_frozen_candidates_for_test(
        ROOT,
        output_root=output_root,
        device="cpu",
        interactions=1,
        methods=("iql_mobile",),
        seeds=(51001,),
        rerun_invalid_from_scratch=True,
    )
    assert result["job_count"] == 4
    assert (attempt / "summary.json").read_bytes() == torn
    assert (
        output_root
        / "training/iql_mobile/c01/51001/attempt-000002/iql_mobile__iql_mobile__51001/manifest.json"
    ).is_file()


def test_noncanonical_test_training_is_unmistakably_labeled(tmp_path: Path) -> None:
    result = physical_training.run_noncanonical_physical_candidate_training_for_test(
        _job("iql_mobile"), "cpu", 1, tmp_path / "training"
    )
    assert result["canonical"] is False
    assert result["evidence_status"] == "noncanonical_test_only"
    assert result["completion_validated"] is True
