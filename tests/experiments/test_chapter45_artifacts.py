from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from problem2.artifacts.chapter45 import _formal_expected_keys, build_chapter45_artifacts
from problem2.artifacts.validate_logs import validate_episode_records
from problem2.config import config_identity, load_config_bundle
from problem2.experiments.specification import protocol_identity
from problem2.experiments.job_identity import JobIdentity
from problem2.experiments.runner import JobRecord, traceable_episode_rows


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"
PROTOCOL = CONFIG_DIR / "experiments" / "chapter4_5.yaml"


def _record(
    family: str,
    condition: str,
    method: str,
    scale: str,
    seed: int,
    scenario: str,
    reduction: float,
) -> dict[str, object]:
    config = load_config_bundle(CONFIG_DIR)
    job_key = f"{family}:{condition}:{method}:{scale}:{seed}"
    job_id = hashlib.sha256(job_key.encode("utf-8")).hexdigest()
    checkpoint_sha256 = hashlib.sha256(f"checkpoint:{job_key}".encode("utf-8")).hexdigest()
    return {
        "run_id": f"{family}:{condition}:{seed}:{scenario}",
        "job_id": job_id,
        "family": family,
        "condition_id": condition,
        "method": method,
        "scale": scale,
        "training_seed": seed,
        "scenario_id": scenario,
        "config_hash": config_identity(config),
        "protocol_hash": protocol_identity(PROTOCOL),
        "git_commit": "a" * 40,
        "source_tree_hash": "b" * 64,
        "git_dirty": True,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_step": 1,
        "split": "validation",
        "parameter_status": "provisional",
        "reduction_rate": reduction,
        "success": reduction >= 0.85,
        "transferred_l": 1.2,
        "request_count": 2,
        "request_completion_rate": 0.75,
        "requested_l": 1.6,
        "request_wait_mean_s": 5.0,
        "request_wait_p90_s": 7.0,
        "wait_s": 8.0,
        "pesticide_disabled_s": 4.0,
        "effective_spray_s": 20.0,
        "service_s": 3.0,
        "rendezvous_road_distance_m": 30.0,
        "uav_rendezvous_distance_m": 10.0,
        "vehicle_distance_m": 50.0,
        "vehicle_idle_s": 6.0,
        "vehicle_inventory_utilization": 0.4,
        "decision_time_mean_ms": 2.0,
    }


def _records() -> list[dict[str, object]]:
    definitions = [
        ("main_comparison", "sr_mappo_mobile__s1__seed-{seed}", "sr_mappo_mobile", "s1", 0.88),
        ("main_comparison", "sr_mappo_fixed__s1__seed-{seed}", "sr_mappo_fixed", "s1", 0.76),
        ("mechanism", "sr_mappo_mobile", "sr_mappo_mobile", "s3", 0.86),
        ("mechanism", "matched_fixed", "sr_mappo_fixed", "s3", 0.73),
        ("mechanism", "teleport_diagnostic", "sr_mappo_mobile", "s3", 0.90),
        ("sensitivity", "vehicle_speed__0p5", "sr_mappo_mobile", "s3", 0.75),
        ("sensitivity", "vehicle_speed__1", "sr_mappo_mobile", "s3", 0.84),
        ("sensitivity", "vehicle_speed__2", "sr_mappo_mobile", "s3", 0.87),
        ("adaptation", "demand_dispersion__clustered", "sr_mappo_mobile", "s3", 0.88),
        ("adaptation", "demand_dispersion__moderate", "sr_mappo_mobile", "s3", 0.84),
        ("adaptation", "demand_dispersion__dispersed", "sr_mappo_mobile", "s3", 0.79),
        ("ablation", "full_sr_mappo", "sr_mappo_mobile", "s3", 0.86),
        ("ablation", "no_endurance_prediction", "sr_mappo_mobile", "s3", 0.78),
    ]
    rows: list[dict[str, object]] = []
    for seed in (0, 1):
        for family, condition_template, method, scale, reduction in definitions:
            scenarios = ("val_001", "val_s1_002") if scale == "s1" else ("val_002", "val_s3_002")
            condition = condition_template.format(seed=seed)
            for scenario_index, scenario in enumerate(scenarios):
                rows.append(_record(
                    family, condition, method, scale, seed, scenario,
                    reduction - 0.01 * scenario_index + 0.005 * seed,
                ))
    return rows


def _complete_records(
    families: set[str] | None = None,
) -> list[dict[str, object]]:
    config = load_config_bundle(CONFIG_DIR)
    from problem2.experiments.specification import load_experiment_spec

    spec = load_experiment_spec(PROTOCOL, config)
    rows: list[dict[str, object]] = []
    for index, key in enumerate(sorted(_formal_expected_keys(config, spec, "validation"))):
        family, condition, method, scale, seed, scenario = key
        if families is not None and str(family) not in families:
            continue
        reduction = 0.72 + 0.02 * (index % 8)
        rows.append(_record(
            str(family), str(condition), str(method), str(scale), int(seed),
            str(scenario), reduction,
        ))
    return rows


def test_log_validation_allows_same_method_scenario_under_distinct_conditions() -> None:
    rows = _records()
    selected = [
        row for row in rows
        if row["condition_id"] in {"vehicle_speed__0p5", "vehicle_speed__1"}
        and row["training_seed"] == 0 and row["scenario_id"] == "val_002"
    ]

    assert len(validate_episode_records(selected, strict=True)) == 2


