from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_resource_pilot_prepositions_uavs_at_serviceable_remote_work_sites() -> None:
    from scripts.run_resource_pilot import _preposition_uavs_for_spatial_probe
    from problem2.scenarios.factory import build_synthetic_scenario

    bundle = build_synthetic_scenario("s3", seed=11, config_dir=ROOT / "configs")
    bundle.reset()

    _preposition_uavs_for_spatial_probe(bundle)

    assert all(position != (0, 0) for position in bundle.adapter.uav_positions.values())
    for uav_id in bundle.adapter.uav_slots:
        uav_position = bundle.adapter._uav_metric_position(uav_id)
        assert any(
            point.position == uav_position
            for point in bundle.adapter._rendezvous_points(uav_id, include_all_nodes=True)
        )


def test_resource_pilot_writes_event_derived_rows_and_activation_report(tmp_path: Path) -> None:
    from scripts.run_resource_pilot import main

    raw = tmp_path / "pilot.jsonl"
    report = tmp_path / "activation.json"
    assert main([
        "--config-dir", str(ROOT / "configs"),
        "--output", str(raw),
        "--report", str(report),
        "--scale", "s1",
        "--episodes", "1",
        "--max-steps", "5",
    ]) == 0
    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 5
    assert {row["condition_id"] for row in rows} == {
        "unlimited_supply", "finite_no_support", "matched_fixed",
        "teleport_diagnostic", "sr_mappo_mobile",
    }
    assert all("events" in row and "pesticide_initial_l" in row for row in rows)
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["record_count"] == 5
    assert payload["activated"] is False
    assert len(payload["config_hash"]) == 64
    assert len(payload["simulation_profile_sha256"]) == 64
    assert len(payload["git_commit"]) == 40
    assert len(payload["source_tree_hash"]) == 64
    assert payload["interpretation_scope"] == "resource_service_activation_only"
    assert payload["endpoint_comparison_valid"] is False
    assert payload["spatial_probe_initialization"] == "prepositioned_serviceable_work_sites"
    assert payload["total_shortage"] is None
    assert payload["spatial_temporal_mismatch"] is None
    assert payload["mobile_gap_closure"] is None
    assert payload["diagnosis"] == "resource_service_chain_not_activated"


def test_resource_pilot_explicit_scale_does_not_also_run_default_s1(tmp_path: Path) -> None:
    from scripts.run_resource_pilot import main

    raw = tmp_path / "pilot.jsonl"
    report = tmp_path / "activation.json"
    assert main([
        "--config-dir", str(ROOT / "configs"),
        "--output", str(raw),
        "--report", str(report),
        "--scale", "s6",
        "--episodes", "1",
        "--max-steps", "1",
    ]) == 0

    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 5
    assert {row["scale"] for row in rows} == {"s6"}
    assert {row["evidence_mode"] for row in rows} == {"simulation"}


def test_resource_pilot_default_horizon_does_not_truncate_service_activation(tmp_path: Path) -> None:
    from scripts.run_resource_pilot import main

    raw = tmp_path / "pilot.jsonl"
    report = tmp_path / "activation.json"
    assert main([
        "--config-dir", str(ROOT / "configs"),
        "--output", str(raw),
        "--report", str(report),
        "--scale", "s1",
        "--episodes", "1",
    ]) == 0

    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    assert max(int(row["steps"]) for row in rows) > 160
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["mobile_service_feasible"] is True
