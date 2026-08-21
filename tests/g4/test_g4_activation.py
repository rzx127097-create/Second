from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from problem2.experiments.g4_activation import run_activation_probe, run_probe_matrix
from problem2.experiments.g4_contract import (
    G4ContractError,
    load_g4_contract,
    load_g4_probe_manifest,
)
from problem2.experiments.g4_support import FixedSupportPolicy, MobileSupportPolicy


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = load_g4_contract(ROOT / "docs/evidence/g4/g4_contract.yaml")
MANIFEST = load_g4_probe_manifest(ROOT / "docs/evidence/g4/g4_probe_manifest.yaml")
OUTPUT_ROOT = ROOT / "outputs/problem2_sr_mappo_v1/g4/pytest-activation"


def test_activation_probe_records_a_fail_closed_scarcity_band(tmp_path: Path) -> None:
    result = run_activation_probe(
        CONTRACT,
        MANIFEST,
        support_policy=FixedSupportPolicy(),
        output_root=OUTPUT_ROOT,
    )

    assert result["scarcity_active"] is True
    lower, upper = result["activation_window"]
    assert CONTRACT.admissible_band[0] <= lower < upper <= CONTRACT.admissible_band[1]
    assert result["request_count"] > 0
    assert result["reservation_count"] > 0
    assert result["service_count"] > 0
    assert result["conservation_error_l"] <= 1.0e-9
    assert result["lineage"]["probe_manifest"] == str(MANIFEST.source_path)
    assert (OUTPUT_ROOT / "raw-probe.jsonl").exists()
    assert (OUTPUT_ROOT / "provenance.json").exists()


def test_activation_probe_rejects_validation_and_sealed_access() -> None:
    with pytest.raises(G4ContractError, match="validation access"):
        run_activation_probe(
            CONTRACT,
            replace(MANIFEST, validation_access_allowed=True),
            support_policy=FixedSupportPolicy(),
            output_root=OUTPUT_ROOT,
        )

    with pytest.raises(G4ContractError, match="sealed-test access"):
        run_activation_probe(
            CONTRACT,
            replace(MANIFEST, sealed_test_access_allowed=True),
            support_policy=FixedSupportPolicy(),
            output_root=OUTPUT_ROOT,
        )


def test_activation_probe_uses_the_same_inputs_for_each_counterfactual_arm() -> None:
    result = run_probe_matrix(CONTRACT, MANIFEST, output_root=OUTPUT_ROOT)

    assert result["lineage"]["validation_accessed"] is False
    assert result["lineage"]["sealed_test_accessed"] is False
    assert result["lineage"]["battery_replenishment_enabled"] is False
    pairs = result["paired_inputs"]
    assert pairs
    for pair in pairs:
        assert pair["fixed"]["input_fingerprint"] == pair["mobile"]["input_fingerprint"]
        assert pair["fixed"]["scale_id"] == pair["mobile"]["scale_id"]
        assert pair["fixed"]["seed"] == pair["mobile"]["seed"]
    assert result["arms"]
    assert {row["support_policy"] for row in result["arms"]} == {
        "fixed",
        "mobile",
    }
