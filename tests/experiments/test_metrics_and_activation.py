from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from problem2.experiments.metrics import episode_record_from_bundle
from problem2.experiments.resource_activation import audit_resource_activation


class Resources:
    total_pesticide_l = 5.0
    _cumulative_sprayed_l = 1.0
    vehicles = {"vehicle-1": type("Vehicle", (), {"inventory_l": 3.0})()}


class Adapter:
    decision_dt_s = 2.0
    _initial_vehicle_inventory = {"vehicle-1": 4.0}


class Bundle:
    pest_density = np.asarray([[0.2, 0.3]])
    resources = Resources()
    adapter = Adapter()
    scale_id = "s1"
    scenario_id = "val_001"
    parameter_status = "provisional"
    success_reduction_threshold = 0.85
    intervention_id = "sr_mappo_mobile"
    intervention_hash = "a" * 64
    support_mode = "mobile"
    last_termination_reason = "max_steps"


def test_episode_metrics_are_derived_from_event_and_resource_ledgers() -> None:
    """Changing event accounting or double-counting time must break these hand values."""
    events = [
        {"event_type": "request_created", "request_id": "r1", "amount_l": 0.8, "step": 1},
        {"event_type": "request_created", "request_id": "r2", "amount_l": 0.6, "step": 2},
        {"event_type": "request_reserved", "request_id": "r1", "rendezvous_road_distance_m": 12.0, "step": 2},
        {"event_type": "service_started", "request_id": "r1", "step": 3},
        {"event_type": "service_active", "request_id": "r1", "duration_s": 2.0, "step": 4},
        {"event_type": "pesticide_transfer", "request_id": "r1", "amount_l": 0.5, "step": 4},
        {"event_type": "request_completed", "request_id": "r1", "step": 4},
        {"event_type": "wait", "request_id": "r1", "duration_s": 2.0, "step": 2},
        {"event_type": "pesticide_disabled", "uav_id": "uav-1", "duration_s": 2.0, "step": 3},
        {"event_type": "spray_applied", "uav_id": "uav-1", "amount_l": 0.1, "step": 1},
        {"event_type": "uav_movement_applied", "uav_id": "uav-1", "distance_m": 5.0, "rendezvous_committed": True, "step": 2},
        {"event_type": "movement_applied", "vehicle_id": "vehicle-1", "travelled_distance_m": 4.0, "step": 1},
        {"event_type": "movement_applied", "vehicle_id": "vehicle-1", "travelled_distance_m": 0.0, "step": 2},
        {"event_type": "movement_applied", "vehicle_id": "vehicle-1", "travelled_distance_m": 0.0, "step": 4},
    ]
    record = episode_record_from_bundle(
        Bundle(),
        episode_id="episode",
        steps=4,
        total_reward=1.0,
        reward_components={},
        initial_pest_total=1.0,
        pesticide_initial_l=6.0,
        events=events,
        agent_ids={"uav": ["uav-1"], "vehicle": ["vehicle-1"]},
        decision_times_s=[0.001, 0.003],
    )
    row = record.to_row()

    assert row["event_schema_version"] == 2
    assert row["request_count"] == 2
    assert row["request_completed_count"] == 1
    assert row["request_completion_rate"] == pytest.approx(0.5)
    assert row["requested_l"] == pytest.approx(1.4)
    assert row["transferred_l"] == pytest.approx(0.5)
    assert row["request_wait_mean_s"] == pytest.approx(4.0)
    assert row["request_wait_p90_s"] == pytest.approx(4.0)
    assert row["wait_s"] == pytest.approx(2.0)
    assert row["pesticide_disabled_s"] == pytest.approx(2.0)
    assert row["effective_spray_s"] == pytest.approx(2.0)
    assert row["service_s"] == pytest.approx(2.0)
    assert row["rendezvous_road_distance_m"] == pytest.approx(12.0)
    assert row["uav_rendezvous_distance_m"] == pytest.approx(5.0)
    assert row["vehicle_distance_m"] == pytest.approx(4.0)
    assert row["vehicle_idle_s"] == pytest.approx(2.0)
    assert row["vehicle_inventory_initial_l"] == pytest.approx(4.0)
    assert row["vehicle_inventory_final_l"] == pytest.approx(3.0)
    assert row["vehicle_inventory_utilization"] == pytest.approx(0.25)
    assert row["decision_time_mean_ms"] == pytest.approx(2.0)
    assert row["termination_reason"] == "max_steps"


