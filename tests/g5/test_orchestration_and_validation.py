from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from problem2.evaluation.schema import (
    ARTIFACT_MANIFEST_SCHEMA,
    RAW_EPISODE_SCHEMA,
    VALIDATED_LONG_TABLE_SCHEMA,
)
from problem2.evaluation.validator import (
    ValidationError,
    quarantine_invalid_row,
    validate_long_table,
    validate_raw_episode,
)
from problem2.experiments.artifacts import (
    atomic_write_bytes,
    artifact_sha256,
    read_quarantine,
)
from problem2.experiments.ledger import AppendOnlyLedger, JobState, LedgerError
from problem2.experiments.orchestrator import deterministic_interleave, GpuTrainingLease
from problem2.experiments.recovery import atomic_checkpoint_write, recover_checkpoint


HASH_A = "a" * 64
HASH_B = "b" * 64
IDENTITY = "c" * 64


def _job(identity: str = IDENTITY, input_hash: str = HASH_A) -> dict[str, object]:
    return {
        "identity": identity,
        "input_hash": input_hash,
        "config_hash": HASH_A,
        "protocol_hash": HASH_B,
        "source_commit": "d" * 40,
    }


def _raw_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "evaluation_identity": IDENTITY,
        "canonical_training_identity": IDENTITY,
        "method": "sr_mappo_mobile",
        "condition_id": "sr_mappo_mobile",
        "scale": "g20x20_d2",
        "training_seed": 42,
        "scenario_id": 10000,
        "partition": "development",
        "source_commit": "d" * 40,
        "config_hash": HASH_A,
        "protocol_hash": HASH_B,
        "checkpoint_hash": "e" * 64,
        "evaluator_hash": "f" * 64,
        "scenario_panel_hash": "1" * 64,
        "episode_index": 0,
        "interaction_count": 2,
        "termination_reason": "horizon",
        "terminated": True,
        "initial_total_pest": 10.0,
        "final_total_pest": 1.0,
        "reduction_rate": 0.9,
        "success_at_0_85": True,
        "pesticide_initial_l": 1.0,
        "pesticide_remaining_l": 0.0,
        "pesticide_transferred_l": 1.0,
        "resource_conservation_residual_l": 0.0,
        "battery_replenishment_l": 0.0,
        "action_uav": 0,
        "action_vehicle_slot": 0,
        "rendezvous_distance_m": 2.0,
        "waiting_steps": 1,
        "pesticide_disabled_steps": 0,
        "return_steps": 0,
        "effective_spray_steps": 2,
        "source_locator": "episodes.jsonl:1",
    }
    row.update(overrides)
    return row


