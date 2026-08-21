from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess

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
from problem2.domain import EpisodeState, Event, ServiceRequest, UavState, VehicleState
from problem2.resources.ledger import new_ledger


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
    assert result["records"][0]["scarcity_level_l"] == 0.05
    assert result["records"][0]["initial_vehicle_inventory_l"] == 20.0
    assert result["records"][0]["initial_uav_pesticide_l"] == 0.05
    assert result["records"][-1]["scarcity_level_l"] == 0.525
    assert result["records"][-1]["initial_vehicle_inventory_l"] == 20.0
    assert result["records"][-1]["initial_uav_pesticide_l"] == 0.525
    for record in result["records"]:
        assert record["initial_uav_pesticide_l"] == record["scarcity_level_l"]
        assert record["initial_vehicle_inventory_l"] == 20.0
        assert record["total_requested_l"] > 0
        assert record["total_transferred_l"] > 0
        assert record["vehicle_inventory_used_l"] > 0
        assert record["final_vehicle_inventory_l"] == pytest.approx(
            20.0 - record["vehicle_inventory_used_l"]
        )
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
        for level in (0.05, 0.2875, 0.525)
    ]


def test_validate_activation_band_rejects_no_activation() -> None:
    with pytest.raises(G4ContractError, match="no activation"):
        validate_activation_band(_band_records(set()), (0.05, 0.2875, 0.525))


def test_validate_activation_band_rejects_one_point_activation() -> None:
    with pytest.raises(G4ContractError, match="at least two"):
        validate_activation_band(_band_records({0.2875}), (0.05, 0.2875, 0.525))


def test_validate_activation_band_rejects_a_gap_between_active_points() -> None:
    with pytest.raises(G4ContractError, match="contiguous"):
        validate_activation_band(_band_records({0.05, 0.525}), (0.05, 0.2875, 0.525))


def test_probe_matrix_rejects_mismatched_arm_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    monkeypatch.setattr(activation, "CANONICAL_G4_ROOT", output_root.resolve())

    def fake_probe(contract, manifest, *, support_policy, output_root):
        return {
            "activation_window": [0.05, 0.525]
            if isinstance(support_policy, FixedSupportPolicy)
            else [0.2875, 0.525],
            "records": [],
            "lineage": {},
        }

    monkeypatch.setattr(activation, "run_activation_probe", fake_probe)
    with pytest.raises(G4ContractError, match="arm activation windows"):
        run_probe_matrix(CONTRACT, MANIFEST, output_root=output_root)


def test_service_start_distance_uses_post_step_vehicle_position() -> None:
    service_start_state = EpisodeState(
        step=1,
        uavs=(UavState("uav-0", 10.0, 0.0, 0.05),),
        vehicle=VehicleState("vehicle-0", 1, 7.0, 0.0, 1.0),
        requests=(ServiceRequest("request-0", "uav-0", 0, 0.5),),
    )

    assert activation._service_start_euclidean_distance(service_start_state, "request-0") == 3.0


def test_run_one_records_service_start_distance_from_post_step_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_uav = UavState("uav-0", 10.0, 0.0, 0.05)
    initial_vehicle = VehicleState("vehicle-0", 0, 0.0, 0.0, 1.0)
    initial_state = EpisodeState(
        step=0,
        uavs=(initial_uav,),
        vehicle=initial_vehicle,
        requests=(ServiceRequest("request-0", "uav-0", 0, 0.5),),
        ledger=new_ledger((initial_uav,), initial_vehicle.inventory_l),
    )
    service_start_state = EpisodeState(
        step=1,
        uavs=(initial_uav,),
        vehicle=VehicleState("vehicle-0", 1, 7.0, 0.0, 1.0),
        requests=initial_state.requests,
        ledger=initial_state.ledger,
        last_step_events=(
            Event(0, "service", "service_started", "request-0"),
            Event(0, "conservation", "conservation_checked", "pesticide", (("error_l", 0.0),)),
        ),
        terminated=True,
    )

    monkeypatch.setattr(activation, "_load_graph", lambda *_: object())
    monkeypatch.setattr(activation, "_initial_state", lambda *_: initial_state)
    monkeypatch.setattr(activation, "build_action_masks", lambda *_: object())
    monkeypatch.setattr(activation, "step_episode", lambda *_args, **_kwargs: service_start_state)

    record = activation._run_one(
        CONTRACT,
        activation.load_g2_config(activation.G2_CONFIG_PATH),
        MANIFEST,
        "g20x20_d2",
        42,
        0.05,
        FixedSupportPolicy(),
    )

    assert record["euclidean_service_start_distance_m"] == 3.0


def test_lineage_binds_generator_contract_commit_not_output_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str) -> str:
        calls.append(args)
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        if args == ("rev-parse", f"{'a' * 40}^{{tree}}"):
            return "b" * 40
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(activation, "_git", fake_git)
    monkeypatch.setattr(activation, "_require_clean_source_provenance", lambda _commit: None)
    monkeypatch.setattr(activation, "_source_file_hashes", lambda: {"source.py": "c" * 64})

    lineage = activation._lineage(
        CONTRACT,
        MANIFEST,
        activation.load_g2_config(activation.G2_CONFIG_PATH),
    )

    assert lineage["source_tree_commit"] == "a" * 40
    assert lineage["source_tree_hash"] == "b" * 40
    assert ("rev-parse", "HEAD") in calls


def test_lineage_rejects_a_dirty_source_provenance_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source-repo"
    source_root.mkdir()
    for relative in activation.SOURCE_PROVENANCE_PATHS:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"tracked {relative}\n", encoding="utf-8")
    for command in (
        ("git", "init"),
        ("git", "config", "user.email", "g4-test@example.invalid"),
        ("git", "config", "user.name", "G4 Test"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source bundle"),
    ):
        subprocess.run(command, cwd=source_root, check=True, capture_output=True, text=True)
    dirty_source = source_root / activation.SOURCE_PROVENANCE_PATHS[0]
    dirty_source.write_text("unstaged change\n", encoding="utf-8")
    monkeypatch.setattr(activation, "ROOT", source_root)

    with pytest.raises(G4ContractError, match="source provenance paths"):
        activation._lineage(CONTRACT, MANIFEST, activation.load_g2_config(activation.G2_CONFIG_PATH))
