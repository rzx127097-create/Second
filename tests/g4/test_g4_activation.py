from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import problem2.experiments.g4_activation as activation
from problem2.experiments.g4_activation import (
    run_activation_probe,
    run_probe_matrix,
    validate_activation_band,
)
from problem2.experiments.g4_contract import (
    G4ContractError,
    load_g4_contract,
    load_g4_probe_manifest,
)
from problem2.experiments.g4_support import FixedSupportPolicy, MobileSupportPolicy


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = load_g4_contract(ROOT / "docs/evidence/g4/g4_contract.yaml")
MANIFEST = load_g4_probe_manifest(ROOT / "docs/evidence/g4/g4_probe_manifest.yaml")


def test_activation_probe_records_a_fail_closed_scarcity_band(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    monkeypatch.setattr(activation, "CANONICAL_G4_ROOT", output_root.resolve())
    result = run_activation_probe(
        CONTRACT,
        MANIFEST,
        support_policy=FixedSupportPolicy(),
        output_root=output_root,
    )

    assert result["scarcity_active"] is True
    lower, upper = result["activation_window"]
    assert CONTRACT.admissible_band[0] <= lower < upper <= CONTRACT.admissible_band[1]
    assert result["request_count"] > 0
    assert result["reservation_count"] > 0
    assert result["service_count"] > 0
    assert result["conservation_error_l"] <= 1.0e-9
    assert result["lineage"]["probe_manifest"] == str(MANIFEST.source_path)
    assert result["records"][0]["initial_vehicle_inventory_l"] == 1.0
    assert result["records"][0]["initial_uav_pesticide_l"] == 0.05
    assert (output_root / "raw-probe.jsonl").exists()
    assert (output_root / "provenance.json").exists()


def test_activation_probe_rejects_validation_and_sealed_access(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    with pytest.raises(G4ContractError, match="validation access"):
        run_activation_probe(
            CONTRACT,
            replace(MANIFEST, validation_access_allowed=True),
            support_policy=FixedSupportPolicy(),
            output_root=output_root,
        )

    with pytest.raises(G4ContractError, match="sealed-test access"):
        run_activation_probe(
            CONTRACT,
            replace(MANIFEST, sealed_test_access_allowed=True),
            support_policy=FixedSupportPolicy(),
            output_root=output_root,
        )


def test_activation_probe_uses_the_same_inputs_for_each_counterfactual_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    monkeypatch.setattr(activation, "CANONICAL_G4_ROOT", output_root.resolve())
    result = run_probe_matrix(CONTRACT, MANIFEST, output_root=output_root)

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
        "fixed_support_probe",
        "mobile_support_probe",
    }


def _band_records(active_levels: set[float]) -> list[dict[str, object]]:
    return [
        {
            "scale_id": "g20x20_d2",
            "seed": 42,
            "scarcity_level_l": level,
            "scarcity_active": level in active_levels,
        }
        for level in (1.0, 6.5, 12.0)
    ]


def test_validate_activation_band_rejects_no_activation() -> None:
    with pytest.raises(G4ContractError, match="no activation"):
        validate_activation_band(_band_records(set()), (1.0, 6.5, 12.0))


def test_validate_activation_band_rejects_one_point_activation() -> None:
    with pytest.raises(G4ContractError, match="at least two"):
        validate_activation_band(_band_records({6.5}), (1.0, 6.5, 12.0))


def test_validate_activation_band_rejects_a_gap_between_active_points() -> None:
    with pytest.raises(G4ContractError, match="contiguous"):
        validate_activation_band(_band_records({1.0, 12.0}), (1.0, 6.5, 12.0))


def test_probe_matrix_rejects_mismatched_arm_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    monkeypatch.setattr(activation, "CANONICAL_G4_ROOT", output_root.resolve())

    def fake_probe(contract, manifest, *, support_policy, output_root):
        return {
            "activation_window": [1.0, 12.0]
            if isinstance(support_policy, FixedSupportPolicy)
            else [6.5, 12.0],
            "records": [],
            "lineage": {},
        }

    monkeypatch.setattr(activation, "run_activation_probe", fake_probe)
    with pytest.raises(G4ContractError, match="arm activation windows"):
        run_probe_matrix(CONTRACT, MANIFEST, output_root=output_root)