def test_append_only_ledger_legal_transition_and_duplicate_lease(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = AppendOnlyLedger(path)
    ledger.register(_job())

    lease = ledger.acquire(IDENTITY, worker_id="worker-a", lease_seconds=60)
    assert ledger.current(IDENTITY).state is JobState.RUNNING
    with pytest.raises(LedgerError, match="lease"):
        ledger.acquire(IDENTITY, worker_id="worker-b", lease_seconds=60)

    ledger.complete(IDENTITY, lease_id=lease.lease_id, worker_id="worker-a")
    assert ledger.current(IDENTITY).state is JobState.COMPLETED
    events = ledger.events(IDENTITY)
    assert [event["new_state"] for event in events] == ["pending", "running", "completed"]
    assert path.read_bytes().count(b"\n") == 3


def test_ledger_same_identity_retry_and_stale_drift_are_append_only(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = AppendOnlyLedger(path)
    ledger.register(_job())
    first = ledger.acquire(IDENTITY, worker_id="worker-a", lease_seconds=60)
    ledger.fail(IDENTITY, lease_id=first.lease_id, worker_id="worker-a", reason="oom")
    retry = ledger.retry(IDENTITY, worker_id="worker-a", input_hash=HASH_A)
    assert retry.attempt == 2
    assert ledger.current(IDENTITY).state is JobState.RUNNING
    ledger.mark_stale(IDENTITY, reason="protocol drift", observed_input_hash=HASH_B)
    assert ledger.current(IDENTITY).state is JobState.STALE
    with pytest.raises(LedgerError, match="stale"):
        ledger.retry(IDENTITY, worker_id="worker-a", input_hash=HASH_A)

    replayed = AppendOnlyLedger(path)
    assert replayed.current(IDENTITY).state is JobState.STALE
    assert len(replayed.events(IDENTITY)) == 5


def test_deterministic_scheduler_interleaves_methods_and_is_repeatable() -> None:
    jobs = [
        {"method": method, "scale": scale, "training_seed": seed, "identity": f"{method}-{scale}-{seed}"}
        for scale in ("g20x20_d2", "g30x50_d4")
        for seed in (42, 123)
        for method in ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile")
    ]
    first = deterministic_interleave(jobs)
    second = deterministic_interleave(jobs)
    assert [job["identity"] for job in first] == [job["identity"] for job in second]
    assert len({job["identity"] for job in first}) == len(jobs)
    assert [job["method"] for job in first[:3]] == ["sr_mappo_mobile", "mappo_mobile", "ippo_mobile"]


def test_gpu_training_lease_allows_one_owner_and_records_attempt() -> None:
    lease = GpuTrainingLease()
    first = lease.acquire(IDENTITY, worker_id="worker-a")
    assert first.attempt == 1
    with pytest.raises(LedgerError, match="GPU"):
        lease.acquire("b" * 64, worker_id="worker-b")
    lease.release(first.lease_id, peak_memory_bytes=123, runtime_seconds=4.5)
    assert lease.history[-1]["peak_memory_bytes"] == 123


def test_atomic_checkpoint_round_trip_and_previous_copy(tmp_path: Path) -> None:
    target = tmp_path / "checkpoint.json"
    atomic_checkpoint_write(target, {"identity": IDENTITY, "step": 1})
    atomic_checkpoint_write(target, {"identity": IDENTITY, "step": 2})
    payload = recover_checkpoint(target, expected_identity=IDENTITY)
    assert payload["step"] == 2
    assert json.loads(target.with_suffix(".json.previous").read_text())["step"] == 1


def test_artifact_write_is_atomic_and_hash_is_content_addressed(tmp_path: Path) -> None:
    target = tmp_path / "artifact.jsonl"
    raw = b'{"identity":"' + IDENTITY.encode() + b'"}\n'
    atomic_write_bytes(target, raw)
    assert target.read_bytes() == raw
    assert artifact_sha256(target) == hashlib.sha256(raw).hexdigest()


def test_valid_raw_episode_and_long_table_are_accepted() -> None:
    row = _raw_row()
    validate_raw_episode(row)
    validated = validate_long_table([row], expected_identities={IDENTITY})
    assert validated[0]["evaluation_identity"] == IDENTITY


@pytest.mark.parametrize(
    "override, message",
    [
        ({"reduction_rate": float("nan")}, "finite"),
        ({"interaction_count": 1, "terminated": False}, "terminal"),
        ({"battery_replenishment_l": 1.0}, "battery"),
        ({"resource_conservation_residual_l": 0.1}, "conservation"),
        ({"success_at_0_85": False}, "success"),
        ({"scenario_id": 30000, "partition": "sealed_test"}, "sealed"),
        ({"action_vehicle_slot": 99}, "action"),
    ],
)
def test_validator_rejects_corrupted_rows(override: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_raw_episode(_raw_row(**override))


def test_validator_rejects_duplicates_and_incomplete_expected_cells() -> None:
    row = _raw_row()
    with pytest.raises(ValidationError, match="duplicate"):
        validate_long_table([row, row], expected_identities={IDENTITY})
    with pytest.raises(ValidationError, match="incomplete"):
        validate_long_table([], expected_identities={IDENTITY})


def test_quarantine_preserves_original_bytes_locator_reason_and_hash(tmp_path: Path) -> None:
    raw = b'{"bad": NaN}\n'
    record = quarantine_invalid_row(
        tmp_path / "quarantine.jsonl", raw, locator="episodes.jsonl:7", reason="nonfinite"
    )
    assert record["original_bytes_b64"]
    assert record["locator"] == "episodes.jsonl:7"
    assert record["reason"] == "nonfinite"
    assert record["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert read_quarantine(tmp_path / "quarantine.jsonl")[0] == record


def test_schema_documents_expose_strict_required_fields() -> None:
    for schema in (RAW_EPISODE_SCHEMA, VALIDATED_LONG_TABLE_SCHEMA, ARTIFACT_MANIFEST_SCHEMA):
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["required"]