def _row(condition: str, reduction: float, *, requests: int, disabled: float, wait: float) -> dict[str, object]:
    return {
        "condition_id": condition,
        "scale": "s3",
        "training_seed": 0,
        "scenario_id": "val_001",
        "reduction_rate": reduction,
        "request_count": requests,
        "request_completion_rate": 1.0 if requests else 0.0,
        "pesticide_disabled_s": disabled,
        "wait_s": wait,
        "requested_l": float(requests),
        "transferred_l": float(requests),
        "pesticide_initial_l": 5.0,
        "pesticide_remaining_l": 3.0,
    }


def test_resource_audit_refuses_to_claim_activation_without_requests_or_disabled_time() -> None:
    report = audit_resource_activation([
        _row("sr_mappo_mobile", 0.6, requests=0, disabled=0.0, wait=0.0),
        _row("matched_fixed", 0.5, requests=0, disabled=0.0, wait=0.0),
    ])

    assert report.activated is False
    assert report.diagnosis == "resource_constraint_not_activated"
    assert report.total_shortage is False
    assert report.spatial_temporal_mismatch is False


def test_resource_audit_identifies_mismatch_and_mobile_gap_closure() -> None:
    rows = [
        _row("unlimited_supply", 0.90, requests=0, disabled=0.0, wait=0.0),
        _row("finite_no_support", 0.40, requests=3, disabled=20.0, wait=20.0),
        _row("matched_fixed", 0.55, requests=3, disabled=12.0, wait=12.0),
        _row("teleport_diagnostic", 0.85, requests=3, disabled=1.0, wait=0.0),
        _row("sr_mappo_mobile", 0.75, requests=3, disabled=4.0, wait=3.0),
    ]

    report = audit_resource_activation(rows)

    assert report.activated is True
    assert report.total_shortage is True
    assert report.spatial_temporal_mismatch is True
    assert report.mobile_gap_closure == pytest.approx((0.75 - 0.55) / (0.85 - 0.55))
    assert report.diagnosis == "mixed_total_and_spatiotemporal_constraint"


def test_resource_audit_does_not_call_unserviceable_mobile_support_activated() -> None:
    rows = [
        _row("unlimited_supply", 0.90, requests=0, disabled=0.0, wait=0.0),
        _row("finite_no_support", 0.50, requests=2, disabled=10.0, wait=0.0),
        _row("matched_fixed", 0.50, requests=2, disabled=10.0, wait=10.0),
        _row("teleport_diagnostic", 0.80, requests=2, disabled=0.0, wait=0.0),
        _row("sr_mappo_mobile", 0.50, requests=2, disabled=10.0, wait=10.0),
    ]
    rows[-1]["request_completion_rate"] = 0.0
    rows[-1]["transferred_l"] = 0.0

    report = audit_resource_activation(rows)

    assert report.demand_activated is True
    assert report.mobile_service_feasible is False
    assert report.activated is False
    assert report.diagnosis == "resource_constraint_active_but_mobile_unserviceable"


def test_mobile_gap_closure_requires_a_positive_teleport_gap() -> None:
    rows = [
        _row("matched_fixed", 0.80, requests=2, disabled=3.0, wait=2.0),
        _row("teleport_diagnostic", 0.70, requests=2, disabled=1.0, wait=0.0),
        _row("sr_mappo_mobile", 0.75, requests=2, disabled=2.0, wait=1.0),
    ]

    report = audit_resource_activation(rows)

    assert report.mobile_gap_closure is None


def test_resource_audit_script_writes_machine_readable_report(tmp_path: Path) -> None:
    input_path = tmp_path / "episodes.jsonl"
    report_path = tmp_path / "audit.json"
    rows = [_row("sr_mappo_mobile", 0.7, requests=2, disabled=3.0, wait=2.0)]
    input_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    from scripts.audit_resource_activation import main

    assert main([str(input_path), "--report", str(report_path)]) == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["record_count"] == 1
    assert payload["activated"] is True
