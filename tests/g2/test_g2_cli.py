from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

import numpy as np
import pytest
import yaml

import problem2.audit as audit_module
from problem2.audit import (
    GeneratorProvenance,
    preprocess_all,
    run_g2_audit,
)
from problem2.config import load_g2_config


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


def _run(
    args: list[str], *, extra_environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment.update(extra_environment or {})
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _provenance() -> GeneratorProvenance:
    return GeneratorProvenance(git_commit="c" * 40, tree_sha256="b" * 64)


def _preprocess(
    config_path: Path,
    output_root: Path,
    provenance: GeneratorProvenance | None = None,
) -> None:
    preprocess_all(
        load_g2_config(config_path), output_root, provenance or _provenance()
    )


def _audit(config_path: Path, output_root: Path) -> dict:
    report = output_root / "g2-deterministic-audit.json"
    return run_g2_audit(
        load_g2_config(config_path),
        config_path.resolve(),
        output_root,
        report,
        _provenance(),
    )


def _roads_snapshot(output_root: Path) -> dict[str, bytes]:
    roads = output_root / "roads"
    return {
        path.relative_to(roads).as_posix(): path.read_bytes()
        for path in sorted(roads.rglob("*"))
        if path.is_file()
    }


def _assert_no_transaction_debris(output_root: Path) -> None:
    assert not (output_root / ".roads-backup").exists()
    assert list(output_root.glob(".roads-staging-*")) == []


def test_preprocessor_generates_exactly_six_valid_cache_pairs(tmp_path: Path) -> None:
    config = _test_config(tmp_path)
    output_root = tmp_path / "g2"

    _preprocess(config, output_root)

    assert sorted(
        path.parent.name for path in output_root.glob("roads/*/road_graph.npz")
    ) == ALL_SCALE_IDS
    assert len(list(output_root.glob("roads/*/metadata.json"))) == 6


def test_audit_validates_all_scales_and_cross_process_replay(tmp_path: Path) -> None:
    config = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    _preprocess(config, output_root)

    report = _audit(config, output_root)

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
    _preprocess(config, output_root)
    cache_path = next(output_root.glob("roads/*/road_graph.npz"))
    with np.load(cache_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["edge_lengths_m"][0] = 999.0
    with cache_path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)

    with pytest.raises(ValueError, match="checksum"):
        _audit(config, output_root)
    assert not (output_root / "g2-deterministic-audit.json").exists()


def test_generation_failure_preserves_complete_prior_roads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    _preprocess(config_path, output_root)
    prior = _roads_snapshot(output_root)
    real_rasterize = audit_module.rasterize_road_source
    calls = 0

    def fail_on_second_scale(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected generation failure")
        return real_rasterize(*args, **kwargs)

    monkeypatch.setattr(audit_module, "rasterize_road_source", fail_on_second_scale)

    with pytest.raises(RuntimeError, match="generation failure"):
        _preprocess(
            config_path,
            output_root,
            GeneratorProvenance(git_commit="d" * 40, tree_sha256="e" * 64),
        )

    assert _roads_snapshot(output_root) == prior
    _assert_no_transaction_debris(output_root)


def test_validation_failure_preserves_complete_prior_roads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    _preprocess(config_path, output_root)
    prior = _roads_snapshot(output_root)
    real_write = audit_module.write_road_cache
    calls = 0

    def corrupt_second_staged_cache(*args, **kwargs):
        nonlocal calls
        calls += 1
        paths = real_write(*args, **kwargs)
        if calls == 2:
            paths[1].write_text("{corrupt", encoding="utf-8")
        return paths

    monkeypatch.setattr(audit_module, "write_road_cache", corrupt_second_staged_cache)

    with pytest.raises(ValueError, match="metadata"):
        _preprocess(config_path, output_root)

    assert _roads_snapshot(output_root) == prior
    _assert_no_transaction_debris(output_root)


def test_publish_failure_rolls_back_complete_prior_roads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    _preprocess(config_path, output_root)
    prior = _roads_snapshot(output_root)
    real_replace = audit_module.os.replace

    def fail_staged_publish(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            source_path.name == "roads"
            and source_path.parent.name.startswith(".roads-staging-")
            and destination_path == output_root / "roads"
        ):
            raise OSError("injected publish failure")
        return real_replace(source, destination)

    monkeypatch.setattr(audit_module.os, "replace", fail_staged_publish)

    with pytest.raises(OSError, match="publish failure"):
        _preprocess(config_path, output_root)

    assert _roads_snapshot(output_root) == prior
    _assert_no_transaction_debris(output_root)


def test_stale_backup_is_recovered_before_generation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _test_config(tmp_path)
    output_root = tmp_path / "g2"
    _preprocess(config_path, output_root)
    prior = _roads_snapshot(output_root)
    shutil.move(output_root / "roads", output_root / ".roads-backup")
    monkeypatch.setattr(
        audit_module,
        "rasterize_road_source",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("injected generation failure")
        ),
    )

    with pytest.raises(RuntimeError, match="generation failure"):
        _preprocess(config_path, output_root)

    assert _roads_snapshot(output_root) == prior
    _assert_no_transaction_debris(output_root)


def test_cli_rejects_external_output_with_forged_pytest_environment(
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
        ],
        extra_environment={"PYTEST_CURRENT_TEST": "forged::test (call)"},
    )

    assert result.returncode != 0
    assert "frozen G2 output root" in result.stderr


@pytest.mark.parametrize("script", [PREPROCESSOR, AUDITOR])
def test_production_cli_has_no_dirty_generator_override(
    script: Path, tmp_path: Path
) -> None:
    args = [str(script), "--config", str(BASE_CONFIG)]
    if script == AUDITOR:
        args.extend(["--report", str(tmp_path / "report.json")])
    result = _run([*args, "--allow-test-output-root"])

    assert result.returncode == 2
    assert "unrecognized arguments: --allow-test-output-root" in result.stderr
