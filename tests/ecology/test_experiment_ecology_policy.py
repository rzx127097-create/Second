from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from problem2.experiments.ecology_policy import (
    DYNAMIC_OUTPUT_ROOT,
    EcologyMode,
    assert_dynamic_primary_environment,
    resolve_output_root,
)


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_G5 = ROOT / "outputs/problem2_sr_mappo_v1/g5"


def test_dynamic_primary_rehomes_historical_requested_root() -> None:
    requested = HISTORICAL_G5 / "pilots"

    resolved = resolve_output_root(
        ROOT,
        "G5",
        requested,
        primary=True,
        partition="development",
        ecology_mode=EcologyMode.DYNAMIC,
    )

    assert resolved == ROOT / DYNAMIC_OUTPUT_ROOT / "g5" / "pilots"


def test_dynamic_primary_rejects_static_mode_and_non_primary_partition() -> None:
    with pytest.raises(ValueError, match="dynamic ecology"):
        resolve_output_root(
            ROOT,
            "G5",
            None,
            primary=True,
            partition="development",
            ecology_mode=EcologyMode.STATIC_DIAGNOSTIC,
        )
    with pytest.raises(ValueError, match="partition"):
        resolve_output_root(
            ROOT,
            "G5",
            None,
            primary=True,
            partition="unknown",
            ecology_mode=EcologyMode.DYNAMIC,
        )


def test_static_diagnostic_is_explicit_and_confined() -> None:
    resolved = resolve_output_root(
        ROOT,
        "G5",
        None,
        primary=False,
        partition="development",
        ecology_mode=EcologyMode.STATIC_DIAGNOSTIC,
    )

    assert resolved == ROOT / "outputs/problem2_sr_mappo_v1/diagnostics/static_ecology/g5"
    assert "diagnostics/static_ecology" in resolved.as_posix()

    with pytest.raises(ValueError, match="development"):
        resolve_output_root(
            ROOT,
            "G5",
            resolved,
            primary=False,
            partition="validation",
            ecology_mode=EcologyMode.STATIC_DIAGNOSTIC,
        )


def test_static_diagnostic_cannot_be_primary() -> None:
    with pytest.raises(ValueError, match="primary"):
        resolve_output_root(
            ROOT,
            "G5",
            None,
            primary=True,
            partition="development",
            ecology_mode=EcologyMode.STATIC_DIAGNOSTIC,
        )


def test_static_diagnostic_scope_rejects_external_output_root(tmp_path: Path) -> None:
    from problem2.training.tuning import _validate_static_diagnostic_scope

    with pytest.raises(ValueError, match="diagnostic"):
        _validate_static_diagnostic_scope(ROOT, tmp_path)


def test_canonical_validation_store_defaults_to_dynamic_namespace() -> None:
    from problem2.experiments.g5_contract import load_g5_contract
    from problem2.training.tuning import CanonicalValidationStore

    contract = load_g5_contract(ROOT)
    store = CanonicalValidationStore(
        ROOT,
        candidate_manifest=ROOT / "outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json",
        budget_manifest=ROOT / "outputs/problem2_sr_mappo_v1/g5/manifests/pilot-budget.json",
        output_root=ROOT / DYNAMIC_OUTPUT_ROOT / "g5" / "validation",
        protocol_hash=contract.file_hashes["configs/problem2/g5/protocol.yaml"],
        physical_scenario_contract_hash=contract.file_hashes[
            "docs/evidence/g5/physical_scenario_contract.yaml"
        ],
    )

    assert store.require_dynamic_ecology is True
    assert store.output_root == ROOT / DYNAMIC_OUTPUT_ROOT / "g5" / "validation"


def test_dynamic_primary_environment_requires_dynamic_provenance() -> None:
    class Environment:
        ecology_mode = "dynamic"
        primary_eligible = True
        partition = "development"
        replenished_resource = "pesticide"
        battery_replenishment_enabled = False
        source_provenance = {
            "ecology_version": "problem2-dynamic-pest-v1",
            "ecology_config_sha256": "a" * 64,
            "ecology_scenario_sha256": "b" * 64,
            "ecology_source_commit": "c" * 40,
            "ecology_implementation_version": "problem2-dynamic-pest-v1",
        }

    assert_dynamic_primary_environment(Environment(), partition="development")

    Environment.ecology_mode = "static_diagnostic"
    with pytest.raises(ValueError, match="dynamic"):
        assert_dynamic_primary_environment(Environment(), partition="development")


@pytest.mark.parametrize(
    ("script", "arguments"),
    [
        (
            "run_g3_training_smoke.py",
            [
                "--config",
                "configs/problem2/g3_heterogeneous_marl.yaml",
                "--output-root",
                "outputs/problem2_sr_mappo_v1/g3",
                "--seed",
                "9017",
                "--updates",
                "1",
            ],
        ),
        ("run_g4_mechanism_probe.py", []),
        ("run_g5_smoke.py", ["--device", "cpu", "--interactions", "1"]),
        ("run_g5_pilots.py", ["--interactions", "1", "--limit", "1"]),
        ("run_g5_jobs.py", []),
        ("run_g5_validation_tuning.py", ["--train-only"]),
        ("preflight_g6.py", []),
        ("run_g6_jobs.py", []),
        ("preflight_g7.py", []),
        ("run_g7_evaluation.py", []),
    ],
)
def test_primary_cli_rejects_static_ecology_before_execution(
    script: str, arguments: list[str]
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / script),
            *arguments,
            "--ecology-mode",
            "static_diagnostic",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "dynamic ecology" in (result.stdout + result.stderr).lower()
