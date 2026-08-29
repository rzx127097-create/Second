from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from problem2.experiments.identity import canonical_training_identity
from problem2.experiments.ledger import AppendOnlyLedger, JobState, LedgerError
from problem2.experiments.recovery import atomic_checkpoint_write, recover_checkpoint
from problem2.training.selection import build_formal_freeze_payloads


ROOT = Path(__file__).resolve().parents[2]
TRAINING_MANIFEST = ROOT / "outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json"
HASH_A = "a" * 64
HASH_B = "b" * 64
SOURCE_COMMIT = "c" * 40
IDENTITY = canonical_training_identity(
    "sr_mappo_mobile", "g20x20_d2", 42, HASH_A, SOURCE_COMMIT
)


def _ledger_job() -> dict[str, str]:
    return {
        "identity": IDENTITY,
        "input_hash": HASH_A,
        "config_hash": HASH_A,
        "protocol_hash": HASH_B,
        "source_commit": SOURCE_COMMIT,
        "checkpoint_hash": "d" * 64,
        "scenario_panel_hash": "e" * 64,
    }


def test_frozen_manifest_contains_exact_unique_canonical_training_identities() -> None:
    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    observed = [job["canonical_training_identity"] for job in payload["jobs"]]
    expected = [
        canonical_training_identity(
            job["method"], job["scale"], job["training_seed"], job["config_hash"], job["git_commit"]
        )
        for job in payload["jobs"]
    ]
    assert observed == expected
    assert len(observed) == len(set(observed)) == 375


def test_freeze_builder_rejects_duplicate_canonical_training_identities() -> None:
    jobs = [
        {
            "canonical_training_identity": f"{index:064x}",
            "family": "algorithm_scale" if index < 150 else "other",
            "config_hash": HASH_A,
        }
        for index in range(375)
    ]
    jobs[-1]["canonical_training_identity"] = jobs[0]["canonical_training_identity"]
    with pytest.raises(ValueError, match="unique"):
        build_formal_freeze_payloads(
            jobs,
            validation_scenario_ids=range(20000, 20050),
            validation_panel_hash=HASH_A,
            sealed_scenario_ids=range(30000, 30100),
            sealed_panel_hash=HASH_B,
            source_commit=SOURCE_COMMIT,
            protocol_hash="d" * 64,
        )


def test_g6_job_and_attempt_transitions_are_append_only(tmp_path: Path) -> None:
    ledger_path = tmp_path / "job-events.jsonl"
    ledger = AppendOnlyLedger(ledger_path)
    ledger.register(_ledger_job())
    first = ledger.acquire(IDENTITY, worker_id="worker-a")
    ledger.fail(IDENTITY, lease_id=first.lease_id, worker_id="worker-a", reason="transient")
    second = ledger.retry(
        IDENTITY,
        worker_id="worker-a",
        input_hash=HASH_A,
        config_hash=HASH_A,
        protocol_hash=HASH_B,
        source_commit=SOURCE_COMMIT,
        checkpoint_hash="d" * 64,
        scenario_panel_hash="e" * 64,
    )
    ledger.complete(IDENTITY, lease_id=second.lease_id, worker_id="worker-a")

    events = ledger.events(IDENTITY)
    assert [event["new_state"] for event in events] == [
        "pending", "running", "failed", "pending", "running", "completed"
    ]
    assert second.attempt == 2
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == len(events)
    assert AppendOnlyLedger(ledger_path).current(IDENTITY).state is JobState.COMPLETED


def test_g6_ledger_events_record_attempt_host_process_time_and_artifact_provenance(
    tmp_path: Path,
) -> None:
    ledger = AppendOnlyLedger(tmp_path / "job-events.jsonl")
    ledger.register(_ledger_job())
    lease = ledger.acquire(IDENTITY, worker_id="worker-a")
    ledger.complete(IDENTITY, lease_id=lease.lease_id, worker_id="worker-a")
    for event in ledger.events(IDENTITY):
        assert {"utc_time", "host_id", "process_id", "attempt"} <= set(event)
    assert "artifact_hashes" in ledger.events(IDENTITY)[-1]


def test_retry_with_any_frozen_input_drift_marks_the_identity_stale(tmp_path: Path) -> None:
    ledger = AppendOnlyLedger(tmp_path / "job-events.jsonl")
    ledger.register(_ledger_job())
    lease = ledger.acquire(IDENTITY, worker_id="worker-a")
    ledger.fail(IDENTITY, lease_id=lease.lease_id, worker_id="worker-a", reason="transient")
    with pytest.raises(LedgerError, match="drift"):
        ledger.retry(IDENTITY, worker_id="worker-a", input_hash="f" * 64)
    assert ledger.current(IDENTITY).state is JobState.STALE


def test_atomic_checkpoint_retains_previous_valid_copy_and_verifies_expected_hash(
    tmp_path: Path,
) -> None:
    target = tmp_path / "checkpoint.json"
    first_hash = atomic_checkpoint_write(target, {"identity": IDENTITY, "step": 1})
    second_hash = atomic_checkpoint_write(target, {"identity": IDENTITY, "step": 2})
    previous = target.with_suffix(".json.previous")

    assert hashlib.sha256(previous.read_bytes()).hexdigest() == first_hash
    assert recover_checkpoint(
        target, expected_identity=IDENTITY, expected_sha256=second_hash
    )["step"] == 2
    with pytest.raises(ValueError, match="hash"):
        recover_checkpoint(target, expected_identity=IDENTITY, expected_sha256="f" * 64)


def test_ablation_and_sensitivity_jobs_are_exactly_sr_mappo_mobile() -> None:
    payload = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    restricted = [
        job for job in payload["jobs"] if job["family"] in {"sr_mappo_ablation", "sr_mappo_sensitivity"}
    ]
    assert restricted
    assert {job["method"] for job in restricted} == {"sr_mappo_mobile"}
