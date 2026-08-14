from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.artifacts import build_artifacts
from problem2.artifacts.figures import plot_metric
from problem2.artifacts.summarize import paired_differences, summarize_records
from problem2.artifacts.validate_logs import read_jsonl


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
            "provisional": True,
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
            "provisional": True,
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
    assert manifest["self"]["path"] == str(tmp_path / "manifest.json")
    assert Path(bundle.paths["figure_svg"]).suffix == ".svg"
    assert Path(bundle.paths["figure_png"]).suffix == ".png"


def test_paired_differences_preserves_each_training_seed() -> None:
    rows = []
    for seed in (1, 2):
        rows.extend([
            {"run_id": f"ref-{seed}", "method": "sr_mappo_mobile", "scale": "small", "training_seed": seed, "scenario_id": "s1", "config_hash": "cfg", "git_commit": "git", "split": "test", "reduction_rate": 0.8, "success": True, "transferred_l": 1.0, "provisional": True},
            {"run_id": f"alt-{seed}", "method": "priority_dispatch", "scale": "small", "training_seed": seed, "scenario_id": "s1", "config_hash": "cfg", "git_commit": "git", "split": "test", "reduction_rate": 0.6, "success": True, "transferred_l": 1.0, "provisional": True},
        ])
    pairs = paired_differences(rows)
    assert len(pairs) == 2
    assert {pair["training_seed"] for pair in pairs} == {1, 2}


def test_production_jsonl_rejects_blank_lines_and_missing_status(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="blank"):
        read_jsonl(path)
    valid_without_status = {"run_id": "a", "method": "m", "scale": "s", "training_seed": 1, "scenario_id": "x", "config_hash": "c", "git_commit": "g", "split": "test", "reduction_rate": 0.5, "success": True, "transferred_l": 1}
    path.write_text(json.dumps(valid_without_status) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="status"):
        read_jsonl(path)


def test_production_jsonl_rejects_mixed_provenance_and_invalid_types(tmp_path: Path) -> None:
    rows = [{"run_id": "a", "method": "m", "scale": "s", "training_seed": 1.5, "scenario_id": "x", "config_hash": "c", "git_commit": "g", "split": "test", "reduction_rate": 0.5, "success": "false", "transferred_l": 1, "provisional": True}]
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_jsonl(path)


def test_build_artifacts_rejects_mixed_identity_within_method_scale(tmp_path: Path) -> None:
    base = {"method": "m", "scale": "s", "training_seed": 1, "scenario_id": "x", "git_commit": "g", "split": "test", "reduction_rate": 0.5, "success": True, "transferred_l": 1, "provisional": True}
    rows = [dict(base, run_id="a", config_hash="c1"), dict(base, run_id="b", config_hash="c2", scenario_id="y")]
    path = tmp_path / "mixed.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mixed provenance"):
        build_artifacts(path, tmp_path / "out", manifest=tmp_path / "manifest.json")


def test_plot_metric_rejects_missing_metric(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing metric"):
        plot_metric([{"method": "m"}], "reduction_rate_mean", str(tmp_path / "x.svg"))
