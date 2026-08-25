from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from problem2.evaluation.sealed_lock import (
    SealedAccessError,
    assert_no_sealed_access,
    assert_partition_allowed,
    load_sealed_lock,
    unlock_g7,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("scenario_id", [30000, 30099])
def test_g5_partition_guard_rejects_sealed_ids_and_paths(scenario_id: int) -> None:
    for partition in ("sealed_test", "sealed", "g7/sealed"):
        with pytest.raises(SealedAccessError):
            assert_partition_allowed(gate="G5", partition=partition, scenario_id=scenario_id)
    with pytest.raises(SealedAccessError):
        assert_partition_allowed(gate="G5", partition="development", scenario_id=scenario_id)


@pytest.mark.parametrize("flag", [True, 1, "true", "1"])
def test_truthy_sealed_access_flags_fail_closed(flag: object) -> None:
    with pytest.raises(SealedAccessError):
        assert_no_sealed_access(gate="G5", scenario_id=30000, sealed_accessed=flag)


def test_pathlike_sealed_locator_is_denied() -> None:
    with pytest.raises(SealedAccessError):
        assert_no_sealed_access("G5", path=Path("outputs/sealed/episode.jsonl"))


def test_validation_requires_explicit_authorization_but_development_is_allowed() -> None:
    assert_partition_allowed(gate="G5", partition="development", scenario_id=10000)
    with pytest.raises(SealedAccessError):
        assert_partition_allowed(gate="G5", partition="validation", scenario_id=20000)


def test_lock_is_unchanged_and_unlock_denied_during_g5(tmp_path: Path) -> None:
    lock_path = tmp_path / "sealed-lock.yaml"
    lock_path.write_text(
        "status: locked\nmaximum_unlock_count: 1\nactual_unlock_count: 0\nunlock_gate: G7\n",
        encoding="utf-8",
    )
    before = lock_path.read_bytes()
    lock = load_sealed_lock(lock_path)
    assert lock.actual_unlock_count == 0
    with pytest.raises(SealedAccessError):
        unlock_g7(lock_path, gate="G5", operator="test", prerequisites={})
    assert lock_path.read_bytes() == before


def test_lock_rejects_boolean_unlock_counter(tmp_path: Path) -> None:
    lock_path = tmp_path / "sealed-lock.yaml"
    lock_path.write_text(
        "status: locked\nmaximum_unlock_count: 1\nactual_unlock_count: false\nunlock_gate: G7\n",
        encoding="utf-8",
    )
    with pytest.raises(SealedAccessError):
        load_sealed_lock(lock_path)


def test_preflight_report_is_read_only_and_contains_exact_audit_fields() -> None:
    from scripts._g5_cli import read_only_preflight

    report = read_only_preflight(ROOT, gate="G6")
    assert report["queue_created"] is False
    assert report["sealed_accessed"] is False
    assert {
        "frozen_contract", "registry_hashes", "frozen_source_clean",
        "frozen_source_remote", "g4_reconciliation", "road_cache_provenance",
        "output_confinement", "disk_space", "runtime_inventory",
        "no_sealed_identities", "sealed_lock",
    } <= set(report["checks"]) | set(report["details"])


def test_registry_preflight_requires_exact_task7_registry_keys() -> None:
    from scripts._g5_cli import _registry_hashes_match

    expected = {
        "configs/problem2/g5/families.yaml": "a" * 64,
        "configs/problem2/g5/ablations.yaml": "b" * 64,
        "configs/problem2/g5/sensitivity.yaml": "c" * 64,
    }
    assert _registry_hashes_match(expected, expected)
    assert not _registry_hashes_match(
        expected,
        {key: value for key, value in expected.items() if key != "configs/problem2/g5/sensitivity.yaml"},
    )


def test_preflight_rejects_arbitrary_root_for_output_confinement(tmp_path: Path) -> None:
    from scripts._g5_cli import read_only_preflight

    report = read_only_preflight(tmp_path, gate="G6")
    assert report["checks"]["output_confinement"] is False


@pytest.mark.parametrize(
    "script, args",
    [
        ("run_g5_jobs.py", ["--scenario-id", "30000"]),
        ("validate_g5_artifacts.py", ["--partition", "sealed_test"]),
        ("preflight_g6.py", ["--scenario-id", "30099"]),
        ("run_g6_jobs.py", ["--scenario-id", "30000"]),
        ("resume_g6_jobs.py", ["--scenario-id", "30099"]),
        ("preflight_g7.py", ["--scenario-id", "30000"]),
        ("unlock_g7.py", ["--scenario-id", "30099"]),
        ("run_g7_evaluation.py", ["--scenario-id", "30000"]),
    ],
)
def test_public_cli_denies_sealed_inputs(script: str, args: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "sealed" in (result.stderr + result.stdout).lower()
