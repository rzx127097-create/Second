from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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
