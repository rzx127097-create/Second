from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_dynamic_audit_emits_machine_readable_m2_invariants(tmp_path: Path) -> None:
    output = tmp_path / "dynamic-pest-implementation.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "audit_dynamic_pest.py"),
            "--root",
            str(ROOT),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["maturity"] == "M2"
    assert payload["ecology_mode"] == "dynamic"
    assert payload["battery_replenishment_enabled"] is False
    assert payload["sealed_accessed"] is False
    assert {
        "numerics",
        "scenario_replay",
        "accepted_spray",
        "conservation",
        "fixed_dimensions",
        "signed_reward",
        "static_primary_rejected",
    } <= {check["name"] for check in payload["checks"]}
