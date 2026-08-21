from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from problem2.experiments.g4_contract import (
    G4ContractError,
    load_g4_contract,
    load_g4_probe_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "docs" / "evidence" / "g4" / "g4_contract.yaml"
MANIFEST_PATH = ROOT / "docs" / "evidence" / "g4" / "g4_probe_manifest.yaml"


def _payload(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict, tmp_path: Path) -> Path:
    target = tmp_path / path.name
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return target


def test_g4_contract_exposes_frozen_boundary() -> None:
    contract = load_g4_contract(CONTRACT_PATH)
    manifest = load_g4_probe_manifest(MANIFEST_PATH)

    assert contract.scarcity_axis == "initial_vehicle_inventory_l"
    assert contract.admissible_band == (1.0, 12.0)
    assert contract.request_trigger_initial_uav_pesticide_l == 0.05
    assert contract.probe_scales == ("g20x20_d2", "g20x30_d3", "g30x30_d3")
    assert contract.probe_seeds == (42, 123, 2024)
    assert contract.comparator_pair == ("fixed_support_probe", "mobile_support_probe")
    assert contract.metrics == (
        "request_count",
        "reservation_count",
        "service_count",
        "started_service_waiting_time_s",
        "euclidean_service_start_distance_m",
        "pesticide_disabled_time_s",
        "sprayed_volume_l",
        "conservation_error_l",
    )
    assert contract.output_root.as_posix() == "outputs/problem2_sr_mappo_v1/g4"
    assert "mechanism activation" in contract.permitted_claim_boundary
    assert manifest.probe_scales == contract.probe_scales
    assert manifest.probe_seeds == contract.probe_seeds
    assert manifest.validation_access_allowed is False
    assert manifest.sealed_test_access_allowed is False


def test_g4_contract_endpoint_root_is_stable_across_working_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    contract = load_g4_contract(CONTRACT_PATH)

    assert contract.output_root.as_posix() == "outputs/problem2_sr_mappo_v1/g4"


def test_g4_contract_rejects_g3_endpoint_evidence_paths(tmp_path: Path) -> None:
    payload = _payload(CONTRACT_PATH)
    payload["output_root"] = "outputs/problem2_sr_mappo_v1/g3"

    with pytest.raises(G4ContractError, match="G3 output-root"):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


@pytest.mark.parametrize(
    "endpoint_root",
    [
        "outputs/problem2_sr_mappo_v1/other",
        "outputs/problem2_sr_mappo_v1/G3",
        "outputs/problem2_sr_mappo_v1/g4/../g3",
        str((ROOT / "outputs" / "problem2_sr_mappo_v1" / "g4").resolve()),
    ],
)
def test_g4_contract_rejects_endpoint_roots_outside_canonical_g4(
    endpoint_root: str, tmp_path: Path
) -> None:
    payload = _payload(CONTRACT_PATH)
    payload["endpoint_evidence_roots"] = [endpoint_root]

    with pytest.raises(G4ContractError, match="endpoint evidence root"):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


def test_g4_contract_rejects_unbounded_scarcity_ranges(tmp_path: Path) -> None:
    payload = _payload(CONTRACT_PATH)
    payload["scarcity_band"].pop("upper")

    with pytest.raises(G4ContractError, match="lower and upper"):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


@pytest.mark.parametrize("seed", [20000, 30000])
def test_g4_contract_rejects_reserved_probe_seeds(seed: int, tmp_path: Path) -> None:
    payload = _payload(CONTRACT_PATH)
    payload["probe_seeds"] = [seed]

    with pytest.raises(G4ContractError, match="validation and sealed"):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


@pytest.mark.parametrize("partition", ["validation", "sealed_test"])
def test_g4_contract_rejects_validation_and_sealed_probe_ids(
    partition: str, tmp_path: Path
) -> None:
    payload = _payload(MANIFEST_PATH)
    payload["probe_partitions"][partition] = {"start": 20000, "end": 20000}

    with pytest.raises(G4ContractError, match="validation|sealed"):
        load_g4_probe_manifest(_write_payload(MANIFEST_PATH, payload, tmp_path))


def test_g4_contract_rejects_non_integer_partition_ids(tmp_path: Path) -> None:
    payload = _payload(MANIFEST_PATH)
    payload["probe_partitions"]["training"] = ["42", 123, 2024]

    with pytest.raises(G4ContractError, match="integer IDs"):
        load_g4_probe_manifest(_write_payload(MANIFEST_PATH, payload, tmp_path))


def test_g4_contract_rejects_battery_activation(tmp_path: Path) -> None:
    payload = _payload(CONTRACT_PATH)
    payload["resources"]["battery_replenishment_enabled"] = True

    with pytest.raises(G4ContractError, match="battery"):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scarcity_axis", "initial_uav_pesticide_l", "scarcity_axis"),
        ("comparator_pair", ["sr_mappo_fixed", "sr_mappo_mobile"], "comparator_pair"),
    ],
)
def test_g4_contract_rejects_final_review_semantic_drift(
    field: str, value: object, message: str, tmp_path: Path
) -> None:
    payload = _payload(CONTRACT_PATH)
    payload[field] = value

    with pytest.raises(G4ContractError, match=message):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["scarcity_band"].update(lower=1.1), "scarcity_band"),
        (lambda payload: payload.update(probe_scales=["g20x20_d2", "g20x40_d3", "g30x30_d3"]), "probe_scales"),
        (lambda payload: payload.update(probe_seeds=[42, 123, 2025]), "probe_seeds"),
        (lambda payload: payload.update(permitted_claim_boundary="superiority claim is permitted"), "claim boundary"),
    ],
)
def test_g4_contract_rejects_exact_frozen_semantic_drift(
    mutate, message: str, tmp_path: Path
) -> None:
    payload = _payload(CONTRACT_PATH)
    mutate(payload)

    with pytest.raises(G4ContractError, match=message):
        load_g4_contract(_write_payload(CONTRACT_PATH, payload, tmp_path))
