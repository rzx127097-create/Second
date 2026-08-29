from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from scripts import _g5_cli


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "c" * 40
SOURCE_SCOPE_SHA256 = "d" * 64


@pytest.fixture(scope="module")
def current_preflight() -> dict[str, object]:
    return _g5_cli.read_only_preflight(ROOT, gate="G6")


def _git_result(stdout: str) -> object:
    return type("GitResult", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()


def _controlled_git(monkeypatch: pytest.MonkeyPatch, *, dirty: bool, remote_matches: bool) -> None:
    local = "a" * 40
    upstream = local
    remote = local if remote_matches else "b" * 40

    def fake_run(args: list[str], **_: object) -> object:
        command = tuple(args)
        if command[:2] == ("git", "status"):
            return _git_result(" M src/problem2/example.py\n" if dirty else "")
        if command == ("git", "rev-parse", "HEAD"):
            return _git_result(local + "\n")
        if command == ("git", "rev-parse", "@{upstream}"):
            return _git_result(upstream + "\n")
        if command == ("git", "branch", "--show-current"):
            return _git_result("codex/problem2-dynamic-pest-model\n")
        if command[:3] == ("git", "ls-remote", "origin"):
            return _git_result(f"{remote}\trefs/heads/codex/problem2-dynamic-pest-model\n")
        raise AssertionError(f"unexpected subprocess command: {args!r}")

    monkeypatch.setattr(_g5_cli.subprocess, "run", fake_run)


def test_preflight_exposes_the_complete_g6_entry_contract(current_preflight: dict[str, object]) -> None:
    checks = current_preflight["checks"]
    required = {
        "frozen_source_commit",
        "frozen_source_scope",
        "runner_available",
        "recovery_available",
        "checkpoint_validator_available",
        "validation_evaluator_available",
        "scheduler_order",
        "storage_budget",
        "gpu_hours",
        "disk_budget",
        "dynamic_ecology",
        "dynamic_output_root",
        "restricted_experiment_families",
        "validation_panel",
        "hardware_inventory",
    }
    assert required <= set(checks), f"missing G6 preflight checks: {sorted(required - set(checks))}"


def test_preflight_rejects_a_dirty_tracked_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    _controlled_git(monkeypatch, dirty=True, remote_matches=True)
    report = _g5_cli.read_only_preflight(ROOT, gate="G6")
    assert report["checks"]["frozen_source_clean"] is False


def test_preflight_rejects_local_upstream_remote_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _controlled_git(monkeypatch, dirty=False, remote_matches=False)
    report = _g5_cli.read_only_preflight(ROOT, gate="G6")
    assert report["checks"]["frozen_source_remote"] is False


def test_freeze_payloads_bind_the_exact_source_commit(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    assert formal_freeze_payloads["g6_training"]["provenance"]["source_commit"] == SOURCE_COMMIT
    assert formal_freeze_payloads["g6_validation"]["provenance"]["source_commit"] == SOURCE_COMMIT


def test_freeze_payloads_bind_the_same_frozen_source_scope(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    assert formal_freeze_payloads["g6_training"]["source_scope_sha256"] == SOURCE_SCOPE_SHA256
    assert formal_freeze_payloads["g6_validation"]["source_scope_sha256"] == SOURCE_SCOPE_SHA256


def test_training_manifest_freezes_scheduler_order(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_training"]
    identities = [job["canonical_training_identity"] for job in payload["jobs"]]
    assert len(payload["scheduler_order"]) == len(identities)
    assert set(payload["scheduler_order"]) == set(identities)


def test_training_manifest_freezes_storage_estimate(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_training"]
    assert payload["expected_storage_bytes"] > 0


def test_training_manifest_freezes_gpu_hours_estimate(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_training"]
    assert payload["expected_gpu_hours"] > 0


def test_preflight_disk_budget_uses_the_frozen_estimate_and_atomic_headroom(
    current_preflight: dict[str, object],
) -> None:
    budget = current_preflight["resource_budget"]
    assert budget["required_bytes_with_atomic_headroom"] > budget["expected_storage_bytes"] > 0
    assert budget["available_bytes"] >= budget["required_bytes_with_atomic_headroom"]


@pytest.mark.parametrize(
    "script_name",
    ["run_g6_jobs.py", "resume_g6_jobs.py", "preflight_g6.py"],
)
def test_g6_entry_module_import_is_side_effect_free_and_exposes_main(
    script_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = ROOT / "scripts" / script_name
    monkeypatch.syspath_prepend(str(path.parent))
    monkeypatch.setattr(sys, "argv", [script_name])
    spec = importlib.util.spec_from_file_location(f"phase1_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
