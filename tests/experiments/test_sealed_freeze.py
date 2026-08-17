from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from problem2.algorithms.common.checkpoint import save_checkpoint
from problem2.experiments.freeze import (
    commit_sealed_access,
    create_sealed_unlock,
    create_validation_freeze,
    release_sealed_access,
    reserve_sealed_access,
    verify_sealed_evidence,
    verify_validation_freeze,
)
from problem2.experiments.job_identity import make_job_identity
from problem2.experiments.runner import JobRecord


ROOT = Path(__file__).resolve().parents[2]


def test_freeze_cli_requires_every_canonical_experiment_family(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    source = ROOT / "scripts" / "freeze_sealed_test.py"
    spec = importlib.util.spec_from_file_location("problem2_freeze_all_families", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    planned_families: list[str] = []
    captured_ids: tuple[str, ...] = ()

    class FakeOrchestrator:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def plan(self, family: str, *, execution_profile: str):
            assert execution_profile == "formal"
            planned_families.append(family)
            return (SimpleNamespace(identity=SimpleNamespace(job_id=f"{family}-job")),)

    def fake_freeze(*_args, expected_job_ids, **_kwargs):
        nonlocal captured_ids
        captured_ids = tuple(expected_job_ids)
        return {"freeze_hash": "f" * 64}

    monkeypatch.setattr(module, "_formal_config_ready", lambda *_: None)
    monkeypatch.setattr(module, "Chapter45Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(module, "load_job_record", lambda _: object())
    monkeypatch.setattr(module, "create_validation_freeze", fake_freeze)

    assert module.main([
        "freeze",
        "--config-dir", str(ROOT / "configs"),
        "--job-file", str(tmp_path / "job.json"),
        "--validation", str(tmp_path / "validation.jsonl"),
        "--output", str(tmp_path / "freeze.json"),
    ]) == 0
    assert planned_families == [
        "mechanism", "main_comparison", "sensitivity", "adaptation", "ablation",
    ]
    assert captured_ids == tuple(f"{family}-job" for family in planned_families)


def test_freeze_cli_simulation_uses_simulation_jobs_and_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    source = ROOT / "scripts" / "freeze_sealed_test.py"
    spec = importlib.util.spec_from_file_location("problem2_freeze_simulation", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    planned_profiles: list[str] = []
    captured_profile = ""

    class FakeOrchestrator:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def plan(self, family: str, *, execution_profile: str):
            planned_profiles.append(execution_profile)
            return (SimpleNamespace(identity=SimpleNamespace(job_id=f"{family}-job")),)

    def fake_freeze(*_args, execution_profile, **_kwargs):
        nonlocal captured_profile
        captured_profile = str(execution_profile)
        return {"freeze_hash": "f" * 64}

    monkeypatch.setattr(module, "Chapter45Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(module, "load_job_record", lambda _: object())
    monkeypatch.setattr(module, "create_validation_freeze", fake_freeze)
    monkeypatch.setattr(
        module,
        "audit_simulation_preflight",
        lambda *_args, **_kwargs: SimpleNamespace(ready=True, to_dict=lambda: {"ready": True}),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_formal_config_ready",
        lambda *_args, **_kwargs: pytest.fail("simulation freeze must not call the formal gate"),
    )

    assert module.main([
        "freeze", "--simulation",
        "--config-dir", str(ROOT / "configs"),
        "--job-file", str(tmp_path / "job.json"),
        "--validation", str(tmp_path / "validation.jsonl"),
        "--output", str(tmp_path / "freeze.json"),
    ]) == 0
    assert set(planned_profiles) == {"simulation"}
    assert captured_profile == "simulation"


class _Algorithm:
    training_seed = 0
    _trainer = None

    def state_dict(self):
        return {"weight": 1.0}


def _formal_job(tmp_path: Path, *, execution_profile: str = "formal") -> JobRecord:
    identity = make_job_identity(
        "sr_mappo_mobile",
        "s1",
        0,
        {"formal": True},
        config_hash="a" * 64,
        git_commit="b" * 40,
        execution_profile=execution_profile,
        target_updates=3,
        rollout_horizon=16,
        family="main_comparison",
        condition_id="sr_mappo_mobile__s1__seed-0",
        protocol_hash="c" * 64,
        source_tree_hash="d" * 64,
        git_dirty=False,
    )
    checkpoint = tmp_path / "checkpoints" / f"{identity.job_id}.pt"
    provenance = {"job_id": identity.job_id, **identity.to_dict()}
    save_checkpoint(checkpoint, _Algorithm(), step=3, provenance=provenance)
    return JobRecord(
        identity=identity,
        status="completed",
        checkpoint_path=checkpoint,
        checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        checkpoint_step=3,
    )


def _validation_file(tmp_path: Path, job: JobRecord) -> Path:
    path = tmp_path / "validation.jsonl"
    rows = [
        {
            "run_id": f"{job.job_id}:0:{scenario}",
            "job_id": job.job_id,
            "method": job.identity.method,
            "scale": job.identity.scale,
            "training_seed": job.identity.training_seed,
            "scenario_id": scenario,
            "split": "validation",
            "config_hash": job.identity.config_hash,
            "git_commit": job.identity.git_commit,
            "git_dirty": job.identity.git_dirty,
            "execution_profile": job.identity.execution_profile,
            "family": job.identity.family,
            "condition_id": job.identity.condition_id,
            "protocol_hash": job.identity.protocol_hash,
            "source_tree_hash": job.identity.source_tree_hash,
            "checkpoint_sha256": job.checkpoint_sha256,
            "checkpoint_step": job.checkpoint_step,
        }
        for scenario in ("val_001", "val_s1_002")
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_validation_freeze_binds_checkpoints_validation_and_statistics(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)
    freeze_path = tmp_path / "validation-freeze.json"

    manifest = create_validation_freeze(
        freeze_path,
        config_hash=job.identity.config_hash,
        protocol_hash=job.identity.protocol_hash,
        statistics={
            "practical_equivalence_margin": 0.02,
            "practical_equivalence_basis": "field measurement resolution",
            "bootstrap_draws": 5000,
        },
        jobs=[job],
        expected_job_ids=(job.job_id,),
        validation_paths=[validation],
        validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
    )

    assert manifest["status"] == "frozen"
    assert len(str(manifest["freeze_hash"])) == 64
    assert manifest["selected_checkpoints"][0]["checkpoint_step"] == 3
    assert verify_validation_freeze(freeze_path)["freeze_hash"] == manifest["freeze_hash"]

    job.checkpoint_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checkpoint hash"):
        verify_validation_freeze(freeze_path)


def test_simulation_validation_freeze_accepts_only_simulation_jobs(tmp_path: Path) -> None:
    job = _formal_job(tmp_path, execution_profile="simulation")
    validation = _validation_file(tmp_path, job)

    manifest = create_validation_freeze(
        tmp_path / "simulation-freeze.json",
        config_hash=job.identity.config_hash,
        protocol_hash=job.identity.protocol_hash,
        statistics={
            "practical_equivalence_margin": 0.02,
            "practical_equivalence_basis": "controlled-simulation reporting resolution",
        },
        jobs=[job],
        expected_job_ids=(job.job_id,),
        validation_paths=[validation],
        validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
        execution_profile="simulation",
    )

    assert manifest["execution_profile"] == "simulation"
    assert verify_validation_freeze(tmp_path / "simulation-freeze.json")["execution_profile"] == "simulation"
    with pytest.raises(ValueError, match="formal jobs"):
        create_validation_freeze(
            tmp_path / "wrong-profile-freeze.json",
            config_hash=job.identity.config_hash,
            protocol_hash=job.identity.protocol_hash,
            statistics={
                "practical_equivalence_margin": 0.02,
                "practical_equivalence_basis": "controlled-simulation reporting resolution",
            },
            jobs=[job],
            expected_job_ids=(job.job_id,),
            validation_paths=[validation],
            validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
        )


def test_validation_freeze_rejects_mislabeled_job_identity_fields(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)
    rows = [json.loads(line) for line in validation.read_text(encoding="utf-8").splitlines()]
    rows[0]["method"] = "mappo_mobile"
    validation.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="method mismatch"):
        create_validation_freeze(
            tmp_path / "validation-freeze.json",
            config_hash=job.identity.config_hash,
            protocol_hash=job.identity.protocol_hash,
            statistics={
                "practical_equivalence_margin": 0.02,
                "practical_equivalence_basis": "field measurement resolution",
            },
            jobs=[job],
            expected_job_ids=(job.job_id,),
            validation_paths=[validation],
            validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
        )


def test_validation_freeze_rejects_caller_selected_job_subset(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)

    with pytest.raises(ValueError, match="formal job set"):
        create_validation_freeze(
            tmp_path / "validation-freeze.json",
            config_hash=job.identity.config_hash,
            protocol_hash=job.identity.protocol_hash,
            statistics={
                "practical_equivalence_margin": 0.02,
                "practical_equivalence_basis": "field measurement resolution",
            },
            jobs=[job],
            expected_job_ids=(job.job_id, "e" * 64),
            validation_paths=[validation],
            validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
        )


def test_sealed_unlock_is_consumable_once_per_frozen_job_and_scenario(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)
    freeze_path = tmp_path / "validation-freeze.json"
    create_validation_freeze(
        freeze_path,
        config_hash=job.identity.config_hash,
        protocol_hash=job.identity.protocol_hash,
        statistics={
            "practical_equivalence_margin": 0.02,
            "practical_equivalence_basis": "field measurement resolution",
        },
        jobs=[job],
        expected_job_ids=(job.job_id,),
        validation_paths=[validation],
        validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
    )
    from scripts.freeze_sealed_test import main as freeze_cli

    cli_unlock_path = tmp_path / "cli-sealed-unlock.json"
    assert freeze_cli([
        "unlock",
        "--freeze", str(freeze_path),
        "--output", str(cli_unlock_path),
        "--scenario", "test_001",
    ]) == 0
    assert cli_unlock_path.is_file()

    unlock_path = tmp_path / "sealed-unlock.json"
    create_sealed_unlock(
        unlock_path,
        freeze_path=freeze_path,
        sealed_scenarios=("test_001",),
    )

    reservation = reserve_sealed_access(
        unlock_path,
        freeze_path=freeze_path,
        job_id=job.job_id,
        scenario_id="test_001",
    )
    assert reservation["access_key"] == f"{job.job_id}:test_001"
    with pytest.raises(ValueError, match="active reservation"):
        reserve_sealed_access(
            unlock_path,
            freeze_path=freeze_path,
            job_id=job.job_id,
            scenario_id="test_001",
        )

    sealed_row = {
        "run_id": f"{job.job_id}:0:test_001",
        "job_id": job.job_id,
        "method": job.identity.method,
        "scale": job.identity.scale,
        "training_seed": job.identity.training_seed,
        "split": "sealed_test",
        "scenario_id": "test_001",
        "config_hash": job.identity.config_hash,
        "git_commit": job.identity.git_commit,
        "git_dirty": job.identity.git_dirty,
        "family": job.identity.family,
        "condition_id": job.identity.condition_id,
        "protocol_hash": job.identity.protocol_hash,
        "source_tree_hash": job.identity.source_tree_hash,
        "checkpoint_sha256": job.checkpoint_sha256,
        "checkpoint_step": job.checkpoint_step,
    }
    evidence = tmp_path / "sealed.jsonl"
    evidence.write_text(json.dumps(sealed_row) + "\n", encoding="utf-8")
    commit_sealed_access(
        unlock_path,
        freeze_path=freeze_path,
        reservation_id=str(reservation["reservation_id"]),
        evidence_path=evidence,
    )
    with pytest.raises(ValueError, match="already consumed"):
        reserve_sealed_access(
            unlock_path,
            freeze_path=freeze_path,
            job_id=job.job_id,
            scenario_id="test_001",
        )
    assert verify_sealed_evidence(
        [sealed_row], evidence_paths=[evidence],
        freeze_path=freeze_path, unlock_path=unlock_path,
    )["verified_record_count"] == 1

    mislabeled = {**sealed_row, "method": "mappo_mobile"}
    with pytest.raises(ValueError, match="method mismatch"):
        verify_sealed_evidence(
            [mislabeled], evidence_paths=[evidence],
            freeze_path=freeze_path, unlock_path=unlock_path,
        )


def test_sealed_reservation_commit_binds_raw_hash_and_is_concurrency_safe(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)
    freeze_path = tmp_path / "validation-freeze.json"
    create_validation_freeze(
        freeze_path,
        config_hash=job.identity.config_hash,
        protocol_hash=job.identity.protocol_hash,
        statistics={
            "practical_equivalence_margin": 0.02,
            "practical_equivalence_basis": "field measurement resolution",
        },
        jobs=[job],
        expected_job_ids=(job.job_id,),
        validation_paths=[validation],
        validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
    )
    unlock_path = tmp_path / "sealed-unlock.json"
    create_sealed_unlock(
        unlock_path,
        freeze_path=freeze_path,
        sealed_scenarios=("test_001",),
    )

    def reserve() -> dict[str, object] | Exception:
        try:
            return reserve_sealed_access(
                unlock_path,
                freeze_path=freeze_path,
                job_id=job.job_id,
                scenario_id="test_001",
            )
        except Exception as exc:  # noqa: BLE001 - collect both race outcomes
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: reserve(), range(2)))
    reservations = [value for value in outcomes if isinstance(value, dict)]
    failures = [value for value in outcomes if isinstance(value, Exception)]
    assert len(reservations) == 1
    assert len(failures) == 1

    release_sealed_access(
        unlock_path,
        freeze_path=freeze_path,
        reservation_id=str(reservations[0]["reservation_id"]),
    )
    reservation = reserve_sealed_access(
        unlock_path,
        freeze_path=freeze_path,
        job_id=job.job_id,
        scenario_id="test_001",
    )
    sealed_row = {
        "run_id": f"{job.job_id}:0:test_001",
        "job_id": job.job_id,
        "method": job.identity.method,
        "scale": job.identity.scale,
        "training_seed": job.identity.training_seed,
        "split": "sealed_test",
        "scenario_id": "test_001",
        "config_hash": job.identity.config_hash,
        "git_commit": job.identity.git_commit,
        "git_dirty": job.identity.git_dirty,
        "family": job.identity.family,
        "condition_id": job.identity.condition_id,
        "protocol_hash": job.identity.protocol_hash,
        "source_tree_hash": job.identity.source_tree_hash,
        "checkpoint_sha256": job.checkpoint_sha256,
        "checkpoint_step": job.checkpoint_step,
    }
    evidence = tmp_path / "sealed.jsonl"
    evidence.write_text(json.dumps(sealed_row) + "\n", encoding="utf-8")
    receipt = commit_sealed_access(
        unlock_path,
        freeze_path=freeze_path,
        reservation_id=str(reservation["reservation_id"]),
        evidence_path=evidence,
    )
    assert receipt["raw_sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert verify_sealed_evidence(
        [sealed_row],
        evidence_paths=[evidence],
        freeze_path=freeze_path,
        unlock_path=unlock_path,
    )["verified_record_count"] == 1

    evidence.write_text(json.dumps({**sealed_row, "method": "mappo_mobile"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        verify_sealed_evidence(
            [sealed_row],
            evidence_paths=[evidence],
            freeze_path=freeze_path,
            unlock_path=unlock_path,
        )


def test_sealed_unlock_rejects_tampered_immutable_scope(tmp_path: Path) -> None:
    job = _formal_job(tmp_path)
    validation = _validation_file(tmp_path, job)
    freeze_path = tmp_path / "validation-freeze.json"
    create_validation_freeze(
        freeze_path,
        config_hash=job.identity.config_hash,
        protocol_hash=job.identity.protocol_hash,
        statistics={
            "practical_equivalence_margin": 0.02,
            "practical_equivalence_basis": "field measurement resolution",
        },
        jobs=[job],
        expected_job_ids=(job.job_id,),
        validation_paths=[validation],
        validation_scenarios_by_scale={"s1": ("val_001", "val_s1_002")},
    )
    unlock_path = tmp_path / "sealed-unlock.json"
    create_sealed_unlock(
        unlock_path,
        freeze_path=freeze_path,
        sealed_scenarios=("test_001",),
    )
    payload = json.loads(unlock_path.read_text(encoding="utf-8"))
    payload["allowed_scenarios"].append("test_unregistered")
    unlock_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unlock identity"):
        reserve_sealed_access(
            unlock_path,
            freeze_path=freeze_path,
            job_id=job.job_id,
            scenario_id="test_001",
        )