def test_chapter45_builder_emits_one_locked_summary_figures_tables_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "episodes.jsonl"
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in _complete_records()), encoding="utf-8",
    )

    bundle = build_chapter45_artifacts(
        [source], tmp_path / "chapter45", config_dir=CONFIG_DIR,
        protocol_path=PROTOCOL, allow_partial=True,
    )

    assert all(path.is_file() and path.stat().st_size > 0 for path in bundle.paths.values())
    summary = json.loads(bundle.paths["locked_summary_json"].read_text(encoding="utf-8"))
    assert summary["locked"] is True
    assert set(summary["families"]) == {
        "main_comparison", "mechanism", "sensitivity", "adaptation", "ablation",
    }
    for figure in ("main_comparison", "mechanism", "sensitivity_adaptation", "ablation"):
        assert {bundle.paths[f"{figure}_{suffix}"].suffix for suffix in ("svg", "pdf", "png")} == {".svg", ".pdf", ".png"}
        svg = bundle.paths[f"{figure}_svg"].read_text(encoding="utf-8")
        assert "Arial" in svg
        assert "linearGradient" not in svg
    for table in ("main_comparison", "mechanism", "sensitivity", "adaptation", "ablation"):
        assert bundle.paths[f"{table}_table_tsv"].is_file()
        assert bundle.paths[f"{table}_table_markdown"].is_file()
    manifest = json.loads(bundle.paths["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["protocol"]["sha256"] == protocol_identity(PROTOCOL)
    assert manifest["identity"]["config_hash"] == [config_identity(load_config_bundle(CONFIG_DIR))]
    assert manifest["maturity"] == "provisional_smoke"
    assert manifest["uncertainty"]["pairing_unit"] == "training_seed_then_shared_scenario"
    assert manifest["outputs"]["locked_summary_json"]["sha256"] == hashlib.sha256(
        bundle.paths["locked_summary_json"].read_bytes()
    ).hexdigest()


def test_partial_chapter45_builder_emits_only_available_families(tmp_path: Path) -> None:
    source = tmp_path / "main-only.jsonl"
    rows = _complete_records({"main_comparison"})
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    bundle = build_chapter45_artifacts(
        [source], tmp_path / "partial", config_dir=CONFIG_DIR,
        protocol_path=PROTOCOL, allow_partial=True,
    )

    assert bundle.paths["main_comparison_svg"].is_file()
    assert bundle.paths["main_comparison_table_tsv"].is_file()
    assert "mechanism_svg" not in bundle.paths
    assert "ablation_table_tsv" not in bundle.paths


def test_partial_chapter45_builder_rejects_incomplete_present_family(tmp_path: Path) -> None:
    source = tmp_path / "incomplete-main.jsonl"
    rows = [row for row in _records() if row["family"] == "main_comparison"]
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="present families.*incomplete"):
        build_chapter45_artifacts(
            [source], tmp_path / "partial", config_dir=CONFIG_DIR,
            protocol_path=PROTOCOL, allow_partial=True,
        )

def test_chapter45_builder_rejects_stale_config_or_protocol_identity(tmp_path: Path) -> None:
    rows = _records()
    rows[0]["config_hash"] = "stale"
    source = tmp_path / "stale.jsonl"
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
    )

    with pytest.raises(ValueError, match="config hash"):
        build_chapter45_artifacts(
            [source], tmp_path / "out", config_dir=CONFIG_DIR,
            protocol_path=PROTOCOL, allow_partial=True,
        )


def test_separate_shared_scenario_evaluations_receive_unique_run_ids() -> None:
    identity = JobIdentity(
        method="sr_mappo_mobile", scale="s1", training_seed=0,
        config_hash="c" * 64, git_commit="g" * 40,
    )
    job = JobRecord(identity=identity)

    class Episode:
        events: list[dict[str, object]] = []

        def __init__(self, scenario_id: str) -> None:
            self.scenario_id = scenario_id

        def to_row(self) -> dict[str, object]:
            return {"scenario_id": self.scenario_id, "intervention_id": "direct"}

    first = traceable_episode_rows([Episode("val_001")], job, split="validation")[0]
    second = traceable_episode_rows([Episode("val_s1_002")], job, split="validation")[0]

    assert first["run_id"] != second["run_id"]
    assert str(first["run_id"]).startswith(f"{job.job_id}:0")


def test_formal_artifact_build_is_blocked_while_protocol_is_provisional(tmp_path: Path) -> None:
    source = tmp_path / "episodes.jsonl"
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in _complete_records()), encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provisional"):
        build_chapter45_artifacts(
            [source], tmp_path / "formal", config_dir=CONFIG_DIR,
            protocol_path=PROTOCOL,
        )


def test_chapter45_artifact_cli_returns_machine_readable_paths(tmp_path: Path) -> None:
    source = tmp_path / "episodes.jsonl"
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in _complete_records()), encoding="utf-8",
    )
    from scripts.build_chapter45_artifacts import main

    output = tmp_path / "cli-output"
    assert main([
        str(source), "--config-dir", str(CONFIG_DIR), "--protocol", str(PROTOCOL),
        "--output", str(output), "--allow-partial",
    ]) == 0
    assert (output / "artifact_manifest.json").is_file()
    assert (output / "locked_summary.json").is_file()
