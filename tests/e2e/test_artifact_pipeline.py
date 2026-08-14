from __future__ import annotations

import json
from pathlib import Path

from problem2.artifacts import build_artifacts


def test_build_artifacts_from_utf8_jsonl_emits_traceable_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "episodes.jsonl"
    rows = [
        {
            "run_id": "run-a",
            "method": "sr_mappo_mobile",
            "scale": "small",
            "training_seed": 1,
            "scenario_id": "scenario-1",
            "config_hash": "cfg-a",
            "git_commit": "commit-a",
            "split": "test",
            "reduction_rate": 0.80,
            "success": True,
            "transferred_l": 2.0,
        },
        {
            "run_id": "run-b",
            "method": "priority_dispatch",
            "scale": "small",
            "training_seed": 1,
            "scenario_id": "scenario-1",
            "config_hash": "cfg-a",
            "git_commit": "commit-a",
            "split": "test",
            "reduction_rate": 0.65,
            "success": False,
            "transferred_l": 3.0,
        },
    ]
    input_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    bundle = build_artifacts(input_path, tmp_path / "artifacts", manifest=tmp_path / "manifest.json")

    for path in bundle.paths.values():
        assert Path(path).exists(), path
    validated = Path(bundle.paths["validated_csv"]).read_text(encoding="utf-8")
    assert "run_id" in validated and "run-a" in validated and "run-b" in validated
    summary = json.loads(Path(bundle.paths["summary_json"]).read_text(encoding="utf-8"))
    assert summary["provisional"] is True
    assert {row["method"] for row in summary["rows"]} == {"sr_mappo_mobile", "priority_dispatch"}
    manifest = json.loads(Path(bundle.paths["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["input"]["path"] == str(input_path)
    assert manifest["outputs"]
    assert Path(bundle.paths["figure_svg"]).suffix == ".svg"
    assert Path(bundle.paths["figure_png"]).suffix == ".png"
