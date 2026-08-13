from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.artifacts.validate_logs import validate_episode_records
from problem2.artifacts.summarize import summarize_records
from problem2.artifacts.evidence_manifest import build_manifest
from problem2.artifacts.tables import three_line_table


def _records() -> list[dict[str, object]]:
    return [{
        "run_id": "run-1", "method": "sr_mappo_mobile", "scale": "s1", "training_seed": 0,
        "scenario_id": "test-1", "config_hash": "abc", "git_commit": "def",
        "reduction_rate": 0.9, "success": True, "transferred_l": 0.2,
    }]


def test_validate_and_summarize_preserve_traceability_fields() -> None:
    valid = validate_episode_records(_records())
    summary = summarize_records(valid)
    assert summary[0]["run_id"] == "run-1"
    assert summary[0]["reduction_rate_mean"] == pytest.approx(0.9)


def test_three_line_table_has_header_body_and_note() -> None:
    table = three_line_table([{"method": "SR-MAPPO", "reduction_rate": 0.9}], columns=["method", "reduction_rate"], note="paired sealed scenarios")
    assert table["top_rule"] and table["bottom_rule"]
    assert table["note"] == "paired sealed scenarios"


def test_manifest_records_input_and_output_hashes(tmp_path: Path) -> None:
    source = tmp_path / "episodes.json"
    source.write_text(json.dumps(_records()), encoding="utf-8")
    output = tmp_path / "summary.csv"
    output.write_text("run_id,reduction_rate_mean\nrun-1,0.9\n", encoding="utf-8")
    manifest = build_manifest({"table-1": (source, output)})
    assert manifest["table-1"]["input_sha256"]
    assert manifest["table-1"]["output_sha256"]
