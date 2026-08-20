from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG = ROOT / "configs" / "problem2" / "g2_deterministic.yaml"
FIXTURE = Path(__file__).parent / "fixtures" / "tiny_road.graphml"
PREPROCESSOR = ROOT / "scripts" / "preprocess_g2_roads.py"
AUDITOR = ROOT / "scripts" / "audit_g2_deterministic.py"
ALL_SCALE_IDS = [
    "g20x20_d2",
    "g20x30_d3",
    "g20x40_d3",
    "g30x30_d3",
    "g30x40_d4",
    "g30x50_d4",
]


def _test_config(tmp_path: Path) -> Path:
    payload = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    payload["source"]["path"] = str(FIXTURE)
    payload["source"]["sha256"] = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    path = tmp_path / "g2-test.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _preprocess(config: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            str(PREPROCESSOR),
            "--config",
            str(config),
            "--output-root",
            str(output_root),
            "--allow-test-output-root",
        ]
    )


def _audit(config: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            str(AUDITOR),
            "--config",
            str(config),
            "--output-root",
            str(output_root),
            "--report",
            str(output_root / "g2-deterministic-audit.json"),
            "--allow-test-output-root",
        ]
    )


def test_preprocessor_generates_exactly_six_valid_cache_pairs(tmp_path: Path) -> None:
    config = _test_config(tmp_path)
    output_root = tmp_path / "g2"

    result = _preprocess(config, output_root)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "pass"
    assert sorted(
        path.parent.name for path in output_root.glob("roads/*/road_graph.npz")
    ) == ALL_SCALE_IDS
    assert len(list(output_root.glob("roads/*/metadata.json"))) == 6


def test_audit_validates_all_scales_and_cross_process_replay(tmp_path: Path) -> None:
    config = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    generated = _preprocess(config, output_root)
    assert generated.returncode == 0, generated.stderr

    result = _audit(config, output_root)

    assert result.returncode == 0, result.stderr
    report = json.loads((output_root / "g2-deterministic-audit.json").read_text())
    assert report["status"] == "pass"
    assert [record["scale_id"] for record in report["scales"]] == ALL_SCALE_IDS
    assert report["cross_process_replay"]["match"] is True
    assert report["sealed_test"]["accessed"] is False
    assert (output_root / "deterministic-event-trace.jsonl").stat().st_size > 0
    assert (output_root / "artifact-manifest.json").is_file()


def test_audit_returns_nonzero_for_corrupt_cache_without_publishing_report(
    tmp_path: Path,
) -> None:
    config = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    generated = _preprocess(config, output_root)
    assert generated.returncode == 0, generated.stderr
    cache_path = next(output_root.glob("roads/*/road_graph.npz"))
    with np.load(cache_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["edge_lengths_m"][0] = 999.0
    with cache_path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    result = _audit(config, output_root)

    assert result.returncode != 0
    assert "checksum" in result.stderr
    assert not (output_root / "g2-deterministic-audit.json").exists()


def test_cli_rejects_output_outside_frozen_root_without_test_mode(
    tmp_path: Path,
) -> None:
    config = _test_config(tmp_path)

    result = _run(
        [
            str(PREPROCESSOR),
            "--config",
            str(config),
            "--output-root",
            str(tmp_path / "forbidden"),
        ]
    )

    assert result.returncode != 0
    assert "frozen G2 output root" in result.stderr
